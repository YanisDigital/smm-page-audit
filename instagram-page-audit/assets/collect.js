// Instagram Page Audit: read-only collector (Method A2).
// Paste this whole file once per page load with javascript_tool, then call the IGA.* functions
// (see references/collection.md). It only reads what the page itself loads: no likes, follows,
// comments, messages or setting changes. State lives in sessionStorage, so it survives
// navigation inside instagram.com and a lost tab can be resumed by opening the profile again.
(() => {
  if (window.IGA) return 'IGA already loaded';
  const KEY = 'iga_state';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const load = () => { try { return JSON.parse(sessionStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const save = s => { sessionStorage.setItem(KEY, JSON.stringify(s)); return s; };
  const codeOf = a => a.getAttribute('href').split('/').filter(Boolean).pop();
  const gridCodes = () => [...new Set([...document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')].map(codeOf))];
  const num = s => {
    s = String(s || '').replace(/[,\s]/g, '');
    const m = s.match(/^([\d.]+)([KkMmКкМм]|тис\.?|млн)?/);
    if (!m) return null;
    let n = parseFloat(m[1]);
    const u = (m[2] || '').toLowerCase();
    if (u === 'k' || u === 'к' || u.startsWith('тис')) n *= 1e3;
    if (u === 'm' || u === 'м' || u === 'млн') n *= 1e6;
    return Math.round(n);
  };

  // Capture the page's own API responses that carry post data
  window.__igaCap = window.__igaCap || [];
  const keep = t => t && (t.includes('like_count') || t.includes('taken_at'));
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    this.addEventListener('load', () => { try { if (keep(this.responseText)) window.__igaCap.push(this.responseText); } catch (e) {} });
    return os.apply(this, arguments);
  };
  const of = window.fetch;
  window.fetch = async function (...a) {
    const r = await of.apply(this, a);
    try { r.clone().text().then(t => { if (keep(t)) window.__igaCap.push(t); }); } catch (e) {}
    return r;
  };

  // Move captured responses into state.posts (only the audited account's posts and its collabs)
  function absorb() {
    const s = load(), H = s.handle, grid = new Set(s.grid || []);
    s.posts = s.posts || {};
    const walk = o => {
      if (!o || typeof o !== 'object') return;
      if (Array.isArray(o)) { o.forEach(walk); return; }
      const owner = (o.user && o.user.username) || (o.owner && o.owner.username);
      const co = (o.coauthor_producers || []).map(x => x.username);
      if (o.code && o.taken_at && (owner === H || co.includes(H) || grid.has(o.code))) {
        const p = s.posts[o.code] = s.posts[o.code] || { code: o.code };
        p.t = o.taken_at;
        if (o.like_count !== undefined) p.likes = o.like_count;
        if (o.like_and_view_counts_disabled) p.hidden = 1;
        if (o.comment_count !== undefined) p.comments = o.comment_count;
        const sh = o.reshare_count ?? o.share_count;
        if (sh != null) p.shares = sh;
        const v = o.play_count ?? o.ig_play_count ?? o.view_count;
        if (v != null && p.views == null) p.views = v;
        if (o.media_type) p.mt = o.media_type;
        if (o.product_type) p.pt = o.product_type;
        if (o.video_duration) p.dur = Math.round(o.video_duration);
        if (o.carousel_media_count) p.cc = o.carousel_media_count;
        if (o.caption && o.caption.text) p.cap = o.caption.text.slice(0, 2200);
        if (o.location && o.location.name) p.loc = o.location.name;
        if ((o.timeline_pinned_user_ids || []).length) p.pinFlag = 1;
        p.collab = owner !== H || co.length > 0 ? 1 : 0;
      }
      Object.values(o).forEach(walk);
    };
    for (const t of window.__igaCap) for (const line of t.split('\n')) { try { walk(JSON.parse(line)); } catch (e) {} }
    window.__igaCap = [];
    return save(s);
  }

  function addGrid() {
    const s = load();
    const seen = new Set(s.grid || []);
    s.grid = (s.grid || []).concat(gridCodes().filter(c => !seen.has(c)));
    return save(s);
  }

  async function start() {
    const handle = location.pathname.split('/').filter(Boolean)[0];
    const prev = load();
    const same = prev.handle === handle;   // same profile: resume, keep what was collected
    const header = document.querySelector('header');
    const more = header && [...header.querySelectorAll('span,div[role=button]')]
      .find(e => /^(more|ещё|ще|більше)$/i.test((e.innerText || '').trim()));
    if (more) { more.click(); await sleep(800); }
    const text = header ? header.innerText : '';
    const lines = text.split('\n').map(x => x.trim()).filter(Boolean)
      // never keep data about the logged-in viewer
      .filter(x => !/^(followed by|подписаны|стежать|you follow|following$|message$|подписки$|follow$)/i.test(x));
    const exact = header && header.querySelector('span[title]');
    const pick = re => { const l = lines.find(x => re.test(x)); return l ? num(l) : null; };
    const st = save({
      handle,
      loggedIn: document.cookie.includes('ds_user_id'),
      headerLines: lines.slice(0, 40),
      followers: exact ? num(exact.getAttribute('title')) : pick(/followers|подписчик|підписник/i),
      following: pick(/following|подписок|підписок|відстеж/i),
      postsCount: pick(/posts|публикац|публікац|допис/i),
      externalLinks: header ? [...header.querySelectorAll('a[href^="http"]')].map(a => a.href)
        .filter(h => !/^https?:\/\/(www\.)?instagram\.com\//.test(h)) : [],
      grid: same ? prev.grid || [] : [], posts: same ? prev.posts || {} : {},
      reelViews: same ? prev.reelViews || {} : {},
    });
    addGrid(); absorb();
    return { handle: st.handle, loggedIn: st.loggedIn, followers: st.followers, header: lines.slice(0, 25) };
  }

  async function scroll(times = 4) {
    for (let i = 0; i < times; i++) { window.scrollTo(0, document.body.scrollHeight); await sleep(2800); addGrid(); }
    window.scrollTo(0, 0);
    const s = absorb();
    return status(s);
  }

  // Posts rendered before the capture started: open each one (read-only modal) to load its data
  async function openMissing(max = 5) {
    let s = absorb();
    const todo = (s.grid || []).filter(c => !s.posts[c]).slice(0, max);
    for (const c of todo) {
      const a = document.querySelector(`a[href$="/${c}/"]`);
      if (!a) continue;
      a.click(); await sleep(3000); history.back(); await sleep(1400);
    }
    s = absorb();
    return status(s);
  }

  // Switches to the profile's own Reels tab (exact link, so IGA survives) and reads tile view counts.
  // The site-wide "Reels" link opens a feed of other accounts — never use it.
  async function reelViews(times = 5) {
    const H = load().handle;
    if (!location.pathname.startsWith(`/${H}/reels`)) {
      const tab = document.querySelector(`a[href="/${H}/reels/"]`);
      if (!tab) return { error: `No /${H}/reels/ tab link: open https://www.instagram.com/${H}/reels/ by URL, paste collect.js, call IGA.reelViews() again` };
      tab.click();
    }
    await sleep(2500);
    for (let i = 0; i < times; i++) { window.scrollTo(0, document.body.scrollHeight); await sleep(2500); }
    const s = load();
    for (const a of document.querySelectorAll('a[href*="/reel/"]')) {
      const c = codeOf(a), v = num((a.innerText || '').trim());
      if (v != null && !(c in s.reelViews)) s.reelViews[c] = v;
    }
    save(s);
    return { tiles: Object.keys(s.reelViews).length, ...status(s) };
  }

  function merged() {
    const s = load();
    return (s.grid || []).filter(c => s.posts[c]).map((c, i) => {
      const p = { ...s.posts[c] };
      if (s.reelViews[c] != null) p.views = s.reelViews[c];
      p.pinned = p.pinFlag && i < 3 ? 1 : 0;   // a collab can carry the co-author's pin flag
      return p;
    });
  }

  function status(s = load()) {
    const ps = merged();
    const reels = ps.filter(p => p.pt === 'clips');
    return {
      grid: (s.grid || []).length, collected: ps.length,
      missing: (s.grid || []).filter(c => !s.posts[c]).length,
      reels: reels.length, reelsWithViews: reels.filter(p => p.views != null).length,
      collabs: ps.filter(p => p.collab).length,
    };
  }

  // Compact rows for transfer out of the browser: one JSON string per post, ≤ 10 per call
  function rows(from = 0, to = 10) {
    const short = c => { c = (c || '').replace(/\s+/g, ' ').trim(); return c.length > 420 ? c.slice(0, 280) + ' … ' + c.slice(-130) : c; };
    const type = p => p.pt === 'clips' ? 'reel' : p.mt === 8 ? 'carousel' : p.mt === 2 ? 'video' : 'image';
    return merged().slice(from, to).map(p => JSON.stringify([
      p.code, new Date(p.t * 1000).toISOString(), type(p), p.hidden ? null : (p.likes ?? null),
      p.comments ?? null, p.views ?? null, p.shares ?? null, p.dur ?? null, p.cc ?? null,
      p.pinned, p.collab, p.loc || null, short(p.cap)]));
  }

  function profile() {
    const s = load();
    return { handle: s.handle, followers: s.followers, following: s.following, postsCount: s.postsCount,
      externalLinks: s.externalLinks, headerLines: s.headerLines };
  }

  window.IGA = { start, scroll, openMissing, reelViews, status, rows, profile, absorb };
  return 'IGA loaded';
})();
