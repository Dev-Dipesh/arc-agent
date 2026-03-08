"""Remote MCP client for invoking Arc tools over SSE transport."""

from __future__ import annotations

import json
import os
from typing import Any

import anyio
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent


class MCPRemoteError(RuntimeError):
    """Remote MCP call failed."""


def _sse_url() -> str:
    raw = os.getenv("ARC_MCP_SSE_URL", "").strip()
    if not raw:
        return ""
    return raw if raw.endswith("/sse") else f"{raw.rstrip('/')}/sse"


def is_remote_mcp_enabled() -> bool:
    """Return true when remote MCP endpoint is configured."""
    return bool(_sse_url())


def _coerce_result_content(content: list[Any]) -> Any:
    if len(content) == 1 and isinstance(content[0], TextContent):
        text = content[0].text
        try:
            return json.loads(text)
        except Exception:
            return {"text": text}
    return [item.model_dump(mode="json") for item in content]


def _normalize_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
        return payload["result"]
    return payload


async def _call_tool_async(name: str, arguments: dict[str, Any]) -> Any:
    url = _sse_url()
    if not url:
        raise MCPRemoteError("ARC_MCP_SSE_URL is not configured.")

    headers: dict[str, Any] | None = None
    api_key = os.getenv("ARC_MCP_API_KEY", "").strip()
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with sse_client(url=url, headers=headers, timeout=10) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name=name, arguments=arguments)
    except Exception as e:
        raise MCPRemoteError(f"MCP call failed for '{name}': {e}") from e

    if result.isError:
        details = _coerce_result_content(result.content)
        raise MCPRemoteError(f"MCP tool '{name}' returned error: {details}")

    if result.structuredContent is not None:
        return _normalize_payload(result.structuredContent)
    return _normalize_payload(_coerce_result_content(result.content))


def call_remote_mcp_tool(name: str, **kwargs: Any) -> Any:
    """Invoke a remote MCP tool by name."""
    return anyio.run(_call_tool_async, name, kwargs)
