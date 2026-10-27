# Contributing to CommitLens

## Quick start

```sh
python3 -m commitlens /path/to/repo
python3 -m unittest discover -s tests   # 16 tests
```

Zero dependencies: Python 3.10+ standard library only, plus the `git` binary it reads history from.

## How to contribute

1. Fork, branch from `main`, one focused change per PR.
2. Add or update a test for any parser or analyser change — the suite must stay green.
3. In the PR, include an example repo or fixture that shows the change, and output before/after if behaviour changed.
4. Author identity is by git name as recorded; do not try to merge identities silently.

## License

MIT — by contributing, you agree your work is released under the MIT license.
