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

## Code Quality

All Python code must include type hints and return types:

```python
def list_tabs(space_id: str | None = None) -> list[dict]:
    """List tabs in Arc, optionally filtered by space.

    Args:
        space_id: The space to filter by, or None for all spaces.

    Returns:
        List of tab dicts with id, title, and url.
    """
```

- Types go in function signatures, not in docstrings.
- Use Google-style docstrings with an Args section for all public functions.
- Focus on "why" over "what" in descriptions.
- Use descriptive, self-explanatory variable names.
- Break complex functions (>20 lines) into smaller, focused functions where it makes sense.

## Linting

Prefer inline `# noqa: RULE` over `[tool.ruff.lint.per-file-ignores]` for individual exceptions. `per-file-ignores` silences a rule for the entire file — one exception can hide future violations silently. Inline `# noqa` is precise and self-documenting.

Reserve `per-file-ignores` for categorical policy that applies to a whole class of files (e.g., tests don't need docstrings).

```python
# Good
script = build_script(tab_id)  # noqa: S603  # input is sanitised above

# Bad — hides all S603 violations in the file
# [tool.ruff.lint.per-file-ignores]
# "backend/tools/arc.py" = ["S603"]
```

## Security

- No `eval()`, `exec()`, or `pickle` on user-controlled input.
- No bare `except:` — always catch specific exceptions and use a `msg` variable for error messages.
- Remove unreachable or commented-out code before committing.
- Defer heavy imports (e.g., `subprocess`, `osascript` wrappers) to the point of use, not module level.

## Testing

Mirror source structure under `tests/`:

```txt
tests/
└── unit_tests/
    └── tools/
        └── test_arc.py   # mirrors backend/tools/arc.py
```

- Unit tests: no network or AppleScript calls — mock `osascript` at the boundary.
- Test actual implementation; don't duplicate logic inside tests.
- Cover edge cases and error conditions.

## Commit Messages

- Keep commit messages clean — no AI branding, attribution lines, or co-author footers.
- Format: `type: short description` (conventional commits style).
- Body is optional; use it only when the why isn't obvious from the subject.

## Collaboration Safety

- Do not remove unknown or untracked files unless the user explicitly asks for deletion.
- If cleanup is needed, list candidate files first and get user confirmation before deleting.

## Multi-Agent Safety

When multiple agents may be running concurrently:

- Do not create, apply, or drop `git stash` entries unless explicitly requested.
- Do not switch branches unless explicitly requested.
- Do not create or remove `git worktree` checkouts unless explicitly requested.
- When committing, scope to your own changes only. "Commit all" means commit everything in grouped chunks.
- When you see unrecognized files, keep going — focus on your changes only.

## Agent Behaviour

- Respond with high-confidence answers only: verify in code before answering; do not guess.
- Lint/format-only diffs: auto-resolve without asking. If a commit was already requested, include formatting fixes in the same commit or a small follow-up — no extra confirmation needed. Only ask when changes are semantic.
- When finishing work on a GitHub Issue or PR, print the full URL at the end.
