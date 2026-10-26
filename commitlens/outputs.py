"""Text, JSON and self-contained HTML renderers for an analysis dict."""

from __future__ import annotations

import html
import json
from datetime import datetime

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def to_jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(value)
    return value


def render_json(result: dict) -> str:
    return json.dumps(to_jsonable(result), indent=2)


def _short(date_iso: str) -> str:
    return date_iso[:10]


def render_text(result: dict) -> str:
    t = result["totals"]
    bf = result["bus_factor"]
    lines = []
    lines.append("CommitLens report")
    lines.append("=" * 60)
    lines.append(f"Commits: {t['commits']}  Authors: {t['authors']}  "
                 f"Files touched: {t['files']}")
    lines.append(f"Lines: +{t['added']} / -{t['deleted']}  "
                 f"Span: {_short(t['first'])} -> {_short(t['last'])} "
                 f"({t['span_days']} days)")
    lines.append(f"Bus factor: {bf['value']} "
                 f"(covers {bf['coverage_pct']}% of files)")
    lines.append("")
    lines.append("Top contributors (commits, +/-, files):")
    for a in result["authors"][:10]:
        lines.append(f"  {a['author']:<24} {a['commits']:>4}  "
                     f"+{a['added']:<7} -{a['deleted']:<7} {a['files']} files")
    lines.append("")
    lines.append("Hottest files (commits, changed lines, top author):")
    for r in result["churn"]:
        lines.append(f"  {r['path']:<44} {r['commits']:>3}  "
                     f"{r['changed']:>6}  {r['top_author']}")
    if result["large_commits"]:
        lines.append("")
        lines.append("Large commits:")
        for c in result["large_commits"]:
            lines.append(f"  {c['sha']} {c['author']:<20} "
                         f"{c['changed']:>5} lines  {c['subject']}")
    if result["stale"]:
        lines.append("")
        lines.append(f"Stale files ({result['stale_all_count']} total, "
                     "showing first few):")
        for r in result["stale"]:
            lines.append(f"  {r['path']:<44} last touched "
                         f"{_short(r['last'])}")
    return "\n".join(lines) + "\n"


def _heatmap_cells(rhythm) -> str:
    peak = max((max(row) for row in rhythm), default=0) or 1
    cells = []
    for d, row in enumerate(rhythm):
        cells.append(f'<div class="rowlabel">{WEEKDAYS[d]}</div>')
        for value in row:
            alpha = value / peak
            bg = f"rgba(52, 211, 153, {0.08 + 0.85 * alpha:.2f})" if value else "#151a1e"
            title = f"{WEEKDAYS[d]} {value} commit(s)"
            cells.append(f'<div class="cell" style="background:{bg}" '
                         f'title="{title}">{value if value else ""}</div>')
    return "".join(cells)


def _rows(rows, cols) -> str:
    out = []
    for r in rows:
        out.append("<tr>" + "".join(
            f"<td>{html.escape(str(r[c]))}</td>" for c in cols) + "</tr>")
    return "".join(out)


def render_html(result: dict, repo_label: str) -> str:
    t = result["totals"]
    bf = result["bus_factor"]
    peak_month = max((m["commits"] for m in result["monthly"]), default=0) or 1
    month_bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{m["month"]}</span>'
        f'<div class="bar-track"><div class="bar-fill" '
        f'style="width:{100 * m["commits"] / peak_month:.0f}%"></div></div>'
        f'<span class="bar-value">{m["commits"]}</span></div>'
        for m in result["monthly"])
    author_rows = _rows(result["authors"],
                        ["author", "commits", "added", "deleted", "files"])
    churn_rows = _rows(
        [{**r, "last": _short(str(r["last"]))} for r in result["churn"]],
        ["path", "commits", "added", "deleted", "top_author"])
    large_rows = _rows(
        [{**c, "date": _short(c["date"])} for c in result["large_commits"]],
        ["sha", "author", "date", "changed", "subject"])
    stale_rows = _rows(
        [{**r, "last": _short(r["last"])} for r in result["stale"]],
        ["path", "commits", "changed", "last", "top_author"])
    repo = html.escape(repo_label)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CommitLens report — {repo}</title>
