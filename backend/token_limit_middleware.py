from __future__ import annotations

from typing import Any

from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.middleware.summarization import REMOVE_ALL_MESSAGES
from langchain_core.messages import RemoveMessage
from langgraph.types import interrupt


class TokenLimitWarningMiddleware(SummarizationMiddleware):
    """Interrupt before summarizing to let the user decide: summarize or start a new chat.

    Instead of automatically compressing context (which loses precise identifiers like
    tab IDs that this agent relies on), this middleware pauses and asks the user whether
    to summarize now or start a fresh thread.
    """

    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        self._ensure_message_ids(messages)

        total_tokens = self.token_counter(messages)
        if not self._should_summarize(messages, total_tokens):
            return None

        decision = interrupt({
            "type": "token_limit_warning",
            "token_count": total_tokens,
        })

        if decision.get("action") != "summarize":
            # User chose to start a new chat — handled on the frontend, nothing to do here
            return None

        # User chose to summarize — run the same logic as SummarizationMiddleware
        cutoff_index = self._determine_cutoff_index(messages)
        if cutoff_index <= 0:
            return None

        messages_to_summarize, preserved_messages = self._partition_messages(
            messages, cutoff_index
        )
        summary = self._create_summary(messages_to_summarize)
        new_messages = self._build_new_messages(summary)

        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *new_messages,
                *preserved_messages,
            ]
        }

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.before_model(state, runtime)
