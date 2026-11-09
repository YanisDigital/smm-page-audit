# Data collection (read-only)

Goal: one `page_data.json` with the profile header, the last 30–60 posts with their public
numbers, and a sample of audience comments. Nothing else is touched on the account.

## Contents
1. Ground rules
2. Collector — `assets/collect.js` (preferred)
3. Method B — reading the page (fallback)
4. `page_data.json` schema
5. What to tell the user

---

## 1. Ground rules

- Use the built-in browser pane (`mcp__Claude_Browser__*`). Use Claude in Chrome only when the
  user asks for it — the snippets below work the same in both.
- Read-only: never click Follow, Like, Save, Message, Comment, or any menu that changes state.
- Login wall ("Log in to see more", redirect to `/accounts/login`) → stop and ask the user to
  log in themselves in the pane. Never type credentials. Continue after they confirm.
- Pace requests: the collector waits 2.5–3 s between scrolls and posts. On HTTP 429 or a "Please wait a few
  minutes" message, stop collecting, keep what you have, and say so in the report.
- Normalize the input: `https://www.instagram.com/<handle>/` (strip `?igsh=…`, `/reels/`, etc.).
  An `@handle` becomes that URL.
- Automated collection may conflict with Instagram's Terms of Use. Collect only public data of
  pages the user owns or is asked to analyze, at a human pace, and stop on any rate-limit sign.
- Privacy: the logged-in page shows data about the viewer ("Followed by …" mutual followers,
  the viewer's avatar/name). Drop it from anything you save. Store comment **text only**, no
  usernames. Never read or print cookie values — only check whether `ds_user_id` is present.


## 2. Collector — `assets/collect.js` (preferred, tested 2026-11)

The collector reads only the responses the profile page loads by itself (it patches XHR/fetch
to keep copies) — it never calls Instagram endpoints on its own. Direct calls to internal
endpoints returned 401/404/429 in every test, so they are not used. State is kept in
`sessionStorage`, so a closed tab or a page change can be resumed.

**Sequence** (each step is one `javascript_tool` call; paste the file text as the first call
on every newly loaded page):

1. Open `https://www.instagram.com/<handle>/`. Paste the full text of `assets/collect.js`.
2. `await IGA.start()` → handle, `loggedIn`, exact followers, header lines (viewer data already
   removed). `loggedIn: false` → ask the user to log in themselves, then reload and repeat.
   Expand nothing else; the bio is in `header` lines.
3. `await IGA.scroll(4)` → loads older posts (≈ 12 per scroll) and captures them. Repeat once
   if `grid` < 30.
4. `await IGA.openMissing(5)` → opens the posts that were rendered before capture started
   (read-only modal), 5 per call to stay under the tool timeout. Repeat until `missing` is 0.
5. `await IGA.reelViews(5)` → switches to the profile's own Reels tab (exact `/<handle>/reels/`
   link, so the collector keeps running) and reads view counts from the tiles. If it returns an
   error, open `https://www.instagram.com/<handle>/reels/` by URL, paste `collect.js`, call it again.
6. `IGA.rows(0, 10)`, `IGA.rows(10, 20)`, … → one JSON string per post. Copy every line into
   `<audit-dir>/raw/rows.jsonl`. Do not ask for more than 10 rows per call: long tool output
   gets truncated.
7. `IGA.profile()` + the header lines → write `raw/profile.json` (handle, name, category, bio,
   external_url, bio_links, followers, following, posts_count, is_verified, is_business,
   highlights as a list of titles). Highlight titles are the short labels under the header.
8. Comments: open 3–5 posts with the most comments by URL (`/p/<code>/`), read them with the
   page-text tool, and keep **text only** in `raw/comments.json`
   (`[{"post_url": "...", "text": "..."}]`). Note the share count if the post shows it.
