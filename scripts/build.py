#!/usr/bin/env python3
"""Regenerate README.md and index.html from data/postings.tsv.

Single source of truth is data/postings.tsv. Edit that, then run:
    python3 scripts/build.py
"""
import csv, datetime, html, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "postings.tsv"
STALE_DAYS = 30          # rows older than this are dropped by prune()
NEW_DAYS = 3             # rows this recent get a "new" badge

ORDER = ["Quant", "Tech", "Startups", "Other"]
BLURB = {
    "Quant": "Trading firms, market makers and hedge funds.",
    "Tech": "Big tech, AI labs and established technology companies.",
    "Startups": "Early-stage and venture-backed technology companies.",
    "Other": "Everything else that cleared the bar.",
}

def today():
    return datetime.date.today()

def load():
    with DATA.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    # Legacy labels collapse into the new four-category taxonomy. The scan
    # will persist the normalized values when it next runs.
    for row in rows:
        if row["category"] in {"Defense & Aero", "Finance"}:
            row["category"] = "Other"
    return rows

def parse(d):
    return datetime.date.fromisoformat(d)

def prune(rows, ref=None):
    ref = ref or today()
    cutoff = ref - datetime.timedelta(days=STALE_DAYS)
    return [r for r in rows if parse(r["added"]) >= cutoff]

def is_new(row, ref=None):
    ref = ref or today()
    return (ref - parse(row["added"])).days <= NEW_DAYS

def sort_key(r):
    return (-parse(r["added"]).toordinal(), r["company"].lower(), r["role"].lower())

# ---------------------------------------------------------------- README

def build_readme(rows, ref):
    L = []
    L.append("# 2027 SWE / Quant Intern Postings")
    L.append("")
    L.append("Internships for Winter / Summer 2027 in software engineering, quant and startup roles.")
    L.append("")
    L.append(f"**{len(rows)} open postings** &middot; last updated {ref.isoformat()} "
             f"&middot; [browsable version](https://ianleung12.github.io/2027-SWE-Intern-Postings/)")
    L.append("")
    L.append("Rows are dropped automatically once they are more than "
             f"{STALE_DAYS} days old. :sparkles: marks a posting added in the last "
             f"{NEW_DAYS} days.")
    L.append("")
    for cat in ORDER:
        sub = sorted([r for r in rows if r["category"] == cat], key=sort_key)
        if not sub:
            continue
        L.append(f"## {cat} <sub>({len(sub)})</sub>")
        L.append("")
        L.append(f"*{BLURB[cat]}*")
        L.append("")
        L.append("| Company | Role | Term | Location | Added | Apply |")
        L.append("| --- | --- | --- | --- | --- | --- |")
        for r in sub:
            star = " :sparkles:" if is_new(r, ref) else ""
            L.append("| **{c}**{s} | {ro} | {t} | {loc} | {a} | [Apply]({u}) |".format(
                c=r["company"], s=star, ro=r["role"], t=r["term"],
                loc=r["location"], a=r["added"], u=r["url"]))
        L.append("")
    L.append("---")
    L.append("")
    L.append("### How this list is maintained")
    L.append("")
    L.append("`data/postings.tsv` is the source of truth. `scripts/build.py` regenerates "
             "this README and `index.html` from it.")
    L.append("")
    L.append("Sources scanned: "
             "[SimplifyJobs](https://github.com/SimplifyJobs/Summer2027-Internships), "
             "[NUFT Quant](https://github.com/northwesternfintech/2027QuantInternships), "
             "[vanshb03](https://github.com/vanshb03/Summer2027-Internships), "
             "[sndsh404](https://github.com/sndsh404/summer-2027-internships).")
    L.append("")
    L.append("Postings already applied to are kept out of this list on purpose.")
    L.append("")
    return "\n".join(L)

# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#faf9f7;--panel:#fff;--ink:#1c1b19;--muted:#6b6862;--line:#e5e2dc;
--accent:#3d5a80;--open:#2f6f4f;--open-bg:#e6f2ea;--soon:#8a6a1f;--soon-bg:#f7efd9;
--new:#8c3b5e;--new-bg:#fbe9f0}
@media (prefers-color-scheme:dark){:root{--bg:#16151a;--panel:#1e1d23;--ink:#eceaf0;
--muted:#9b97a3;--line:#31303a;--accent:#8fb3d9;--open:#7fc9a0;--open-bg:#1d3329;
--soon:#d9bb70;--soon-bg:#332c1a;--new:#e8a3c0;--new-bg:#38202b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);padding:32px 20px 64px;
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0 0 20px;font-size:14px}
h2{font-size:17px;margin:34px 0 4px;letter-spacing:-.01em}
h2 .n{color:var(--muted);font-weight:400;font-size:13px;margin-left:6px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
input[type=search]{flex:1;min-width:200px;padding:9px 12px;border:1px solid var(--line);
border-radius:8px;background:var(--panel);color:var(--ink);font-size:14px}
textarea{width:100%;min-height:58px;padding:9px 12px;border:1px solid var(--line);
border-radius:8px;background:var(--panel);color:var(--ink);font:14px inherit;resize:vertical}
.exclude{width:100%;margin:0 0 10px}.exclude label{display:block;color:var(--muted);
font-size:12px;margin-bottom:4px}.exclude small{color:var(--muted);font-size:11px}
button{padding:8px 13px;border:1px solid var(--line);border-radius:8px;
background:var(--panel);color:var(--ink);font-size:13px;cursor:pointer}
button.on{background:var(--accent);border-color:var(--accent);color:#fff}
table{width:100%;border-collapse:collapse;background:var(--panel);
border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:6px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.07em;
color:var(--muted);font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line)}
td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.co{font-weight:600;white-space:nowrap}
td.role{color:var(--muted)}
td.added{color:var(--muted);font-size:12.5px;white-space:nowrap}
a{color:var(--accent)}
.pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11.5px;
font-weight:600;white-space:nowrap}
.p-sum{background:var(--open-bg);color:var(--open)}
.p-off{background:var(--soon-bg);color:var(--soon)}
.tag-new{background:var(--new-bg);color:var(--new);margin-left:6px}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);
color:var(--muted);font-size:12.5px}
tr.hide{display:none}
"""

JS = """
(function(){
var q=document.getElementById('q'),exclude=document.getElementById('exclude'),
rows=[].slice.call(document.querySelectorAll('tbody tr')),f='all';
try{exclude.value=localStorage.getItem('excludedCompanies')||'';}catch(e){}
function list(){return exclude.value.split(/[\n,]+/).map(function(x){return x.trim().toLowerCase();}).filter(Boolean);}
function apply(){var t=q.value.toLowerCase(),blocked=list();
 rows.forEach(function(r){var txt=r.textContent.toLowerCase();
  var company=r.querySelector('.co').textContent.trim().toLowerCase();
  var okT=!t||txt.indexOf(t)>-1,okE=blocked.indexOf(company)<0,okF;
  if(f==='all')okF=true;
  else if(f==='new')okF=!!r.querySelector('.tag-new');
  else if(f==='off')okF=!/summer 2027/.test(txt);
  else okF=txt.indexOf(f.toLowerCase())>-1;
  r.classList.toggle('hide',!(okT&&okE&&okF));});
 try{localStorage.setItem('excludedCompanies',exclude.value);}catch(e){}
}
q.addEventListener('input',apply);
exclude.addEventListener('input',apply);
[].slice.call(document.querySelectorAll('button[data-f]')).forEach(function(b){
 b.addEventListener('click',function(){
  document.querySelectorAll('button[data-f]').forEach(function(x){x.classList.remove('on')});
  b.classList.add('on');f=b.dataset.f;apply();});});
})();
"""

def build_html(rows, ref):
    e = html.escape
    P = []
    P.append('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">')
    P.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    P.append("<title>2027 SWE / Quant Intern Postings</title>")
    P.append(f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">")
    P.append("<h1>2027 SWE / Quant Intern Postings</h1>")
    P.append(f'<p class="sub">{len(rows)} open postings &middot; updated {ref.isoformat()} '
             f'&middot; <a href="https://github.com/IanLeung12/2027-SWE-Intern-Postings">source on GitHub</a>. '
             f'Rows drop off after {STALE_DAYS} days.</p>')
    P.append('<div class="controls"><input type="search" id="q" placeholder="Filter by company, role, or location...">'
             '<button data-f="all" class="on">All</button><button data-f="new">New</button>'
             '<button data-f="Summer 2027">Summer 2027</button>'
             '<button data-f="off">Winter / Spring</button></div>'
             '<div class="exclude"><label for="exclude">Exclude companies</label>'
             '<textarea id="exclude" placeholder="One company per line or separate with commas"></textarea>'
             '<small>Exclusions are saved in this browser and matched case-insensitively.</small></div>')
    for cat in ORDER:
        sub = sorted([r for r in rows if r["category"] == cat], key=sort_key)
        if not sub:
            continue
        P.append(f'<h2>{e(cat)} <span class="n">{len(sub)} open &mdash; {e(BLURB[cat])}</span></h2>')
        P.append("<table><thead><tr><th>Company</th><th>Role</th><th>Term</th>"
                 "<th>Location</th><th>Added</th><th>Apply</th></tr></thead><tbody>")
        for r in sub:
            pill = "p-sum" if "summer 2027" in r["term"].lower() else "p-off"
            tag = '<span class="pill tag-new">new</span>' if is_new(r, ref) else ""
            P.append(
                f'<tr><td class="co">{e(r["company"])}</td>'
                f'<td class="role">{e(r["role"])} {tag}</td>'
                f'<td><span class="pill {pill}">{e(r["term"])}</span></td>'
                f'<td>{e(r["location"])}</td>'
                f'<td class="added">{e(r["added"])}</td>'
                f'<td><a href="{e(r["url"])}">link</a></td></tr>')
        P.append("</tbody></table>")
    P.append('<footer>Generated by <code>scripts/build.py</code> from '
             '<code>data/postings.tsv</code>. Links are copied from the source trackers '
             'and are not re-verified after the date shown &mdash; a posting may close '
             'before its row ages out.</footer>')
    P.append(f"</div>\n<script>{JS}</script>\n</body>\n</html>")
    return "\n".join(P)

def main():
    ref = today()
    rows = load()
    kept = prune(rows, ref)
    dropped = len(rows) - len(kept)
    (ROOT / "README.md").write_text(build_readme(kept, ref), encoding="utf-8")
    (ROOT / "index.html").write_text(build_html(kept, ref), encoding="utf-8")
    if dropped:
        # keep the TSV in sync with what was published
        with (DATA).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t",
                               lineterminator="\n")
            w.writeheader()
            w.writerows(kept)
    print(f"built {len(kept)} rows ({dropped} pruned as stale)")

if __name__ == "__main__":
    sys.exit(main())
