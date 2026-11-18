"""Fetch threads, classify posts, and write the dashboard's summary.json.

Usage:
    python -m pipeline.build            # add new months, refresh the latest two
    python -m pipeline.build --full     # rebuild every month (after taxonomy changes)
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from . import fetch, parse, taxonomy

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "site" / "data" / "summary.json"
REFRESH_LATEST = 2  # threads keep collecting posts for a few weeks


def _pct(n: int, total: int) -> float:
    return round(n / total, 4) if total else 0.0


def summarize(thread: fetch.Thread, raw_posts: list[str], now: datetime) -> dict:
    posts = [parse.classify(p) for p in raw_posts]
    total = len(posts)
    salaries = [p.salary_mid for p in posts if p.salary_mid is not None]
    arrangement = {k: 0 for k in ("remote", "hybrid", "onsite", "unspecified")}
    for p in posts:
        arrangement[p.arrangement] += 1
    return {
        "month": thread.month,
        "thread_id": thread.id,
        "in_progress": thread.month == now.strftime("%Y-%m"),
        "posts": total,
        "arrangement": {k: _pct(v, total) for k, v in arrangement.items()},
        "salary_listed": _pct(len(salaries), total),
        "salary_median": round(median(salaries)) if salaries else None,
        "salary_n": len(salaries),
        "visa": _pct(sum(p.visa_offered for p in posts), total),
        "junior": _pct(sum(p.junior for p in posts), total),
        "intern": _pct(sum(p.intern for p in posts), total),
        "tech": {name: _pct(sum(name in p.techs for p in posts), total) for name in taxonomy.TECH},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="rebuild every month")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    existing = {} if args.full or not OUT.exists() else {
        row["month"]: row for row in json.loads(OUT.read_text(encoding="utf-8"))["months"]
    }
    threads = fetch.list_threads()
    latest = {t.month for t in threads[-REFRESH_LATEST:]}
    todo = [t for t in threads if args.full or t.month not in existing or t.month in latest]
    print(f"{len(threads)} threads, building {len(todo)}")

    def build(t: fetch.Thread) -> dict:
        raw = fetch.thread_posts(t, CACHE, refresh=t.month in latest)
        row = summarize(t, raw, now)
        print(f"  {t.month}: {row['posts']} posts")
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        for row in pool.map(build, todo):
            existing[row["month"]] = row

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": now.isoformat(timespec="seconds"),
        "source": "https://hn.algolia.com/api",
        "techs": list(taxonomy.TECH),
        "months": [existing[m] for m in sorted(existing)],
    }, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
