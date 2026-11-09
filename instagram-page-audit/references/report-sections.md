# Report sections and `report_content.json`

## Contents
1. File structure
2. Block types
3. Required sections with minimum content
4. Writing style

---

## 1. File structure

```json
{
  "language": "uk",
  "account_type": "local_business | expert | creator | brand",
  "reduced": false,
  "title": "Аудит Instagram @handle",
  "subtitle": "Стратегія просування, контент-план і реклама",
  "summary": {
    "verdict": "2–4 sentences: where the page stands and the main lever.",
    "scores": [{ "area": "Профіль і біо", "score": 5, "reason": "one line based on data" }],
    "problems": ["top 5 problems, each with data"],
    "quick_wins": ["top 5 actions doable today, no budget"]
  },
  "sections": [
    { "id": "stats", "title": "Статистика й ефективність", "intro": "optional lead paragraph",
      "blocks": [ { "type": "metrics" }, { "type": "paragraph", "text": "..." } ] }
  ],
  "assumptions": ["what was inferred instead of known"],
  "sources": [{ "title": "Source name", "url": "https://..." }]
}
```

`build_report.py` validates this file and prints clear errors, including **minimum content
per section** (section 3 below). `reduced: true` (private account, thin data only) turns the
minimums into warnings. Section `id`s become anchors
in the navigation. Text fields support `**bold**` and line breaks (`\n`); everything else is
escaped as plain text.

## 2. Block types

| `type` | Fields | Use for |
|---|---|---|
| `paragraph` | `text` | Explanations, findings |
| `list` | `items` (strings), `ordered` (bool, optional) | Findings, steps |
| `table` | `columns` (strings), `rows` (array of string arrays) | Calendar, ads structure, KPIs |
| `cards` | `items`: `{ "title", "body", "tag"?, "meta"? }` | Reels/Stories/post ideas, segments, creatives |
| `callout` | `tone`: `info` / `warn` / `good`, `title`?, `text` | Key insight, risk, data caveat |
| `copy` | `label`, `text` | Ready-to-paste text: bio, captions, ad copy, auto-replies (gets a Copy button) |
| `checklist` | `items` (strings) | Action checklist |
| `metrics` | — | Auto: key metric tiles from `metrics.json` |
| `posts` | `which`: `top` / `bottom` | Auto: table of top or bottom posts with links |
| `format_mix` | — | Auto: format share and ER per format bars |
| `trend` | — | Auto: medians per month (posts, ER, likes, comments, Reels views) |
| `rubrics` | — | Auto: the same per rubric, with share of posts |
| `collab_split` | — | Auto: owned posts vs collabs |

## 3. Required sections (in this order)

Section 1 (summary & scorecard) is rendered from `summary`; the `sections` array holds 2–10.

**2. `stats` — Statistics & effectiveness**
- `metrics`, `format_mix`, `trend`, `posts` top, `posts` bottom blocks; `rubrics` and
  `collab_split` when the data has rubrics or collabs.
- Paragraph/list: what the numbers mean vs sourced benchmarks (cite them).
- Why top posts worked, why bottom posts failed (hook, topic, format).
- Timing hint (weekday/hour) if the sample allows, with the caveat.
- `callout` (info): public data only; which Insights screenshots would sharpen it.

**3. `audience` — Audience & positioning**
- Who engages now (from comments), 2–4 target segments as `cards`
  (who, need/pain, what content hooks them, what offer converts them).
