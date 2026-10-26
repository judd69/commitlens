"""Turn parsed commits into the numbers CommitLens reports.

Bus factor here is the pragmatic, widely used approximation: sort authors
by the number of distinct files they have touched (most first) and count
how many authors it takes to cover at least half of all files. A bus
factor of 1 means one person touches at least half the codebase — the
number every maintainer wants to see grow.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from .gitlog import Commit


def analyze(commits: list, top_n: int = 10, stale_days: int = 180,
            large_threshold: int = 500) -> dict:
    dates = [c.date for c in commits]
    first, last = min(dates), max(dates)

    authors: dict = {}
    for c in commits:
        a = authors.setdefault(c.author, {
            "author": c.author, "email": c.email, "commits": 0,
            "added": 0, "deleted": 0, "files": set(),
            "first": c.date, "last": c.date,
        })
        a["commits"] += 1
        a["added"] += sum(f.added for f in c.files)
        a["deleted"] += sum(f.deleted for f in c.files)
        a["files"].update(f.path for f in c.files)
        a["first"] = min(a["first"], c.date)
        a["last"] = max(a["last"], c.date)

    files: dict = {}
    file_authors: dict = defaultdict(Counter)
    for c in commits:
        for f in c.files:
            rec = files.setdefault(f.path, {
                "path": f.path, "commits": 0, "added": 0, "deleted": 0,
                "last": c.date,
            })
            rec["commits"] += 1
            rec["added"] += f.added
            rec["deleted"] += f.deleted
            rec["last"] = max(rec["last"], c.date)
            file_authors[f.path][c.author] += 1

    # Bus factor: fewest authors covering >= 50% of distinct files.
    all_files = set(files)
    covered: set = set()
    author_files = {name: a["files"] for name, a in authors.items()}
    bus_factor = 0
    for name, _ in sorted(author_files.items(),
                          key=lambda kv: len(kv[1]), reverse=True):
        if len(covered) * 2 >= len(all_files):
            break
        covered |= author_files[name]
        bus_factor += 1
    bus_coverage = round(100 * len(covered) / max(1, len(all_files)), 1)

    # Commit rhythm: weekday (Mon=0) x hour grid, and monthly totals.
    rhythm = [[0] * 24 for _ in range(7)]
    monthly: Counter = Counter()
    for c in commits:
        rhythm[c.date.weekday()][c.date.hour] += 1
        monthly[c.date.strftime("%Y-%m")] += 1

    churn = sorted(
        ({**rec, "changed": rec["added"] + rec["deleted"],
          "top_author": file_authors[rec["path"]].most_common(1)[0][0]}
         for rec in files.values()),
        key=lambda r: r["changed"], reverse=True)

    stale_cutoff = last - timedelta(days=stale_days)
    stale = [r for r in churn if r["last"] <= stale_cutoff]

    large = sorted((c for c in commits if c.changed >= large_threshold),
                   key=lambda c: c.changed, reverse=True)

    author_rows = sorted(
        ({**a, "files": len(a["files"])} for a in authors.values()),
        key=lambda a: a["commits"], reverse=True)

    total_added = sum(a["added"] for a in authors.values())
    total_deleted = sum(a["deleted"] for a in authors.values())

    return {
        "totals": {
            "commits": len(commits),
            "authors": len(authors),
            "files": len(files),
            "added": total_added,
            "deleted": total_deleted,
            "first": first.isoformat(),
            "last": last.isoformat(),
            "span_days": (last - first).days,
        },
        "bus_factor": {"value": bus_factor, "coverage_pct": bus_coverage},
        "authors": author_rows,
        "churn": churn[:top_n],
        "stale": [{
            "path": r["path"], "commits": r["commits"],
            "changed": r["changed"], "last": r["last"].isoformat(),
            "top_author": r["top_author"],
        } for r in stale[:top_n]],
        "large_commits": [{
            "sha": c.sha[:12], "author": c.author,
            "date": c.date.isoformat(), "subject": c.subject,
            "changed": c.changed, "files": len(c.files),
        } for c in large[:top_n]],
        "rhythm": rhythm,
        "monthly": [{"month": m, "commits": n}
                    for m, n in sorted(monthly.items())],
        "churn_all_count": len(churn),
        "stale_all_count": len(stale),
        "large_all_count": len(large),
    }