<style>
body{{background:#0a0b0d;color:#eef2f3;font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;margin:0;padding:32px 16px}}
main{{max-width:980px;margin:0 auto}}
h1{{font-size:30px;margin:0 0 4px}} h1 span{{color:#34d399}}
.sub{{color:#94a1a7;margin:0 0 28px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:28px}}
.card{{background:#101315;border:1px solid #232b2f;border-radius:12px;padding:16px}}
.card b{{font-size:28px;display:block}} .card span{{color:#94a1a7;font-size:13px}}
.card.alert b{{color:#f43f5e}} .card.alert{{border-color:#f43f5e55}}
section{{background:#101315;border:1px solid #232b2f;border-radius:12px;padding:20px;margin-bottom:20px}}
h2{{margin:0 0 14px;font-size:18px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;color:#94a1a7;cursor:pointer;border-bottom:1px solid #232b2f;padding:6px 8px}}
td{{padding:6px 8px;border-bottom:1px solid #1b2125;word-break:break-all}}
.heat{{display:grid;grid-template-columns:44px repeat(24,1fr);gap:3px;font-size:11px}}
.rowlabel{{color:#94a1a7;line-height:22px}}
.cell{{height:22px;border-radius:4px;text-align:center;line-height:22px;color:#eef2f3}}
.hourlabels{{display:grid;grid-template-columns:44px repeat(24,1fr);gap:3px;color:#94a1a7;font-size:11px;margin-bottom:4px}}
.bar-row{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}}
.bar-label{{width:64px;color:#94a1a7}} .bar-track{{flex:1;background:#1b2125;height:14px;border-radius:7px;overflow:hidden}}
.bar-fill{{height:100%;background:linear-gradient(90deg,#059669,#34d399)}}
.bar-value{{width:36px;text-align:right}}
.note{{color:#94a1a7;font-size:13px}} a{{color:#34d399}}
</style></head><body><main>
<h1>🔍 CommitLens <span>report</span></h1>
<p class="sub">History X-ray of <b>{repo}</b> · {_short(t["first"])} → {_short(t["last"])}</p>
<div class="cards">
<div class="card"><b>{t["commits"]}</b><span>commits</span></div>
<div class="card"><b>{t["authors"]}</b><span>authors</span></div>
<div class="card"><b>{t["files"]}</b><span>files touched</span></div>
<div class="card"><b>+{t["added"]} / −{t["deleted"]}</b><span>lines changed</span></div>
<div class="card alert"><b>{bf["value"]}</b><span>bus factor · covers {bf["coverage_pct"]}% of files</span></div>
</div>
<section><h2>When does the team commit? (weekday × hour)</h2>
<div class="hourlabels"><span></span>{''.join(f'<span>{h}</span>' for h in range(24))}</div>
<div class="heat">{_heatmap_cells(result["rhythm"])}</div>
<p class="note">Rows are weekdays, columns are hours (local repo time as recorded by git). Brighter = more commits.</p>
</section>
<section><h2>Commits per month</h2>{month_bars or '<p class="note">No monthly data.</p>'}</section>
<section><h2>Top contributors</h2>
<table><thead><tr><th data-i="0">Author ↕</th><th data-i="1">Commits ↕</th><th data-i="2">Added ↕</th><th data-i="3">Deleted ↕</th><th data-i="4">Files ↕</th></tr></thead>
<tbody>{author_rows}</tbody></table></section>
<section><h2>Hottest files</h2>
<table><thead><tr><th data-i="0">File ↕</th><th data-i="1">Commits ↕</th><th data-i="2">Added ↕</th><th data-i="3">Deleted ↕</th><th data-i="4">Top author ↕</th></tr></thead>
<tbody>{churn_rows}</tbody></table></section>
<section><h2>Large commits (≥ threshold)</h2>
<table><thead><tr><th data-i="0">SHA ↕</th><th data-i="1">Author ↕</th><th data-i="2">Date ↕</th><th data-i="3">Changed ↕</th><th data-i="4">Subject ↕</th></tr></thead>
<tbody>{large_rows or '<tr><td colspan="5" class="note">None — no commit crossed the threshold.</td></tr>'}</tbody></table></section>
<section><h2>Stale files ({result["stale_all_count"]} total)</h2>
<table><thead><tr><th data-i="0">File ↕</th><th data-i="1">Commits ↕</th><th data-i="2">Changed ↕</th><th data-i="3">Last touched ↕</th><th data-i="4">Top author ↕</th></tr></thead>
<tbody>{stale_rows or '<tr><td colspan="5" class="note">None — every file was touched recently.</td></tr>'}</tbody></table>
<p class="note">Generated by <a href="https://github.com/judd69/commitlens">CommitLens</a> — zero-dependency Python. Bus factor = fewest authors covering ≥ 50% of files.</p>
</section></main>
<script>
document.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {{
  const table = th.closest("table"), i = +th.dataset.i, tbody = table.tBodies[0];
  const rows = [...tbody.rows];
  const num = rows.every(r => /^\\d+$/.test(r.cells[i].textContent.trim()));
  rows.sort((a, b) => {{
    const x = a.cells[i].textContent.trim(), y = b.cells[i].textContent.trim();
    return num ? (+x - +y) : x.localeCompare(y);
  }});
  if (table.dataset.dir === "asc") {{ rows.reverse(); table.dataset.dir = "desc"; }}
  else table.dataset.dir = "asc";
  rows.forEach(r => tbody.appendChild(r));
}}));
</script></body></html>
"""
