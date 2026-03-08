"""Arc browser history via Chromium's SQLite history file."""

import shutil
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone

HISTORY_PATH = Path.home() / "Library/Application Support/Arc/User Data/Default/History"

# Chromium stores timestamps as microseconds since 1601-01-01
_CHROMIUM_EPOCH_DELTA = 11644473600  # seconds between 1601-01-01 and 1970-01-01


def _chromium_ts_to_iso(ts: int) -> str:
    """Convert Chromium timestamp (microseconds since 1601) to ISO 8601 string."""
    if not ts:
        return ""
    try:
        unix_ts = (ts / 1_000_000) - _CHROMIUM_EPOCH_DELTA
        return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _copy_and_connect() -> sqlite3.Connection:
    """
    Copy the live history file to a temp location before reading.
    Avoids SQLite WAL lock conflicts with the running browser.
    """
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"Arc history not found at {HISTORY_PATH}")
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    shutil.copy2(HISTORY_PATH, tmp.name)
    return sqlite3.connect(tmp.name)


def search_history(query: str, limit: int = 20) -> list[dict]:
    """
    Search Arc browser history by title or URL.
    Returns up to `limit` results sorted by most recent visit.
    """
    try:
        conn = _copy_and_connect()
        cursor = conn.execute(
            """
            SELECT u.url, u.title, u.visit_count, MAX(v.visit_time) as last_visit
            FROM urls u
            JOIN visits v ON u.id = v.url
            WHERE u.url LIKE ? OR u.title LIKE ?
            GROUP BY u.id
            ORDER BY last_visit DESC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "url": row[0],
                "title": row[1] or "",
                "visit_count": row[2],
                "last_visit": _chromium_ts_to_iso(row[3]),
            }
            for row in rows
        ]
    except FileNotFoundError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"History query failed: {e}"}]


def find_closed_tab(query: str, limit: int = 10) -> list[dict]:
    """
    Search history to find a previously closed or archived tab.
    Useful for reopening something you closed.
    """
    results = search_history(query, limit=limit)
    if results and "error" in results[0]:
        return results
    return [
        {
            "url": r["url"],
            "title": r["title"],
            "last_visit": r["last_visit"],
            "visit_count": r["visit_count"],
        }
        for r in results
    ]
