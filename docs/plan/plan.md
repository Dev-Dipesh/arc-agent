# Arc Agent — Build Plan

## Overview

A conversational AI agent that controls Arc browser on macOS. The user interacts through a chat UI; the agent translates natural language into AppleScript commands that manipulate Arc's tabs, spaces, and windows.

---

## Architecture

```
Arc Browser
    ↑
AppleScript (osascript) + SQLite (history)
    ↑
backend/tools/          ← pure Python, no framework deps
    ↑
backend/mcp_server.py   ← FastMCP wraps all tools
    ↑
├── Claude Code         ← test during development (stdio transport)
├── LangGraph agent     ← imports tools directly (no MCP overhead)
└── mcp.so / remote     ← hosted MCP for third-party use (SSE transport)
    ↑
agent-chat-ui           ← chat interface connected to LangGraph server
```

**Tools are defined once as plain Python functions. The MCP server and the LangGraph agent both use the same underlying functions — no duplication, no round-trip overhead in production.**

---

## Arc Data Model

Tabs belong to **spaces**, not windows. Windows are viewports — any window can display any space.

```
Application
└── Spaces (global)
    └── Tabs
        └── location: topApp | pinned | unpinned
└── Windows (viewports, 1–N)
    └── active space (one per window at a time)
```

Practical implication: query spaces directly for tab data. To open a URL into a specific space: `make new tab in space X`.

---

## Build Phases

### Phase 1 — Tools (pure Python)

`backend/tools/arc.py` — AppleScript wrappers via `subprocess.run(["osascript", ...])`.
`backend/tools/history.py` — SQLite reader for Arc's Chromium history file.

All functions return plain dicts. Errors returned as `{"error": "..."}`.

**Spaces**

| Function                | AppleScript             | Returns         |
| ----------------------- | ----------------------- | --------------- |
| `list_spaces()`         | `every space` on window | `[{id, title}]` |
| `focus_space(space_id)` | `focus` on space        | confirmation    |

**Tabs — Query**

| Function               | AppleScript                | Returns                                        |
| ---------------------- | -------------------------- | ---------------------------------------------- |
| `list_tabs(space_id?)` | `every tab` on space(s)    | `[{id, title, url, location, loading, space}]` |
| `find_tabs(query)`     | iterate + filter           | matching tabs with space context               |
| `find_duplicates()`    | compare URLs across spaces | groups of duplicate tabs                       |

**Tabs — Actions**

| Function                             | AppleScript             | Notes                           |
| ------------------------------------ | ----------------------- | ------------------------------- |
| `open_url_active_window(url)`        | `make new tab` on `window 1` | opens directly in active space |
| `open_url_mini_window(url, space_id)`| `make new tab in target space` | may show Arc mini-window handoff |
| `open_url(url, space_id?)`           | compatibility alias     | no `space_id` -> active, with `space_id` -> mini-window path |
| `close_tab(tab_id)`                  | `close tab id X`        | HITL confirm before calling     |
| `switch_to_tab(tab_id)`              | `select` on tab         | —                               |
| `reload_tab(tab_id)`                 | `reload` on tab         | —                               |
| `stop_tab(tab_id)`                   | `stop` on tab           | —                               |
| `navigate_tab(tab_id, url)`          | set `URL` on tab        | navigate existing tab           |
| `go_back(tab_id)`                    | `go back` on tab        | —                               |
| `go_forward(tab_id)`                 | `go forward` on tab     | —                               |
| `set_tab_location(tab_id, location)` | set `location` property | `topApp`, `pinned`, `unpinned`  |

**JavaScript**

| Function                    | Notes                                                           |
| --------------------------- | --------------------------------------------------------------- |
| `read_page_content(tab_id)` | `execute javascript` — extracts readable text for summarisation |

**History**

Arc's history: `~/Library/Application Support/Arc/User Data/Default/History` (Chromium SQLite).
Copy before reading to avoid WAL lock.

| Function                        | Returns                      |
| ------------------------------- | ---------------------------- |
| `search_history(query, limit?)` | `[{title, url, last_visit}]` |
| `find_closed_tab(query)`        | matching past URLs to reopen |

**Not supported**

- Moving tabs between spaces (workaround: `open_url` in target space + `close_tab` original)
- Tab groups/folders within a space
- Creating or deleting spaces

**Open mode guidance**

- `active_window` mode is more stable and opens tabs directly in the currently focused Arc window/space.
- `mini_window` mode preserves multi-window focus context and uses Arc's mini-window handoff UX for target space flows.
- Because Arc AppleScript behavior can vary by window/session state, keep both paths available and let the user choose.

