#!/usr/bin/env python3
"""swipe.py - rank posts you collected from X by how far each beat its author.

You browse x.com yourself and save posts to a TSV (or CSV). This script never
logs in, scrapes or fetches anything. For each post it computes engagement
(likes + reposts + replies) as a multiple of that author's median in your
file, classifies the hook with x-post/hooks.json, and prints a ranked swipe
file plus patterns: hook types, length, and posting time.
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
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOOKS = os.path.normpath(os.path.join(HERE, "..", "x-post", "hooks.json"))

ALIASES = {
    "text": ["text", "post", "tweet", "post text", "tweet text", "content", "body"],
    "likes": ["likes", "like count", "favorites", "favourites", "hearts"],
    "reposts": ["reposts", "retweets", "rts", "repost count", "retweet count"],
    "replies": ["replies", "reply count", "comments"],
    "views": ["views", "impressions", "impression count", "view count"],
    "author": ["author", "handle", "username", "user", "account", "screen name"],
    "date": ["date", "time", "posted", "posted at", "created at", "timestamp", "datetime"],
    "url": ["url", "link", "post link", "permalink", "tweet permalink"],
    "bookmarks": ["bookmarks", "bookmark count"],
}
ENGAGEMENT = ("likes", "reposts", "replies")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def norm_header(h):
    return re.sub(r"[\s_]+", " ", (h or "").strip().lower())


def map_columns(header):
    found = {}
    normed = [norm_header(h) for h in header]
    for key, names in ALIASES.items():
        for i, h in enumerate(normed):
            if h in names and i not in found.values():
                found[key] = i
                break
    return found


def parse_count(s):
    """'1.2K' -> (1200, True). Blank or '-' -> (None, False). Bad -> raises ValueError."""
    raw = (s or "").strip()
    t = raw.replace(",", "").replace("\u00a0", "").replace(" ", "")
    if t.lower() in ("", "-", "n/a", "na", "none", "null", "?"):
        return None, False
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kKmMbB]?)", t)
    if not m:
        raise ValueError(raw)
    mult = {"": 1, "k": 1e3, "m": 1e6, "b": 1e9}[m.group(2).lower()]
    return int(round(float(m.group(1)) * mult)), bool(m.group(2))


DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%b %d, %Y %H:%M",
                "%b %d, %Y %I:%M %p", "%b %d, %Y", "%d %b %Y %H:%M", "%d %b %Y",
                "%a %b %d %H:%M:%S %z %Y")


def parse_date(s):
    """Return (datetime or None, has_time)."""
    s = (s or "").strip()
    if not s:
        return None, False
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt, bool(re.search(r"\d:\d", s))
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt), "%H" in fmt or "%I" in fmt
        except ValueError:
            continue
    return None, False


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [(x["id"], re.compile(x["match"], re.IGNORECASE)) for x in data.get("formulas", [])]
    except (OSError, ValueError, KeyError, re.error):
        return []


def classify(text, formulas):
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    for fid, rx in formulas:
        if rx.search(first):
            return fid
    return "unclassified"


def rejoin_tsv(raw):
    """Rebuild TSV rows when a pasted post carried real line breaks."""
    lines = [ln for ln in raw.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    header = lines[0].split("\t")
    n = len(header)
    rows, buf = [], None
    for ln in lines[1:]:
        if buf is not None:
            buf += "\n" + ln
        elif ln.count("\t") == 0 and rows and n > 1:
            rows[-1][-1] += "\n" + ln  # continuation of a last-column post
            continue
        else:
            buf = ln
        if buf.count("\t") >= n - 1:
            rows.append(buf.split("\t"))
            buf = None
    if buf is not None:
        rows.append(buf.split("\t"))
    return [header] + rows


def read_table(raw, path):
    first = next((ln for ln in raw.splitlines() if ln.strip()), "")
    is_tsv = "\t" in first or (path or "").lower().endswith(".tsv")
    rows = list(csv.reader(io.StringIO(raw), delimiter="\t" if is_tsv else ","))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        sys.exit("swipe.py: the file is empty.")
    if is_tsv and any(len(r) != len(rows[0]) for r in rows[1:]):
        rows = [r for r in rejoin_tsv(raw) if any(c.strip() for c in r)]
    return rows[0], rows[1:]


def load_posts(raw, path):
    header, body = read_table(raw, path)
    cols = map_columns(header)
    if "text" not in cols:
        sys.exit("swipe.py: no text column found. Header was: %s" % ", ".join(header))
    eng_cols = [c for c in ENGAGEMENT if c in cols]
    if not eng_cols:
        sys.exit("swipe.py: need at least one of likes, reposts, replies.")
    notes, posts, abbreviated = [], [], 0
    for n, row in enumerate(body, 2):
        get = lambda k: row[cols[k]] if k in cols and cols[k] < len(row) else ""
        text = get("text").replace("\\n", "\n").strip()
        p = {"row": n, "text": text, "author": get("author").strip() or "(unknown)",
             "url": get("url").strip()}
        bad = False
        for k in ENGAGEMENT + ("views", "bookmarks"):
            if k not in cols:
                p[k] = None
                continue
            try:
                p[k], abbr = parse_count(get(k))
                abbreviated += abbr
            except ValueError as e:
                notes.append("row %d: could not read %s value %r; left out." % (n, k, str(e)))
                p[k] = None
                bad = True
        missing = [k for k in eng_cols if p[k] is None]
        if missing and not bad:
            notes.append("row %d: no %s value; engagement not computed." % (n, "/".join(missing)))
        p["engagement"] = None if missing else sum(p[k] for k in eng_cols)
        dt, has_time = parse_date(get("date"))
        if get("date").strip() and dt is None:
            notes.append("row %d: could not read date %r." % (n, get("date")))
        p["date"] = dt.isoformat(sep=" ") if dt else (get("date").strip() or None)
        p["_dt"], p["_has_time"] = dt, has_time
        posts.append(p)
    if abbreviated:
        notes.append("%d values were abbreviated by X (e.g. 1.2K). They are rounded, so "
                     "multiples are approximate." % abbreviated)
    if "author" not in cols:
        notes.append("No author column: the baseline is the median of the whole file.")
    if eng_cols != list(ENGAGEMENT):
        notes.append("Engagement uses %s only (no %s column)."
                     % (" + ".join(eng_cols), ", ".join(c for c in ENGAGEMENT if c not in eng_cols)))
    return posts, cols, notes


def analyze(posts, formulas, min_posts):
    by_author = defaultdict(list)
    for p in posts:
        if p["engagement"] is not None:
            by_author[p["author"]].append(p["engagement"])
    for p in posts:
        base_list = by_author.get(p["author"], [])
        p["author_posts"] = len(base_list)
        p["author_median"] = statistics.median(base_list) if base_list else None
        if p["engagement"] is None or len(base_list) < min_posts or not p["author_median"]:
            p["multiple"] = None
        else:
            p["multiple"] = round(p["engagement"] / p["author_median"], 2)
        p["rate"] = (round(p["engagement"] / p["views"] * 100, 2)
                     if p["engagement"] is not None and p["views"] else None)
        p["hook"] = classify(p["text"], formulas)
        p["chars"] = len(p["text"])
        p["lines"] = len([ln for ln in p["text"].splitlines() if ln.strip()])
        first = next((ln for ln in p["text"].splitlines() if ln.strip()), "")
        p["number_in_hook"] = bool(re.search(r"\d", first))
        p["question"] = "?" in p["text"]
        p["link"] = bool(re.search(r"https?://|www\.", p["text"]))
    ranked = sorted((p for p in posts if p["multiple"] is not None), key=lambda p: -p["multiple"])
    no_base = sorted((p for p in posts if p["multiple"] is None and p["engagement"] is not None),
                     key=lambda p: -p["engagement"])
    return ranked, no_base


def patterns(ranked, no_base):
    pool = ranked if ranked else no_base
    if not pool:
        return None
    k = max(1, len(pool) // 4)
    top, rest = pool[:k], pool[k:]

    def med(xs, key):
        vals = [x[key] for x in xs]
        return statistics.median(vals) if vals else None

    def share(xs, key):
        return "%d/%d" % (sum(1 for x in xs if x[key]), len(xs))

    timed = [p for p in top if p["_dt"] is not None]
    hours = Counter("%02d-%02d" % (p["_dt"].hour // 2 * 2, p["_dt"].hour // 2 * 2 + 2)
                    for p in timed if p["_has_time"])
    days = Counter(WEEKDAYS[p["_dt"].weekday()] for p in timed)
    return {
        "basis": "author multiple" if ranked else "raw engagement (no author baselines)",
        "top_n": len(top), "rest_n": len(rest),
        "hooks_top": Counter(p["hook"] for p in top).most_common(),
        "hooks_all": Counter(p["hook"] for p in pool).most_common(),
        "median_chars": [med(top, "chars"), med(rest, "chars")],
        "median_lines": [med(top, "lines"), med(rest, "lines")],
        "number_in_hook": [share(top, "number_in_hook"), share(rest, "number_in_hook")],
        "question": [share(top, "question"), share(rest, "question")],
        "link": [share(top, "link"), share(rest, "link")],
        "weekday_top": days.most_common(),
        "hour_top": sorted(hours.items()),
        "top_with_time": sum(1 for p in timed if p["_has_time"]),
    }


def fmt_n(x):
    return "-" if x is None else "{:,}".format(int(x)) if float(x).is_integer() else "%.1f" % x


def short(s, n):
    s = s.replace("\n", " / ")
    return s if len(s) <= n else s[: n - 3] + "..."


def render(ranked, no_base, pat, notes, top, n_posts, n_authors, min_posts):
    out = ["Swipe file: %d posts from %d authors" % (n_posts, n_authors), ""]
    out.append("rank  x-median   eng     views  author           hook                 first line")
    out.append("----  --------  ------  -------  ---------------  -------------------  " + "-" * 30)
    for i, p in enumerate(ranked[:top] if top else ranked, 1):
        out.append("%4d  %7.1fx  %6s  %7s  %-15s  %-19s  %s" % (
            i, p["multiple"], fmt_n(p["engagement"]), fmt_n(p["views"]),
            short(p["author"], 15), short(p["hook"], 19), short(p["text"], 30)))
    if not ranked:
        out.append("  (no author has %d+ posts in the file, so no multiples)" % min_posts)
    if no_base:
        out.append("")
        out.append("No baseline (author has fewer than %d posts in the file), by raw engagement:" % min_posts)
        for p in no_base[:10]:
            out.append("      %6s eng  %7s views  %-15s  %-19s  %s" % (
                fmt_n(p["engagement"]), fmt_n(p["views"]), short(p["author"], 15),
                short(p["hook"], 19), short(p["text"], 30)))
    if pat:
        out.append("")
        out.append("Patterns: top 25%% (%d posts) vs the rest (%d), by %s"
                   % (pat["top_n"], pat["rest_n"], pat["basis"]))
        out.append("  hook types, top:     " + ", ".join("%s %d" % kv for kv in pat["hooks_top"]))
        out.append("  hook types, all:     " + ", ".join("%s %d" % kv for kv in pat["hooks_all"]))
        mc, ml = pat["median_chars"], pat["median_lines"]
        out.append("  median length:       %s chars vs %s" % (fmt_n(mc[0]), fmt_n(mc[1])))
        out.append("  median lines:        %s vs %s" % (fmt_n(ml[0]), fmt_n(ml[1])))
        out.append("  number in hook:      %s vs %s" % tuple(pat["number_in_hook"]))
        out.append("  has a question:      %s vs %s" % tuple(pat["question"]))
        out.append("  has a link:          %s vs %s" % tuple(pat["link"]))
        if pat["weekday_top"]:
            out.append("  top posts, weekday:  " + ", ".join("%s %d" % kv for kv in pat["weekday_top"]))
        if pat["hour_top"]:
            out.append("  top posts, hour:     " + ", ".join("%s %d" % kv for kv in pat["hour_top"])
                       + "  (times as written in your file; timezone unknown)")
        elif pat["weekday_top"]:
            out.append("  top posts, hour:     no times in the dates, so no hour pattern")
        else:
            out.append("  posting time:        no dates in the file")
        out.append("  Small samples are noisy. Treat these as leads to test, not rules.")
    if notes:
        out.append("")
        out.append("Notes:")
        out += ["  - " + n for n in notes]
    return "\n".join(out)


def write_md(path, ranked, no_base, top):
    lines = ["# Swipe file", "",
             "Ranked by engagement as a multiple of each author's median in the source file.", ""]
    for i, p in enumerate(ranked[: top or 10], 1):
        lines.append("## %d. %.1fx  %s  (%s)" % (i, p["multiple"], p["author"], p["hook"]))
        meta = ["engagement %s" % fmt_n(p["engagement"])]
        if p["views"]:
            meta.append("views %s" % fmt_n(p["views"]))
        if p["date"]:
            meta.append(str(p["date"]))
        if p["url"]:
            meta.append(p["url"])
        lines += ["", " | ".join(meta), ""]
        lines += ["> " + ln if ln.strip() else ">" for ln in p["text"].splitlines()]
        lines += ["", "Why it worked:", "", "How I'd adapt it (my own idea, my own words):", ""]
    if no_base:
        lines += ["## No baseline", ""]
        lines += ["- %s: %s (engagement %s)" % (p["author"], short(p["text"], 80), fmt_n(p["engagement"]))
                  for p in no_base[:10]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def clean_for_json(p):
    return {k: v for k, v in p.items() if not k.startswith("_")}


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Rank X posts you collected by engagement as a multiple of each author's "
                    "median, classify each hook, and summarize patterns (hook types, length, "
                    "posting time). Reads a TSV or CSV; never fetches anything.",
        epilog="Columns (header row required, names are flexible): text, likes, reposts,\n"
               "replies, views, author, date, url. Write line breaks inside a post as \\n.\n"
               "Numbers like 1.2K and 3,400 are fine. Dates: 2026-11-03 or 2026-11-03 14:20.\n\n"
               "examples:\n"
               "  python3 swipe.py posts.tsv\n"
               "  python3 swipe.py posts.tsv --top 5 --md swipe.md\n"
               "  python3 swipe.py posts.csv --min-posts 2 --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="TSV or CSV file (default: stdin)")
    ap.add_argument("--top", type=int, default=0, help="show only the top N ranked posts")
    ap.add_argument("--min-posts", type=int, default=3,
                    help="posts an author needs in the file for a baseline (default 3)")
    ap.add_argument("--hooks", metavar="PATH", default=DEFAULT_HOOKS,
                    help="hooks.json (default: ../x-post/hooks.json)")
    ap.add_argument("--md", metavar="FILE", help="also write a markdown swipe file")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    if args.file in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("swipe.py: no input. Pass a TSV/CSV file or pipe one in. See --help.")
        raw = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8-sig", newline="") as f:
                raw = f.read()
        except OSError as e:
            sys.exit("swipe.py: cannot read %s: %s" % (args.file, e.strerror))

    formulas = load_formulas(args.hooks)
    posts, cols, notes = load_posts(raw, args.file)
    if not formulas:
        notes.append("hooks.json not found at %s; hooks are unclassified. Use --hooks." % args.hooks)
    ranked, no_base = analyze(posts, formulas, args.min_posts)
    pat = patterns(ranked, no_base)
    n_authors = len(set(p["author"] for p in posts))
    if args.md:
        write_md(args.md, ranked, no_base, args.top)
        notes.append("wrote markdown swipe file to %s" % args.md)

    if args.json:
        payload = {"posts": len(posts), "authors": n_authors, "columns": sorted(cols),
                   "ranked": [clean_for_json(p) for p in (ranked[: args.top] if args.top else ranked)],
                   "no_baseline": [clean_for_json(p) for p in no_base],
                   "patterns": pat, "notes": notes}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(render(ranked, no_base, pat, notes, args.top, len(posts), n_authors, args.min_posts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
