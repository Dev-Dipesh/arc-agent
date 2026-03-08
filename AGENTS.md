# Arc Agent

An AI agent that controls Arc browser on macOS through natural language. Built with LangGraph (Python backend) and agent-chat-ui (Next.js frontend).

## Project Structure

```
arc-agent/
├── backend/              # LangGraph agent (Python)
│   ├── agent.py          # Graph definition and agent logic
│   ├── tools/
│   │   └── arc.py        # AppleScript-based Arc browser tools
│   ├── langgraph.json    # LangGraph server config
│   └── pyproject.toml
├── frontend/             # agent-chat-ui (Next.js)
└── docs/plan/            # Project planning docs
```

## Tech Stack

- **Backend**: Python, LangGraph, LangChain, OpenAI
- **Frontend**: Next.js, agent-chat-ui
- **Tracing**: LangSmith
- **Browser Control**: macOS AppleScript via `osascript`

## Arc Tools

| Tool | Description |
|------|-------------|
| `list_spaces` | List all Arc spaces |
| `list_tabs` | List tabs (all or by space) |
| `close_tab` | Close a tab by ID or title |
| `switch_to_tab` | Focus a specific tab |
| `move_tab_to_space` | Move a tab to a different space |
| `open_url` | Open a URL in Arc |
| `find_tabs` | Search tabs by title or URL |
| `reload_tab` | Reload a tab |

## Running Locally

```bash
# Backend (LangGraph server on :2024)
cd backend
uv run langgraph dev

# Frontend (on :3000)
cd frontend
pnpm dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:2024` and `NEXT_PUBLIC_ASSISTANT_ID=agent` in frontend `.env`.

## Environment

See `.env.example` for required variables. Copy to `.env` and fill in keys.
