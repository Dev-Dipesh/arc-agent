"""Arc browser tools via AppleScript (osascript)."""

import subprocess
from typing import Optional


def _run(script: str) -> str:
    """Run an AppleScript and return stdout, or raise on error."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _run_multi(lines: list[str]) -> str:
    """Run a multi-line AppleScript."""
    return _run("\n".join(lines))


# ---------------------------------------------------------------------------
# Spaces
# ---------------------------------------------------------------------------

def list_spaces() -> list[dict]:
    """List all Arc spaces with their IDs and titles."""
    script = """
tell application "Arc"
    set out to {}
    repeat with s in spaces of window 1
        set end of out to (id of s) & "|||" & (title of s)
    end repeat
    return out
end tell
"""
    try:
        raw = _run(script)
        if not raw:
            return []
        spaces = []
        for item in raw.split(", "):
            parts = item.split("|||")
            if len(parts) == 2:
                spaces.append({"id": parts[0].strip(), "title": parts[1].strip()})
        return spaces
    except RuntimeError as e:
        return [{"error": str(e)}]


def focus_space(space_id: str) -> dict:
    """Switch to a space by ID."""
    script = f"""
tell application "Arc"
    set target to first space of window 1 whose id is "{space_id}"
    focus target
end tell
"""
    try:
        _run(script)
        return {"ok": True, "space_id": space_id}
    except RuntimeError as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tabs — query
# ---------------------------------------------------------------------------

def list_tabs(space_id: Optional[str] = None) -> list[dict]:
    """
    List tabs. If space_id is given, list only tabs in that space.
    Otherwise list tabs across all spaces.
    """
    script = """
tell application "Arc"
    set out to {}
    repeat with s in spaces of window 1
        set sId to id of s
        set sTitle to title of s
        repeat with t in tabs of s
            set end of out to sId & "|||" & sTitle & "|||" & (id of t) & "|||" & (title of t) & "|||" & (URL of t) & "|||" & (location of t)
        end repeat
    end repeat
    return out
end tell
"""
    space_script = f"""
tell application "Arc"
    set s to first space of window 1 whose id is "{space_id}"
    set sId to id of s
    set sTitle to title of s
    set out to {{}}
    repeat with t in tabs of s
        set end of out to sId & "|||" & sTitle & "|||" & (id of t) & "|||" & (title of t) & "|||" & (URL of t) & "|||" & (location of t)
    end repeat
    return out
end tell
"""
    try:
        raw = _run(space_script if space_id else script)
        if not raw:
            return []
        tabs = []
        for item in raw.split(", "):
            parts = item.split("|||")
            if len(parts) == 6:
                tabs.append({
                    "space_id": parts[0].strip(),
                    "space_title": parts[1].strip(),
                    "id": parts[2].strip(),
                    "title": parts[3].strip(),
                    "url": parts[4].strip(),
                    "location": parts[5].strip(),
                })
        return tabs
    except RuntimeError as e:
        return [{"error": str(e)}]


def find_tabs(query: str) -> list[dict]:
    """Search tabs by title or URL (case-insensitive substring match)."""
    all_tabs = list_tabs()
    if all_tabs and "error" in all_tabs[0]:
        return all_tabs
    q = query.lower()
    return [t for t in all_tabs if q in t.get("title", "").lower() or q in t.get("url", "").lower()]


def find_duplicates() -> list[list[dict]]:
    """Find tabs with duplicate URLs across all spaces. Returns groups of duplicates."""
    all_tabs = list_tabs()
    if all_tabs and "error" in all_tabs[0]:
        return []
    seen: dict[str, list[dict]] = {}
    for tab in all_tabs:
        url = tab.get("url", "").rstrip("/")
        seen.setdefault(url, []).append(tab)
    return [group for group in seen.values() if len(group) > 1]


# ---------------------------------------------------------------------------
# Tabs — actions
# ---------------------------------------------------------------------------

def open_url(url: str, space_id: Optional[str] = None) -> dict:
    """
    Open a URL in Arc. If space_id is given, opens in that space.
    Otherwise opens in the currently active space.
    """
    if space_id:
        script = f"""
tell application "Arc"
    set target to first space of window 1 whose id is "{space_id}"
    tell target
        make new tab with properties {{URL:"{url}"}}
    end tell
end tell
"""
    else:
        script = f"""
tell application "Arc"
    tell window 1
        make new tab with properties {{URL:"{url}"}}
    end tell
end tell
"""
    try:
        _run(script)
        return {"ok": True, "url": url, "space_id": space_id}
    except RuntimeError as e:
        return {"error": str(e)}


def close_tab(tab_id: str) -> dict:
    """Close a tab by ID."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                close t
                return "closed"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def switch_to_tab(tab_id: str) -> dict:
    """Focus a tab by ID."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                select t
                return "selected"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def reload_tab(tab_id: str) -> dict:
    """Reload a tab by ID."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                reload t
                return "reloaded"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def stop_tab(tab_id: str) -> dict:
    """Stop a loading tab by ID."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                stop t
                return "stopped"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def navigate_tab(tab_id: str, url: str) -> dict:
    """Navigate an existing tab to a new URL."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                set URL of t to "{url}"
                return "navigated"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id, "url": url}
    except RuntimeError as e:
        return {"error": str(e)}


def go_back(tab_id: str) -> dict:
    """Navigate back in a tab's history."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                go back t
                return "ok"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def go_forward(tab_id: str) -> dict:
    """Navigate forward in a tab's history."""
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                go forward t
                return "ok"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id}
    except RuntimeError as e:
        return {"error": str(e)}


def set_tab_location(tab_id: str, location: str) -> dict:
    """
    Set a tab's sidebar location within its space.
    location: 'topApp' | 'pinned' | 'unpinned'
    """
    if location not in ("topApp", "pinned", "unpinned"):
        return {"error": f"Invalid location '{location}'. Must be topApp, pinned, or unpinned."}
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                set location of t to "{location}"
                return "ok"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        return {"ok": True, "tab_id": tab_id, "location": location}
    except RuntimeError as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

def read_page_content(tab_id: str) -> dict:
    """
    Extract readable text content from a tab for summarisation.
    Returns the page title and cleaned body text.
    """
    js = (
        "(function(){"
        "var title=document.title;"
        "var body=document.body?document.body.innerText:'';"
        "var trimmed=body.replace(/\\s+/g,' ').trim().slice(0,8000);"
        "return JSON.stringify({title:title,content:trimmed});"
        "})()"
    )
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if id of t is "{tab_id}" then
                return execute t javascript "{js}"
            end if
        end repeat
    end repeat
    return "not_found"
end tell
"""
    try:
        result = _run(script)
        if result == "not_found":
            return {"error": f"Tab {tab_id} not found"}
        import json
        return json.loads(result)
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to parse page content: {e}"}
