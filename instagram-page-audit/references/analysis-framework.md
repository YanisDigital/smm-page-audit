# Analysis framework

How to turn `page_data.json` + `metrics.json` into findings, scores and actions.

## Contents
1. Metrics computed by `metrics.py`
2. Reading the numbers
3. Qualitative checks (profile, visuals, captions, conversion path)
4. Scorecard rubric
5. From finding to action
6. Account types

---

## 1. Metrics computed by `metrics.py`

| Key in `metrics.json` | Formula | Notes |
|---|---|---|
| `engagement.er_followers_avg` | mean of (likes + comments) / followers × 100 per post | Main health number. Posts with hidden likes are skipped. |
| `engagement.er_followers_median` | median of the same | Use the median when 1–2 viral posts skew the mean. |
| `engagement.by_type[type]` | same ER per format + average views | Shows which format the audience rewards. |
| `reels.avg_views`, `reels.median_views` | from `views` | Reels reach beyond followers. |
| `reels.views_to_followers` | median views / followers | > 1 means Reels reach non-followers (growth engine working). |
| `reels.er_views_avg` | (likes + comments) / views × 100 | Quality of the Reel for people who saw it. |
| `reels.likes_per_view_median` | median of likes / views × 100 | Low (< ~1 %) with huge views can mean paid or boosted distribution — a hypothesis, check "Paid partnership" labels. |
| `engagement.median_shares` | median shares where visible | Shares (sends) are a key reach signal; `shares_known` tells how many posts had the number. |
| `collab_split` | `group_stats` for owned posts vs collabs | Do collabs bring more than own posts? Big share of collabs = weak own voice. |
| `trend` | `group_stats` per calendar month (pinned excluded) | Rising or falling; compare months with ≥ 5 posts only. |
| `rubrics` | `group_stats` + share per rubric | Which themes earn attention; needs `rubric` tags on posts. |
| `calendar` | next Monday after collection + 4 week starts | Dates for the content calendar. |
| `engagement.comments_to_likes` | total comments / total likes | Conversation depth; low = passive audience. |
| `cadence.posts_per_week` | posts / period weeks | Over the analyzed period; pinned posts are excluded (often months old). |
| `cadence.max_gap_days`, `cadence.days_since_last_post` | — | Long gaps and an inactive page hurt reach. |
| `format_mix` | share of reel / carousel / image / video | |
| `timing.by_weekday`, `timing.by_hour` | post count + avg ER per bucket | In the audience time zone when `brief.utc_offset` is set, otherwise UTC — say which. Small samples: a hint only. |
| `captions` | avg length, % with CTA, % with question, % with hashtags, avg hashtags | CTA list is multilingual (uk/ru/en). |
| `top_posts`, `bottom_posts` | by (likes + comments) | Open 2–3 of each and explain *why* (hook, topic, format, faces, offer). |
| `warnings` | data gaps | Repeat relevant ones in the report. |

## 2. Reading the numbers

Benchmarks change every year and differ by niche and follower count. **Always use benchmarks
from Step 4 web research, with the source in the report.** The ranges below are only a rough
orientation for sanity checks and must not be quoted as facts:

- ER by followers tends to fall as the account grows: small local accounts (< 10K) often sit
  around 2–6 %, mid-size (10K–100K) around 1–3 %, large accounts lower.
- Reels views/followers below ~0.3 usually means Reels are shown mostly to existing followers
  (weak hooks, no trend fit, or irregular posting).
- Comments/likes below ~2 % usually means content triggers no conversation (no questions,
  no polarizing or useful-to-save topics).

Patterns to look for:

- **Format gap** — one format has 2× the ER or views of another but is posted less → shift the mix.
- **Topic gap** — top posts share a theme (people/face, behind the scenes, price, before/after,
  local place) → make it a rubric.
- **Consistency gap** — gaps > 10 days or fewer than ~3 posts/week → cadence plan first.
- **Conversion gap** — good engagement but weak bio/CTA/link → fix the path to purchase first;
  it is the cheapest win.
- **Reach gap** — healthy ER but low views/followers → Reels hooks, trends, collabs, ads.
- **Pinned posts** — are the 3 pinned posts doing a job (offer, social proof, who we are)?

