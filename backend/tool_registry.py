"""Shared Arc tool registry used by MCP server and LangGraph agent."""

from collections.abc import Callable

from langchain_core.tools import BaseTool, tool

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


def arc_list_spaces() -> list[dict]:
    """List all Arc spaces with their IDs and titles."""
    return list_spaces()


def arc_focus_space(space_id: str) -> dict:
    """Switch Arc to a specific space by ID."""
    return focus_space(space_id)


def arc_list_tabs(space_id: str = "") -> list[dict]:
    """List tabs in Arc. Pass a space_id or leave empty for all spaces."""
    return list_tabs(space_id or None)


def arc_find_tabs(query: str) -> list[dict]:
    """Search Arc tabs by title or URL."""
    return find_tabs(query)


def arc_find_duplicates() -> list[list[dict]]:
    """Find tabs with duplicate URLs across all spaces."""
    return find_duplicates()


def arc_open_url(url: str, space_id: str = "") -> dict:
    """Open URL in Arc (legacy behavior)."""
    return open_url(url, space_id or None)


def arc_open_url_active_window(url: str) -> dict:
    """Open URL directly in active Arc window (no mini-window handoff)."""
    return open_url_active_window(url)


def arc_open_url_mini_window(url: str, space_id: str) -> dict:
    """Open URL via target-space path, which may appear as mini-window first."""
    return open_url_mini_window(url, space_id)


def arc_close_tab(tab_id: str) -> dict:
    """Close a tab by ID."""
    return close_tab(tab_id)


def arc_switch_to_tab(tab_id: str) -> dict:
    """Focus (select) a tab by ID."""
    return switch_to_tab(tab_id)


def arc_reload_tab(tab_id: str) -> dict:
    """Reload a tab by ID."""
    return reload_tab(tab_id)


def arc_stop_tab(tab_id: str) -> dict:
    """Stop a loading tab by ID."""
    return stop_tab(tab_id)


def arc_navigate_tab(tab_id: str, url: str) -> dict:
    """Navigate an existing tab to URL."""
    return navigate_tab(tab_id, url)


def arc_go_back(tab_id: str) -> dict:
    """Go back in a tab's history."""
    return go_back(tab_id)


def arc_go_forward(tab_id: str) -> dict:
    """Go forward in a tab's history."""
    return go_forward(tab_id)


def arc_read_page_content(tab_id: str) -> dict:
    """Extract readable page text from a tab."""
    return read_page_content(tab_id)


def arc_search_history(query: str, limit: int = 20) -> list[dict]:
    """Search Arc browser history by title or URL."""
    return search_history(query, limit)


def arc_find_closed_tab(query: str) -> list[dict]:
    """Find previously closed tabs from history-like records."""
    return find_closed_tab(query)


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

