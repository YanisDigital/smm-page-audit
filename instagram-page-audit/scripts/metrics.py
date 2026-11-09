"""Compute Instagram page metrics from page_data.json.

Usage: python metrics.py <path/to/page_data.json> [--out metrics.json]
Writes metrics.json next to the input by default. Standard library only.
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

CTA_PATTERNS = [
    # uk
    r"пиш[іи]ть", r"напиш", r"запис", r"замов", r"дірект", r"директ", r"посилання", r"переход",
    r"зберіж", r"збереж", r"зберіга", r"поділ", r"коментар", r"телефон", r"дзвон", r"бронюй", r"купу",
    # ru
    r"пишите", r"заказ", r"ссылк", r"сохран", r"подел", r"звон", r"брониру", r"покупа",
    # en
    r"\bdm\b", r"link in bio", r"book", r"order", r"\bsave\b", r"\bshare\b", r"comment", r"call", r"\bbuy\b",
    r"shop now", r"sign up",
]
CTA_RE = re.compile("|".join(CTA_PATTERNS), re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[\wЀ-ӿ]+", re.UNICODE)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def r2(x):
    return None if x is None else round(x, 2)


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def interactions(post):
    if post.get("likes") is None and post.get("comments") is None:
        return None
    return (post.get("likes") or 0) + (post.get("comments") or 0)


def er_followers(post, followers):
    total = interactions(post)
    if total is None or post.get("likes") is None or not followers:
        return None
    return total / followers * 100


def group_stats(items, followers):
    """Medians for a group of posts (a month, a rubric, owned vs collab)."""
    reels = [p for p in items if p.get("type") == "reel"]
    return {
        "count": len(items),
        "er_followers_median": r2(median(er_followers(p, followers) for p in items)),
        "median_likes": r2(median(p.get("likes") for p in items)),
        "median_comments": r2(median(p.get("comments") for p in items)),
        "median_reel_views": r2(median(p.get("views") for p in reels)),
    }


def post_summary(post, followers):
    return {
        "url": post.get("url"),
        "type": post.get("type"),
        "date": post.get("date"),
        "likes": post.get("likes"),
        "comments": post.get("comments"),
        "views": post.get("views"),
        "er_followers": r2(er_followers(post, followers)),
        "caption_start": (post.get("caption") or "").strip().split("\n")[0][:140],
    }


def compute(data):
    profile = data.get("profile") or {}
    followers = profile.get("followers")
    posts = data.get("posts") or []
    warnings = []

    if not followers:
        warnings.append("Followers count unknown: ER by followers not computed.")
    if not posts:
        warnings.append("No posts collected: only profile-level audit possible.")
    elif len(posts) < 12:
        warnings.append(f"Only {len(posts)} posts: statistics are indicative only.")

    hidden = sum(1 for p in posts if p.get("likes") is None)
    if hidden:
        warnings.append(f"{hidden} post(s) with hidden or unknown likes excluded from ER.")

    # Engagement
    ers = [er_followers(p, followers) for p in posts]
    total_likes = sum(p.get("likes") or 0 for p in posts)
    total_comments = sum(p.get("comments") or 0 for p in posts)

    by_type = defaultdict(list)
    for p in posts:
        by_type[p.get("type") or "unknown"].append(p)
    type_stats = {}
    for t, items in sorted(by_type.items()):
        type_stats[t] = {
            "count": len(items),
            "er_followers_avg": r2(mean(er_followers(p, followers) for p in items)),
            "er_followers_median": r2(median(er_followers(p, followers) for p in items)),
            "avg_interactions": r2(mean(interactions(p) for p in items)),
            "avg_views": r2(mean(p.get("views") for p in items)),
        }

    # Reels
    reels = [p for p in posts if p.get("type") == "reel"]
    reel_views = [p.get("views") for p in reels if p.get("views") is not None]
    reel_er_views = [
        interactions(p) / p["views"] * 100
        for p in reels
        if p.get("views") and interactions(p) is not None and p.get("likes") is not None
    ]
    med_views = median(reel_views)
    likes_per_view = [p["likes"] / p["views"] * 100 for p in reels if p.get("views") and p.get("likes") is not None]
    shares = [p.get("shares") for p in posts if p.get("shares") is not None]

    # Owned posts vs collabs (co-authored or published by a partner)
    collabs = [p for p in posts if p.get("collab")]
    collab_split = ({"owned": group_stats([p for p in posts if not p.get("collab")], followers),
                     "collab": group_stats(collabs, followers)} if collabs else {})

    # Trend by calendar month, pinned posts excluded (they are usually old)
    months = defaultdict(list)
    for p in posts:
        d = parse_date(p.get("date"))
        if d and not p.get("pinned"):
            months[d.strftime("%Y-%m")].append(p)
    trend = {m: group_stats(items, followers) for m, items in sorted(months.items())}

    # Rubrics: the "rubric" field is tagged by the model from captions
    rubric_groups = defaultdict(list)
    for p in posts:
        if p.get("rubric"):
            rubric_groups[p["rubric"]].append(p)
    rubrics = {
        name: {**group_stats(items, followers), "share_pct": r2(len(items) / len(posts) * 100)}
        for name, items in sorted(rubric_groups.items(), key=lambda kv: -len(kv[1]))
    }
    if posts and not rubric_groups:
        warnings.append("No 'rubric' tags on posts: rubric table not computed.")

    # Cadence: pinned posts are often old and would stretch the period
    dates = sorted(d for d in (parse_date(p.get("date")) for p in posts if not p.get("pinned")) if d)
    cadence = {"first_post": None, "last_post": None, "period_days": None, "posts_per_week": None,
               "avg_gap_days": None, "max_gap_days": None, "days_since_last_post": None}
    if dates:
        period_days = max((dates[-1] - dates[0]).total_seconds() / 86400, 1)
        gaps = [(b - a).total_seconds() / 86400 for a, b in zip(dates, dates[1:])]
        ref = parse_date(data.get("collected_at")) or datetime.now(timezone.utc)
        cadence.update({
            "first_post": dates[0].date().isoformat(),
            "last_post": dates[-1].date().isoformat(),
            "period_days": r2(period_days),
            "posts_per_week": r2(len(dates) / period_days * 7) if len(dates) > 1 else None,
            "avg_gap_days": r2(mean(gaps)),
            "max_gap_days": r2(max(gaps)) if gaps else None,
            "days_since_last_post": r2((ref - dates[-1]).total_seconds() / 86400),
        })
        if cadence["max_gap_days"] and cadence["max_gap_days"] > 14:
            warnings.append(f"Posting gap of {cadence['max_gap_days']} days in the period.")

    # Timing, shifted to the audience's time zone when the brief gives brief.utc_offset (hours)
    offset = (data.get("brief") or {}).get("utc_offset")
    shift = timedelta(hours=offset) if isinstance(offset, (int, float)) else timedelta(0)
    weekday = defaultdict(list)
    hour = defaultdict(list)
    for p in posts:
        d = parse_date(p.get("date"))
        if d:
            d = d + shift
            weekday[WEEKDAYS[d.weekday()]].append(er_followers(p, followers))
            hour[d.hour].append(er_followers(p, followers))
    timing = {
        "timezone_note": (f"Hours are in the audience time zone (UTC{offset:+g})." if shift
                          else "Hours are in UTC; set brief.utc_offset to shift them to the audience time zone."),
        "by_weekday": {k: {"posts": len(weekday[k]), "er_avg": r2(mean(weekday[k]))} for k in WEEKDAYS if k in weekday},
        "by_hour": {str(h): {"posts": len(v), "er_avg": r2(mean(v))} for h, v in sorted(hour.items())},
    }

    # Captions
    captions = [p.get("caption") or "" for p in posts]
    n = len(captions) or 1
    tag_counts = [len(HASHTAG_RE.findall(c)) for c in captions]
    all_tags = Counter(t.lower() for c in captions for t in HASHTAG_RE.findall(c))
    caption_stats = {
        "avg_length": r2(mean(len(c) for c in captions)),
        "pct_with_cta": r2(sum(1 for c in captions if CTA_RE.search(c)) / n * 100),
        "pct_with_question": r2(sum(1 for c in captions if "?" in c) / n * 100),
        "pct_with_hashtags": r2(sum(1 for t in tag_counts if t) / n * 100),
        "avg_hashtags": r2(mean(tag_counts)),
        "top_hashtags": [t for t, _ in all_tags.most_common(10)],
        "pct_empty": r2(sum(1 for c in captions if not c.strip()) / n * 100),
    }

    ranked = sorted((p for p in posts if interactions(p) is not None), key=interactions, reverse=True)
    mix = Counter(p.get("type") or "unknown" for p in posts)

    # Content calendar starts the Monday after collection
    collected = parse_date(data.get("collected_at")) or datetime.now(timezone.utc)
    start = collected.date() + timedelta(days=7 - collected.weekday())
    calendar = {"start": start.isoformat(),
                "week_starts": [(start + timedelta(weeks=w)).isoformat() for w in range(4)]}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": {
            "handle": profile.get("handle"),
            "followers": followers,
            "following": profile.get("following"),
            "posts_count": profile.get("posts_count"),
            "highlight_count": profile.get("highlight_count"),
            "has_link": bool(profile.get("external_url") or profile.get("bio_links")),
            "bio_length": len(profile.get("bio") or ""),
        },
        "posts_analyzed": len(posts),
        "engagement": {
            "er_followers_avg": r2(mean(ers)),
            "er_followers_median": r2(median(ers)),
            "avg_likes": r2(mean(p.get("likes") for p in posts)),
            "avg_comments": r2(mean(p.get("comments") for p in posts)),
            "comments_to_likes": r2(total_comments / total_likes * 100) if total_likes else None,
            "median_shares": r2(median(shares)),
            "shares_known": len(shares),
            "by_type": type_stats,
        },
        "collab_split": collab_split,
        "trend": trend,
        "rubrics": rubrics,
        "calendar": calendar,
        "reels": {
            "count": len(reels),
            "avg_views": r2(mean(reel_views)),
            "median_views": r2(med_views),
            "views_to_followers": r2(med_views / followers) if med_views is not None and followers else None,
            "er_views_avg": r2(mean(reel_er_views)),
            "likes_per_view_median": r2(median(likes_per_view)),
            "avg_duration_sec": r2(mean(p.get("duration_sec") for p in reels)),
        },
        "format_mix": {t: {"count": c, "share_pct": r2(c / (len(posts) or 1) * 100)} for t, c in mix.most_common()},
        "cadence": cadence,
        "timing": timing,
        "captions": caption_stats,
        "pinned_count": sum(1 for p in posts if p.get("pinned")),
        "collab_count": sum(1 for p in posts if p.get("collab")),
        "top_posts": [post_summary(p, followers) for p in ranked[:5]],
        "bottom_posts": [post_summary(p, followers) for p in ranked[-5:][::-1]] if len(ranked) > 5 else [],
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("page_data")
    parser.add_argument("--out")
    args = parser.parse_args()

    src = Path(args.page_data)
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Cannot read {src}: {exc}")

    metrics = compute(data)
    out = Path(args.out) if args.out else src.with_name("metrics.json")
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    e, c = metrics["engagement"], metrics["cadence"]
    print(f"Wrote {out}")
    print(f"Posts analyzed: {metrics['posts_analyzed']} | ER avg: {e['er_followers_avg']}% "
          f"| median: {e['er_followers_median']}% | posts/week: {c['posts_per_week']}")
    for w in metrics["warnings"]:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
