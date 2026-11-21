#!/usr/bin/env python3
"""audit.py - score an X profile against rubric.json and list the top 3 fixes.

Input is plain text with 'key: value' lines that you copy from your own
profile (see --help for the keys). A key you leave out is 'not provided' and
its checks are not scored; a key that is present but empty means the profile
has none, and scores 0. Runs locally; it never visits x.com.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RUBRIC = os.path.join(HERE, "rubric.json")
KEYS = ("name", "handle", "bio", "location", "link", "website", "banner", "pinned",
        "pinned_date", "recent_posts", "followers", "following")
KEY_RE = re.compile(r"^\s*(%s)\s*:\s?(.*)$" % "|".join(KEYS), re.I)
STOPWORDS = set("""
a an and are as at be but by for from has have i in is it its my of on or our so
that the their them they this to was we what when with you your about into over
than then just more most very can will not no all any how who why where which
after before every share like make made get got day days week weeks year years
""".split())
BUZZ_RE = re.compile(
    r"\b(passionate|enthusiast|ninja|guru|rockstar|visionary|lover of|thought leader|"
    r"serial entrepreneur|dreamer|wanderlust|coffee addict|aspiring|wizard|evangelist|"
    r"views (are )?my own|opinions (are )?my own|living my best life|creative soul)\b", re.I)
WHO_WHAT_RE = re.compile(
    r"\b(i help|helping|i build|i write|i teach|i share|i ship|i make|i design|i run|"
    r"building|founder|co-founder|developer|dev|designer|writer|engineer|marketer|coach|"
    r"consultant|creator|author|researcher|teacher|analyst|for (\w+ ){0,2}(founders|developers|"
    r"designers|creators|marketers|freelancers|students|teams|startups|parents|writers))\b", re.I)
CTA_RE = re.compile(
    r"(\b(newsletter|join|subscribe|free|get|download|book|dm|below|link|read|grab|apply|"
    r"waitlist|try|follow|sign up|start here)\b|↓|\U0001F447|->)", re.I)
WEAK_RE = re.compile(
    r"^\s*(so\b|just\b|i think|some thoughts|hey\b|hi\b|hello\b|a thread|thread\b|"
    r"\U0001F9F5|i('ve| have) been thinking|let'?s talk about|welcome to my)", re.I)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
NO_BANNER_RE = re.compile(r"^\s*(none|default|blank|empty|no banner|missing|not set|n/?a)\s*\.?$", re.I)
BANNER_MSG_RE = re.compile(
    r"\b(text|says|tagline|headline|logo|product|screenshot|photo|face|portrait|book|cover|"
    r"newsletter|offer|url|cta|results?|testimonial|promise|stats?)\b", re.I)
NO_TEXT_RE = re.compile(r"\bno (text|words|tagline|message)\b", re.I)


def parse_profile(raw):
    fields, cur = {}, None
    for line in raw.splitlines():
        m = KEY_RE.match(line)
        if m:
            cur = m.group(1).lower()
            if cur == "website":
                cur = "link"
            fields[cur] = m.group(2).rstrip()
        elif cur is not None:
            fields[cur] = (fields[cur] + "\n" + line.rstrip()) if fields[cur] else line.rstrip()
    fields = {k: v.strip() for k, v in fields.items()}
    if "recent_posts" in fields:
        posts = []
        for ln in fields["recent_posts"].splitlines():
            if not ln.strip() or ln.strip() == "---":
                continue
            m = re.match(r"^\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.*)$", ln)
            if m:
                try:
                    posts.append({"date": datetime.strptime(m.group(1), "%Y-%m-%d").date(), "text": m.group(2)})
                    continue
                except ValueError:
                    pass
            posts.append({"date": None, "text": ln.strip()})
        fields["_posts"] = posts
    return fields


def read_voice_keywords(path):
    with open(path, encoding="utf-8-sig") as f:
        raw = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)
    kws, cur = [], None
    for line in raw.splitlines():
        m = re.match(r"^\s{0,3}#{2,6}\s+(.*?)\s*$", line)
        if m:
            cur = m.group(1).lower()
            continue
        if cur and ("words i use" in cur or cur.startswith("niche")):
            line = re.sub(r"^\s*([-*+]|\d+[.)])\s*", "", line)
            if "words i use" in cur:
                kws += [x.strip() for x in re.split(r"[,;]", line) if x.strip()]
            else:
                kws += [w for w in re.findall(r"[A-Za-z][A-Za-z+-]{3,}", line) if w.lower() not in STOPWORDS]
    return kws


def stem(w):
    w = w.lower()
    for suf in ("ing", "ers", "er", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def stems_of(text):
    return set(stem(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text or "") if w.lower() not in STOPWORDS and len(w) >= 3)


def keyword_hit(text, keywords):
    low = " " + " ".join(re.findall(r"[a-z0-9]+", (text or "").lower())) + " "
    st = stems_of(text)
    for kw in keywords:
        toks = re.findall(r"[a-z0-9]+", kw.lower())
        if not toks:
            continue
        if " " + " ".join(toks) + " " in low or (len(toks) == 1 and len(toks[0]) >= 3 and stem(toks[0]) in st):
            return kw
    return None


def run_check(cid, f, keywords, today):
    """Return (earned_fraction 0..1, note)."""
    bio = f.get("bio", "")
    if cid == "bio-length":
        n = len(bio)
        if n == 0:
            return 0, "no bio"
        if n > 160:
            return 0, "%d chars, over X's 160 limit" % n
        return (1 if n >= 60 else 0.4), "%d chars" % n
    if cid == "bio-who-what":
        m = WHO_WHAT_RE.search(bio)
        return (1, "says what you do ('%s')" % m.group(0)) if m else (0, "no clear 'what I do / who I help'")
    if cid == "bio-no-buzzwords":
        hits = sorted(set(m.group(0).lower() for m in BUZZ_RE.finditer(bio)))
        if not bio:
            return 0, "no bio"
        return (0, "labels: %s" % ", ".join(hits)) if hits else (1, "no empty labels")
    if cid == "bio-proof":
        m = re.search(r"\d|\bex-\w+|@\w+|\b(built|founded|created|launched|shipped|wrote|author of)\b", bio, re.I)
        return (1, "proof point ('%s')" % m.group(0)) if m else (0, "no number, product or result")
    if cid == "bio-clean":
        tags, emo = len(re.findall(r"(?<!\w)#\w+", bio)), len(EMOJI_RE.findall(bio))
        ok = tags <= 2 and emo <= 3 and bool(bio)
        return (1 if ok else 0), "%d hashtags, %d emoji" % (tags, emo)
    pinned = f.get("pinned", "")
    if cid == "pinned-exists":
        return (1, "pinned post present") if pinned else (0, "nothing pinned")
    if cid == "pinned-hook":
        if not pinned:
            return 0, "nothing pinned"
        first = next((ln.strip() for ln in pinned.splitlines() if ln.strip()), "")
        sent = re.split(r"(?<=[.!?])\s", first, maxsplit=1)[0]
        if WEAK_RE.match(first):
            return 0, "opens with filler ('%s')" % WEAK_RE.match(first).group(0).strip()
        if len(sent) > 100:
            return 0.5, "first sentence is %d chars" % len(sent)
        return 1, "first sentence %d chars, no filler" % len(sent)
    if cid == "pinned-recent":
        try:
            d = datetime.strptime(f.get("pinned_date", "")[:10], "%Y-%m-%d").date()
        except ValueError:
            return None, "pinned_date not in YYYY-MM-DD form"
        age = (today - d).days
        return (1 if age <= 180 else 0), "pinned %d days ago" % age
    if cid == "pinned-cta":
        if not pinned:
            return 0, "nothing pinned"
        tail = pinned.strip().splitlines()[-1]
        ok = "?" in tail or bool(CTA_RE.search(tail)) or bool(re.search(r"https?://", pinned))
        return (1, "ends with an ask") if ok else (0, "no question, link or follow reason at the end")
    handle = f.get("handle", "").lstrip("@").strip()
    if cid == "handle-short":
        n = len(handle)
        if n == 0:
            return 0, "no handle"
        return (1 if n <= 12 else 0.5 if n <= 15 else 0), "%d chars" % n
    if cid == "handle-clean":
        digits = re.search(r"\d{3,}", handle)
        unders = handle.count("_")
        ok = not digits and unders <= 1
        return (1 if ok else 0), "%s, %d underscore%s" % (
            "digit string '%s'" % digits.group(0) if digits else "no digit strings", unders, "" if unders == 1 else "s")
    name = f.get("name", "")
    if cid == "name-real":
        letters = re.findall(r"[A-Za-zऀ-ॿ]", name)
        if not name:
            return 0, "no name"
        if len(name) > 50:
            return 0, "%d chars, over X's 50 limit" % len(name)
        return (1, "readable name") if len(letters) >= 3 else (0, "no readable name")
    if cid == "name-clean":
        emo = len(EMOJI_RE.findall(name))
        caps = name.isupper() and len(re.findall(r"[A-Z]", name)) > 4
        return (1 if emo <= 2 and not caps else 0), "%d emoji%s" % (emo, ", all caps" if caps else "")
    banner = f.get("banner", "")
    if cid == "banner-set":
        return (0, "no custom banner") if not banner or NO_BANNER_RE.match(banner) else (1, "custom banner")
    if cid == "banner-message":
        if not banner or NO_BANNER_RE.match(banner):
            return 0, "no banner"
        if NO_TEXT_RE.search(banner) or not BANNER_MSG_RE.search(banner):
            return 0, "no promise, product or proof described"
        return 1, "banner carries a message"
    posts = f.get("_posts", [])
    if cid == "consistency-cadence":
        dated = sorted(p["date"] for p in posts if p["date"])
        span = max(1, (dated[-1] - dated[0]).days + 1)
        per_week = len(dated) / (span / 7.0)
        return (1 if per_week >= 3 else 0.5 if per_week >= 1 else 0), \
            "%.1f posts/week (%d posts over %d days)" % (per_week, len(dated), span)
    if cid == "consistency-on-topic":
        if not posts:
            return 0, "no recent posts"
        on = sum(1 for p in posts if keyword_hit(p["text"], keywords))
        share = on / len(posts)
        return (1 if share >= 0.6 else 0.5 if share >= 0.4 else 0), \
            "%d of %d recent posts on your niche keywords" % (on, len(posts))
    if cid == "niche-single":
        segs = [s for s in re.split(r"\s*[|•·/]\s*|\s+\+\s+", bio) if s.strip()]
        n = len(segs)
        return (1 if n <= 3 else 0.4 if n == 4 else 0), "%d segment%s in the bio" % (n, "" if n == 1 else "s")
    if cid == "niche-bio-pinned":
        shared = (stems_of(bio) & stems_of(pinned)) - {"thi", "thing"}
        if not pinned:
            return 0, "nothing pinned"
        return (1, "shared words: %s" % ", ".join(sorted(shared)[:4])) if shared else (0, "pinned post shares no key words with the bio")
    if cid == "niche-keyword":
        hit = keyword_hit(name + " " + bio, keywords)
        return (1, "uses '%s'" % hit) if hit else (0, "none of your niche keywords in name or bio")
    link = f.get("link", "")
    if cid == "link-present":
        return (1, link) if link else (0, "no link")
    if cid == "cta-in-bio":
        m = CTA_RE.search(bio)
        return (1, "ask in bio ('%s')" % m.group(0)) if m else (0, "bio has no next step")
    if cid == "link-off-x":
        if not link:
            return 0, "no link"
        on_x = re.search(r"(^|//|\.)(x|twitter)\.com\b", link, re.I)
        return (0, "links to X itself") if on_x else (1, "links off X")
    return None, "no automatic check; judge by hand"


def available(fields, keywords):
    have = {k for k in fields if not k.startswith("_")}
    if keywords:
        have.add("keywords")
    if any(p["date"] for p in fields.get("_posts", [])) and \
            len([p for p in fields.get("_posts", []) if p["date"]]) >= 2:
        have.add("recent_posts_dated")
    return have


def audit(fields, rubric, keywords, today):
    have = available(fields, keywords)
    results, earned, possible, unscored = [], 0, 0, 0
    for crit in rubric["criteria"]:
        cres = {"id": crit["id"], "name": crit["name"], "points": crit["points"],
                "earned": 0, "scored_points": 0, "checks": []}
        for chk in crit["checks"]:
            missing = [n for n in chk.get("needs", []) if n not in have]
            item = {"id": chk["id"], "points": chk["points"], "desc": chk["desc"], "fix": chk["fix"]}
            if missing:
                item.update(scored=False, earned=None, note="not scored: %s not provided" % ", ".join(missing))
                unscored += chk["points"]
            else:
                frac, note = run_check(chk["id"], fields, keywords, today)
                if frac is None:
                    item.update(scored=False, earned=None, note="not scored: " + note)
                    unscored += chk["points"]
                else:
                    pts = round(chk["points"] * frac)
                    item.update(scored=True, earned=pts, note=note)
                    cres["earned"] += pts
                    cres["scored_points"] += chk["points"]
            cres["checks"].append(item)
        earned += cres["earned"]
        possible += cres["scored_points"]
        results.append(cres)
    lost = [(c["points"] - c["earned"], crit["name"], c) for crit in results for c in crit["checks"]
            if c["scored"] and c["earned"] < c["points"]]
    lost.sort(key=lambda t: -t[0])
    fixes = [{"criterion": name, "check": c["id"], "points_lost": pts, "fix": c["fix"], "why": c["note"]}
             for pts, name, c in lost[:3]]
    return {"earned": earned, "scored_points": possible, "unscored_points": unscored,
            "percent": round(100.0 * earned / possible) if possible else None,
            "criteria": results, "top_fixes": fixes}


def render(res, fields):
    out = []
    who = fields.get("handle") or fields.get("name") or "profile"
    out.append("Profile audit: %s" % who)
    if res["scored_points"]:
        out.append("score %d / %d scored points (%d%%)%s" % (
            res["earned"], res["scored_points"], res["percent"],
            "   %d points not scored (missing input)" % res["unscored_points"] if res["unscored_points"] else ""))
    else:
        out.append("Nothing could be scored: no profile fields were provided.")
    out.append("")
    for crit in res["criteria"]:
        sp = crit["scored_points"]
        head = "%d/%d" % (crit["earned"], sp) if sp else "not scored"
        out.append("%-18s %-11s (of %d)" % (crit["name"], head, crit["points"]))
        for c in crit["checks"]:
            mark = "?" if not c["scored"] else ("+" if c["earned"] == c["points"] else "-")
            pts = "  - " if not c["scored"] else "%d/%d" % (c["earned"], c["points"])
            out.append("  %s %-22s %5s  %s" % (mark, c["id"], pts, c["note"]))
    out.append("")
    if res["top_fixes"]:
        out.append("Top %d fixes" % len(res["top_fixes"]))
        for i, fx in enumerate(res["top_fixes"], 1):
            out.append("%d. [%s, -%d] %s" % (i, fx["criterion"], fx["points_lost"], fx["fix"]))
            out.append("   now: %s" % fx["why"])
    else:
        out.append("No points lost on the checks that could be scored.")
    out.append("")
    out.append("Heuristic checks on text you pasted. Judge the banner and tone by eye too.")
    return "\n".join(out)


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Score an X profile you pasted against a 100-point rubric (bio, pinned post, "
                    "handle and name, banner, consistency, niche focus, CTA and link) and list "
                    "the top 3 fixes.",
        epilog="Input keys, one per line as 'key: value' (multi-line values continue on the\n"
               "next lines): name, handle, bio, location, link, banner (describe it), pinned\n"
               "(text of the pinned post), pinned_date (YYYY-MM-DD), recent_posts (one per\n"
               "line, optionally 'YYYY-MM-DD | text'). Leave a key out if you don't know it;\n"
               "write 'bio:' with nothing after it if the profile has no bio.\n\n"
               "examples:\n"
               "  python3 audit.py profile.txt --voice voice.md\n"
               "  python3 audit.py profile.txt --keywords \"saas, pricing, indie\" --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="profile text file (default: stdin)")
    ap.add_argument("--keywords", default="", help="comma-separated niche keywords")
    ap.add_argument("--voice", metavar="PATH", help="voice.md (Niche and 'Words I use' become keywords)")
    ap.add_argument("--rubric", metavar="PATH", default=DEFAULT_RUBRIC, help="rubric.json to use")
    ap.add_argument("--today", metavar="YYYY-MM-DD", help="date to measure pinned-post age from (default: today)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    try:
        with open(args.rubric, encoding="utf-8") as f:
            rubric = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("audit.py: cannot load rubric %s: %s" % (args.rubric, e))
    total = sum(c["points"] for c in rubric["criteria"])
    if total != 100:
        print("audit.py: note: rubric totals %d points, not 100." % total, file=sys.stderr)

    if args.file in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("audit.py: no input. Pass a profile file or pipe one in. See --help.")
        raw = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8-sig") as f:
                raw = f.read()
        except OSError as e:
            sys.exit("audit.py: cannot read %s: %s" % (args.file, e.strerror))

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.voice:
        try:
            keywords += read_voice_keywords(args.voice)
        except OSError as e:
            sys.exit("audit.py: cannot read %s: %s" % (args.voice, e.strerror))
    today = date.today()
    if args.today:
        try:
            today = datetime.strptime(args.today, "%Y-%m-%d").date()
        except ValueError:
            sys.exit("audit.py: --today must be YYYY-MM-DD")

    fields = parse_profile(raw)
    if not any(k in fields for k in KEYS):
        sys.exit("audit.py: no 'key: value' profile fields found. See --help for the format.")
    res = audit(fields, rubric, keywords, today)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(render(res, fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
