"""Local macOS bridge server that executes Arc tools on host."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from backend.tools.arc import (
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
from backend.tools.history import find_closed_tab, search_history


def _tool_table() -> dict[str, Any]:
    return {
        "list_spaces": lambda args: list_spaces(),
        "focus_space": lambda args: focus_space(args["space_id"]),
        "list_tabs": lambda args: list_tabs(args.get("space_id") or None),
        "find_tabs": lambda args: find_tabs(args["query"]),
        "find_duplicates": lambda args: find_duplicates(),
        "open_url": lambda args: open_url(args["url"], args.get("space_id") or None),
        "open_url_active_window": lambda args: open_url_active_window(args["url"]),
        "open_url_mini_window": lambda args: open_url_mini_window(args["url"], args["space_id"]),
        "close_tab": lambda args: close_tab(args["tab_id"]),
        "switch_to_tab": lambda args: switch_to_tab(args["tab_id"]),
        "reload_tab": lambda args: reload_tab(args["tab_id"]),
        "stop_tab": lambda args: stop_tab(args["tab_id"]),
        "navigate_tab": lambda args: navigate_tab(args["tab_id"], args["url"]),
        "go_back": lambda args: go_back(args["tab_id"]),
        "go_forward": lambda args: go_forward(args["tab_id"]),
        "read_page_content": lambda args: read_page_content(args["tab_id"]),
        "search_history": lambda args: search_history(args["query"], int(args.get("limit", 20))),
        "find_closed_tab": lambda args: find_closed_tab(args["query"]),
    }


class BridgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/tool":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        expected_key = os.getenv("ARC_BRIDGE_API_KEY", "").strip()
        if not expected_key:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "ARC_BRIDGE_API_KEY not set"})
            return

        got_key = self.headers.get("X-Arc-Bridge-Key", "")
        if got_key != expected_key:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
        except Exception:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        tool_name = str(data.get("tool", ""))
        args = data.get("args", {})
        if not isinstance(args, dict):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "args_must_be_object"})
            return

        table = _tool_table()
        fn = table.get(tool_name)
        if fn is None:
            self._json(HTTPStatus.BAD_REQUEST, {"error": f"unknown_tool: {tool_name}"})
            return

        try:
            result = fn(args)
            self._json(HTTPStatus.OK, {"ok": True, "result": result})
        except KeyError as e:
            self._json(HTTPStatus.BAD_REQUEST, {"error": f"missing_arg: {e}"})
        except Exception as e:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep bridge logs concise.
        return


def main() -> None:
    host = os.getenv("ARC_BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("ARC_BRIDGE_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), BridgeHandler)
    print(f"Arc bridge listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

