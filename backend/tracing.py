"""Tracing adapter for LangGraph/LangChain runtime."""

from __future__ import annotations

import json
import os
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class JsonlTraceHandler(BaseCallbackHandler):
    """Write concise runtime trace events to a local JSONL file."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, payload: dict[str, Any]) -> None:
        payload["ts"] = datetime.now(UTC).isoformat()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def on_chat_model_start(self, serialized: Any, messages: Any, **kwargs: Any) -> None:
        model = ""
        if isinstance(serialized, dict):
            model = str(serialized.get("name", ""))
        self._write({"event": "chat_model_start", "model": model, "extra": kwargs})

    def on_chat_model_end(self, response: Any, **kwargs: Any) -> None:
        self._write({"event": "chat_model_end", "extra": kwargs})

    def on_chat_model_error(self, error: BaseException, **kwargs: Any) -> None:
        self._write({"event": "chat_model_error", "error": str(error), "extra": kwargs})

    def on_tool_start(self, serialized: Any, input_str: str, **kwargs: Any) -> None:
        name = ""
        if isinstance(serialized, dict):
            name = str(serialized.get("name", ""))
        self._write({"event": "tool_start", "tool": name, "input": input_str})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self._write({"event": "tool_end", "output_preview": str(output)[:500]})

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self._write({"event": "tool_error", "error": str(error)})


def get_tracing_callbacks() -> list[BaseCallbackHandler]:
    """
    Return callback handlers based on TRACING_BACKEND.

    Supported:
    - langsmith: rely on LANGSMITH_* env and LangSmith native instrumentation
    - langfuse: attach Langfuse callback handler (if installed/configured)
    - jsonl: write local runtime traces to TRACE_JSONL_PATH
    - none: disable all tracing callbacks
    """
    backend = os.getenv("TRACING_BACKEND", "langsmith").strip().lower()
    callbacks: list[BaseCallbackHandler] = []

    if backend == "none":
        os.environ["LANGSMITH_TRACING"] = "false"
        return callbacks

    if backend == "langsmith":
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        return callbacks

    if backend == "langfuse":
        os.environ["LANGSMITH_TRACING"] = "false"
        try:
            try:
                from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
            except Exception:
                from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
        except Exception:
            warnings.warn(
                "TRACING_BACKEND=langfuse but 'langfuse' package is not installed. "
                "Tracing will be disabled.",
                stacklevel=2,
            )
            return callbacks

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")
        if not public_key or not secret_key:
            warnings.warn(
                "TRACING_BACKEND=langfuse but LANGFUSE_PUBLIC_KEY/SECRET_KEY are missing. "
                "Tracing will be disabled.",
                stacklevel=2,
            )
            return callbacks

        # langfuse callback APIs vary by version; prefer env-based secret/host wiring.
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
        if host:
            os.environ.setdefault("LANGFUSE_HOST", host)
        callbacks.append(LangfuseCallbackHandler(public_key=public_key))
        return callbacks

    if backend == "jsonl":
        os.environ["LANGSMITH_TRACING"] = "false"
        trace_path = os.getenv("TRACE_JSONL_PATH", "./traces/agent-runtime.jsonl")
        callbacks.append(JsonlTraceHandler(trace_path))
        return callbacks

    warnings.warn(
        f"Unknown TRACING_BACKEND='{backend}'. Falling back to no callbacks.",
        stacklevel=2,
    )
    os.environ["LANGSMITH_TRACING"] = "false"
    return callbacks
