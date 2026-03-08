"""Arc browser tools via AppleScript (osascript)."""

import json
import subprocess
from typing import Optional


_FIELD_SEP = "\x1f"  # ASCII Unit Separator
_RECORD_SEP = "\x1e"  # ASCII Record Separator


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


def _as_apple_string(value: str) -> str:
    """Safely embed a Python string inside an AppleScript string literal."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


# ---------------------------------------------------------------------------
# Spaces
# ---------------------------------------------------------------------------

def list_spaces() -> list[dict]:
    """List all Arc spaces with their IDs and titles."""
    script = """
tell application "Arc"
    set fieldSep to ASCII character 31
    set recordSep to ASCII character 30
    set out to ""
    repeat with s in spaces of window 1
        set out to out & (id of s as text) & fieldSep & (title of s as text) & recordSep
    end repeat
    return out
end tell
"""
    try:
        raw = _run(script)
        if not raw:
            return []
        spaces = []
        for item in raw.split(_RECORD_SEP):
            if not item:
                continue
            parts = item.split(_FIELD_SEP)
            if len(parts) == 2:
                spaces.append({"id": parts[0].strip(), "title": parts[1].strip()})
        return spaces
    except RuntimeError as e:
        return [{"error": str(e)}]


def focus_space(space_id: str) -> dict:
    """Switch to a space by ID."""
    safe_space_id = _as_apple_string(space_id)
    script = f"""
tell application "Arc"
    set targetSpace to first space of window 1 whose id is "{safe_space_id}"
    focus targetSpace
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
    set fieldSep to ASCII character 31
    set recordSep to ASCII character 30
    set out to ""
    repeat with s in spaces of window 1
        set sId to id of s as text
        set sTitle to title of s as text
        repeat with t in tabs of s
            set out to out & sId & fieldSep & sTitle & fieldSep & (id of t as text) & fieldSep & (title of t as text) & fieldSep & (URL of t as text) & fieldSep & (location of t as text) & recordSep
        end repeat
    end repeat
    return out
end tell
"""
    try:
        raw = _run(script)
        if not raw:
            return []
        tabs = []
        for item in raw.split(_RECORD_SEP):
            if not item:
                continue
            parts = item.split(_FIELD_SEP)
            if len(parts) == 6:
                tabs.append({
                    "space_id": parts[0].strip(),
                    "space_title": parts[1].strip(),
                    "id": parts[2].strip(),
                    "title": parts[3].strip(),
                    "url": parts[4].strip(),
                    "location": parts[5].strip(),
                })
        if not space_id:
            return tabs
        return [tab for tab in tabs if tab["space_id"] == space_id]
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
        return [all_tabs]
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
    safe_url = _as_apple_string(url)
    if space_id:
        safe_space_id = _as_apple_string(space_id)
        script = f"""
tell application "Arc"
    set targetSpace to first space of window 1 whose id is "{safe_space_id}"
    make new tab in targetSpace with properties {{URL:"{safe_url}"}}
end tell
"""
    else:
        script = f"""
tell application "Arc"
    tell window 1
        make new tab with properties {{URL:"{safe_url}"}}
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    safe_url = _as_apple_string(url)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
                set URL of t to "{safe_url}"
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
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
    safe_tab_id = _as_apple_string(tab_id)
    safe_js = _as_apple_string(js)
    script = f"""
tell application "Arc"
    repeat with s in spaces of window 1
        repeat with t in tabs of s
            if (id of t as text) is "{safe_tab_id}" then
                return execute t javascript "{safe_js}"
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
        return json.loads(result)
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to parse page content: {e}"}
