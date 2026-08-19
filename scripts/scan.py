#!/usr/bin/env python3
"""Scan the public 2027 internship trackers for postings added in the last N days.

Appends anything new to data/postings.tsv. Designed to run in CI and open a PR,
so a bad parse never lands on main unreviewed.

    python3 scripts/scan.py --days 2
    python3 scripts/scan.py --days 2 --dry-run
"""
import argparse, csv, datetime, pathlib, re, sys, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "postings.tsv"
APPLIED = ROOT / "data" / "applied.txt"
CATS = ROOT / "data" / "categories.tsv"
REPORT = ROOT / "scan-report.md"

# Skip companies listed in data/applied.txt?
#   False -> everything is listed, applied.txt is ignored (current setting)
#   True  -> postings from those companies are dropped at scan time
# The file is kept either way, so this is a one-line switch.
USE_APPLIED_FILTER = False

TRACKERS = {
    "SimplifyJobs": "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
    "NUFT Quant":   "https://raw.githubusercontent.com/northwesternfintech/2027QuantInternships/main/README.md",
    "sndsh404":     "https://raw.githubusercontent.com/sndsh404/summer-2027-internships/main/README.md",
    "vanshb03":     "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/README.md",
}

AGE_RE = re.compile(r"^(\d+)\s*(d|h|mo)$", re.I)
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
SHORT_DATE_RE = re.compile(r"^([A-Za-z]{3,9})\s+(\d{1,2})$")
URL_RE = re.compile(r'https?://[^\s"\'<>)\]]+')
MDLINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
TAG_RE = re.compile(r"<[^>]+>")
EMOJI_RE = re.compile(
    r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF\U00002B00-\U00002BFF]"
    r"|[\uFE0E\uFE0F\u200D]"
)

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "2027-intern-scanner"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def clean(cell):
    cell = MDLINK_RE.sub(r"\1", cell)
    cell = TAG_RE.sub("", cell)
    cell = cell.replace("**", "").replace("*", "").replace("🔒", "")
    cell = EMOJI_RE.sub("", cell)
    return " ".join(cell.split()).strip()

def age_days(cell):
    m = AGE_RE.match(clean(cell))
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    return {"h": 0, "d": n, "mo": n * 30}[unit]

def date_age(cell, today=None):
    """Return the age of an ISO or ``Mon DD`` date, or None."""
    today = today or datetime.date.today()
    value = clean(cell)
    match = ISO_DATE_RE.match(value)
    if match:
        posted = datetime.date(*(int(x) for x in match.groups()))
    else:
        match = SHORT_DATE_RE.match(value)
        if not match:
            return None
        try:
            posted = datetime.date(today.year, datetime.datetime.strptime(
                match.group(1)[:3], "%b").month, int(match.group(2)))
        except ValueError:
            return None
        if posted > today:
            posted = posted.replace(year=posted.year - 1)
    return max(0, (today - posted).days)

