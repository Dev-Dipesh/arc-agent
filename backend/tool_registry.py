"""Shared Arc tool registry used by MCP server and LangGraph agent."""

from collections.abc import Callable

from langchain_core.tools import BaseTool, tool

from mcp_remote_client import (
    MCPRemoteError,
    call_remote_mcp_tool,
    is_remote_mcp_enabled,
)
from tools.arc import (
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
from tools.history import find_closed_tab, search_history


def _call(tool_name: str, local_fn: Callable, /, **kwargs):
    if is_remote_mcp_enabled():
        try:
            return call_remote_mcp_tool(tool_name, **kwargs)
        except MCPRemoteError as e:
            return {"error": str(e)}
    return local_fn(**kwargs)


def arc_list_spaces() -> list[dict]:
    """List all Arc spaces with their IDs and titles."""
    return _call("arc_list_spaces", list_spaces)


def arc_focus_space(space_id: str) -> dict:
    """Switch Arc to a specific space by ID."""
    return _call("arc_focus_space", focus_space, space_id=space_id)


def arc_list_tabs(space_id: str = "") -> list[dict]:
    """List tabs in Arc. Pass a space_id or leave empty for all spaces."""
    return _call("arc_list_tabs", list_tabs, space_id=space_id or None)


def arc_find_tabs(query: str) -> list[dict]:
    """Search Arc tabs by title or URL."""
    return _call("arc_find_tabs", find_tabs, query=query)


def arc_find_duplicates() -> list[list[dict]]:
    """Find tabs with duplicate URLs across all spaces."""
    return _call("arc_find_duplicates", find_duplicates)


def arc_open_url(url: str, space_id: str = "") -> dict:
    """Open URL in Arc (legacy behavior)."""
    return _call("arc_open_url", open_url, url=url, space_id=space_id or None)


def arc_open_url_active_window(url: str) -> dict:
    """Open URL directly in active Arc window (no mini-window handoff)."""
    return _call("arc_open_url_active_window", open_url_active_window, url=url)


def arc_open_url_mini_window(url: str, space_id: str) -> dict:
    """Open URL via target-space path, which may appear as mini-window first."""
    return _call("arc_open_url_mini_window", open_url_mini_window, url=url, space_id=space_id)


def arc_close_tab(tab_id: str) -> dict:
    """Close a tab by ID."""
    return _call("arc_close_tab", close_tab, tab_id=tab_id)


def arc_switch_to_tab(tab_id: str) -> dict:
    """Focus (select) a tab by ID."""
    return _call("arc_switch_to_tab", switch_to_tab, tab_id=tab_id)


def arc_reload_tab(tab_id: str) -> dict:
    """Reload a tab by ID."""
    return _call("arc_reload_tab", reload_tab, tab_id=tab_id)


def arc_stop_tab(tab_id: str) -> dict:
    """Stop a loading tab by ID."""
    return _call("arc_stop_tab", stop_tab, tab_id=tab_id)


def arc_navigate_tab(tab_id: str, url: str) -> dict:
    """Navigate an existing tab to URL."""
    return _call("arc_navigate_tab", navigate_tab, tab_id=tab_id, url=url)


def arc_go_back(tab_id: str) -> dict:
    """Go back in a tab's history."""
    return _call("arc_go_back", go_back, tab_id=tab_id)


def arc_go_forward(tab_id: str) -> dict:
    """Go forward in a tab's history."""
    return _call("arc_go_forward", go_forward, tab_id=tab_id)


def arc_read_page_content(tab_id: str) -> dict:
    """Extract readable page text from a tab."""
    return _call("arc_read_page_content", read_page_content, tab_id=tab_id)


def arc_search_history(query: str, limit: int = 20) -> list[dict]:
    """Search Arc browser history by title or URL."""
    return _call("arc_search_history", search_history, query=query, limit=limit)


def arc_find_closed_tab(query: str) -> list[dict]:
    """Find previously closed tabs from history-like records."""
    return _call("arc_find_closed_tab", find_closed_tab, query=query)


MCP_TOOL_FUNCTIONS: list[Callable] = [
    arc_list_spaces,
    arc_focus_space,
    arc_list_tabs,
    arc_find_tabs,
    arc_find_duplicates,
    arc_open_url,
    arc_open_url_active_window,
    arc_open_url_mini_window,
    arc_close_tab,
    arc_switch_to_tab,
    arc_reload_tab,
    arc_stop_tab,
    arc_navigate_tab,
    arc_go_back,
    arc_go_forward,
    arc_read_page_content,
    arc_search_history,
    arc_find_closed_tab,
]


def build_langgraph_tools(exclude: set[str] | None = None) -> list[BaseTool]:
    """Build LangGraph/LangChain tool objects from shared registry."""
    excluded = exclude or set()
    return [tool(fn) for fn in MCP_TOOL_FUNCTIONS if fn.__name__ not in excluded]
