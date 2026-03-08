"""Arc Browser MCP Server — exposes Arc browser control as MCP tools."""

from mcp.server.fastmcp import FastMCP

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
    set_tab_location,
    stop_tab,
    switch_to_tab,
)
from tools.history import find_closed_tab, search_history

mcp = FastMCP(
    "arc-browser",
    instructions=(
        "Tools for controlling Arc browser on macOS. "
        "Tabs belong to spaces — always use space context when acting on tabs. "
        "Call list_spaces first if you don't know the available spaces. "
        "Always confirm with the user before calling close_tab."
    ),
)


# ---------------------------------------------------------------------------
# Spaces
# ---------------------------------------------------------------------------


@mcp.tool()
def arc_list_spaces() -> list[dict]:
    """List all Arc spaces with their IDs and titles."""
    return list_spaces()


@mcp.tool()
def arc_focus_space(space_id: str) -> dict:
    """Switch Arc to a specific space by ID."""
    return focus_space(space_id)


# ---------------------------------------------------------------------------
# Tabs — query
# ---------------------------------------------------------------------------


@mcp.tool()
def arc_list_tabs(space_id: str = "") -> list[dict]:
    """
    List tabs in Arc. Pass a space_id to list tabs in a specific space,
    or leave empty to list all tabs across all spaces.
    """
    return list_tabs(space_id or None)


@mcp.tool()
def arc_find_tabs(query: str) -> list[dict]:
    """Search Arc tabs by title or URL (case-insensitive substring match)."""
    return find_tabs(query)


@mcp.tool()
def arc_find_duplicates() -> list[list[dict]]:
    """Find tabs with duplicate URLs across all spaces."""
    return find_duplicates()


# ---------------------------------------------------------------------------
# Tabs — actions
# ---------------------------------------------------------------------------


@mcp.tool()
def arc_open_url(url: str, space_id: str = "") -> dict:
    """
    Open a URL in Arc (legacy behavior).
    - Without space_id: opens directly in active window.
    - With space_id: uses target-space path that may appear as a mini-window first.
    """
    return open_url(url, space_id or None)


@mcp.tool()
def arc_open_url_active_window(url: str) -> dict:
    """Open a URL directly in the active Arc window (no mini-window handoff)."""
    return open_url_active_window(url)


@mcp.tool()
def arc_open_url_mini_window(url: str, space_id: str) -> dict:
    """
    Open a URL using Arc's target-space path, which may first appear in a mini window.
    Use when the user explicitly prefers mini-window behavior.
    """
    return open_url_mini_window(url, space_id)


@mcp.tool()
def arc_close_tab(tab_id: str) -> dict:
    """
    Close a tab by ID.
    IMPORTANT: Only call this after the user has explicitly confirmed they want to close this tab.
    """
    return close_tab(tab_id)


@mcp.tool()
def arc_switch_to_tab(tab_id: str) -> dict:
    """Focus (select) a tab by ID, bringing it into view."""
    return switch_to_tab(tab_id)


@mcp.tool()
def arc_reload_tab(tab_id: str) -> dict:
    """Reload a tab by ID."""
    return reload_tab(tab_id)


@mcp.tool()
def arc_stop_tab(tab_id: str) -> dict:
    """Stop a loading tab by ID."""
    return stop_tab(tab_id)


@mcp.tool()
def arc_navigate_tab(tab_id: str, url: str) -> dict:
    """Navigate an existing tab to a new URL."""
    return navigate_tab(tab_id, url)


@mcp.tool()
def arc_go_back(tab_id: str) -> dict:
    """Navigate back in a tab's history."""
    return go_back(tab_id)


@mcp.tool()
def arc_go_forward(tab_id: str) -> dict:
    """Navigate forward in a tab's history."""
    return go_forward(tab_id)


@mcp.tool()
def arc_set_tab_location(tab_id: str, location: str) -> dict:
    """
    Set a tab's sidebar location within its space.
    location must be one of: 'topApp', 'pinned', 'unpinned'
    - topApp: pinned to the top of the sidebar (above the fold)
    - pinned: pinned in the sidebar
    - unpinned: regular (today) tab
    """
    return set_tab_location(tab_id, location)


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------


@mcp.tool()
def arc_read_page_content(tab_id: str) -> dict:
    """
    Extract the readable text content of a tab for summarisation or analysis.
    Returns the page title and up to 8000 chars of body text.
    """
    return read_page_content(tab_id)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@mcp.tool()
def arc_search_history(query: str, limit: int = 20) -> list[dict]:
    """
    Search Arc browser history by title or URL.
    Returns up to `limit` results sorted by most recent visit.
    """
    return search_history(query, limit)


@mcp.tool()
def arc_find_closed_tab(query: str) -> list[dict]:
    """
    Search history to find a previously closed or archived tab.
    Returns matching URLs with last visit time so you can reopen them.
    """
    return find_closed_tab(query)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
