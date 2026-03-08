# Arc Agent — Build Plan

## Overview

A conversational AI agent that controls Arc browser on macOS. The user interacts through a chat UI; the agent translates natural language into AppleScript commands that manipulate Arc's tabs, spaces, and windows.

---

## Architecture

```
[agent-chat-ui]  ←→  [LangGraph Server]  ←→  [AppleScript → Arc]
  Next.js :3000        Python :2024          [SQLite → Arc History]
```

- **Frontend**: `agent-chat-ui` — pre-built Next.js chat interface that streams from any LangGraph server
- **Backend**: LangGraph agent with Arc browser tools exposed as LangChain tools
- **Browser control**: macOS `osascript` (AppleScript) — no extensions or CDP needed
- **History access**: Direct SQLite read of Arc's Chromium history file
- **Tracing**: LangSmith
- **Memory**: LangGraph checkpointing for persistent conversation memory across sessions

> **UI isolation**: During dev/testing, open `localhost:3000` in Safari or Firefox — never in Arc, since the agent controls Arc and could accidentally close the tab. Post-launch: wrap with Tauri for a standalone macOS app.

---

## Arc Data Model (Important)

Tabs belong to **spaces**, not windows. Windows are viewports — any window can display any space. The agent queries spaces directly for tab data, not windows.

```
Application
└── Windows (viewports, 1–N, order: front to back)
    └── active space (one per window at a time)
└── Spaces (global, all windows share the same spaces)
    └── Tabs (belong to spaces, not windows)
        └── location: topApp | pinned | unpinned
```

Practical implication: to list all tabs, iterate spaces. To open a URL into a specific space, use `make new tab in space X`.

---

## Phase 1 — Backend (LangGraph Agent)

### 1.1 Project Setup

- Initialize with `uv` and `pyproject.toml`
- Dependencies: `langgraph`, `langchain`, `langchain-openai`, `langsmith`
- `langgraph.json` config pointing to the agent graph

### 1.2 Arc Tools (`backend/tools/arc.py`)

Capabilities verified against Arc's actual AppleScript dictionary (`sdef /Applications/Arc.app`).

**Spaces**

| Tool | AppleScript | Returns |
|------|-------------|---------|
| `list_spaces` | `every space` on any window | Space names + IDs |
| `focus_space` | `focus` on space | Confirmation |

**Tabs — Query**

| Tool | AppleScript | Returns |
|------|-------------|---------|
| `list_tabs` | `every tab` on a space (or all spaces) | Title, URL, ID, location, loading state |
| `find_tabs` | Iterate spaces/tabs, filter by title or URL | Matching tabs with space context |
| `find_duplicates` | Compare URLs across all spaces | Groups of duplicate tabs |

**Tabs — Actions**

| Tool | AppleScript | Notes |
|------|-------------|-------|
| `open_url` | `make new tab in space X` with URL | Opens into a specific space |
| `close_tab` | `close tab id X` | **HITL confirm before executing** |
| `switch_to_tab` | `select` on tab | Focuses the tab |
| `reload_tab` | `reload` on tab | — |
| `stop_tab` | `stop` on tab | — |
| `navigate_tab` | Set `URL` property on tab | Navigate existing tab to new URL |
| `go_back` | `go back` on tab | — |
| `go_forward` | `go forward` on tab | — |
| `set_tab_location` | Set `location`: `topApp`, `pinned`, `unpinned` | Sidebar position within space |

**JavaScript**

| Tool | Notes |
|------|-------|
| `read_page_content` | `execute javascript` — extracts readable text/content from active tab for summarisation |

**Not supported via AppleScript**
- Moving tabs between spaces (no API — workaround: open URL in target space, close original)
- Tab groups/folders within a space (not in Arc's AppleScript dictionary)
- Creating new spaces

**History (`backend/tools/history.py`)**

Arc stores history in a Chromium SQLite file:
`~/Library/Application Support/Arc/User Data/Default/History`

| Tool | Method | Returns |
|------|--------|---------|
| `search_history` | SQLite query on `urls` + `visits` tables | Title, URL, last visit time |
| `find_closed_tab` | Search history by title/URL | Matching past URLs to reopen |

> Copy the file before querying — SQLite WAL mode means the live file may be locked.

**HITL (Human in the Loop)**

Destructive actions (`close_tab`, bulk close) use LangGraph's `interrupt()` before execution. The agent presents what it will do and waits for user confirmation in the chat UI before proceeding.

All tools return structured dicts. Errors are caught and returned as `{"error": "..."}` so the agent can report them gracefully.

### 1.3 Agent Graph (`backend/agent.py`)

- ReAct agent using `create_react_agent` from LangGraph
- LLM: `gpt-4o`
- System prompt: instructs the agent on Arc's data model, available tools, and when to confirm before acting
- State: `MessagesState` with LangGraph checkpointing (SQLite checkpointer for local dev)
- Graph compiled and exported as `graph`

### 1.4 LangGraph Server Config (`backend/langgraph.json`)

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  }
}
```

Serves at `http://localhost:2024` via `langgraph dev`.

---

## Phase 2 — Frontend (agent-chat-ui)

### 2.1 Setup

```bash
npx create-agent-chat-app frontend
```

### 2.2 Configuration (`frontend/.env`)

```
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

No code changes needed — the UI connects to the LangGraph server out of the box.

---

## Phase 3 — Integration & Polish

### 3.1 System Prompt

- Explain Arc's data model (spaces own tabs, not windows)
- Define when to confirm vs. act (anything destructive = confirm)
- Format tab lists as markdown tables with space context
- Be proactive: after listing, offer to act (find dupes, close stale tabs, etc.)

### 3.2 Tool Robustness

- Handle Arc not running
- Fuzzy match on space/tab names (user says "Dev space", not exact ID)
- Copy SQLite history file before reading (avoid lock conflicts)
- Handle AppleScript Automation permission errors with a clear user message

### 3.3 Tracing

LangSmith tracing is on by default via env vars. All tool calls, LLM turns, and interrupts are traced automatically under the `arc-agent` project.

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
│   ├── agent.py
│   └── tools/
│       ├── __init__.py
│       ├── arc.py        # AppleScript tools
│       └── history.py    # SQLite history tools
└── frontend/             # agent-chat-ui (via npx)
```

---

## Dev Workflow

```bash
# Terminal 1 — backend
cd backend && uv run langgraph dev

# Terminal 2 — frontend
cd frontend && pnpm dev
```

Open `http://localhost:3000` in Safari/Firefox. Connect to `http://localhost:2024`, graph ID `agent`.

---

## Mac Permissions Required

- **Automation**: `System Settings → Privacy & Security → Automation → Terminal → Arc`
- **Full Disk Access** (for history SQLite): may be required depending on macOS version
