"""LangGraph agent for Arc browser control (Phase 3)."""

import atexit
import os
import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

from tools.arc import (
    close_tab,
    find_duplicates,
    find_tabs,
    focus_space,
    go_back,
    go_forward,
    list_spaces,
    list_tabs,
    navigate_tab,
    open_url,
    open_url_active_window,
    open_url_mini_window,
    read_page_content,
    reload_tab,
    stop_tab,
    switch_to_tab,
)
from tools.history import find_closed_tab, search_history

CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "langgraph.db")
PREFERENCES_DB_PATH = os.getenv("PREFERENCES_DB_PATH", ".arc_agent_prefs.sqlite")
DEFAULT_OPEN_MODE = os.getenv("DEFAULT_OPEN_MODE", "active_window")

SYSTEM_PROMPT = """
You are Arc Agent, an assistant that controls Arc browser on macOS.

Rules:
- Tabs belong to spaces; use space context when needed.
- Call list_spaces before space-specific operations if space identity is ambiguous.
- Use open mode preference for generic "open URL" requests:
  - active_window: open directly in currently active Arc window.
  - mini_window: use Arc target-space path (mini-window handoff behavior).
- Ask for explicit confirmation before destructive actions.
- For close_tab tool, a runtime interrupt confirmation is required.
- Be concise and include tab IDs when proposing follow-up tab actions.
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


@tool
def list_spaces_tool() -> list[dict]:
    """List all Arc spaces with IDs and titles."""
    return list_spaces()


@tool
def focus_space_tool(space_id: str) -> dict:
    """Focus/switch to an Arc space by space ID."""
    return focus_space(space_id)


@tool
def list_tabs_tool(space_id: str = "") -> list[dict]:
    """List Arc tabs. Provide optional space_id to filter to one space."""
    return list_tabs(space_id or None)


@tool
def find_tabs_tool(query: str) -> list[dict]:
    """Find open tabs by title or URL substring (case-insensitive)."""
    return find_tabs(query)


@tool
def find_duplicates_tool() -> list[list[dict]]:
    """Find duplicate open tabs by URL across spaces."""
    return find_duplicates()


@tool
def set_open_mode_preference(
    mode: str, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Set default open mode preference for this conversation thread: active_window or mini_window."""
    if mode not in {"active_window", "mini_window"}:
        return {"error": "Invalid mode. Use 'active_window' or 'mini_window'."}
    thread_id = _thread_id(config)
    _set_preference(thread_id, "open_mode", mode)
    return {"ok": True, "thread_id": thread_id, "open_mode": mode}


@tool
def get_open_mode_preference(config: RunnableConfig | None = None) -> dict[str, Any]:
    """Get current open mode preference for this conversation thread."""
    thread_id = _thread_id(config)
    mode = _get_preference(thread_id, "open_mode") or DEFAULT_OPEN_MODE
    return {"ok": True, "thread_id": thread_id, "open_mode": mode}


@tool
def open_url_tool(
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
        return open_url_active_window(url)
    if selected_mode == "mini_window":
        if not space_id:
            return {"error": "space_id is required for mini_window mode."}
        return open_url_mini_window(url, space_id)
    return {"error": "Invalid mode. Use 'active_window' or 'mini_window'."}


@tool
def open_url_active_window_tool(url: str) -> dict:
    """Open URL directly in the active Arc window/space."""
    return open_url_active_window(url)


@tool
def open_url_mini_window_tool(url: str, space_id: str) -> dict:
    """Open URL using Arc target-space path (mini-window handoff behavior)."""
    return open_url_mini_window(url, space_id)


@tool
def open_url_legacy_tool(url: str, space_id: str = "") -> dict:
    """Legacy open_url behavior for compatibility."""
    return open_url(url, space_id or None)


@tool
def close_tab_tool(tab_id: str) -> dict:
    """Close a tab by ID (requires interrupt confirmation)."""
    response = interrupt(
        {
            "action": "close_tab",
            "tab_id": tab_id,
            "question": f"Confirm closing tab {tab_id}?",
            "instructions": "Resume with true/yes to approve, otherwise false/no to cancel.",
        }
    )

    approved = False
    if isinstance(response, bool):
        approved = response
    elif isinstance(response, str):
        approved = response.strip().lower() in {"yes", "y", "true", "approve", "approved"}
    elif isinstance(response, dict):
        approved = bool(response.get("approved"))

    if not approved:
        return {"ok": False, "cancelled": True, "tab_id": tab_id}

    return close_tab(tab_id)


@tool
def switch_to_tab_tool(tab_id: str) -> dict:
    """Switch/focus a tab by ID."""
    return switch_to_tab(tab_id)


@tool
def reload_tab_tool(tab_id: str) -> dict:
    """Reload a tab by ID."""
    return reload_tab(tab_id)


@tool
def stop_tab_tool(tab_id: str) -> dict:
    """Stop a tab load by ID."""
    return stop_tab(tab_id)


@tool
def navigate_tab_tool(tab_id: str, url: str) -> dict:
    """Navigate an existing tab to URL."""
    return navigate_tab(tab_id, url)


@tool
def go_back_tool(tab_id: str) -> dict:
    """Go back in tab history for tab ID."""
    return go_back(tab_id)


@tool
def go_forward_tool(tab_id: str) -> dict:
    """Go forward in tab history for tab ID."""
    return go_forward(tab_id)


@tool
def read_page_content_tool(tab_id: str) -> dict:
    """Read text content from a tab (title + extracted content)."""
    return read_page_content(tab_id)


@tool
def search_history_tool(query: str, limit: int = 20) -> list[dict]:
    """Search Arc browsing history by query."""
    return search_history(query, limit)


@tool
def find_closed_tab_tool(query: str) -> list[dict]:
    """Find possibly-closed tabs from browsing history."""
    return find_closed_tab(query)


TOOLS = [
    list_spaces_tool,
    focus_space_tool,
    list_tabs_tool,
    find_tabs_tool,
    find_duplicates_tool,
    set_open_mode_preference,
    get_open_mode_preference,
    open_url_tool,
    open_url_active_window_tool,
    open_url_mini_window_tool,
    open_url_legacy_tool,
    close_tab_tool,
    switch_to_tab_tool,
    reload_tab_tool,
    stop_tab_tool,
    navigate_tab_tool,
    go_back_tool,
    go_forward_tool,
    read_page_content_tool,
    search_history_tool,
    find_closed_tab_tool,
]


_checkpoint_path = str(Path(CHECKPOINT_DB_PATH))
_checkpointer_cm = SqliteSaver.from_conn_string(_checkpoint_path)
checkpointer = _checkpointer_cm.__enter__()
atexit.register(lambda: _checkpointer_cm.__exit__(None, None, None))

model_name = os.getenv("LLM_MODEL", "gpt-5o-mini")
model = ChatOpenAI(model=model_name, temperature=0)

graph = create_react_agent(
    model=model,
    tools=TOOLS,
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
    name="agent",
)