def table_rows(text):
    """Yield cells from Markdown tables and HTML tables."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|"):
            cells = [c for c in line.split("|")[1:-1]]
            if cells:
                yield cells
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", text, re.I | re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.I | re.S)
        if cells:
            yield cells

def parse_tracker(text, today=None):
    """Yield postings from the tracker formats used by the source repos."""
    today = today or datetime.date.today()
    out, last_company = [], None
    for cells in table_rows(text):
        if len(cells) < 4:
            continue
        if set(clean("".join(cells))) <= {"-", ":", " "}:
            continue                                    # separator row
        age = next((age_days(c) for c in reversed(cells) if age_days(c) is not None), None)
        if age is None:
            age = next((date_age(c, today) for c in reversed(cells)
                        if date_age(c, today) is not None), None)
        if age is None:
            continue                                    # no age column -> can't date it
        company = clean(cells[0])
        if company in {"", "↳", "->"} or company.startswith("↳"):
            company = last_company                      # continuation of previous company
        if not company:
            continue
        last_company = company
        if company.lower() in {"company", "name"}:
            continue                                    # header row
        if "\U0001f512" in "|".join(cells):
            continue                                    # closed posting
        # Look for the apply link only in cells AFTER the company cell, so we
        # never mistake the company's homepage link for an application URL.
        apply_url = None
        for cell in cells[1:]:
            for u in URL_RE.findall(cell):
                if u.endswith((".png", ".svg", ".jpg", ".gif")):
                    continue
                if "simplify.jobs" in u or "/img/" in u:
                    continue
                apply_url = u
                break
            if apply_url:
                break
        if not apply_url:
            continue                                    # no live application link
        out.append({
            "company": company,
            "role": clean(cells[1]) if len(cells) > 1 else "",
            "location": clean(cells[2]) if len(cells) > 2 else "",
            "url": apply_url.rstrip("),"),
            "age": age,
        })
    if out:
        return out

    # NUFT's generated README has one section per company and role/link
    # tables, but intentionally carries no posting dates.
    company = location = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            company, location = clean(heading.group(1)), ""
            continue
        loc = re.match(r"^\*\*Locations\*\*:\s*(.+)$", line)
        if loc:
            location = clean(loc.group(1))
            continue
        if company and line.lstrip().startswith("|"):
            cells = [c for c in line.strip().split("|")[1:-1]]
            if len(cells) < 2 or cells[0].lower() in {"role", "-------"}:
                continue
            links = URL_RE.findall(cells[1])
            apply_url = next((u for u in links if not u.startswith("mailto:")), None)
            if not apply_url or "🔒" in line:
                continue
            out.append({"company": company, "role": clean(cells[0]),
                        "location": location, "url": apply_url.rstrip("),"), "age": 0})
    return out

def load_list(path):
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]

def applied_matcher(names):
    """Match applied-company names on word boundaries, not raw substrings.

    A plain substring test makes short entries dangerous: "SIG" swallows
    "Two Sigma" and "Insight Global". Boundaries keep "SIG" matching only the
    standalone token.
    """
    if not names:
        return lambda _company: False
    pat = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in names) + r")(?!\w)", re.I)
    return lambda company: bool(pat.search(company))

def load_categories():
    pairs = []
    for line in load_list(CATS):
        if "\t" not in line:
            continue
        pat, cat = line.split("\t", 1)
        if pat.strip().lower() == "pattern":
            continue
        pairs.append((pat.strip().lower(), cat.strip()))
    return pairs

QUANT_ROLE_RE = re.compile(
    r"\b(?:qt|qr|qd|quant(?:itative)?\s+(?:trader|trading|research(?:er)?|developer|dev))\b",
    re.I,
)
TECH_ROLE_RE = re.compile(
    r"\b(?:swe|software engineer(?:ing)?|software developer|full[- ]stack|frontend|backend)\b",
    re.I,
)

def categorize(company, pairs, role="", source=""):
    """Categorize using reliable source/role signals before name rules."""
    if QUANT_ROLE_RE.search(role):
        return "Quant", True
    if TECH_ROLE_RE.search(role):
        return "Tech", True
    low = company.lower()
    for pat, cat in pairs:
        if pat in low:
            return cat, True
    return "Other", False

def norm_url(u):
    u = u.split("?")[0].rstrip("/")
    return u.lower()

def guess_term(role, location):
    blob = f"{role} {location}".lower()
    for needle, term in (("summer 2027", "Summer 2027"), ("winter 2027", "Winter 2027"),
                         ("spring 2027", "Spring 2027"), ("fall 2026", "Fall 2026")):
        if needle in blob:
            return term
    return "Summer 2027"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    today = datetime.date.today()
    with DATA.open(newline="", encoding="utf-8") as fh:
        existing = list(csv.DictReader(fh, delimiter="\t"))
    fields = list(existing[0].keys()) if existing else \
        ["category", "company", "role", "term", "location", "added", "url"]
    seen = {norm_url(r["url"]) for r in existing}

    is_applied = (applied_matcher(load_list(APPLIED))
    if USE_APPLIED_FILTER else (lambda _c: False))
    pairs = load_categories()
    learned = {row.get("company", "") for row in existing
               if QUANT_ROLE_RE.search(row.get("role", ""))}
    pairs_for_scan = ([(company.lower(), "Quant") for company in learned] + pairs)

    reclassified = 0
    rewritten = False
    for row in existing:
        for field in ("company", "role", "location"):
            normalized = clean(row.get(field, ""))
            if normalized != row.get(field, ""):
                row[field] = normalized
                rewritten = True
        category, known = categorize(row.get("company", ""), pairs_for_scan,
                                      row.get("role", ""))
        if known and row.get("category") != category:
            row["category"] = category
            reclassified += 1
            rewritten = True

    added, unknown, failures = [], [], []
    for name, url in TRACKERS.items():
        try:
            text = fetch(url)
        except Exception as exc:                        # noqa: BLE001
            failures.append(f"{name}: {exc}")
            continue
        rows = parse_tracker(text)
        if not rows:
            failures.append(f"{name}: parsed 0 rows (format may have changed)")
            continue
        for r in rows:
            if r["age"] > args.days:
                continue
            if norm_url(r["url"]) in seen:
                continue
            if is_applied(r["company"]):
                continue
            cat, known = categorize(r["company"], pairs_for_scan, r["role"], name)
            if not known:
                unknown.append(r["company"])
            elif cat == "Quant" and r["company"] not in learned:
                learned.add(r["company"])
                pairs_for_scan.insert(0, (r["company"].lower(), "Quant"))
            seen.add(norm_url(r["url"]))
            added.append({
                "category": cat,
                "company": r["company"],
                "role": r["role"] or "Software Engineer Intern",
                "term": guess_term(r["role"], r["location"]),
                "location": r["location"],
                "added": (today - datetime.timedelta(days=r["age"])).isoformat(),
                "url": r["url"],
            })

    # A newly recognized Quant company retroactively classifies all of its
    # existing and newly found postings, regardless of their individual role.
    for row in existing + added:
        category, known = categorize(row.get("company", ""), pairs_for_scan)
        if known and row.get("category") != category:
            row["category"] = category
            if row in existing:
                reclassified += 1
                rewritten = True

    if learned and not args.dry_run:
        existing_rules = {(pat, cat) for pat, cat in pairs}
        with CATS.open("a", encoding="utf-8") as fh:
            for company in sorted(set(learned), key=str.lower):
                rule = (company.lower(), "Quant")
                if rule not in existing_rules:
                    fh.write(f"{rule[0]}\t{rule[1]}\n")
                    existing_rules.add(rule)

    if rewritten and not args.dry_run:
        with DATA.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(existing)

    lines = [f"### Scan {today.isoformat()}", ""]
    lines.append(f"- trackers OK: {len(TRACKERS) - len(failures)}/{len(TRACKERS)}")
    lines.append(f"- new postings: **{len(added)}**")
    if reclassified:
        lines.append(f"- reclassified postings: **{reclassified}**")
    if failures:
        lines.append("")
        lines.append("**Sources that failed — these were NOT scanned:**")
        lines += [f"- {f}" for f in failures]
    if unknown:
        lines.append("")
        lines.append("**Filed as `Other` — no category rule matched. Review these, "
                     "and add a rule to `data/categories.tsv` if they should be kept:**")
        lines += [f"- {c}" for c in sorted(set(unknown))]
    if added:
        lines.append("")
        lines.append("| Category | Company | Role | Location | Added |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in added:
            lines.append(f"| {r['category']} | {r['company']} | {r['role']} | "
                         f"{r['location']} | {r['added']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.dry_run:
        print("\n".join(lines))
        return 0

    if added:
        with DATA.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
            w.writerows(added)
    print(f"{len(added)} new; {len(failures)} source failures; {len(set(unknown))} uncategorized")
    return 0

if __name__ == "__main__":
    sys.exit(main())
