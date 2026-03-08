# Arc Agent — Build Plan

## Overview

A conversational AI agent that controls Arc browser on macOS. The user interacts through a chat UI; the agent translates natural language into AppleScript commands that manipulate Arc's tabs, spaces, and windows.

---

## Architecture

```
[agent-chat-ui]  ←→  [LangGraph Server]  ←→  [AppleScript → Arc]
  Next.js :3000        Python :2024
```

- **Frontend**: `agent-chat-ui` — pre-built Next.js chat interface that streams from any LangGraph server
- **Backend**: LangGraph agent with Arc browser tools exposed as LangChain tools
- **Browser control**: macOS `osascript` (AppleScript) — no extensions or CDP needed
- **Tracing**: LangSmith (already configured)

---

## Phase 1 — Backend (LangGraph Agent)

### 1.1 Project Setup

- Initialize with `uv` and `pyproject.toml`
- Dependencies: `langgraph`, `langchain`, `langchain-openai`, `langsmith`
- `langgraph.json` config pointing to the agent graph

### 1.2 Arc Tools (`backend/tools/arc.py`)

Each tool wraps an AppleScript command via `subprocess.run(["osascript", "-e", ...])`.

| Tool | AppleScript Target | Returns |
|------|--------------------|---------|
| `list_spaces` | `window 1 → every space` | List of space names + IDs |
| `list_tabs` | `space → every tab` | Tabs with title, URL, ID |
| `close_tab` | `close tab id X` | Confirmation |
| `switch_to_tab` | `tell tab X to select` | Confirmation |
| `move_tab_to_space` | `move tab to space` | Confirmation |
| `open_url` | `make new tab with URL` | New tab info |
| `find_tabs` | Search all tabs | Matching tabs |
| `reload_tab` | `reload tab` | Confirmation |

All tools return structured dicts. Errors are caught and returned as `{"error": "..."}` so the agent can report them gracefully.

### 1.3 Agent Graph (`backend/agent.py`)

- Simple ReAct agent using `create_react_agent` from LangGraph
- LLM: `gpt-4o` (OpenAI)
- System prompt: instructs the agent it controls Arc browser, defines available actions
- State: standard `MessagesState`
- Graph compiled and exported as `graph` (what `langgraph.json` references)

### 1.4 LangGraph Server Config (`backend/langgraph.json`)

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  }
}
```

Serves the graph at `http://localhost:2024` via `langgraph dev`.

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

### 3.1 System Prompt Tuning

- Make the agent proactive: when listing tabs, offer to organize
- Handle ambiguity: "close Twitter" should confirm if multiple Twitter tabs exist
- Format responses cleanly (markdown tables for tab lists)

### 3.2 Tool Robustness

- Handle Arc not running
- Handle spaces/tabs not found (fuzzy match on names)
- Handle AppleScript permission errors (Accessibility permissions)

### 3.3 Tracing

- LangSmith tracing enabled via env vars
- Project: `arc-agent`
- All tool calls and LLM interactions traced automatically

---

## File Structure (Final)

```
arc-agent/
├── .env
├── .env.example
├── .gitignore
├── AGENTS.md
├── docs/
│   └── plan/
│       └── plan.md
├── backend/
│   ├── pyproject.toml
│   ├── langgraph.json
│   ├── agent.py
│   └── tools/
│       ├── __init__.py
│       └── arc.py
└── frontend/           # agent-chat-ui (cloned via npx)
```

---

## Dev Workflow

```bash
# Terminal 1 — backend
cd backend && uv run langgraph dev

# Terminal 2 — frontend
cd frontend && pnpm dev
```

Open `http://localhost:3000`, connect to `http://localhost:2024` with graph ID `agent`.

---

## Mac Permissions Required

Arc must be granted **Automation** permission for the Terminal/IDE running the agent:
`System Settings → Privacy & Security → Automation → Terminal → Arc`
