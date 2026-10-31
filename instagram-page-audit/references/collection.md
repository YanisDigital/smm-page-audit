# Data collection (read-only)

Goal: one `page_data.json` with the profile header, the last 24–30 posts with their public
numbers, and a sample of audience comments. Nothing else is touched on the account.

## Contents
1. Ground rules
2. Method A — in-page fetch (fast, preferred)
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
- Pace requests: the snippet waits 1.5 s between pages. On HTTP 429 or a "Please wait a few
  minutes" message, stop collecting, keep what you have, and say so in the report.
- Normalize the input: `https://www.instagram.com/<handle>/` (strip `?igsh=…`, `/reels/`, etc.).
  An `@handle` becomes that URL.
- Automated collection may conflict with Instagram's Terms of Use. Collect only public data of
  pages the user owns or is asked to analyze, at a human pace, and stop on any rate-limit sign.
- Privacy: the logged-in page shows data about the viewer ("Followed by …" mutual followers,
  the viewer's avatar/name). Drop it from anything you save. Store comment **text only**, no
  usernames. Never read or print cookie values — only check whether `ds_user_id` is present.

## 2. Method A — in-page fetch (preferred)

Open the profile URL first (so requests run on instagram.com with the user's session), then run
this with `javascript_tool`. It uses the same internal endpoints the Instagram web app uses;
they are unofficial and may change — if it throws, go to Method B.

```js
await (async () => {
  const MAX_POSTS = 30, CAPTION_MAX = 700, COMMENT_POSTS = 4, COMMENTS_PER_POST = 8;
  const username = location.pathname.split('/').filter(Boolean)[0];
  const H = { 'x-ig-app-id': '936619743392459', 'x-requested-with': 'XMLHttpRequest' };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const get = async u => {
    const r = await fetch(u, { headers: H, credentials: 'include' });
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${u}`);
    return r.json();
  };
  const notes = [];
  const info = await get(`/api/v1/users/web_profile_info/?username=${encodeURIComponent(username)}`);
  const u = info.data.user;

  let highlights = [];
  try {
    const t = await get(`/api/v1/highlights/${u.id}/highlights_tray/`);
    highlights = (t.tray || []).map(h => ({ title: h.title, count: h.media_count ?? null }));
  } catch (e) { notes.push('Highlights titles unavailable: ' + e.message); }

  const items = [];
  let maxId = null;
  if (!u.is_private) {
    try {
      while (items.length < MAX_POSTS) {
        await sleep(1500);
        const f = await get(`/api/v1/feed/user/${u.id}/?count=12` + (maxId ? `&max_id=${maxId}` : ''));
        items.push(...(f.items || []));
        if (!f.more_available || !f.next_max_id) break;
        maxId = f.next_max_id;
      }
    } catch (e) { notes.push('Feed stopped early: ' + e.message); }
  } else notes.push('Account is private: posts not available.');

  const typeOf = it => it.media_type === 8 ? 'carousel'
    : it.media_type === 2 ? (it.product_type === 'clips' ? 'reel' : 'video') : 'image';
  const posts = items.slice(0, MAX_POSTS).map(it => ({
    id: String(it.pk),
    url: `https://www.instagram.com/${it.product_type === 'clips' ? 'reel' : 'p'}/${it.code}/`,
    type: typeOf(it),
    date: new Date(it.taken_at * 1000).toISOString(),
    caption: (it.caption?.text || '').slice(0, CAPTION_MAX),
    likes: it.like_and_view_counts_disabled ? null : (it.like_count ?? null),
    comments: it.comment_count ?? null,
    views: it.play_count ?? it.ig_play_count ?? it.view_count ?? null,
    duration_sec: it.video_duration ? Math.round(it.video_duration) : null,
    carousel_count: it.carousel_media_count ?? null,
    pinned: !!(it.timeline_pinned_user_ids?.length || it.clips_tab_pinned_user_ids?.length),
    collab: !!(it.coauthor_producers?.length),
    location: it.location?.name || null,
  }));

  const comments_sample = [];
  const byComments = [...posts].filter(p => p.comments).sort((a, b) => b.comments - a.comments).slice(0, COMMENT_POSTS);
  for (const p of byComments) {
    try {
      await sleep(1500);
      const c = await get(`/api/v1/media/${p.id}/comments/?can_support_threading=true&permalink_enabled=false`);
      (c.comments || []).slice(0, COMMENTS_PER_POST).forEach(x =>
        comments_sample.push({ post_url: p.url, text: (x.text || '').slice(0, 300), likes: x.comment_like_count ?? null }));
    } catch (e) { notes.push('Comments unavailable for ' + p.url + ': ' + e.message); break; }
  }

  return {
    collected_at: new Date().toISOString(),
    method: 'in-page-fetch',
    url: `https://www.instagram.com/${username}/`,
    profile: {
      handle: u.username, name: u.full_name, category: u.category_name || u.business_category_name || null,
      bio: u.biography, external_url: u.external_url || null,
      bio_links: (u.bio_links || []).map(l => l.url),
      followers: u.edge_followed_by?.count ?? null, following: u.edge_follow?.count ?? null,
      posts_count: u.edge_owner_to_timeline_media?.count ?? null,
      is_verified: !!u.is_verified, is_business: !!u.is_business_account,
      is_professional: !!u.is_professional_account, is_private: !!u.is_private,
      has_email: !!u.business_email, has_phone: !!u.business_phone_number,
      highlight_count: u.highlight_reel_count ?? highlights.length, highlights,
    },
    posts, comments_sample, notes,
  };
})()
```

Save the returned object with the Write tool as `page_data.json` in the audit folder.
Then add `"brief"` (Step 1 answers) by hand — see schema.

## 2b. Method A2 — capture the grid's own responses (tested 2026-10-30)

When Method A fails with 401 (not logged in), 429 (rate limit on `web_profile_info`) or 404
(`/api/v1/feed/user/…` changed), the logged-in profile page still loads posts through
`/api/graphql`. Capture those responses instead of calling endpoints yourself:

1. On the profile page, patch XHR/fetch to keep responses that contain `like_count` or
   `taken_at`:
   ```js
   window.__cap = window.__cap || [];
   if (!window.__capPatched) {
     window.__capPatched = true;
     const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
     XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
     XMLHttpRequest.prototype.send = function () {
       this.addEventListener('load', () => { try { const t = this.responseText;
         if (t && (t.includes('like_count') || t.includes('taken_at'))) window.__cap.push({ u: String(this.__u), t }); } catch (e) {} });
       return os.apply(this, arguments);
     };
     const of = window.fetch;
     window.fetch = async function (...a) { const r = await of.apply(this, a);
       try { r.clone().text().then(t => { if (t.includes('like_count') || t.includes('taken_at')) window.__cap.push({ u: String(a[0]?.url || a[0]), t }); }); } catch (e) {}
       return r; };
   }
   ```
2. Scroll to the bottom 3–4 times with 3 s pauses → older posts load and get captured.
3. The first ~12 grid items were loaded before the patch. Open each of them by clicking its
   grid link (opens the post modal, read-only), wait ~3 s, `history.back()`. Do this in small
   batches (4–5 per call) — a 12-post loop exceeds the 45 s tool timeout.
4. Parse: walk every captured JSON line (responses can be multi-line), keep objects with
   `code` + `taken_at` + `like_count`/`comment_count` **and `user.username` (or
   `owner.username`) equal to the audited handle** — other accounts' posts get captured too.
   Views: open `https://www.instagram.com/<handle>/reels/` by URL (clicking the Reels tab can
   open the global Reels feed with other people's videos), scroll, and read the view count from
   each tile's text (`a[href*="/reel/"]` innerText, e.g. `4,677` / `14.8K`).
   Pinned posts have `timeline_pinned_user_ids` — but a collab post can carry the
   co-author's pin; trust the grid order (pinned items come first) over this flag.
   Comments: objects with `text` + `user.username` + `comment_like_count`.
