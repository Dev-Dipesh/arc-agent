"""LangGraph agent for Arc browser control (Phase 3)."""

import os
import sqlite3
from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from token_limit_middleware import TokenLimitWarningMiddleware
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from tracing import get_tracing_callbacks
from tool_registry import (
    arc_open_url,
    arc_open_url_active_window,
    arc_open_url_mini_window,
    build_langgraph_tools,
)

PREFERENCES_DB_PATH = os.getenv("PREFERENCES_DB_PATH", ".arc_agent_prefs.sqlite")
DEFAULT_OPEN_MODE = os.getenv("DEFAULT_OPEN_MODE", "mini_window")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4.1-mini")
SUMMARY_TRIGGER_TOKENS = int(os.getenv("SUMMARY_TRIGGER_TOKENS", "80000"))
SUMMARY_TRIGGER_MESSAGES = int(os.getenv("SUMMARY_TRIGGER_MESSAGES", "120"))
SUMMARY_KEEP_MESSAGES = int(os.getenv("SUMMARY_KEEP_MESSAGES", "60"))
TOOL_CALL_THREAD_LIMIT = int(os.getenv("TOOL_CALL_THREAD_LIMIT", "200"))
TOOL_CALL_RUN_LIMIT = int(os.getenv("TOOL_CALL_RUN_LIMIT", "40"))

SYSTEM_PROMPT = """
You are Arc Agent, an assistant that controls Arc browser on macOS.

Rules:
- Tabs belong to spaces; use space context when needed.
- Call arc_list_spaces before space-specific operations if space identity is ambiguous.
- Use open mode preference for generic "open URL" requests:
  - active_window: open directly in currently active Arc window.
- mini_window: use Arc target-space path (mini-window handoff behavior).
- Ask for explicit confirmation before destructive actions. Middleware enforces HITL for arc_close_tab.
- Response formatting:
  - Default: do not list tab IDs in informational summaries.
  - Prefer concise counts and space/tab titles.
  - For follow-up actions, ask/use natural-language references first (title, URL, space, recency, ordinal).
  - Do not include sample IDs unless the user explicitly asks for IDs.
  - Only provide full tab IDs when explicitly requested.
""".strip()


def _thread_id(config: RunnableConfig | None) -> str:
    if not config:
        return "default"
    configurable = config.get("configurable", {})
    return str(configurable.get("thread_id", "default"))


def _ensure_preferences_db() -> None:
    with sqlite3.connect(PREFERENCES_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                thread_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (thread_id, key)
            )
            """
        )
        conn.commit()


def _get_preference(thread_id: str, key: str) -> str | None:
    _ensure_preferences_db()
    with sqlite3.connect(PREFERENCES_DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM user_preferences WHERE thread_id = ? AND key = ?",
            (thread_id, key),
        ).fetchone()
    return None if row is None else str(row[0])


def _set_preference(thread_id: str, key: str, value: str) -> None:
    _ensure_preferences_db()
    with sqlite3.connect(PREFERENCES_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (thread_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(thread_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (thread_id, key, value),
        )
        conn.commit()


@tool("set_open_mode_preference")
def set_open_mode_preference(
    mode: str, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Set default open mode preference for this conversation thread: active_window or mini_window."""
    if mode not in {"active_window", "mini_window"}:
        return {"error": "Invalid mode. Use 'active_window' or 'mini_window'."}
    thread_id = _thread_id(config)
    _set_preference(thread_id, "open_mode", mode)
    return {"ok": True, "thread_id": thread_id, "open_mode": mode}


@tool("get_open_mode_preference")
def get_open_mode_preference(config: RunnableConfig | None = None) -> dict[str, Any]:
    """Get current open mode preference for this conversation thread."""
    thread_id = _thread_id(config)
    mode = _get_preference(thread_id, "open_mode") or DEFAULT_OPEN_MODE
    return {"ok": True, "thread_id": thread_id, "open_mode": mode}


@tool("arc_open_url")
def open_url_with_preference(
    url: str,
    space_id: str = "",
    mode: str = "",
    config: RunnableConfig | None = None,
) -> dict:
    """
    Open URL with preference-aware routing.
    mode can be:
    - active_window
    - mini_window
    If mode is empty, use thread preference (or default).
    """
    selected_mode = mode.strip()
    if not selected_mode:
        thread_id = _thread_id(config)
        selected_mode = _get_preference(thread_id, "open_mode") or DEFAULT_OPEN_MODE

    if selected_mode == "active_window":
        return arc_open_url_active_window(url)
    if selected_mode == "mini_window":
        if not space_id:
            return {"error": "space_id is required for mini_window mode."}
        return arc_open_url_mini_window(url, space_id)
    return {"error": "Invalid mode. Use 'active_window' or 'mini_window'."}


@tool("arc_open_url_legacy")
def open_url_legacy_tool(url: str, space_id: str = "") -> dict:
    """Legacy open_url behavior for compatibility."""
    return arc_open_url(url, space_id or "")


TOOLS = build_langgraph_tools(exclude={"arc_open_url"}) + [
    set_open_mode_preference,
    get_open_mode_preference,
    open_url_with_preference,
    open_url_legacy_tool,
]

callbacks = get_tracing_callbacks()

model_name = os.getenv("LLM_MODEL", "gpt-5-nano")
model = ChatOpenAI(model=model_name, temperature=0, callbacks=callbacks)

class ArcAgentState(AgentState):
    """Agent state extension hook for future fields."""


graph = create_agent(
    model=model,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=None,  # LangGraph runtime manages persistence in dev/server mode.
    state_schema=ArcAgentState,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "arc_close_tab": {"allowed_decisions": ["approve", "reject"]},
            },
            description_prefix="Arc action requires approval",
        ),
        TokenLimitWarningMiddleware(
            model=SUMMARY_MODEL,
            trigger=[
                ("tokens", SUMMARY_TRIGGER_TOKENS),
                ("messages", SUMMARY_TRIGGER_MESSAGES),
            ],
            keep=("messages", SUMMARY_KEEP_MESSAGES),
        ),
        ToolCallLimitMiddleware(
            thread_limit=TOOL_CALL_THREAD_LIMIT,
            run_limit=TOOL_CALL_RUN_LIMIT,
        ),
        ToolRetryMiddleware(
            max_retries=2,
            backoff_factor=2.0,
            initial_delay=0.5,
        ),
    ],
    name="agent",
)
