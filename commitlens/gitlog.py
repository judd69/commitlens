"""Parse `git log` output into commit records.

The log format produced by :func:`collect` is deliberately boring so this
parser can stay small and exact:

    COMMIT <hash>
    AUTHOR <name> <<email>>
    DATE <ISO-8601>
    SUBJECT <subject>
    <added>\t<deleted>\t<path>
    ...

Numstat lines use ``-`` for binary files. Merge commits simply have no
numstat lines. Anything that is not a COMMIT/AUTHOR/DATE/SUBJECT line
after the header block is treated as a numstat line; malformed numstat
lines are skipped rather than aborting the whole parse.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone

MIN_DATE = datetime.min.replace(tzinfo=timezone.utc)


@dataclass
class FileChange:
    path: str
    added: int
    deleted: int


@dataclass
class Commit:
    sha: str
    author: str
    email: str
    date: datetime
    subject: str
    files: list = field(default_factory=list)

    @property
    def changed(self) -> int:
        return sum(f.added + f.deleted for f in self.files)


_LOG_FORMAT = [
    "log",
    "--pretty=format:COMMIT %H%nAUTHOR %an <%ae>%nDATE %aI%nSUBJECT %s",
    "--numstat",
]


def build_command(repo: str, branch: str | None, since: str | None,
                  until: str | None) -> list:
    cmd = ["git", "-C", repo] + _LOG_FORMAT
    if branch:
        cmd.append(branch)
    if since:
        cmd += ["--since", since]
    if until:
        cmd += ["--until", until]
    return cmd


def collect(repo: str, branch: str | None = None, since: str | None = None,
            until: str | None = None) -> list:
    """Run git log in *repo* and return parsed :class:`Commit` objects."""
    cmd = build_command(repo, branch, since, until)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found on PATH") from exc
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if "not a git repository" in err:
            raise RuntimeError(f"not a git repository: {repo}")
        if "does not have any commits yet" in err:
            raise RuntimeError(f"repository has no commits yet: {repo}")
        raise RuntimeError(f"git log failed: {err or 'exit ' + str(proc.returncode)}")
    commits = parse(proc.stdout)
    if not commits:
        raise RuntimeError(f"no commits found in repository: {repo}")
    return commits


_NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.*)$")


def _num(value: str) -> int:
    return 0 if value == "-" else int(value)


def parse(text: str) -> list:
    """Parse git-log text (see module docstring) into Commit objects."""
    commits: list = []
    cur: Commit | None = None
    in_header = False
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("COMMIT "):
            if cur is not None:
                commits.append(cur)
            cur = Commit(sha=line[7:].strip(), author="", email="",
                         date=MIN_DATE, subject="")
            in_header = True
            continue
        if cur is None:
            continue
        if in_header:
            if line.startswith("AUTHOR "):
                body = line[7:]
                m = re.match(r"^(.*) <(.*)>$", body)
                if m:
                    cur.author, cur.email = m.group(1), m.group(2)
                else:
                    cur.author = body
            elif line.startswith("DATE "):
                raw_date = line[5:].strip()
                try:
                    cur.date = datetime.fromisoformat(raw_date)
                except ValueError:
                    cur.date = MIN_DATE
            elif line.startswith("SUBJECT "):
                cur.subject = line[8:]
            elif line == "":
                in_header = False
            else:
                in_header = False
                _maybe_numstat(cur, line)
        else:
            _maybe_numstat(cur, line)
    if cur is not None:
        commits.append(cur)
    return commits


def _maybe_numstat(commit: Commit, line: str) -> None:
    m = _NUMSTAT_RE.match(line)
    if m:
        commit.files.append(FileChange(path=m.group(3),
                                       added=_num(m.group(1)),
                                       deleted=_num(m.group(2))))
