# Security Policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report privately through GitHub: **Security** tab → **Report a vulnerability**
(<https://github.com/YanisDigital/smm-page-audit/security/advisories/new>).

Include what you found, steps to reproduce, and the impact. You should get a reply within 7 days.

## In scope

- `scripts/build_report.py`: HTML injection or unsafe links in generated reports.
- `scripts/metrics.py`: crashes or unsafe handling of crafted `page_data.json`.
- `SKILL.md` and `references/`: instructions that could make Claude leak the user's data
  (cookies, the logged-in viewer's identity) or follow instructions hidden in collected content.

## Out of scope

- Instagram or Meta platform behavior, rate limits, or account restrictions.
- Data you collected yourself: audit folders are yours to protect; never publish them.