- Positioning: one-sentence USP + tone of voice (3 do / 3 don't).
- Repeated audience questions and words (raw material for content and ads).

**4. `strategy` — Promotion & growth strategy (90 days)**
- `table`: Month 1 / 2 / 3 → focus, actions, KPI.
- Growth channels with concrete steps: Reels reach, collabs/co-author posts with local
  businesses or creators, UGC and reviews, giveaways (with rules to avoid bot audiences),
  local SEO (Google Business Profile, Maps), cross-posting (TikTok, Facebook, Threads), ads.
- Profile rework: `copy` blocks with a new name field, 2–3 bio variants, highlight list with
  cover/topic for each, 3 pinned posts with purpose.

**5. `content_plan` — Content plan & schedule**
- Rubrics/pillars with share % and purpose (reach / trust / sale), as `table`.
- Cadence: Reels, carousels/posts and Stories per week, best slots (from data or a tested
  default, labeled).
- 4-week calendar `table`: columns `Дата/День`, `Формат`, `Рубрика`, `Тема`, `Хук`, `CTA`
  (≥ 12 rows; ≥ 3 posts/week unless the brief says otherwise). Dates start next Monday.

**6. `ideas` — Ideas for Reels, Stories and posts**
- ≥ 10 Reels as `cards`: title, body = hook (first 1–2 s) + scenario beats + on-screen text +
  sound/trend note; `tag` = rubric.
- ≥ 10 Stories ideas as `cards` or `list`, plus a 7-day Stories sequence `table` with
  interactive stickers (poll, quiz, question, slider, link) and goal per day.
- ≥ 8 posts/carousels: title, slide-by-slide outline, caption first line, CTA.

**7. `ads` — Targeted ads plan (plan only)**
- Objective tied to the brief goal; why this objective.
- Campaign structure `table`: campaign → ad set → audience → placements → budget share.
- Audiences: broad/Advantage+ vs manual suggestions (per current rules from research), geo,
  custom audiences (IG engagers 30/90/365 days, video viewers 50 %+, site visitors, customer
  list), lookalikes, exclusions.
- 3–5 creative concepts as `cards` (format, hook, visual, angle) + `copy` blocks with primary
  text (short ≤ 125 chars and long), headline, CTA button.
- Budget split and test plan (what is tested first, how long, how many creatives).
- KPI thresholds and stop/scale rules `table` (CTR, CPM, CPC, hook rate, cost per lead/DM).
- `callout` (warn): Meta policy check results and rewritten risky lines.
- If the brief says "no budget", keep the section short: boost-post plan + when to start ads.

**8. `clients` — Attracting new audience & clients**
- Lead magnet / entry offer ideas (≥ 3).
- DM funnel: keyword auto-replies (comment-to-DM), quick replies, `copy` blocks with scripts.
- Partnerships, referrals, reviews and social proof collection routine.
- Offline/online touchpoints that drive to Instagram (QR, Maps, packaging), if relevant.

**9. `kpi` — KPIs & tracking**
- `table`: metric, current (from data or "unknown"), 30-day target, 90-day target.
- Weekly review routine (what to check in Insights, 15 min) and UTM scheme for link in bio.

**10. `checklist` — Action checklist**
- Three `checklist` blocks or one with prefixes: Week 1 / Month 1 / Months 2–3.

### Minimums enforced by `build_report.py`

| Section | Minimum |
|---|---|
| summary | 6 scores, 3 problems, 3 quick wins |
| stats | 2 `posts` blocks, 1 `trend` block |
| audience | 2 segment cards |
| strategy | 3 table rows (months), 2 `copy` blocks (name/bio) |
| content_plan | one table with ≥ 12 rows |
| ideas | ≥ 18 cards (Reels + posts), ≥ 28 list/card items in total, 7-row Stories table |
| ads | ≥ 3 table rows, 2 `copy` blocks, 1 policy `callout` |
| clients | 2 `copy` blocks (scripts / auto-replies), ≥ 3 list or card items |
| kpi | ≥ 5 table rows |
| checklist | ≥ 8 checklist items |

These are floors, not targets: a strong report usually goes well beyond them.

## 4. Writing style

- Report language = `language`; the reader is the business owner, not a marketer — short
  sentences, no jargon without a gloss (write "ER (engagement rate)" the first time).
- Numbers from `metrics.json` with the same rounding; estimates marked *(оцінка)* / *(estimate)*.
- Every problem → action → KPI. No generic advice like "post quality content".
- Ready-made texts sound like the page's own voice, not like an agency.
