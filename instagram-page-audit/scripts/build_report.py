"""Build the HTML audit report.

Usage: python build_report.py <audit-dir> [--out report.html]
Reads page_data.json, metrics.json and report_content.json from <audit-dir>,
validates report_content.json and writes report.html. Standard library only.
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "report-template.html"
REQUIRED_SECTIONS = ["stats", "audience", "strategy", "content_plan", "ideas", "ads", "clients", "kpi", "checklist"]
BLOCK_FIELDS = {
    "paragraph": ["text"],
    "list": ["items"],
    "table": ["columns", "rows"],
    "cards": ["items"],
    "callout": ["text"],
    "copy": ["text"],
    "checklist": ["items"],
    "metrics": [],
    "posts": ["which"],
    "format_mix": [],
    "trend": [],
    "rubrics": [],
    "collab_split": [],
}
ACCOUNT_TYPES = ("local_business", "expert", "creator", "brand")

# Minimum content per section, so a report is never thin. (block type, field, count):
# "items" counts list/cards/checklist entries, "rows" counts table rows, "blocks" counts blocks.
MINIMUMS = {
    "stats": [("posts", "blocks", 2), ("trend", "blocks", 1)],
    "audience": [("cards", "items", 2)],
    "strategy": [("table", "rows", 3), ("copy", "blocks", 2)],
    "content_plan": [("table", "max_rows", 12)],
    "ideas": [("cards", "items", 18), ("*", "items", 28), ("table", "rows", 7)],
    "ads": [("table", "rows", 3), ("copy", "blocks", 2), ("callout", "blocks", 1)],
    "clients": [("copy", "blocks", 2), ("*", "items", 3)],
    "kpi": [("table", "rows", 5)],
    "checklist": [("checklist", "items", 8)],
}
SUMMARY_MINIMUMS = {"scores": 6, "problems": 3, "quick_wins": 3}


def count_in(section, btype, what):
    blocks = [b for b in section.get("blocks") or [] if btype == "*" or b.get("type") == btype]
    if what == "blocks":
        return len(blocks)
    if what == "rows":
        return sum(len(b.get("rows") or []) for b in blocks)
    if what == "max_rows":
        return max((len(b.get("rows") or []) for b in blocks), default=0)
    return sum(len(b.get("items") or []) for b in blocks if b.get("type") in ("list", "cards", "checklist"))


def check_minimums(content):
    """Return a list of 'too thin' messages."""
    thin = []
    summary = content.get("summary") or {}
    for key, n in SUMMARY_MINIMUMS.items():
        if len(summary.get(key) or []) < n:
            thin.append(f"summary.{key}: {len(summary.get(key) or [])}, need ≥ {n}")
    sections = {s.get("id"): s for s in content.get("sections") or []}
    for sid, rules in MINIMUMS.items():
        section = sections.get(sid)
        if not section:
            continue
        for btype, what, n in rules:
            got = count_in(section, btype, what)
            if got < n:
                label = "list/cards" if btype == "*" else btype
                unit = "rows in one table" if what == "max_rows" else what
                thin.append(f"{sid}: {label} {unit} = {got}, need ≥ {n}")
    return thin

LABELS = {
    "uk": {
        "summary": "Підсумок і оцінка", "overall": "Загальна оцінка", "problems": "Головні проблеми",
        "quick_wins": "Швидкі перемоги", "followers": "Підписники", "following": "Підписки",
        "posts": "Публікації", "er_avg": "ER середній", "er_median": "ER медіана",
        "posts_week": "Постів на тиждень", "reels_views": "Медіана переглядів Reels",
        "views_followers": "Перегляди / підписники", "comments_likes": "Коментарі / лайки",
        "days_since": "Днів від останнього посту", "max_gap": "Найдовша пауза, днів",
        "cta": "Пости із CTA", "format": "Формат", "share": "Частка", "count": "К-сть",
        "avg_views": "Сер. перегляди", "date": "Дата", "type": "Тип", "likes": "Лайки",
        "comments": "Коментарі", "views": "Перегляди", "caption": "Початок підпису", "open": "відкрити",
        "copy": "Копіювати", "copied": "Скопійовано", "assumptions": "Припущення",
        "sources": "Джерела", "data_notes": "Обмеження даних", "collected": "Дані зібрано",
        "analyzed": "Проаналізовано постів",
        "likes_views": "Лайки / перегляди Reels", "period": "Період", "rubric": "Рубрика", "group": "Група", "owned": "Власні пости", "collab": "Колаборації", "median_likes": "Медіана лайків", "median_views": "Медіана переглядів Reels", "account_type": "Тип акаунта", "account_types": {"local_business": "Локальний бізнес", "expert": "Експерт / послуги", "creator": "Блогер / креатор", "brand": "Великий бренд"}, "generated": "Звіт згенеровано", "contents": "Зміст",
        "types": {"reel": "Reels", "carousel": "Карусель", "image": "Фото", "video": "Відео", "unknown": "Інше"},
    },
    "ru": {
        "summary": "Итог и оценка", "overall": "Общая оценка", "problems": "Главные проблемы",
        "quick_wins": "Быстрые победы", "followers": "Подписчики", "following": "Подписки",
        "posts": "Публикации", "er_avg": "ER средний", "er_median": "ER медиана",
        "posts_week": "Постов в неделю", "reels_views": "Медиана просмотров Reels",
        "views_followers": "Просмотры / подписчики", "comments_likes": "Комментарии / лайки",
        "days_since": "Дней с последнего поста", "max_gap": "Самая длинная пауза, дней",
        "cta": "Посты с CTA", "format": "Формат", "share": "Доля", "count": "Кол-во",
        "avg_views": "Ср. просмотры", "date": "Дата", "type": "Тип", "likes": "Лайки",
        "comments": "Комментарии", "views": "Просмотры", "caption": "Начало подписи", "open": "открыть",
        "copy": "Копировать", "copied": "Скопировано", "assumptions": "Допущения",
        "sources": "Источники", "data_notes": "Ограничения данных", "collected": "Данные собраны",
        "analyzed": "Проанализировано постов",
        "likes_views": "Лайки / просмотры Reels", "period": "Период", "rubric": "Рубрика", "group": "Группа", "owned": "Свои посты", "collab": "Коллаборации", "median_likes": "Медиана лайков", "median_views": "Медиана просмотров Reels", "account_type": "Тип аккаунта", "account_types": {"local_business": "Локальный бизнес", "expert": "Эксперт / услуги", "creator": "Блогер / креатор", "brand": "Крупный бренд"}, "generated": "Отчёт создан", "contents": "Содержание",
        "types": {"reel": "Reels", "carousel": "Карусель", "image": "Фото", "video": "Видео", "unknown": "Другое"},
    },
    "en": {
        "summary": "Summary & scorecard", "overall": "Overall score", "problems": "Top problems",
        "quick_wins": "Quick wins", "followers": "Followers", "following": "Following",
        "posts": "Posts", "er_avg": "ER average", "er_median": "ER median",
        "posts_week": "Posts per week", "reels_views": "Median Reels views",
        "views_followers": "Views / followers", "comments_likes": "Comments / likes",
        "days_since": "Days since last post", "max_gap": "Longest gap, days",
        "cta": "Posts with a CTA", "format": "Format", "share": "Share", "count": "Count",
        "avg_views": "Avg views", "date": "Date", "type": "Type", "likes": "Likes",
        "comments": "Comments", "views": "Views", "caption": "Caption start", "open": "open",
        "copy": "Copy", "copied": "Copied", "assumptions": "Assumptions",
        "sources": "Sources", "data_notes": "Data limitations", "collected": "Data collected",
        "analyzed": "Posts analyzed",
        "likes_views": "Likes / Reels views", "period": "Period", "rubric": "Rubric", "group": "Group", "owned": "Owned posts", "collab": "Collabs", "median_likes": "Median likes", "median_views": "Median Reels views", "account_type": "Account type", "account_types": {"local_business": "Local business", "expert": "Expert / services", "creator": "Creator", "brand": "Large brand"}, "generated": "Report generated", "contents": "Contents",
        "types": {"reel": "Reels", "carousel": "Carousel", "image": "Photo", "video": "Video", "unknown": "Other"},
    },
}


class ReportError(Exception):
    pass


def esc(text):
    return html.escape(str(text), quote=True)


def safe_url(url):
    """Escaped URL for href; anything but http(s) becomes '#' (blocks javascript: and data: links)."""
    url = str(url or "").strip()
    return esc(url) if re.match(r"https?://", url, re.IGNORECASE) else "#"


def rich(text):
    """Escape text, then allow **bold** and line breaks."""
    out = esc(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return out.replace("\n", "<br>")


def num(value, digits=0):
    if value is None:
        return "—"
    if digits == 0:
        return f"{round(value):,}".replace(",", " ")
    return f"{value:,.{digits}f}".replace(",", " ")


def pct(value):
    return "—" if value is None else f"{value:.2f}%".replace(".00%", "%")


def validate(content):
    errors = []
    if content.get("account_type") not in ACCOUNT_TYPES:
        errors.append(f"'account_type' must be one of: {', '.join(ACCOUNT_TYPES)}.")
    if not isinstance(content.get("sections"), list):
        errors.append("'sections' must be a list.")
        raise ReportError("\n".join(errors))
    summary = content.get("summary") or {}
    for key in ("verdict", "scores", "problems", "quick_wins"):
        if not summary.get(key):
            errors.append(f"summary.{key} is missing or empty.")
    for i, s in enumerate(summary.get("scores") or []):
        if not isinstance(s.get("score"), (int, float)) or not 0 <= s["score"] <= 10:
            errors.append(f"summary.scores[{i}].score must be a number 0–10.")
    ids = []
    for i, section in enumerate(content["sections"]):
        where = f"sections[{i}] ({section.get('id', '?')})"
        for key in ("id", "title", "blocks"):
            if not section.get(key):
                errors.append(f"{where}: '{key}' is missing.")
        ids.append(section.get("id"))
        for j, block in enumerate(section.get("blocks") or []):
            btype = block.get("type")
            if btype not in BLOCK_FIELDS:
                errors.append(f"{where}.blocks[{j}]: unknown type '{btype}'.")
                continue
            for field in BLOCK_FIELDS[btype]:
                if block.get(field) in (None, "", []):
                    errors.append(f"{where}.blocks[{j}] ({btype}): '{field}' is missing.")
            if btype == "table":
                width = len(block.get("columns") or [])
                for k, row in enumerate(block.get("rows") or []):
                    if len(row) != width:
                        errors.append(f"{where}.blocks[{j}] row {k}: {len(row)} cells, expected {width}.")
    missing = [s for s in REQUIRED_SECTIONS if s not in ids]
    if missing:
        errors.append("Missing required sections: " + ", ".join(missing))
    thin = check_minimums(content)
    if thin and content.get("reduced"):
        # A reduced audit (private account, thin data) may be shorter: warn only
        for t in thin:
            print("WARNING (reduced audit):", t)
    else:
        errors += [f"Too thin: {t}" for t in thin]
    if errors:
        raise ReportError("\n".join(errors))


def render_metrics(metrics, L):
    e, r, c, p = metrics["engagement"], metrics["reels"], metrics["cadence"], metrics["profile"]
    tiles = [
        (L["followers"], num(p.get("followers"))),
        (L["posts"], num(p.get("posts_count"))),
        (L["er_avg"], pct(e.get("er_followers_avg"))),
        (L["er_median"], pct(e.get("er_followers_median"))),
        (L["posts_week"], num(c.get("posts_per_week"), 1)),
        (L["reels_views"], num(r.get("median_views"))),
        (L["views_followers"], num(r.get("views_to_followers"), 2)),
        (L["likes_views"], pct(r.get("likes_per_view_median"))),
        (L["comments_likes"], pct(e.get("comments_to_likes"))),
        (L["days_since"], num(c.get("days_since_last_post"))),
        (L["max_gap"], num(c.get("max_gap_days"))),
        (L["cta"], pct(metrics["captions"].get("pct_with_cta"))),
    ]
    items = "".join(f'<div class="tile"><div class="tile-value">{esc(v)}</div>'
                    f'<div class="tile-label">{esc(k)}</div></div>' for k, v in tiles)
    return f'<div class="tiles">{items}</div>'


def render_format_mix(metrics, L):
    mix, by_type = metrics["format_mix"], metrics["engagement"]["by_type"]
    max_er = max((v.get("er_followers_avg") or 0 for v in by_type.values()), default=0) or 1
    rows = []
    for t, m in mix.items():
        er = by_type.get(t, {}).get("er_followers_avg")
        width = 0 if er is None else max(er / max_er * 100, 2)
        rows.append(
            f'<tr><td>{esc(L["types"].get(t, t))}</td><td class="num">{esc(m["count"])}</td>'
            f'<td class="num">{pct(m["share_pct"])}</td>'
            f'<td><div class="bar"><span style="width:{width:.0f}%"></span></div>{pct(er)}</td>'
            f'<td class="num">{num(by_type.get(t, {}).get("avg_views"))}</td></tr>')
    head = (f'<tr><th>{L["format"]}</th><th>{L["count"]}</th><th>{L["share"]}</th>'
            f'<th>{L["er_avg"]}</th><th>{L["avg_views"]}</th></tr>')
    return f'<div class="table-wrap"><table><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_groups(groups, first_col, L, share=False):
    """Table of group_stats() rows from metrics.json (trend, rubrics, owned vs collab)."""
    if not groups:
        return ""
    head = (f'<tr><th>{esc(first_col)}</th><th>{L["count"]}</th>' + (f'<th>{L["share"]}</th>' if share else "")
            + f'<th>{L["er_median"]}</th><th>{L["median_likes"]}</th><th>{L["comments"]}</th>'
            f'<th>{L["median_views"]}</th></tr>')
    rows = "".join(
        f'<tr><td>{esc(name)}</td><td class="num">{num(g.get("count"))}</td>'
        + (f'<td class="num">{pct(g.get("share_pct"))}</td>' if share else "")
        + f'<td class="num">{pct(g.get("er_followers_median"))}</td><td class="num">{num(g.get("median_likes"))}</td>'
        f'<td class="num">{num(g.get("median_comments"))}</td><td class="num">{num(g.get("median_reel_views"))}</td></tr>'
        for name, g in groups.items())
    return f'<div class="table-wrap"><table><thead>{head}</thead><tbody>{rows}</tbody></table></div>'


def render_posts(metrics, which, L):
    posts = metrics["top_posts"] if which == "top" else metrics["bottom_posts"]
    if not posts:
        return ""
    head = (f'<tr><th>#</th><th>{L["date"]}</th><th>{L["type"]}</th><th>{L["likes"]}</th>'
            f'<th>{L["comments"]}</th><th>{L["views"]}</th><th>ER</th><th>{L["caption"]}</th></tr>')
    rows = []
    for i, p in enumerate(posts, 1):
        link = f' <a href="{safe_url(p["url"])}" target="_blank" rel="noopener">{L["open"]}</a>' if p.get("url") else ""
        rows.append(
            f'<tr><td class="num">{i}</td><td>{esc((p.get("date") or "")[:10])}</td>'
            f'<td>{esc(L["types"].get(p.get("type"), p.get("type") or ""))}</td>'
            f'<td class="num">{num(p.get("likes"))}</td><td class="num">{num(p.get("comments"))}</td>'
            f'<td class="num">{num(p.get("views"))}</td><td class="num">{pct(p.get("er_followers"))}</td>'
            f'<td>{esc(p.get("caption_start") or "")}{link}</td></tr>')
    return f'<div class="table-wrap"><table><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_block(block, metrics, L):
    t = block["type"]
    if t == "paragraph":
        return f"<p>{rich(block['text'])}</p>"
    if t == "list":
        tag = "ol" if block.get("ordered") else "ul"
        return f"<{tag}>" + "".join(f"<li>{rich(i)}</li>" for i in block["items"]) + f"</{tag}>"
    if t == "checklist":
        return '<ul class="checklist">' + "".join(
            f'<li><label><input type="checkbox"> <span>{rich(i)}</span></label></li>' for i in block["items"]) + "</ul>"
    if t == "table":
        head = "".join(f"<th>{esc(c)}</th>" for c in block["columns"])
        body = "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in row) + "</tr>" for row in block["rows"])
        return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    if t == "cards":
        cards = []
        for i, c in enumerate(block["items"], 1):
            tag = f'<span class="tag">{esc(c["tag"])}</span>' if c.get("tag") else ""
            meta = f'<div class="card-meta">{rich(c["meta"])}</div>' if c.get("meta") else ""
            cards.append(f'<article class="card"><div class="card-head"><span class="card-n">{i}</span>{tag}</div>'
                         f'<h4>{rich(c.get("title", ""))}</h4><div class="card-body">{rich(c.get("body", ""))}</div>{meta}</article>')
        return f'<div class="cards">{"".join(cards)}</div>'
    if t == "callout":
        tone = block.get("tone") if block.get("tone") in ("info", "warn", "good") else "info"
        title = f"<strong>{esc(block['title'])}</strong><br>" if block.get("title") else ""
        return f'<div class="callout {tone}">{title}{rich(block["text"])}</div>'
    if t == "copy":
        label = f'<div class="copy-label">{esc(block.get("label", ""))}</div>'
        return (f'<div class="copy">{label}<pre>{esc(block["text"])}</pre>'
                f'<button type="button" class="copy-btn" data-done="{esc(L["copied"])}">{esc(L["copy"])}</button></div>')
    if t == "metrics":
        return render_metrics(metrics, L)
    if t == "format_mix":
        return render_format_mix(metrics, L)
    if t == "posts":
        return render_posts(metrics, block["which"], L)
    if t == "trend":
        return render_groups(metrics.get("trend") or {}, L["period"], L)
    if t == "rubrics":
        return render_groups(metrics.get("rubrics") or {}, L["rubric"], L, share=True)
    if t == "collab_split":
        split = metrics.get("collab_split") or {}
        return render_groups({L[k]: split[k] for k in ("owned", "collab") if k in split}, L["group"], L)
    return ""


def render_summary(content, L):
    s = content["summary"]
    scores = s["scores"]
    overall = sum(x["score"] for x in scores) / len(scores)
    bars = "".join(
        f'<div class="score"><div class="score-top"><span>{esc(x["area"])}</span><b>{x["score"]:g}/10</b></div>'
        f'<div class="bar"><span class="lvl-{"low" if x["score"] < 4 else "mid" if x["score"] < 7 else "high"}" '
        f'style="width:{x["score"] * 10:.0f}%"></span></div>'
        f'<div class="score-reason">{rich(x.get("reason", ""))}</div></div>' for x in scores)
    problems = "".join(f"<li>{rich(p)}</li>" for p in s["problems"])
    wins = "".join(f"<li>{rich(w)}</li>" for w in s["quick_wins"])
    return f'''<section id="summary"><h2><span class="sec-n">1</span>{esc(L["summary"])}</h2>
<div class="verdict"><div class="overall"><div class="overall-value">{overall:.1f}</div>
<div class="overall-label">{esc(L["overall"])} / 10</div></div><p>{rich(s["verdict"])}</p></div>
<div class="scores">{bars}</div>
<div class="two-col"><div class="panel warn"><h3>{esc(L["problems"])}</h3><ol>{problems}</ol></div>
<div class="panel good"><h3>{esc(L["quick_wins"])}</h3><ol>{wins}</ol></div></div></section>'''


def build(audit_dir, out_path):
    def load(name):
        path = audit_dir / name
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReportError(f"Cannot read {path}: {exc}")

    page, metrics, content = load("page_data.json"), load("metrics.json"), load("report_content.json")
    validate(content)
    lang = content.get("language", "uk")
    L = LABELS.get(lang, LABELS["en"])
    profile = page.get("profile") or {}
    handle = profile.get("handle") or "instagram"
    title = content.get("title") or f"Instagram @{handle}"

    nav = [f'<a href="#summary">1. {esc(L["summary"])}</a>']
    body = [render_summary(content, L)]
    for n, section in enumerate(content["sections"], 2):
        sid = esc(section["id"])
        nav.append(f'<a href="#{sid}">{n}. {esc(section["title"])}</a>')
        intro = f'<p class="lead">{rich(section["intro"])}</p>' if section.get("intro") else ""
        blocks = "".join(render_block(b, metrics, L) for b in section["blocks"])
        body.append(f'<section id="{sid}"><h2><span class="sec-n">{n}</span>{esc(section["title"])}</h2>{intro}{blocks}</section>')

    notes = list(metrics.get("warnings") or []) + list(page.get("notes") or [])
    extra = []
    if notes:
        extra.append(f'<h3>{esc(L["data_notes"])}</h3><ul>' + "".join(f"<li>{esc(x)}</li>" for x in notes) + "</ul>")
    if content.get("assumptions"):
        extra.append(f'<h3>{esc(L["assumptions"])}</h3><ul>' + "".join(f"<li>{rich(x)}</li>" for x in content["assumptions"]) + "</ul>")
    if content.get("sources"):
        extra.append(f'<h3>{esc(L["sources"])}</h3><ol class="sources">' + "".join(
            f'<li><a href="{safe_url(s.get("url"))}" target="_blank" rel="noopener">{esc(s.get("title") or s.get("url", ""))}</a></li>'
            for s in content["sources"]) + "</ol>")
    if extra:
        body.append(f'<section id="notes" class="notes">{"".join(extra)}</section>')

    kind = L["account_types"].get(content.get("account_type"), "")
    hero = f'''<p class="eyebrow">Instagram audit · @{esc(handle)} · {esc(kind)}</p><h1>{esc(title)}</h1>
<p class="subtitle">{esc(content.get("subtitle", ""))}</p>
<div class="hero-meta"><span><b>{num(profile.get("followers"))}</b> {esc(L["followers"])}</span>
<span><b>{num(profile.get("following"))}</b> {esc(L["following"])}</span>
<span><b>{num(profile.get("posts_count"))}</b> {esc(L["posts"])}</span>
<a href="{safe_url(page.get("url"))}" target="_blank" rel="noopener">{esc(page.get("url", ""))}</a></div>'''
    footer = (f'{esc(L["collected"])}: {esc((page.get("collected_at") or "")[:10])} · '
              f'{esc(L["analyzed"])}: {esc(metrics.get("posts_analyzed", 0))} · '
              f'{esc(L["generated"])}: {datetime.now().strftime("%Y-%m-%d")}')

    # One pass, so a "{{...}}" inside collected text is never treated as a placeholder
    slots = {"LANG": esc(lang), "TITLE": esc(title), "CONTENTS_LABEL": esc(L["contents"]),
             "HERO": hero, "NAV": "".join(nav), "CONTENT": "".join(body), "FOOTER": footer}
    template = TEMPLATE.read_text(encoding="utf-8")
    page_html = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: slots.get(m.group(1), m.group(0)), template)
    out_path.write_text(page_html, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audit_dir")
    parser.add_argument("--out")
    args = parser.parse_args()
    audit_dir = Path(args.audit_dir)
    out = Path(args.out) if args.out else audit_dir / "report.html"
    try:
        path = build(audit_dir, out)
    except ReportError as exc:
        sys.exit(f"Report not built:\n{exc}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
