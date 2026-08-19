# 2027 SWE / Quant Intern Postings

Internships for Winter / Summer 2027 in software engineering, quant and startup roles.

**0 open postings** &middot; last updated 2026-08-19 &middot; [browsable version](https://ianleung12.github.io/2027-SWE-Intern-Postings/)

Rows are dropped automatically once they are more than 30 days old. :sparkles: marks a posting added in the last 3 days.

---

### First run

This list ships empty on purpose. To populate it, run the **Daily scan** workflow
manually (Actions -> Daily scan -> Run workflow) with `days` set to `30`. That
backfills the last 30 days from the trackers and opens a PR. After that the
daily schedule keeps it current with a 2-day window.

### How this list is maintained

`data/postings.tsv` is the source of truth. `scripts/build.py` regenerates this README and `index.html` from it.

Sources scanned: [SimplifyJobs](https://github.com/SimplifyJobs/Summer2027-Internships), [NUFT Quant](https://github.com/northwesternfintech/2027QuantInternships), [vanshb03](https://github.com/vanshb03/Summer2027-Internships), [sndsh404](https://github.com/sndsh404/summer-2027-internships).

`data/applied.txt` lists companies already applied to. It is currently **not**
used for filtering - every posting is listed. Flip `USE_APPLIED_FILTER` in
`scripts/scan.py` to `True` to start excluding them again.
