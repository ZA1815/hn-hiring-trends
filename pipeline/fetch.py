"""Hacker News data via the public Algolia HN API (no key required)."""

from __future__ import annotations

import gzip
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API = "https://hn.algolia.com/api/v1"
USER_AGENT = "hn-hiring-trends (+https://github.com/ZA1815/hn-hiring-trends)"
_TITLE = re.compile(r"(?i)who is hiring\?\s*\((\w+)\s+(\d{4})\)")
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


@dataclass(frozen=True)
class Thread:
    id: int
    month: str  # YYYY-MM


def _get_json(url: str, attempts: int = 4) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise
            wait = 2 ** attempt * 2
            print(f"  retry in {wait}s after {exc}")
            time.sleep(wait)
    raise AssertionError("unreachable")


def _hit_month(hit: dict) -> str | None:
    m = _TITLE.search(hit.get("title") or "")
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    return f"{m.group(2)}-{_MONTHS[m.group(1).lower()]:02d}"


def _collect(hits: list[dict], best: dict[str, tuple[int, Thread]], only: str | None = None) -> None:
    for hit in hits:
        month = _hit_month(hit)
        if month is None or (only and month != only):
            continue
        comments = hit.get("num_comments") or 0
        # If a month was posted more than once, keep the thread people actually used.
        if month not in best or comments > best[month][0]:
            best[month] = (comments, Thread(id=int(hit["objectID"]), month=month))


def _month_range(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    out = []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def list_threads() -> list[Thread]:
    """Every monthly 'Ask HN: Who is hiring?' thread, oldest first.

    Threads come from the whoishiring bot (and its _whoishiring stand-in). A few early
    months were posted by community members instead; those gaps are filled by a title
    search that keeps the most-commented thread for the month.
    """
    best: dict[str, tuple[int, Thread]] = {}
    data = _get_json(f"{API}/search_by_date?tags=story,(author_whoishiring,author__whoishiring)&hitsPerPage=1000")
    _collect(data["hits"], best)
    names = {v: k for k, v in _MONTHS.items()}
    for month in _month_range(min(best), max(best)):
        if month in best and best[month][0] >= 50:
            continue
        y, m = month.split("-")
        query = urllib.parse.quote(f'"who is hiring" {names[int(m)]} {y}')
        data = _get_json(f"{API}/search?tags=story&restrictSearchableAttributes=title&hitsPerPage=20&query={query}")
        _collect(data["hits"], best, only=month)
    return sorted((t for _, t in best.values()), key=lambda t: t.month)


def thread_posts(thread: Thread, cache_dir: Path, refresh: bool = False) -> list[str]:
    """Raw HTML of every top-level job post in a thread, cached as gzip JSON."""
    path = cache_dir / f"{thread.month}-{thread.id}.json.gz"
    if path.exists() and not refresh:
        return json.loads(gzip.decompress(path.read_bytes()))
    item = _get_json(f"{API}/items/{thread.id}")
    posts = [
        c["text"]
        for c in item.get("children", [])
        if c.get("text") and c.get("author") and c.get("author") != "whoishiring"
    ]
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(posts).encode()))
    return posts
