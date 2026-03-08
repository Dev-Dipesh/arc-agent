"""HTTP client for Arc bridge server."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class BridgeError(RuntimeError):
    """Bridge call failed."""


def is_bridge_enabled() -> bool:
    """Return true when bridge URL is configured."""
    return bool(os.getenv("ARC_BRIDGE_URL", "").strip())


def call_bridge_tool(name: str, **kwargs: Any) -> Any:
    """
    Call bridge tool endpoint.

    Expected env:
    - ARC_BRIDGE_URL: e.g. http://host.docker.internal:8765
    - ARC_BRIDGE_API_KEY: shared secret for bridge auth
    """
    base_url = os.getenv("ARC_BRIDGE_URL", "").strip().rstrip("/")
    if not base_url:
        raise BridgeError("ARC_BRIDGE_URL is not configured.")

    api_key = os.getenv("ARC_BRIDGE_API_KEY", "").strip()
    if not api_key:
        raise BridgeError("ARC_BRIDGE_API_KEY is not configured.")

    payload = json.dumps({"tool": name, "args": kwargs}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/tool",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Arc-Bridge-Key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise BridgeError(f"Bridge HTTP {e.code}: {e.reason}") from e
    except Exception as e:
        raise BridgeError(f"Bridge call failed: {e}") from e

    try:
        data = json.loads(raw)
    except Exception as e:
        raise BridgeError(f"Bridge returned invalid JSON: {raw[:200]}") from e

    if not isinstance(data, dict):
        raise BridgeError("Bridge response is not an object.")
    if "error" in data:
        raise BridgeError(str(data["error"]))
    return data.get("result")

