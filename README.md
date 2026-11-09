# Instagram Page Audit — a Claude Code skill

Give Claude an Instagram profile link and get one HTML report:

- statistics and effectiveness (engagement rate, Reels views, posting cadence, format mix, top and bottom posts);
- audience and positioning;
- a 90-day promotion strategy with ready-to-paste bio and highlight texts;
- a 4-week content plan and posting schedule;
- ideas for Reels, Stories and carousels;
- a targeted-ads plan for Meta Ads (a plan only — nothing is launched);
- ways to attract new clients (lead magnets, DM keyword funnels, scripts);
- KPIs and an action checklist.

The goal behind every section: make the page recognizable, raise audience activity and bring in new clients.
Every number in the report comes from collected data or from a cited source; everything else is labeled as an estimate or assumption.

## ⚠️ Responsible use — read first

- **Unofficial.** This project is not affiliated with, endorsed by or connected to Meta or Instagram.
- **Terms of Use.** The skill collects public profile data in your logged-in browser, partly through undocumented web endpoints that Instagram uses itself. Automated collection may conflict with [Instagram's Terms of Use](https://help.instagram.com/581066165581870). Using it can lead to rate limits or restrictions on **your** account. You use it at your own risk.
- **Permission.** Audit only pages you own or that you have been asked to analyze (for example, a client's page).
- **Read-only.** The skill never likes, follows, comments, sends messages or changes settings, never types passwords, and stops on rate-limit signs.
- **Third-party data.** Audit folders (`instagram-audit-*/`) contain other people's captions, comments and statistics. Keep them private; this repository's `.gitignore` excludes them.
- **No guarantees.** The report is marketing advice, not a promise of results. The ads section is a plan only; check all ad texts against [Meta's Advertising Standards](https://transparency.meta.com/policies/ad-standards/) before use.

## Requirements

- [Claude Code](https://claude.com/claude-code) (CLI, desktop app or IDE extension) with skills support.
- A browser Claude can drive, logged in to Instagram: the desktop app's built-in browser or the Claude in Chrome extension.
- Python 3.8+ (standard library only, no packages to install).
- Web search enabled (used for current benchmarks and Meta Ads rules).

## Install

Copy the `instagram-page-audit` folder into your skills directory:

```bash
git clone https://github.com/YanisDigital/smm-page-audit.git
cp -r smm-page-audit/instagram-page-audit ~/.claude/skills/
```

Or into a project's `.claude/skills/` to use it only there.

## Usage

Share a profile link and ask for an analysis, in any wording:

> Analyze https://www.instagram.com/some_page/ — it's a coffee shop in Lviv, we want more visitors, ad budget $300/month.

The skill also triggers on Ukrainian and Russian phrasing («проаналізуй інстаграм», «аудит сторінки», «стратегія просування», «проанализируй инстаграм», «аудит страницы»).

Claude then:

1. asks a short optional brief (what you sell, city, goal, ad budget, competitors);
2. collects the profile and the last 24–30 posts read-only in the browser;
3. computes metrics with `scripts/metrics.py`;
4. runs 3–5 web searches for current benchmarks and platform rules;
5. writes the analysis and builds `report.html` with `scripts/build_report.py`.

Output goes to `instagram-audit-<handle>-<date>/` in the current directory:

| File | Contents |
|---|---|
| `page_data.json` | Collected public data |
| `metrics.json` | Computed metrics |
| `report_content.json` | Report text and structure |
| `report.html` | The report: self-contained, light/dark theme, mobile-friendly, printable |

The report language follows your chat language (Ukrainian, Russian or English).

## Try it without Instagram

A fictional demo page is included:

```bash
cd instagram-page-audit
python scripts/metrics.py evals/fixtures/demo/page_data.json
python scripts/build_report.py evals/fixtures/demo
```

Open `evals/fixtures/demo/report.html` in a browser.

## What is (and isn't) stored

- Stored: public profile fields, post type, date, caption, likes, comments, views, and comment **text** samples.
- Not stored: commenters' usernames, cookie values, the logged-in viewer's identity or "Followed by …" mutual followers.
- Text collected from Instagram and the web is treated as data; instructions hidden in captions or pages are ignored.
- The report builder escapes all text and allows only `http(s)` links.

## Repository layout

```
instagram-page-audit/
├── SKILL.md                    # workflow and rules Claude follows
├── references/
│   ├── collection.md           # browser data collection, page_data.json schema
│   ├── analysis-framework.md   # metric formulas, scoring rubric, account types
│   ├── benchmarks.md           # sourced benchmarks with confidence levels
│   └── report-sections.md      # report sections and block schema
├── scripts/
│   ├── build_page_data.py      # raw/ files -> page_data.json
│   ├── metrics.py              # page_data.json -> metrics.json
│   └── build_report.py         # -> report.html
├── assets/
│   ├── collect.js              # read-only browser collector
│   └── report-template.html
└── evals/                      # test prompts and the demo fixture
```

## License

[MIT](LICENSE)
