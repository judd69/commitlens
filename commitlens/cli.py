"""Command-line interface for CommitLens."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .analyze import analyze
from .gitlog import collect
from .outputs import render_html, render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="commitlens",
        description="X-ray a git repository's history: bus factor, "
                    "contributors, churn, rhythm, stale files.")
    p.add_argument("repo", nargs="?", default=".",
                   help="path to the git repository (default: current dir)")
    p.add_argument("--branch", default=None,
                   help="branch or ref to analyze (default: HEAD)")
    p.add_argument("--since", default=None,
                   help="only commits after this date (git --since syntax)")
    p.add_argument("--until", default=None,
                   help="only commits before this date (git --until syntax)")
    p.add_argument("--format", choices=["text", "json", "html"],
                   default="text", help="output format (default: text)")
    p.add_argument("--output", "-o", default=None,
                   help="write report to this file instead of stdout")
    p.add_argument("--top", type=int, default=10,
                   help="rows shown per table (default: 10)")
    p.add_argument("--stale-days", type=int, default=180,
                   help="a file is stale if untouched for this many days "
                        "(default: 180)")
    p.add_argument("--large", type=int, default=500,
                   help="a commit is large if it changes at least this many "
                        "lines (default: 500)")
    p.add_argument("--version", action="version",
                   version=f"commitlens {__version__}")
    return p


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        commits = collect(args.repo, args.branch, args.since, args.until)
    except RuntimeError as exc:
        print(f"commitlens: error: {exc}", file=sys.stderr)
        return 1
    result = analyze(commits, top_n=args.top,
                     stale_days=args.stale_days,
                     large_threshold=args.large)
    if args.format == "json":
        out = render_json(result)
    elif args.format == "html":
        out = render_html(result, args.repo)
    else:
        out = render_text(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
