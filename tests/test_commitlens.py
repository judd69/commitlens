"""Tests for CommitLens: parser, analysis, outputs and CLI exit codes."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commitlens.analyze import analyze  # noqa: E402
from commitlens.cli import main  # noqa: E402
from commitlens.gitlog import parse  # noqa: E402
from commitlens.outputs import render_html, render_json, render_text  # noqa: E402

FIXTURE = """COMMIT aaa111
AUTHOR Ada Lovelace <ada@example.com>
DATE 2026-01-05T09:00:00+00:00
SUBJECT Add core engine
10\t2\tengine.py
3\t0\tREADME.md
COMMIT bbb222
AUTHOR Grace Hopper <grace@example.com>
DATE 2026-01-06T10:30:00+00:00
SUBJECT Fix parser edge case
5\t5\tengine.py
COMMIT ccc333
AUTHOR Ada Lovelace <ada@example.com>
DATE 2026-03-01T14:00:00+00:00
SUBJECT Merge branch feature
COMMIT ddd444
AUTHOR Alan Turing <alan@example.com>
DATE 2026-06-20T22:15:00+00:00
SUBJECT Vendor the big dataset
-\t-\tdata.bin
600\t10\tengine.py
COMMIT eee555
AUTHOR Ada Lovelace <ada@example.com>
DATE 2026-06-21T08:00:00+00:00
SUBJECT Polish docs
1\t1\tREADME.md
"""


def fixture_commits():
    return parse(FIXTURE)


class TestParse(unittest.TestCase):
    def test_commit_count_and_fields(self):
        commits = fixture_commits()
        self.assertEqual(len(commits), 5)
        self.assertEqual(commits[0].sha, "aaa111")
        self.assertEqual(commits[0].author, "Ada Lovelace")
        self.assertEqual(commits[0].email, "ada@example.com")
        self.assertEqual(commits[0].subject, "Add core engine")
        self.assertEqual(commits[0].date,
                         datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc))

    def test_numstat_and_binary(self):
        commits = fixture_commits()
        self.assertEqual([(f.path, f.added, f.deleted)
                          for f in commits[0].files],
                         [("engine.py", 10, 2), ("README.md", 3, 0)])
        big = commits[3]
        self.assertEqual(big.files[0].added, 0)  # binary file: '-'
        self.assertEqual(big.changed, 610)

    def test_merge_commit_has_no_files(self):
        self.assertEqual(fixture_commits()[2].files, [])
        self.assertEqual(fixture_commits()[2].changed, 0)

    def test_malformed_lines_skipped(self):
        commits = parse("COMMIT zzz\nAUTHOR X <x@y>\nDATE 2026-01-01T00:00:00+00:00\n"
                        "SUBJECT hi\ngarbage line\n2\t1\tok.py\n")
        self.assertEqual(len(commits), 1)
        self.assertEqual([f.path for f in commits[0].files], ["ok.py"])


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.result = analyze(fixture_commits())

    def test_totals(self):
        t = self.result["totals"]
        self.assertEqual(t["commits"], 5)
        self.assertEqual(t["authors"], 3)
        self.assertEqual(t["files"], 3)
        self.assertEqual(t["added"], 619)
        self.assertEqual(t["deleted"], 18)

    def test_bus_factor(self):
        # Ada touches engine.py + README.md = 2 of 3 files -> covers >= 50%.
        self.assertEqual(self.result["bus_factor"]["value"], 1)
        self.assertAlmostEqual(self.result["bus_factor"]["coverage_pct"], 66.7, places=1)

    def test_author_ranking(self):
        authors = self.result["authors"]
        self.assertEqual(authors[0]["author"], "Ada Lovelace")
        self.assertEqual(authors[0]["commits"], 3)
        self.assertEqual(authors[0]["files"], 2)

    def test_churn_order_and_ownership(self):
        churn = self.result["churn"]
        self.assertEqual(churn[0]["path"], "engine.py")
        self.assertEqual(churn[0]["changed"], 632)
        self.assertEqual(churn[0]["top_author"], "Ada Lovelace")

    def test_large_commit_detected(self):
        large = self.result["large_commits"]
        self.assertEqual(len(large), 1)
        self.assertEqual(large[0]["sha"], "ddd444")
        self.assertEqual(large[0]["changed"], 610)

    def test_stale_files(self):
        # Last commit 2026-06-21; with 180 days, nothing is stale.
        self.assertEqual(self.result["stale_all_count"], 0)
        # A dedicated two-commit fixture: old.py untouched since January,
        # new.py touched in June. With a 30-day window only old.py is stale.
        commits = parse(
            "COMMIT a1\nAUTHOR A <a@x>\nDATE 2026-01-10T09:00:00+00:00\n"
            "SUBJECT old work\n5\t0\told.py\n"
            "COMMIT b2\nAUTHOR B <b@x>\nDATE 2026-06-21T08:00:00+00:00\n"
            "SUBJECT new work\n3\t0\tnew.py\n")
        result = analyze(commits, stale_days=30)
        stale_paths = {r["path"] for r in result["stale"]}
        self.assertEqual(stale_paths, {"old.py"})

    def test_rhythm_and_monthly(self):
        rhythm = self.result["rhythm"]
        # 2026-01-05 is a Monday, 09:00.
        self.assertEqual(rhythm[0][9], 1)
        months = {m["month"]: m["commits"] for m in self.result["monthly"]}
        self.assertEqual(months, {"2026-01": 2, "2026-03": 1, "2026-06": 2})


class TestOutputs(unittest.TestCase):
    def setUp(self):
        self.result = analyze(fixture_commits())

    def test_text_contains_key_numbers(self):
        text = render_text(self.result)
        self.assertIn("Bus factor: 1", text)
        self.assertIn("Ada Lovelace", text)
        self.assertIn("engine.py", text)

    def test_json_round_trips(self):
        data = json.loads(render_json(self.result))
        self.assertEqual(data["totals"]["commits"], 5)
        self.assertEqual(data["bus_factor"]["value"], 1)

    def test_html_is_self_contained(self):
        html_doc = render_html(self.result, "fixture-repo")
        self.assertIn("CommitLens", html_doc)
        self.assertIn("engine.py", html_doc)
        self.assertIn("bus factor", html_doc)
        self.assertNotIn("http://", html_doc.replace("https://github.com", ""))
        self.assertNotIn("<script src", html_doc)
        self.assertNotIn("<link ", html_doc)


class TestCli(unittest.TestCase):
    def test_not_a_repo_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            with io.StringIO() as buf, redirect_stdout(buf):
                code = main([tmp])
            self.assertEqual(code, 1)

    def test_end_to_end_on_real_repo(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("git not available")
        with tempfile.TemporaryDirectory() as tmp:
            def run(*args, env=None):
                full_env = dict(os.environ)
                full_env.update(env or {})
                subprocess.run([git] + list(args), cwd=tmp, env=full_env,
                               check=True, capture_output=True)
            run("init", "-q", "-b", "main")
            run("config", "user.name", "Ada")
            run("config", "user.email", "ada@example.com")
            with open(os.path.join(tmp, "a.py"), "w") as fh:
                fh.write("x = 1\n")
            run("add", ".")
            run("commit", "-qm", "first",
                env={"GIT_AUTHOR_DATE": "2026-01-05T09:00:00+00:00",
                     "GIT_COMMITTER_DATE": "2026-01-05T09:00:00+00:00"})
            with io.StringIO() as buf, redirect_stdout(buf):
                code = main([tmp, "--format", "json"])
                out = buf.getvalue()
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["totals"]["commits"], 1)
            self.assertEqual(data["bus_factor"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