9. Read the captions in the rows and tag each post with a rubric (4–7 themes named in the
   page's own terms) in `raw/rubrics.json` (`{"<code>": "<rubric>"}`).
10. Optional `raw/brief.json` (brief answers; add `"utc_offset": 2` for the audience's time zone)
    and `raw/notes.json` (data limitations). Then:
    `python <skill-dir>/scripts/build_page_data.py <audit-dir>`.

**Row fields** (`IGA.rows`): code, ISO date (UTC), type, likes (null if hidden), comments,
views, shares, duration (s), carousel slides, pinned, collab, location, caption (long captions
keep the first 280 and last 130 characters, so a closing call to action is still seen).

**What the collector filters out:** posts of other accounts (only the audited handle, its
co-authored posts and the posts in its own grid are kept), the viewer's "Followed by …" line,
and the co-author's pin flag (a post counts as pinned only among the first three grid items).

**If something goes wrong**
- `missing` stays above 0 after 3 calls → note it in `notes.json` and continue.
- Reels page shows other people's videos → the site-wide Reels feed was opened; open
  `/<handle>/reels/` by URL.
- The tab closed → open the profile again, paste `collect.js`, `await IGA.start()` (state resumes
  for the same handle), then continue from the step you were on.

## 3. Method B — reading the page (fallback)

Use when the collector fails (page structure changed) or the user is not logged in and only the
public view is available.

1. On the profile page: `get_page_text` → name, bio, category, link, followers/following/posts
   (Instagram shows abbreviated numbers like `12.4K` — convert: K ×1 000, M ×1 000 000; Ukrainian
   UI: `тис.` ×1 000, `млн` ×1 000 000) and highlight titles.
2. Grid links: `javascript_tool` →
   ```js
   [...new Set([...document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')].map(a => a.href))].slice(0, 30)
   ```
   Scroll (`computer` scroll) once or twice if fewer than 24 links appear.
3. Open each post URL (`navigate`), `get_page_text` → date, caption, likes, comments count,
   views for Reels, and the first visible comments. Wait ~2 s between posts. If time is short,
   cover at least the 12 newest posts and say so in `notes`.
4. Fill `page_data.json` with the same schema; unknown values are `null`, never guessed.
   Set `"method": "page-read"`.

Without login Instagram usually shows only the header and ~12 posts with no counts — run a
reduced audit and record this in `notes`.

## 4. `page_data.json` schema

```json
{
  "collected_at": "2026-10-30T10:00:00Z",
  "method": "in-page-capture | page-read | screenshots",
  "url": "https://www.instagram.com/<handle>/",
  "brief": {
    "business": "what they sell, price range", "geo": "city/country",
    "goal": "leads | sales | bookings | awareness", "ad_budget_month": "e.g. 300 USD or none",
    "competitors": ["https://www.instagram.com/..."], "own_page": true,
    "utc_offset": 2,
    "assumptions": ["anything inferred instead of answered"]
  },
  "profile": {
    "handle": "", "name": "", "category": null, "bio": "", "external_url": null, "bio_links": [],
    "followers": 0, "following": 0, "posts_count": 0,
    "is_verified": false, "is_business": true, "is_professional": true, "is_private": false,
    "has_email": false, "has_phone": false,
    "highlight_count": 0, "highlights": [{ "title": "", "count": null }]
  },
  "posts": [{
    "id": "", "url": "", "type": "reel | video | carousel | image",
    "date": "ISO-8601", "caption": "", "likes": null, "comments": null, "views": null,
    "shares": null, "duration_sec": null, "carousel_count": null, "pinned": false,
    "collab": false, "location": null, "rubric": "content theme tagged by the model"
  }],
  "comments_sample": [{ "post_url": "", "text": "", "likes": null }],
  "insights": {},
  "notes": []
}
```

`brief.utc_offset` (hours from UTC) shifts weekday/hour stats to the audience's time zone.
`collab` is true for co-authored posts and for posts published by a partner that appear in the
grid. `insights` is optional: if the user shares Insights screenshots, put the numbers they show here
(reach, accounts engaged, follower age/gender/top cities, top posts by reach) with a `"source":
"screenshot"` field. `metrics.py` ignores unknown keys, so anything extra is safe.

## 5. What to tell the user

After collection, one short message in the user's language: how many posts were collected, the
period they cover, and what was unavailable (hidden likes, private account, rate limit).
