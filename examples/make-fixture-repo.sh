#!/bin/sh
# Build a small deterministic fixture repo for CommitLens demos/tests.
# Usage: make-fixture-repo.sh <target-dir>
# All dates/authors are pinned, so the generated report is reproducible.
set -eu
TARGET="$1"
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"
git init -q -b main
git config user.name "Ada Lovelace"
git config user.email "ada@example.com"

commit_as() {
  # $1 = name, $2 = email, $3 = ISO date, $4 = message
  GIT_AUTHOR_NAME="$1" GIT_AUTHOR_EMAIL="$2" \
  GIT_COMMITTER_NAME="$1" GIT_COMMITTER_EMAIL="$2" \
  GIT_AUTHOR_DATE="$3" GIT_COMMITTER_DATE="$3" \
  git commit -qm "$4"
}

printf 'def engine():\n    return 42\n' > engine.py
printf '# Demo repo\n' > README.md
git add .
commit_as "Ada Lovelace" "ada@example.com" "2026-01-05T09:00:00+00:00" "Add core engine"

printf 'def engine():\n    return 43\n' > engine.py
git add .
commit_as "Grace Hopper" "grace@example.com" "2026-01-06T10:30:00+00:00" "Fix parser edge case"

git checkout -qb feature
printf 'x = 1\n' > feature.py
git add .
commit_as "Ada Lovelace" "ada@example.com" "2026-03-01T14:00:00+00:00" "Add feature module"
git checkout -q main
GIT_AUTHOR_DATE="2026-03-02T09:00:00+00:00" GIT_COMMITTER_DATE="2026-03-02T09:00:00+00:00" \
  git merge -q --no-ff feature -m "Merge branch feature"

python3 -c "print('x = 2\n' * 400)" > engine.py
git add .
commit_as "Alan Turing" "alan@example.com" "2026-06-20T22:15:00+00:00" "Vendor the big dataset"

printf '# Demo repo\n\nPolished.\n' > README.md
git add .
commit_as "Ada Lovelace" "ada@example.com" "2026-06-21T08:00:00+00:00" "Polish docs"
echo "fixture repo ready at $TARGET"
