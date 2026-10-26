# 🔍 CommitLens

**X-ray a git repository's history.** Point it at any repo and it answers
the questions every maintainer quietly worries about: who actually carries
this codebase, where is the churn, when does the team work, and which files
have gone stale?

- **Bus factor** — the fewest authors covering ≥ 50% of files. A bus factor
  of 1 is a risk you can finally put a number on.
- **Top contributors** — commits, lines added/removed, files touched.
- **File churn** — hottest files by commits and changed lines, with the top
  author for each file, so ownership is obvious.
- **Commit rhythm** — a weekday × hour heatmap of when the team works.
- **Stale files** — files untouched for longer than your threshold
  (default 180 days).
- **Large commits** — commits over your line threshold, ranked.
- **Three outputs** — human-readable text, machine-readable JSON, and a
  self-contained HTML report (no server, no CDN, no tracking).

Zero dependencies: Python 3.10+ standard library only, plus the `git`
binary it reads history from.

## The portfolio arc

AIGuard audits your code · JarLens audits your jars · CinderLens audits
your speed · RepoScope audits any repo · VulnLens audits your supply chain
· **CommitLens audits your history.**

## Run it

No install step — clone and run from the project root:

```sh
# Text report for a repo
python3 -m commitlens /path/to/repo

# Self-contained HTML report
python3 -m commitlens /path/to/repo --format html -o report.html

# JSON, for piping into other tooling
python3 -m commitlens /path/to/repo --format json

# Only the last quarter, stricter stale/large thresholds, more rows
python3 -m commitlens /path/to/repo --since 2026-07-01 \
    --stale-days 90 --large 300 --top 20
```

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `repo` | `.` | Path to the git repository |
| `--branch` | HEAD | Branch or ref to analyze |
| `--since` / `--until` | — | Date window (git date syntax) |
| `--format` | `text` | `text`, `json`, or `html` |
| `--output` / `-o` | stdout | Write the report to a file |
| `--top` | 10 | Rows shown per table |
| `--stale-days` | 180 | A file is stale after this many untouched days |
| `--large` | 500 | A commit is large at this many changed lines |

Exit codes: `0` on success, `1` if the path is not a git repo, the repo
has no commits, or git fails, `2` for bad arguments.

## Example output

Running CommitLens on its own demo fixture repo
(see `examples/make-fixture-repo.sh`):

```
CommitLens report
============================================================
Commits: 6  Authors: 3  Files touched: 3
Lines: +408 / -3  Span: 2026-01-05 -> 2026-06-21 (166 days)
Bus factor: 1 (covers 100.0% of files)

Top contributors (commits, +/-, files):
  Ada Lovelace                4  +6       -0       3 files
  Alan Turing                 1  +401     -2       1 files
  Grace Hopper                1  +1       -1       1 files

Hottest files (commits, changed lines, top author):
  engine.py                                      3     407  Alan Turing
  README.md                                      2       3  Ada Lovelace
  feature.py                                     1       1  Ada Lovelace
```

A real HTML report generated from that fixture ships in
[`docs/sample-report.html`](docs/sample-report.html) — open it to see the
heatmap, monthly bars, and sortable tables. The landing page in `docs/`
is what GitHub Pages serves.

## How it works

1. `git log --numstat` is parsed into commit records (hash, author, date,
   subject, per-file added/deleted lines). Binary files count as 0 lines;
   merge commits have no file changes.
2. Authors, files, rhythm, and monthly totals are aggregated in memory.
3. Bus factor: authors sorted by distinct files touched, counted until
   their union covers ≥ 50% of all files.
4. The report is rendered as text, JSON, or one self-contained HTML file.

## Tests

```sh
python3 -m unittest discover -s tests
```

16 tests: log parsing (including binary files, merge commits, malformed
lines), analysis (bus factor, churn, stale files, rhythm), output
rendering (including the HTML self-containment check), CLI exit codes,
and an end-to-end run against a real temporary git repo.

## Limitations

- History only: uncommitted changes, stashes, and ignored files are
  invisible by design.
- Author identity is by name as recorded in git; the same person with
  two names counts as two authors.
- Rename detection is off, so a renamed file looks like a delete plus an
  add. Line counts come from `--numstat` and ignore whitespace-only
  changes only in the sense that git counts them.
