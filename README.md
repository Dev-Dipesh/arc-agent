# Arc Agent

Natural-language Arc browser control on macOS using:

- Python backend (LangGraph + LangChain)
- Next.js chat frontend
- Host-local MCP server for AppleScript tool execution

## What This Project Does

Arc Agent lets you chat with an agent that can:

- list spaces/tabs
- open/navigate/reload/switch/close tabs
- read page content
- query Arc history

The backend runs in LangGraph; browser automation runs on the host Mac through an MCP server, since AppleScript cannot execute Arc inside containers.

## Architecture

- `backend/`: LangGraph agent, tools, tracing, tool registry
- `backend/mcp_server.py`: host MCP server that executes Arc tools locally
- `frontend/`: chat UI (Next.js)
- `docker/compose.yml`: frontend + postgres addon services

## Run Modes

### Full stack (recommended)

```bash
make stack-up
```

Starts:

- host MCP server (SSE transport)
- LangGraph backend (`langgraph up`)
- frontend container
- postgres container

### Bring everything down

1. Press `Ctrl+C` in the terminal running `make stack-up` (stops host MCP server + backend process).
2. Run:

```bash
make compose-down
```

This stops frontend + postgres containers.

## Important Notes for `make stack-up`

You may see:

- `For local dev, requires env var LANGSMITH_API_KEY with access to LangSmith Deployment.`
- `For production use, requires a license key in env var LANGGRAPH_CLOUD_LICENSE_KEY.`

What this means:

- This message is emitted by the `langgraph up` runtime startup path.
- You can still use LangSmith tracing separately via your configured tracing backend.
- For this local project workflow, keep your required env vars in `.env` as documented in `.env.example`.

You may also see:

- `Security Recommendation: Consider switching to Wolfi Linux ...`

This is a recommendation, not a blocker. The current setup can run without switching image distro.

## Environment

Copy and fill environment values:

```bash
cp .env.example .env
```

Minimum keys to run:

- `OPENAI_API_KEY`
- `ARC_MCP_SSE_URL_DOCKER` (defaults are provided in `.env.example`)
- `POSTGRES_URI_DOCKER` (or `POSTGRES_URI`)
- frontend vars (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ASSISTANT_ID`) are prefilled with defaults

## Security

This project is currently designed for personal/local use on a trusted machine.
In that mode, many SaaS-style hardening controls are optional because:

- the Arc automation surface is your own host
- services are expected to be on localhost/private Docker network
- there is no multi-tenant user model

If you host this beyond personal local use (shared network, remote access, cloud VM), add security controls before exposing it:

- app-level authentication and authorization for MCP/API access
- strict network allowlists/ACLs (least privilege)
- private connectivity (for example, Tailscale/private VPN) instead of public exposure
- TLS termination and secret management
- request rate limits, audit logging, and rotation of credentials
- non-root containers and hardened runtime images (for example, Wolfi)

## System Diagrams (Overall Scope)

### 1) Deployment and system boundaries

![Arc Agent deployment and boundaries](docs/script/diagrams/arc-agent-1.png)

### 2) End-to-end interaction sequence

![Arc Agent end-to-end sequence](docs/script/diagrams/arc-agent-2.png)

Backend-specific diagrams (thread lifecycle, internal running flow, persistence responsibilities) are documented in [backend/README.md](/Users/dipesh/Local-Projects/arc-agent/backend/README.md).
