"""Assemble page_data.json from what assets/collect.js returned.

Usage: python build_page_data.py <audit-dir> [--method in-page-capture]
Reads from <audit-dir>/raw/:
  profile.json   required: {"handle", "name", "category", "bio", "external_url", "bio_links",
                 "followers", "following", "posts_count", "is_verified", "is_business",
                 "highlights": ["title", ...]}
  rows.jsonl     required: one IGA.rows() line per post (a JSON array of 13 fields)
  brief.json     optional: the "brief" object (see references/collection.md)
  rubrics.json   optional: {"<post code>": "<rubric name>"}
  comments.json  optional: [{"post_url": "...", "text": "..."}]  (text only, no usernames)
  notes.json     optional: ["data limitation", ...]
Writes <audit-dir>/page_data.json. Standard library only.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["id", "date", "type", "likes", "comments", "views", "shares", "duration_sec",
          "carousel_count", "pinned", "collab", "location", "caption"]


def read_json(path, default=None):
    if not path.exists():
        if default is None:
            sys.exit(f"Missing {path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Bad JSON in {path}: {exc}")


def read_rows(path):
    if not path.exists():
        sys.exit(f"Missing {path}")
    posts, seen = [], set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip().rstrip(",")
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, str):   # a line copied with its outer quotes
                row = json.loads(row)
        except json.JSONDecodeError as exc:
            sys.exit(f"{path.name} line {n}: {exc}")
        if len(row) != len(FIELDS):
            sys.exit(f"{path.name} line {n}: {len(row)} fields, expected {len(FIELDS)}")
        post = dict(zip(FIELDS, row))
        if post["id"] in seen:
            continue
        seen.add(post["id"])
        kind = "reel" if post["type"] == "reel" else "p"
        post["url"] = f"https://www.instagram.com/{kind}/{post['id']}/"
        post["pinned"] = bool(post["pinned"])
        post["collab"] = bool(post["collab"])
        posts.append(post)
    return posts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audit_dir")
    parser.add_argument("--method", default="in-page-capture")
    args = parser.parse_args()
    audit = Path(args.audit_dir)
    raw = audit / "raw"

    prof = read_json(raw / "profile.json")
    posts = read_rows(raw / "rows.jsonl")
    rubrics = read_json(raw / "rubrics.json", {})
    for p in posts:
        if p["id"] in rubrics:
            p["rubric"] = rubrics[p["id"]]

    highlights = prof.get("highlights") or []
    profile = {
        "handle": prof.get("handle"), "name": prof.get("name"), "category": prof.get("category"),
        "bio": prof.get("bio") or "", "external_url": prof.get("external_url"),
        "bio_links": prof.get("bio_links") or [],
        "followers": prof.get("followers"), "following": prof.get("following"),
        "posts_count": prof.get("posts_count"),
        "is_verified": bool(prof.get("is_verified")), "is_business": bool(prof.get("is_business")),
        "is_professional": bool(prof.get("is_professional", prof.get("is_business"))),
        "is_private": bool(prof.get("is_private")),
        "has_email": bool(prof.get("has_email")), "has_phone": bool(prof.get("has_phone")),
        "highlight_count": prof.get("highlight_count", len(highlights)),
        "highlights": [h if isinstance(h, dict) else {"title": h, "count": None} for h in highlights],
    }
    data = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": args.method,
        "url": f"https://www.instagram.com/{profile['handle']}/",
        "brief": read_json(raw / "brief.json", {}),
        "profile": profile,
        "posts": posts,
        "comments_sample": [{"post_url": c.get("post_url"), "text": c.get("text"), "likes": c.get("likes")}
                            for c in read_json(raw / "comments.json", [])],
        "insights": {},
        "notes": read_json(raw / "notes.json", []),
    }
    out = audit / "page_data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tagged = sum(1 for p in posts if p.get("rubric"))
    print(f"Wrote {out}: {len(posts)} posts, {tagged} with rubric, {len(data['comments_sample'])} comments")


if __name__ == "__main__":
    main()
