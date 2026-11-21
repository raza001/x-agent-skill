#!/usr/bin/env python3
"""angles.py - filter trending topics for relevance to your niche.

Reads a trending list (pasted from X's Explore page, a one-per-line list, a
TSV, or the JSON that fetch_api.py prints), scores each topic's relevance
against your niche keywords, flags risky topics (politics, tragedy,
controversy, religion, health scares) so you can decide, and prints angle
prompts for the relevant ones.

Keyword matching is crude: it misses synonyms and context. Read the low
scores by eye too. Runs locally; nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

STOPWORDS = set("""
a an and are as at be but by for from has have i in is it its my of on or our so
that the their them they this to was we what when with you your about into over
than then just more most very can will not no all any how who why where which
small solo first one two make making made get got like day days week weeks
""".split())

RISK = {
    "politics": r"\b(election|elections|vote|voting|votes|ballot|bjp|congress|aap|modi|rahul gandhi|trump|biden|harris|"
                r"parliament|lok sabha|senate|minister|president|prime minister|government|govt|"
                r"protest|protests|campaign|democrat|republican|right wing|left wing|sanctions|"
                r"impeach\w*|referendum|tariff\w*)\b",
    "tragedy": r"\b(dies|died|dead|death|deaths|rip|killed|crash|shooting|attack|attacks|"
               r"bomb\w*|blast|earthquake|flood|floods|cyclone|hurricane|tsunami|wildfire|fire|victims|"
               r"tragedy|missing person|stampede|collapse|war|massacre|terror\w*|hostage\w*|funeral|"
               r"condolences)\b",
    "controversy": r"\b(scandal|arrested|arrest|lawsuit|sued|boycott|cancel\w*|allegations?|accused|"
                   r"leaked|leak|exposed|slams|controversy|backlash|outrage|ban|banned|fraud|"
                   r"scam|racist|sexist|harass\w*|abuse)\b",
    "religion": r"\b(allah|hindu|muslim|christian|sikh|jewish|temple|mosque|church|religio\w*|"
                r"blasphem\w*|ram mandir|eid|diwali riots)\b",
    "health": r"\b(outbreak|pandemic|virus|covid|vaccine|epidemic|cases rise|hospitali[sz]ed|cancer)\b",
}

SKIP_LINES = re.compile(
    r"^(what'?s happening|trends for you|trending now|show more|explore|for you|trending|"
    r"news|sports|entertainment|search|settings|\d+|\d+\s*[·.])$", re.I)
CATEGORY_RE = re.compile(r"^(?:\d+\s*[·.]\s*)?(?:(.+?)\s*[·]\s*)?trending(?:\s+in\s+(.+))?$", re.I)
VOLUME_RE = re.compile(r"^([\d.,]+\s*[KkMm]?)\s+(posts|tweets)$", re.I)
WITH_RE = re.compile(r"^trending with\s+(.+)$", re.I)


def split_tag(s):
    s = s.lstrip("#$")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    s = re.sub(r"([A-Za-z])(\d)", r"\1 \2", s)
    return s


def tokens(s):
    # Only hashtags and cashtags get camelCase splitting (#BuildInPublic);
    # plain words such as "SaaS" stay whole.
    words = [split_tag(w) if w.startswith(("#", "$")) else w for w in s.split()]
    return re.findall(r"[a-z0-9ऀ-ॿ]+", " ".join(words).lower())


def stem(w):
    for suf, rep in (("ies", "y"), ("ing", ""), ("ers", ""), ("ed", ""), ("es", ""), ("er", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: len(w) - len(suf)] + rep
    return w


def parse_count(s):
    t = (s or "").replace(",", "").strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KkMm]?)", t)
    if not m:
        return None
    return int(round(float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6}[m.group(2).lower()]))


def parse_topics(raw):
    raw = raw.strip()
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if data is not None:
            items = data.get("trends", data.get("data", [])) if isinstance(data, dict) else data
            out = []
            for it in items:
                if isinstance(it, str):
                    out.append({"topic": it, "volume": None, "category": None, "related": []})
                else:
                    name = it.get("name") or it.get("trend_name") or it.get("topic")
                    vol = it.get("post_count", it.get("tweet_count", it.get("volume")))
                    if name:
                        out.append({"topic": name, "volume": vol if isinstance(vol, int) else parse_count(str(vol or "")),
                                    "category": it.get("category"), "related": []})
            return out
    lines = [ln.strip() for ln in raw.splitlines()]
    if lines and "\t" in lines[0] and lines[0].lower().startswith("topic"):
        header = [h.strip().lower() for h in lines[0].split("\t")]
        out = []
        for ln in lines[1:]:
            if not ln:
                continue
            cells = dict(zip(header, [c.strip() for c in ln.split("\t")]))
            out.append({"topic": cells.get("topic", ""), "volume": parse_count(cells.get("volume", "")),
                        "category": cells.get("category") or None, "related": []})
        return [t for t in out if t["topic"]]
    out, pending_cat = [], None
    for ln in lines:
        if not ln or SKIP_LINES.match(ln):
            continue
        m = VOLUME_RE.match(ln)
        if m and out:
            out[-1]["volume"] = parse_count(m.group(1))
            continue
        m = WITH_RE.match(ln)
        if m and out:
            out[-1]["related"] = [x.strip() for x in m.group(1).split(",") if x.strip()]
            continue
        m = CATEGORY_RE.match(ln)
        if m and ("trending" in ln.lower()):
            pending_cat = (m.group(1) or ("Trending in " + m.group(2) if m.group(2) else None))
            continue
        topic = re.sub(r"^\d+[.)]\s+", "", ln)
        out.append({"topic": topic, "volume": None, "category": pending_cat, "related": []})
        pending_cat = None
    return out


def read_voice(path):
    with open(path, encoding="utf-8-sig") as f:
        raw = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)
    sections, cur = {}, None
    for line in raw.splitlines():
        m = re.match(r"^\s{0,3}#{2,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            cur = m.group(1).strip().lower()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def section(sections, name):
    for k, v in sections.items():
        if name in k:
            return v
    return ""


def keywords_from_voice(sections):
    kws = []
    for line in section(sections, "words i use").splitlines():
        line = re.sub(r"^\s*([-*+]|\d+[.)])\s*", "", line)
        kws += [x.strip() for x in re.split(r"[,;]", line) if x.strip()]
    niche = section(sections, "niche")
    kws += [w for w in re.findall(r"[A-Za-z][A-Za-z+-]{2,}", niche) if w.lower() not in STOPWORDS]
    avoid = section(sections, "topics to avoid")
    avoid_terms = [x.strip() for x in re.split(r"[,;\n]", avoid) if x.strip() and not x.strip().startswith("-")]
    avoid_terms += [re.sub(r"^\s*[-*+]\s*", "", x).strip() for x in avoid.splitlines() if x.strip().startswith(("-", "*", "+"))]
    audience = section(sections, "audience").split("\n")[0].strip()
    return kws, [a.rstrip(".") for a in avoid_terms if a], audience


def score_topic(t, keywords):
    text = t["topic"]
    toks = tokens(text)
    stems = set(stem(x) for x in toks)
    rel_toks = set(stem(x) for r in t["related"] for x in tokens(r))
    joined = " " + " ".join(toks) + " "
    score, matched = 0, []
    for kw in keywords:
        kt = tokens(kw)
        if not kt:
            continue
        phrase = " " + " ".join(kt) + " "
        if phrase in joined:
            score += 60 if not matched else 20
            matched.append(kw)
        elif len(kt) == 1 and len(kt[0]) >= 3 and stem(kt[0]) in stems:
            score += 35 if not matched else 15
            matched.append(kw)
        elif any(stem(x) in rel_toks for x in kt if len(x) >= 3) or (len(kt) == 1 and kt[0] in rel_toks):
            score += 25 if not matched else 10
            matched.append(kw + " (related)")
    return min(100, score), matched


def risk_of(t, avoid):
    hay = " ".join(tokens(t["topic"]) + t["related"]).lower()
    flags = []
    for cat, rx in RISK.items():
        m = re.search(rx, hay)
        if m:
            flags.append("%s ('%s')" % (cat, m.group(0)))
    cat = (t.get("category") or "").lower()
    if "politic" in cat and not any(f.startswith("politics") for f in flags):
        flags.append("politics (X category)")
    for a in avoid:
        if a and re.search(r"(?<!\w)" + re.escape(a.lower()) + r"(?!\w)", hay):
            flags.append("on your 'topics to avoid' ('%s')" % a)
    return flags


def fmt_vol(v):
    if v is None:
        return "-"
    for div, suf in ((1_000_000, "M"), (1000, "K")):
        if v >= div:
            tenths = (v * 10 + div // 2) // div  # round half up to one decimal
            return ("%d.%d" % (tenths // 10, tenths % 10)).rstrip("0").rstrip(".") + suf
    return str(v)


def angle_prompts(topic):
    return {
        "hot_take": "What does your niche get wrong about %s? Take a clear side you can defend." % topic,
        "explainer": "What does your audience need to know about %s, in 3 plain points?" % topic,
        "personal_experience": "When did %s touch your own work? What happened, with real details?" % topic,
    }


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Score trending topics for relevance to your niche keywords, flag risky "
                    "topics (politics, tragedy, controversy, religion, health), and print angle "
                    "prompts (hot take, explainer, personal experience) for relevant ones.",
        epilog="Input formats: text pasted from X's Explore tab (category, topic and 'N posts'\n"
               "lines are understood), one topic per line, a TSV with a 'topic' header\n"
               "(optional volume, category columns), or fetch_api.py trends --json output.\n\n"
               "examples:\n"
               "  python3 angles.py trending.txt --voice voice.md\n"
               "  python3 angles.py trending.txt --keywords \"saas, pricing, indie, side project\"\n"
               "  python3 fetch_api.py trends --woeid 1 --live --json | python3 angles.py --voice voice.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="topics file (default: stdin)")
    ap.add_argument("--keywords", default="", help="comma-separated niche keywords")
    ap.add_argument("--voice", metavar="PATH", help="voice.md: uses Niche, Words I use, Audience, Topics to avoid")
    ap.add_argument("--min", type=int, default=30, help="relevance score to count as relevant (default 30)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    avoid, audience = [], ""
    if args.voice:
        try:
            kws, avoid, audience = keywords_from_voice(read_voice(args.voice))
        except OSError as e:
            print("angles.py: cannot read %s: %s" % (args.voice, e.strerror), file=sys.stderr)
            return 2
        keywords += kws
    seen, uniq = set(), []
    for k in keywords:
        if k.lower() not in seen:
            seen.add(k.lower())
            uniq.append(k)
    keywords = uniq
    if not keywords:
        print("angles.py: no niche keywords. Pass --keywords or --voice voice.md.", file=sys.stderr)
        return 2

    if args.file in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("angles.py: no input. Pass a topics file or pipe one in. See --help.")
        raw = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8-sig") as f:
                raw = f.read()
        except OSError as e:
            sys.exit("angles.py: cannot read %s: %s" % (args.file, e.strerror))

    topics = parse_topics(raw)
    if not topics:
        print("angles.py: no topics found in input.", file=sys.stderr)
        return 2
    for t in topics:
        t["relevance"], t["matched"] = score_topic(t, keywords)
        t["risk"] = risk_of(t, avoid)
        t["relevant"] = t["relevance"] >= args.min
        if t["relevant"]:
            t["angles"] = angle_prompts(t["topic"])
    topics.sort(key=lambda t: (-t["relevance"], t["topic"].lower()))
    relevant = [t for t in topics if t["relevant"]]
    risky = [t for t in topics if t["risk"]]

    if args.json:
        print(json.dumps({"keywords": keywords, "audience": audience or None, "min": args.min,
                          "topics": topics}, ensure_ascii=False, indent=2))
        return 0

    shown = ", ".join(keywords[:10]) + (" ..." if len(keywords) > 10 else "")
    print("Trending topics vs your niche")
    print("keywords: %s" % shown)
    if audience:
        print("audience: %s" % audience)
    print("")
    print(" rel  risk   volume   topic                           matched")
    print(" ---  -----  -------  ------------------------------  " + "-" * 24)
    for t in topics:
        topic = t["topic"] if len(t["topic"]) <= 30 else t["topic"][:27] + "..."
        print(" %3d  %-5s  %7s  %-30s  %s" % (
            t["relevance"], "RISK" if t["risk"] else "-", fmt_vol(t["volume"]), topic,
            ", ".join(t["matched"]) or "-"))
    print("")
    print("Relevant (score >= %d): %d of %d topics" % (args.min, len(relevant), len(topics)))
    for i, t in enumerate(relevant, 1):
        print("")
        print("%d. %s   [%s posts]%s" % (i, t["topic"], fmt_vol(t["volume"]),
                                        "   RISK: " + "; ".join(t["risk"]) if t["risk"] else ""))
        print("   angle prompts (write these in your voice, with your own facts):")
        for key, label in (("hot_take", "hot take"), ("explainer", "explainer"),
                           ("personal_experience", "personal")):
            print("   - %-10s %s" % (label + ":", t["angles"][key]))
    if risky:
        print("")
        print("Risky topics, your call (politics, tragedy, controversy, religion, health):")
        for t in risky:
            print("  - %s: %s" % (t["topic"], "; ".join(t["risk"])))
    print("")
    print("Keyword matching misses synonyms and context. Scan the zero scores by eye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
