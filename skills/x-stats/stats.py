#!/usr/bin/env python3
"""stats.py - analyze your own X post performance from a TSV or CSV.

Computes engagement rate = (likes + reposts + replies) / views for each post,
ranks posts, reports medians and totals, lists the best and worst posts, and
summarizes what the top 25% have in common compared with the rest.

Works with hand-made files and with analytics exports: common column names
(impressions, retweets, "post text", "tweet permalink"...) are recognized.
Missing values stay missing; nothing is estimated. Runs locally.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import statistics
import sys
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOOKS = os.path.normpath(os.path.join(HERE, "..", "x-post", "hooks.json"))

ALIASES = {
    "id": ["id", "post id", "tweet id"],
    "url": ["url", "link", "post link", "permalink", "tweet permalink"],
    "text": ["text", "post text", "tweet text", "post", "tweet", "content"],
    "views": ["views", "impressions", "impression count", "view count"],
    "likes": ["likes", "like count", "favorites", "favourites"],
    "reposts": ["reposts", "retweets", "repost count", "retweet count"],
    "replies": ["replies", "reply count"],
    "bookmarks": ["bookmarks", "bookmark count"],
    "date": ["date", "time", "created at", "posted", "posted at", "timestamp", "datetime"],
}
METRICS = ("views", "likes", "reposts", "replies", "bookmarks")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%b %d, %Y %H:%M",
                "%b %d, %Y %I:%M %p", "%b %d, %Y", "%a, %b %d, %Y", "%d %b %Y %H:%M", "%d %b %Y",
                "%a %b %d %H:%M:%S %z %Y")


def norm(h):
    return re.sub(r"[\s_]+", " ", (h or "").strip().lower())


def map_columns(header):
    found, normed = {}, [norm(h) for h in header]
    for key, names in ALIASES.items():
        for i, h in enumerate(normed):
            if h in names and i not in found.values():
                found[key] = i
                break
    return found


def parse_count(s):
    raw = (s or "").strip()
    t = raw.replace(",", "").replace("\u00a0", "").replace(" ", "")
    if t.lower() in ("", "-", "n/a", "na", "none", "null", "?"):
        return None, False
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kKmMbB]?)", t)
    if not m:
        raise ValueError(raw)
    return int(round(float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6, "b": 1e9}[m.group(2).lower()])), bool(m.group(2))


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None, False
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")), bool(re.search(r"\d:\d", s))
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt), "%H" in fmt or "%I" in fmt
        except ValueError:
            continue
    return None, False


def read_rows(raw, path):
    first = next((ln for ln in raw.splitlines() if ln.strip()), "")
    delim = "\t" if ("\t" in first or (path or "").lower().endswith(".tsv")) else ","
    rows = [r for r in csv.reader(io.StringIO(raw), delimiter=delim) if any(c.strip() for c in r)]
    if not rows:
        sys.exit("stats.py: the file is empty.")
    return rows[0], rows[1:]


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [(x["id"], re.compile(x["match"], re.IGNORECASE)) for x in data.get("formulas", [])]
    except (OSError, ValueError, KeyError, re.error):
        return []


def load(raw, path, formulas):
    header, body = read_rows(raw, path)
    cols = map_columns(header)
    notes, posts, abbr_count = [], [], 0
    for key in ("views", "likes", "reposts", "replies"):
        if key not in cols:
            notes.append("No %s column. Engagement rate needs views, likes, reposts and replies, "
                         "so it is not computed where %s is missing." % (key, key))
    if "text" not in cols:
        notes.append("No text column: patterns about wording are skipped.")
    for n, row in enumerate(body, 2):
        get = lambda k: row[cols[k]] if k in cols and cols[k] < len(row) else ""
        p = {"row": n, "text": get("text").replace("\\n", "\n").strip(),
             "url": get("url").strip() or None, "id": get("id").strip() or None}
        for k in METRICS:
            if k not in cols:
                p[k] = None
                continue
            try:
                p[k], abbr = parse_count(get(k))
                abbr_count += abbr
            except ValueError as e:
                p[k] = None
                notes.append("row %d: could not read %s %r; left out." % (n, k, str(e)))
        dt, has_time = parse_date(get("date"))
        if get("date").strip() and dt is None:
            notes.append("row %d: could not read date %r." % (n, get("date")))
        p["_dt"], p["_has_time"] = dt, has_time
        p["date"] = dt.strftime("%Y-%m-%d %H:%M" if has_time else "%Y-%m-%d") if dt else None
        parts = [p["likes"], p["reposts"], p["replies"]]
        p["engagements"] = None if any(v is None for v in parts) else sum(parts)
        p["er"] = (p["engagements"] / p["views"]) if p["engagements"] is not None and p["views"] else None
        text = p["text"]
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        p["hook"] = next((fid for fid, rx in formulas if rx.search(first)), "unclassified") if first else None
        p["chars"] = len(text)
        p["lines"] = len([ln for ln in text.splitlines() if ln.strip()])
        p["number_in_hook"] = bool(re.search(r"\d", first))
        p["question"] = "?" in text
        p["link"] = bool(re.search(r"https?://|www\.", text))
        p["hashtag"] = bool(re.search(r"(?<![\w&])#\w*[A-Za-z]\w*", text))
        p["thread"] = bool(re.match(r"^\s*(1/|\(1/|\U0001F9F5)", text))
        posts.append(p)
    if abbr_count:
        notes.append("%d values were abbreviated (e.g. 1.2K), so totals and rates are approximate."
                     % abbr_count)
    zero_views = sum(1 for p in posts if p["views"] == 0)
    if zero_views:
        notes.append("%d posts have 0 views; their engagement rate is undefined." % zero_views)
    return posts, cols, notes


def med(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def pct(x, digits=2):
    return "-" if x is None else ("%." + str(digits) + "f%%") % (x * 100)


def num(x):
    if x is None:
        return "-"
    return "{:,}".format(int(round(x))) if abs(x - round(x)) < 1e-9 or x >= 100 else "%.1f" % x


def common_ground(top, rest):
    """Plain statements about where the top posts differ from the rest."""
    out = []
    if not top or not rest:
        return out

    def share(xs, key):
        return sum(1 for x in xs if x.get(key)), len(xs)

    labels = {"number_in_hook": "open with a number in the first line",
              "question": "ask a question", "link": "include a link",
              "hashtag": "use a hashtag", "thread": "are threads"}
    for key, label in labels.items():
        a, n_a = share(top, key)
        b, n_b = share(rest, key)
        if abs(a / n_a - b / n_b) >= 0.3:
            out.append("%d of %d top posts %s, vs %d of %d others." % (a, n_a, label, b, n_b))
    for key, label in (("chars", "length"), ("lines", "line count")):
        ma, mb = med(x[key] for x in top), med(x[key] for x in rest)
        if ma is not None and mb and abs(ma - mb) / mb >= 0.25:
            unit = " characters" if key == "chars" else " lines"
            out.append("Median %s is %s%s for top posts vs %s for the others."
                       % (label, num(ma), unit, num(mb)))
    hooks = Counter(x["hook"] for x in top if x["hook"] and x["hook"] != "unclassified")
    for hook, c in hooks.most_common(2):
        if c >= 2:
            others = sum(1 for x in rest if x["hook"] == hook)
            out.append("%d of %d top posts use the '%s' hook (vs %d of %d others)."
                       % (c, len(top), hook, others, len(rest)))
    timed = [x for x in top if x["_dt"] is not None]
    days = Counter(WEEKDAYS[x["_dt"].weekday()] for x in timed)
    for day, c in days.most_common(1):
        if c >= 2:
            out.append("%d of %d top posts went out on a %s." % (c, len(top), day))
    hours = Counter(x["_dt"].hour // 2 * 2 for x in timed if x["_has_time"])
    for h, c in hours.most_common(1):
        if c >= 2:
            out.append("%d of %d top posts went out between %02d:00 and %02d:00 (as written in "
                       "the file; timezone unknown)." % (c, len(top), h, h + 2))
    return out


def analyze(posts, sort_key, n_best, min_views):
    rated = [p for p in posts if p["er"] is not None and (p["views"] or 0) >= min_views]
    keyfn = {"er": lambda p: p["er"] if p["er"] is not None else -1,
             "views": lambda p: p["views"] or -1, "likes": lambda p: p["likes"] or -1,
             "engagements": lambda p: p["engagements"] if p["engagements"] is not None else -1,
             "bookmarks": lambda p: p["bookmarks"] or -1}[sort_key]
    ranked = sorted(posts, key=keyfn, reverse=True)
    by_er = sorted(rated, key=lambda p: p["er"], reverse=True)
    k = max(1, len(by_er) // 4) if by_er else 0
    top, rest = by_er[:k], by_er[k:]
    dates = [p["_dt"] for p in posts if p["_dt"] is not None]
    summary = {
        "posts": len(posts),
        "rated_posts": len(rated),
        "date_range": [min(dates).strftime("%Y-%m-%d"), max(dates).strftime("%Y-%m-%d")] if dates else None,
        "medians": {k2: med(p[k2] for p in posts) for k2 in METRICS},
        "median_er": med(p["er"] for p in rated),
        "totals": {k2: (sum(p[k2] for p in posts if p[k2] is not None)
                        if any(p[k2] is not None for p in posts) else None) for k2 in METRICS},
        "missing": {k2: sum(1 for p in posts if p[k2] is None) for k2 in METRICS},
    }
    both = [p for p in posts if p["engagements"] is not None and p["views"]]
    summary["overall_er"] = (sum(p["engagements"] for p in both) / sum(p["views"] for p in both)
                             if both else None)
    return {
        "summary": summary,
        "ranked": ranked,
        "best": by_er[:n_best],
        "worst": list(reversed(by_er[-n_best:])) if len(by_er) > n_best else [],
        "top_n": len(top),
        "rest_n": len(rest),
        "common": common_ground(top, rest),
        "low_view_posts": sum(1 for p in posts if p["views"] is not None and 0 < p["views"] < 100),
    }


def short(s, n):
    s = (s or "").replace("\n", " / ")
    return s if len(s) <= n else s[: n - 3] + "..."


def render(res, cols, notes, top_n_rows, min_views):
    s = res["summary"]
    out = []
    span = " (%s to %s)" % tuple(s["date_range"]) if s["date_range"] else ""
    out.append("Post performance: %d posts%s" % (s["posts"], span))
    out.append("engagement rate (ER) = (likes + reposts + replies) / views")
    out.append("")
    m = s["medians"]
    out.append("medians   views %s   likes %s   reposts %s   replies %s   bookmarks %s   ER %s" % (
        num(m["views"]), num(m["likes"]), num(m["reposts"]), num(m["replies"]),
        num(m["bookmarks"]) if "bookmarks" in cols else "n/a", pct(s["median_er"])))
    t = s["totals"]
    out.append("totals    views %s   likes %s   reposts %s   replies %s   bookmarks %s   ER %s (all posts)" % (
        num(t["views"]), num(t["likes"]), num(t["reposts"]), num(t["replies"]),
        num(t["bookmarks"]) if "bookmarks" in cols else "n/a", pct(s["overall_er"])))
    missing = ["%s on %d" % (k, v) for k, v in s["missing"].items() if v and (k in cols)]
    if missing:
        out.append("missing   " + ", ".join(missing) + " posts (left out of those medians)")
    out.append("")
    out.append("rank     ER     views  likes  reposts  replies  bkmk  date              post")
    out.append("----  ------  -------  -----  -------  -------  ----  ----------------  " + "-" * 28)
    rows = res["ranked"][:top_n_rows] if top_n_rows else res["ranked"]
    for i, p in enumerate(rows, 1):
        out.append("%4d  %6s  %7s  %5s  %7s  %7s  %4s  %-16s  %s" % (
            i, pct(p["er"]), num(p["views"]), num(p["likes"]), num(p["reposts"]),
            num(p["replies"]), num(p["bookmarks"]), p["date"] or "-", short(p["text"] or p["url"] or "", 28)))
    for label, items in (("Best", res["best"]), ("Worst", res["worst"])):
        if not items:
            continue
        out.append("")
        out.append("%s %d by engagement rate%s:" % (label, len(items),
                                                   " (min %d views)" % min_views if min_views else ""))
        for p in items:
            out.append("  %s  %s views  \"%s\"%s" % (pct(p["er"]), num(p["views"]), short(p["text"], 70),
                                                     "  " + p["url"] if p["url"] else ""))
    out.append("")
    if res["top_n"] and res["rest_n"]:
        out.append("What the top 25%% (%d posts by ER) have in common vs the other %d:"
                   % (res["top_n"], res["rest_n"]))
        if res["common"]:
            out += ["  - " + c for c in res["common"]]
        else:
            out.append("  - No clear differences in this sample.")
        if s["rated_posts"] < 12:
            out.append("  (%d rated posts is a small sample; treat these as leads to test.)" % s["rated_posts"])
    else:
        out.append("Not enough rated posts to compare the top 25% with the rest.")
    if res["low_view_posts"] and not min_views:
        notes = notes + ["%d posts have under 100 views; their rates swing a lot. Try --min-views 100."
                         % res["low_view_posts"]]
    if notes:
        out.append("")
        out.append("Notes:")
        out += ["  - " + n for n in notes]
    return "\n".join(out)


def jsonable(p):
    q = {k: v for k, v in p.items() if not k.startswith("_")}
    if q.get("er") is not None:
        q["er"] = round(q["er"], 6)
    return q


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Analyze your X posts: engagement rate (likes + reposts + replies) / views, "
                    "ranking, medians, totals, best and worst posts, and what the top 25% have "
                    "in common.",
        epilog="Columns (header row; flexible names): url, text, views (or impressions), likes,\n"
               "reposts (or retweets), replies, bookmarks, date. TSV or CSV. Numbers like 1.2K\n"
               "are accepted. Blank cells stay blank; nothing is estimated.\n\n"
               "examples:\n"
               "  python3 stats.py posts.csv\n"
               "  python3 stats.py posts.tsv --min-views 100 --best 5\n"
               "  python3 stats.py posts.csv --sort bookmarks --top 10 --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="TSV or CSV file (default: stdin)")
    ap.add_argument("--sort", choices=("er", "views", "likes", "engagements", "bookmarks"),
                    default="er", help="ranking order (default: er)")
    ap.add_argument("--top", type=int, default=0, help="show only the top N rows of the ranking")
    ap.add_argument("--best", type=int, default=3, help="how many best and worst posts to list (default 3)")
    ap.add_argument("--min-views", type=int, default=0,
                    help="leave posts under this many views out of best/worst and patterns")
    ap.add_argument("--hooks", metavar="PATH", default=DEFAULT_HOOKS,
                    help="hooks.json for hook types (default: ../x-post/hooks.json)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    if args.file in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("stats.py: no input. Pass a TSV/CSV file or pipe one in. See --help.")
        raw = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8-sig", newline="") as f:
                raw = f.read()
        except OSError as e:
            sys.exit("stats.py: cannot read %s: %s" % (args.file, e.strerror))

    formulas = load_formulas(args.hooks)
    posts, cols, notes = load(raw, args.file, formulas)
    if not posts:
        print("stats.py: no data rows.", file=sys.stderr)
        return 2
    if not formulas:
        notes.append("hooks.json not found at %s; hook types skipped." % args.hooks)
    res = analyze(posts, args.sort, args.best, args.min_views)

    if args.json:
        payload = {"summary": res["summary"],
                   "ranked": [jsonable(p) for p in (res["ranked"][: args.top] if args.top else res["ranked"])],
                   "best": [jsonable(p) for p in res["best"]],
                   "worst": [jsonable(p) for p in res["worst"]],
                   "top_vs_rest": {"top": res["top_n"], "rest": res["rest_n"], "common": res["common"]},
                   "notes": notes}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(render(res, cols, notes, args.top, args.min_views))
    return 0


if __name__ == "__main__":
    sys.exit(main())