Sample size: under 12 posts, state that the stats are indicative only.

Viral outliers: when pinned or viral posts make the mean ER several times the median, quote
the median as the page's ER and analyze the outliers separately (what made them viral, can the
formula be repeated). For "recent Reels reach", compute the median views of non-pinned Reels
from the analyzed period yourself and label it as your calculation.

## 3. Qualitative checks

Go through the profile as a new visitor who has 5 seconds:

**Profile & bio**
- Name field contains a searchable keyword (e.g. "Manicure Lviv"), not just the brand.
- Bio answers: what, for whom, where, why us, what to do next (CTA).
- Link in bio works and leads to a conversion page (booking, catalog, messenger), with UTM.
- Contact buttons present (business/professional account); category set correctly.
- Highlights: covers consistent; must-have topics: services/prices, reviews, works/portfolio,
  how to order/book, about us, FAQ/delivery. Missing ones become actions.

**Visual identity**
- Grid recognizable at a glance (consistent colors, fonts, covers for Reels).
- Faces present (the owner/team builds trust and recognition).
- Text on covers readable at thumbnail size.

**Captions & hooks**
- First line works as a hook (it is all people see before "more").
- CTA present and specific (DM a keyword, book via link, save, share).
- Hashtags: few and relevant (3–5), plus local ones if the business is local.

**Audience voice** (`comments_sample`)
- Who comments: customers, other businesses, friends, bots/giveaway hunters?
- Repeated questions (price, delivery, address) → content ideas and FAQ highlight.
- Words customers use → hooks and ad copy.

**Competitors** (from web research / their pages)
- What they post that gets engagement; what they do not cover (a free angle).

## 4. Scorecard rubric (0–10 each)

| Area | 0–3 | 4–6 | 7–10 |
|---|---|---|---|
| Profile & bio | unclear what/where, no CTA, no link | clear offer, weak CTA or link | keyword name, offer, geo, CTA, tracked link, contacts |
| Visual identity | random, no style | some consistency | recognizable grid, covers, faces |
| Content mix | one format, no rubrics | 2 formats, loose topics | Reels + carousels + Stories, clear rubrics |
| Engagement | far below benchmark | near benchmark | above benchmark, real conversations |
| Consistency | gaps > 2 weeks | irregular 1–2/week | steady 3+/week, Stories daily |
| Conversion path | no way to buy/book visible | path exists but hidden | offer + CTA + highlight + link + DM flow |

Overall score = average, one decimal. Every score gets a one-line reason built on data.

## 5. From finding to action

Each problem in the report follows: **observation (data) → why it matters → action → expected
effect / KPI**. Example:

> Reels get a median 640 views at 4 100 followers (0.16×) → Reels are not reaching new people →
> start every Reel with a 1-second visual hook + on-screen question; post 3 Reels/week for 4 weeks →
> target median views ≥ 0.5× followers.

Quick wins = actions doable in under a day with no budget (bio, highlights, pinned posts,
link, CTA in captions, auto-reply keywords).

## 6. Account types

Set `account_type` in `report_content.json`. The same 10 sections stay, but depth and reading
change:

| Type | Typical goal | Sections that get most depth | Reading the scorecard | "Clients" section becomes |
|---|---|---|---|---|
| `local_business` | visits, bookings, DMs | profile/bio, local reach, ads, clients | Conversion path and local signals (geo, Maps) weigh most | booking/DM funnel, reviews, partners nearby |
| `expert` | leads, course/service sales | positioning, content plan, DM funnel | Trust (cases, reviews) and offer clarity weigh most | lead magnets, keyword auto-replies, sales scripts |
| `creator` | audience growth, brand deals | Reels ideas, collabs, consistency | Reach (views/followers) and engagement weigh most | brand-deal media kit, collab outreach |
| `brand` | awareness, product adoption | stats depth (trend, collabs, rubrics), content system, UGC | Engagement per view and path to product weigh most; ads budget tiers are not useful | path into the product: in-app actions, UGC challenges, creator program |

For `brand`, write the ads section as creative hypotheses and audience/test structure (budget
as shares, not sums); for small accounts, use budget tiers when the budget is unknown.