5. The tool output truncates long strings: return arrays of small rows (≤10 posts per call,
   captions cut to ~300 chars) instead of one big `JSON.stringify`.
6. Full bio: click the header "more" button, then read `header.innerText`; exact follower count
   is in `header span[title]`. The header text includes the viewer's "Followed by …" line —
   do not save it.

## 3. Method B — reading the page (fallback)

Use when Method A fails (endpoint changed, 401/403) or the user is not logged in and only the
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
  "method": "in-page-fetch | page-read | screenshots",
  "url": "https://www.instagram.com/<handle>/",
  "brief": {
    "business": "what they sell, price range", "geo": "city/country",
    "goal": "leads | sales | bookings | awareness", "ad_budget_month": "e.g. 300 USD or none",
    "competitors": ["https://www.instagram.com/..."], "own_page": true,
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
    "duration_sec": null, "carousel_count": null, "pinned": false, "collab": false, "location": null
  }],
  "comments_sample": [{ "post_url": "", "text": "", "likes": null }],
  "insights": {},
  "notes": []
}
```

`insights` is optional: if the user shares Insights screenshots, put the numbers they show here
(reach, accounts engaged, follower age/gender/top cities, top posts by reach) with a `"source":
"screenshot"` field. `metrics.py` ignores unknown keys, so anything extra is safe.

## 5. What to tell the user

After collection, one short message in the user's language: how many posts were collected, the
period they cover, and what was unavailable (hidden likes, private account, rate limit).
