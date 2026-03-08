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

## Contributing Ideas

The current control layer is AppleScript-only. Each method covers different ground — they're complementary, not competing:

| Capability | AppleScript | CDP (Chromium DevTools) | Browser Extension API |
|---|---|---|---|
| List/switch spaces | ✓ | — | — |
| List/open/close tabs | ✓ | ✓ | ✓ |
| Pin/unpin tabs | ✗ (Arc bug) | ✗ | ✓ |
| Read page DOM/text | — | ✓ | ✓ |
| Execute JavaScript | — | ✓ | ✓ |
| Screenshot a tab | — | ✓ | — |
| Intercept network | — | ✓ | ✓ |
| History/bookmarks | ✓ (partial) | — | ✓ |

**CDP layer** — Arc is Chromium-based. Launching it with `--remote-debugging-port=9222` exposes a WebSocket API (`ws://localhost:9222`) that allows JS execution, DOM inspection, screenshots, and network interception per tab. Useful for deep page interaction the agent currently can't do.

**Chrome extension bridge** — A small extension installed in Arc can expose a local HTTP endpoint and use `chrome.tabs.update({pinned: true})` and other extension APIs that neither AppleScript nor CDP can reach. This is the only reliable path to tab pinning until Arc fixes their AppleScript setter.

**Firefox/cross-browser support** — The MCP server (`backend/mcp_server.py`) and tool registry (`backend/tool_registry.py`) are browser-agnostic by design. A Firefox variant could use `browser.tabs` WebExtension APIs directly, enabling the same agent to work across browsers.

## Commit Messages

- Keep commit messages clean — no AI branding, attribution lines, or co-author footers.
- Format: `type: short description` (conventional commits style).
- Body is optional; use it only when the why isn't obvious from the subject.

## Collaboration Safety

- Do not remove unknown or untracked files unless the user explicitly asks for deletion.
- If cleanup is needed, list candidate files first and get user confirmation before deleting.