---

### Phase 2 — MCP Server

`backend/mcp_server.py` — FastMCP server wrapping all Phase 1 functions.

```python
from mcp.server.fastmcp import FastMCP
from tools.arc import list_spaces, list_tabs, ...
from tools.history import search_history, ...

mcp = FastMCP("arc-browser")

@mcp.tool()
def list_spaces_tool() -> list[dict]:
    """List all Arc spaces"""
    return list_spaces()
# ... etc
```

**Transports**

- `stdio` — for Claude Code and local MCP clients
- `sse` — for hosting on mcp.so or remote agents

**Open URL tools (explicit modes)**

- `arc_open_url_active_window(url)` — open directly in active window (default/recommended)
- `arc_open_url_mini_window(url, space_id)` — use Arc target-space path (mini-window capable)
- `arc_open_url(url, space_id?)` — backward-compatible alias

**Claude Code integration** (for testing Phase 2 before building the agent):

```json
// .claude/settings.json
{
  "mcpServers": {
    "arc": {
      "command": "uv",
      "args": ["run", "python", "backend/mcp_server.py"],
      "cwd": "/path/to/arc-agent"
    }
  }
}
```

Once connected, Claude Code can call Arc tools directly to verify everything works end-to-end before wiring up LangGraph.

---

### Phase 3 — LangGraph Agent

`backend/agent.py` — imports tool functions directly (not via MCP).

- ReAct agent via `create_react_agent`
- LLM: `gpt-5o-mini`
- Tools: LangChain `@tool` wrappers around Phase 1 functions
- HITL: `interrupt()` before `close_tab` or any bulk destructive action. Use langchain node-style middleware instead of custome building it
- Memory: SQLite checkpointer for persistent conversation across sessions
- System prompt covers Arc's data model, confirmation behaviour, response formatting
- Runtime preference state (conversation/session): `open_mode = active_window | mini_window`
- Routing policy:
  - Default to `active_window` for reliability
  - If user asks for mini-window behavior, route to `open_url_mini_window`
  - Allow explicit one-shot override per request (e.g., "open this one directly")
  - Persist user preference after explicit confirmation ("Use this as default")

`backend/langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./agent.py:graph" }
}
```

Serves at `http://localhost:2024` via `langgraph dev`.

---

### Phase 4 — Frontend

```bash
npx create-agent-chat-app frontend
```

`frontend/.env`

```
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

No code changes needed. Open in Safari/Firefox (not Arc).

---

### Phase 5 — Polish & Hosting

- Tune system prompt: proactive suggestions after listing tabs, smart duplicate handling
- Fuzzy match on space/tab names
- Handle Arc not running, AppleScript permission errors
- SSE transport for MCP server → publish to mcp.so

**Packaging (required before mcp.so)**

Currently the MCP server runs as a plain script via `uv --directory backend run python mcp_server.py`. To publish to mcp.so or allow `uvx` installs, the backend needs to be a proper Python package:

1. Add a build backend to `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
arc-mcp = "mcp_server:main"
```

2. Add `tool.uv.package = true` so uv installs entry points
3. Then `.mcp.json` can use `uvx` like any other published MCP server:

```json
{ "command": "uvx", "args": ["arc-mcp"] }
```

4. Publish to PyPI: `uv publish`
5. Register on mcp.so

---

## File Structure

```
arc-agent/
├── .env
├── .env.example
├── .gitignore
├── AGENTS.md
├── docs/plan/plan.md
├── backend/
│   ├── pyproject.toml
│   ├── langgraph.json
│   ├── mcp_server.py       ← Phase 2
│   ├── agent.py            ← Phase 3
│   └── tools/
│       ├── __init__.py
│       ├── arc.py          ← Phase 1
│       └── history.py      ← Phase 1
└── frontend/               ← Phase 4 (agent-chat-ui via npx)
```

---

## Dev Workflow

```bash
# Phase 2 test — MCP in Claude Code (add to .claude/settings.json, restart)
uv run python backend/mcp_server.py

# Phase 3+4 — full stack
cd backend && uv run langgraph dev      # Terminal 1
cd frontend && pnpm dev                  # Terminal 2
```

---

## Mac Permissions Required

- **Automation**: `System Settings → Privacy & Security → Automation → Terminal → Arc`
- **Full Disk Access**: may be required for reading Arc's history SQLite file
