import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import scan

SAMPLE = """
| Company | Role | Location | Application | Age |
| --- | --- | --- | --- | --- |
| **[Optiver](https://optiver.com)** | Software Engineer Intern | Chicago, IL | <a href="https://optiver.com/apply/123"><img src="x.png"></a> | 0d |
| ↳ | Hardware Intern | Austin, TX | <a href="https://optiver.com/apply/456"><img src="x.png"></a> | 1d |
| **[RTX](https://rtx.com)** | Software Engineering Intern - Summer 2027 | Largo, FL | <a href="https://rtx.com/apply/789">Apply</a> | 6d |
| **[Citadel](https://citadel.com)** | SWE Intern | NYC | <a href="https://citadel.com/apply/1">Apply</a> | 0d |
| **[Weird Co](https://x.com)** | Intern | Remote | <a href="https://x.com/apply/2">Apply</a> | 2d |
| **[Closed Co](https://y.com)** | 🔒 Intern | NYC | Closed | 1d |
"""

rows = scan.parse_tracker(SAMPLE)
by = {r["url"]: r for r in rows}

assert len(rows) == 5, f"expected 5 parsed rows, got {len(rows)}: {rows}"
assert by["https://optiver.com/apply/123"]["company"] == "Optiver"
assert by["https://optiver.com/apply/456"]["company"] == "Optiver", "continuation row must inherit company"
assert by["https://optiver.com/apply/456"]["age"] == 1
assert by["https://rtx.com/apply/789"]["age"] == 6
assert by["https://rtx.com/apply/789"]["location"] == "Largo, FL"

pairs = scan.load_categories()
assert scan.categorize("Optiver", pairs) == ("Quant", True)
assert scan.categorize("RTX", pairs)[0] == "Other"
assert scan.categorize("Replit", pairs)[0] == "Startups"
assert scan.categorize("Weird Co", pairs) == ("Other", False), "unknown must be flagged"
assert scan.categorize("Jane Street", pairs, "QT new", "sndsh404") == ("Quant", True)
assert scan.categorize("Unknown Fund", pairs, "Quantitative Developer Intern", "sndsh404") == ("Quant", True)
assert scan.categorize("Unknown Fund", pairs, "SWE Intern", "NUFT Quant") == ("Tech", True)
assert scan.categorize("Citadel", [("citadel", "Quant")] + pairs, "SWE Intern") == ("Tech", True)
assert scan.categorize("Melius", [("melius", "Quant")] + pairs,
                       "Software Engineer Intern") == ("Tech", True)
assert scan.categorize("UVIMCO", pairs, "Software Engineer Intern",
                       "NUFT Quant") == ("Tech", True)

applied = [a.lower() for a in scan.load_list(scan.APPLIED)]
assert any(a in "citadel" for a in applied), "Citadel must be filtered as already-applied"

assert scan.norm_url("https://a.com/x/?utm=1") == scan.norm_url("https://a.com/x")
assert scan.guess_term("SWE Intern Winter 2027", "") == "Winter 2027"
assert scan.guess_term("SWE Intern", "") == "Summer 2027"

# Source-format regression coverage: HTML tables, calendar dates, and NUFT's
# undated company-section format.
HTML = """
<table><tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr>
<tr><td><strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td><td>SWE</td><td>NYC</td>
<td><a href="https://acme.example/jobs/1"><img src="apply.png"></a></td><td>0d</td></tr></table>
"""
assert scan.parse_tracker(HTML)[0]["company"] == "Acme"
assert scan.parse_tracker(
    "| Acme | SWE | NYC | [apply](https://acme.example/jobs/2) | Aug 16 |",
    __import__("datetime").date(2026, 8, 18),
)[0]["age"] == 2
NUFT = """
## Acme
**Locations**: Chicago
|Role|Links|
|-------|-------|
|SWE|[✅ ](https://acme.example/jobs/3)|
"""
assert scan.parse_tracker(NUFT)[0]["location"] == "Chicago"

print("all parser tests passed")

# --- applied-list matching must be word-boundary, not substring -------------
m = scan.applied_matcher(scan.load_list(scan.APPLIED))
assert m("Citadel"),            "exact applied name must match"
assert m("Jane Street"),        "multi-word applied name must match"
assert m("SIG"),                "standalone short name must match"
assert not m("Two Sigma"),      "SIG must not swallow Two Sigma"
assert not m("Sigma Computing"), "SIG must not swallow Sigma Computing"
assert not m("Insight Global"), "SIG must not match inside a word"
assert not m("Virtusa"),        "Virtu must not swallow Virtusa"
assert not m("Optiver"),        "unrelated company must pass through"
print("applied-matcher tests passed")
