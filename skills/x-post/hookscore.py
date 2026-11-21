#!/usr/bin/env python3
"""hookscore.py - score X post hooks from 0 to 100 and rank them.

Five properties, 0-20 each: specificity, curiosity gap, brevity, concrete
number or noun, and clarity. Each score comes with a one-line reason.

These are transparent heuristics, not a prediction of how a post will do.
Use the ranking to pick which hooks to develop, then use your judgement.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOOKS = os.path.join(HERE, "hooks.json")

NUMBER_WORDS = (r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                r"fifteen|twenty|thirty|fifty|hundred|thousand|million|billion|dozen")
DIGIT_RE = re.compile(r"[$₹€£]?\d[\d,.]*\s?(%|x|k|m|b|lakh|crore)?", re.I)
NUMWORD_RE = re.compile(r"\b(" + NUMBER_WORDS + r")\b", re.I)
ROUND_RE = re.compile(r"^[$₹€£]?(10+|[1-9]0+|[1-9],?000+)$")
CONCRETE_NOUNS = set("""
followers subscribers clients customers users dollars rupees emails posts tweets
threads books hours minutes days weeks months years lines words pages apps tools
steps lessons interviews calls meetings kg km projects jobs offers sales leads
signups downloads videos views likes replies dms templates prompts students
companies startups founders designers developers engineers writers freelancers
teachers doctors invoices contracts scripts screenshots spreadsheets slides
features bugs commits repos websites newsletters podcasts episodes chapters
drafts rejections applications resumes salaries prices products orders reviews
""".split())
ABSTRACT_NOUNS = set("""
success growth mindset value journey potential impact strategy things stuff life
results passion motivation greatness excellence synergy innovation transformation
abundance purpose vision solutions opportunities happiness wealth freedom
""".split())
AUDIENCE_RE = re.compile(
    r"\b(freelancers?|founders?|designers?|developers?|devs|engineers?|writers?|"
    r"creators?|marketers?|students?|parents?|managers?|beginners?|teachers?|nurses?|"
    r"doctors?|lawyers?|coaches?|consultants?|agencies|agency owners?|indie hackers?|"
    r"solopreneurs?|introverts?|new grads?|job seekers?|recruiters?|investors?)\b", re.I)
TIMEFRAME_RE = re.compile(
    r"\b(in|for|after|within|every|per|last|this|over|first|past|next)\s+(\d+|one|two|three|four|five|six|"
    r"seven|eight|nine|ten|a|an|a few)\s+(seconds?|minutes?|hours?|days?|weeks?|months?|"
    r"years?|nights?|mornings?)\b|\b(daily|weekly|monthly|yesterday|tonight|last (week|"
    r"month|year|night)|(19|20)\d\d)\b|\b\d+[- ](minute|hour|day|week|month|year)\b", re.I)
VAGUE_RE = re.compile(
    r"\b(things?|stuff|some|many|various|certain|a lot|lots of|very|really|everything|"
    r"something|anything|everyone|somehow|kind of|sort of)\b", re.I)
HEDGE_RE = re.compile(
    r"\b(maybe|might|perhaps|probably|possibly|arguably|i think|i feel|i guess|"
    r"could be|seems? to)\b", re.I)
OPEN_LOOP_RE = re.compile(
    r"\b(here'?s (how|why|what|the)|the (one|only|real|exact|single|simple)|nobody|no one|"
    r"why|how|what|the reason|this is (why|how|what)|until|turns out|the truth|"
    r"the mistake|the part|nobody tells)\b", re.I)
TENSION_RE = re.compile(
    r"\b(but|instead|without|yet|despite|still|even though|wrong|mistake|stop|never|"
    r"actually|lost|failed|quit|zero|no one)\b", re.I)
CLICKBAIT_RE = re.compile(
    r"(you won'?t believe|shocking|mind[- ]?blowing|insane|this will change your life|"
    r"game[- ]?changer|jaw[- ]?dropping|crazy|secret (that|they)|nobody will tell you this|"
    r"revolutioni[sz]e|must[- ]see|\b(omg|wow)\b)", re.I)
JARGON_RE = re.compile(
    r"\b(leverag\w*|synerg\w*|unlock\w*|delve|game[- ]?changer|paradigm|robust|seamless\w*|"
    r"holistic|ecosystem|empower\w*|revolutioni[sz]\w*|cutting[- ]edge|next[- ]level|"
    r"optimi[sz]e|utili[sz]e|actionable|scalable|disrupt\w*)\b", re.I)
FILLER_OPENER_RE = re.compile(
    r"^\s*(so|just|i think|i feel like|hey|hi|hello|in today'?s|a thread|thread|"
    r"here'?s a thread|let'?s talk about|i('ve| have) been thinking|some thoughts|"
    r"quick thought|random thought|gm|good morning|i (just )?wanted to)\b", re.I)
PASSIVE_RE = re.compile(r"\b(is|are|was|were|been|being|be)\s+\w+ed\b", re.I)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
ACRONYMS = {"HTML", "JSON", "NASA", "ASAP", "GDPR", "SAAS", "FOMO", "TLDR", "LLMS", "B2B", "B2C"}


def clamp(x, lo=0, hi=20):
    return max(lo, min(hi, int(round(x))))


def words_of(text):
    return re.findall(r"[A-Za-zऀ-ॿ0-9'$%₹]+", text)


def proper_nouns(text):
    out = []
    for sent in re.split(r"(?<=[.!?:])\s+|\n", text):
        toks = re.findall(r"[A-Za-z][\w&'.-]*", sent)
        for t in toks[1:]:
            if t[0].isupper() and t not in ("I", "I'm", "I've", "I'd", "I'll") and not t.isupper():
                out.append(t.rstrip(".'"))
    return out


def score_specificity(h):
    pts, notes = 8, []
    aud = AUDIENCE_RE.findall(h)
    if aud:
        pts += 5
        notes.append("names an audience (%s)" % (aud[0] if isinstance(aud[0], str) else aud[0][0]))
    tf = TIMEFRAME_RE.search(h)
    if tf:
        pts += 5
        notes.append("has a timeframe (%s)" % tf.group(0))
    pn = proper_nouns(h)
    if pn:
        pts += 3
        notes.append("names something (%s)" % pn[0])
    vague = [m.group(0) for m in VAGUE_RE.finditer(h)]
    hedges = [m.group(0) for m in HEDGE_RE.finditer(h)]
    if vague:
        pts -= 3 * len(vague)
        notes.append("vague: %s" % ", ".join("'%s'" % v for v in vague[:3]))
    if hedges:
        pts -= 4 * len(hedges)
        notes.append("hedges: %s" % ", ".join("'%s'" % v for v in hedges[:3]))
    return clamp(pts), "; ".join(notes) or "no audience, timeframe or named thing"


def score_curiosity(h):
    pts, notes = 6, []
    loops = [m.group(0) for m in OPEN_LOOP_RE.finditer(h)]
    if loops:
        pts += 5 + min(2, len(loops) - 1)
        notes.append("open loop ('%s')" % loops[0])
    stripped = h.rstrip()
    if stripped.endswith((":", "...", "…")):
        pts += 4
        notes.append("ends on '%s', promising a payoff" % stripped[-1])
    tension = [m.group(0) for m in TENSION_RE.finditer(h)]
    if tension:
        pts += 4
        notes.append("tension word ('%s')" % tension[0])
    if "?" in h:
        pts += 3
        notes.append("asks a question")
    bait = [m.group(0) for m in CLICKBAIT_RE.finditer(h)]
    if bait:
        pts -= 7 * len(bait)
        notes.append("clickbait costs trust ('%s')" % bait[0])
    filler = FILLER_OPENER_RE.match(h)
    if filler:
        pts -= 6
        notes.append("filler opener ('%s') delays the point" % filler.group(0).strip())
    return clamp(pts), "; ".join(notes) or "states everything; nothing left to find out"


def score_brevity(h):
    n_words, n_chars = len(words_of(h)), len(h)
    if n_chars <= 60:
        pts = 20
    elif n_chars <= 80:
        pts = 18
    elif n_chars <= 100:
        pts = 15
    elif n_chars <= 140:
        pts = 10
    elif n_chars <= 200:
        pts = 5
    else:
        pts = 2
    if n_words > 20:
        pts -= 3
    if n_chars <= 100:
        note = "%d words, %d chars: fits in the first 100 characters" % (n_words, n_chars)
    else:
        note = "%d words, %d chars: runs past the first 100 characters" % (n_words, n_chars)
    return clamp(pts), note


def score_concrete(h):
    pts, notes = 0, []
    digits = [m.group(0).strip() for m in DIGIT_RE.finditer(h) if re.search(r"\d", m.group(0))]
    if digits:
        pts += 10 + (3 if len(digits) > 1 else 0)
        notes.append("number%s: %s" % ("s" if len(digits) > 1 else "", ", ".join(digits[:3])))
        if all(ROUND_RE.match(d.strip().rstrip("%xkmb")) for d in digits):
            pts -= 2
            notes.append("round numbers read as estimates")
    elif NUMWORD_RE.search(h):
        pts += 5
        notes.append("number written as a word ('%s')" % NUMWORD_RE.search(h).group(0))
    toks = [w.lower().strip("'") for w in words_of(h)]
    nouns = [t for t in toks if t in CONCRETE_NOUNS]
    pn = proper_nouns(h)
    money = re.search(r"[$₹€£]\s?\d", h)
    concrete = nouns + pn + (["money"] if money else [])
    if concrete:
        pts += 7 + (3 if len(concrete) > 1 else 0)
        notes.append("concrete noun (%s)" % concrete[0])
    abstract = [t for t in toks if t in ABSTRACT_NOUNS]
    if abstract:
        pts -= 3 * len(abstract)
        notes.append("abstract: %s" % ", ".join("'%s'" % a for a in abstract[:3]))
    return clamp(pts), "; ".join(notes) or "no number and no tangible noun"


def score_clarity(h):
    pts, notes = 20, []
    jargon = [m.group(0) for m in JARGON_RE.finditer(h)]
    if jargon:
        pts -= 4 * len(jargon)
        notes.append("jargon: %s" % ", ".join("'%s'" % j for j in jargon[:3]))
    toks = words_of(h)
    long_words = [w for w in toks if len(w) > 12]
    if long_words:
        pts -= 2 * len(long_words)
        notes.append("long word '%s'" % long_words[0])
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", h.strip()) if s]
    if len(sentences) >= 3:
        pts -= 4
        notes.append("%d sentences; a hook is one or two" % len(sentences))
    if h.count(",") >= 3:
        pts -= 3
        notes.append("%d commas" % h.count(","))
    if PASSIVE_RE.search(h):
        pts -= 3
        notes.append("passive ('%s')" % PASSIVE_RE.search(h).group(0))
    caps = [w for w in re.findall(r"\b[A-Z]{4,}\b", h) if w not in ACRONYMS]
    if caps:
        pts -= 3 * len(caps)
        notes.append("shouting ('%s')" % caps[0])
    alpha = [w for w in toks if w.isalpha()]
    if alpha and sum(len(w) for w in alpha) / len(alpha) > 6.2:
        pts -= 3
        notes.append("long average word length")
    if "(" in h:
        pts -= 2
        notes.append("parenthesis slows the read")
    if len(EMOJI_RE.findall(h)) > 2:
        pts -= 2
        notes.append("emoji clutter")
    return clamp(pts), "; ".join(notes) or "plain words, one idea"


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [(x["id"], re.compile(x["match"], re.IGNORECASE)) for x in data.get("formulas", [])]
    except (OSError, ValueError, KeyError, re.error):
        return []


def score_hook(h, formulas):
    parts = {
        "specificity": score_specificity(h),
        "curiosity": score_curiosity(h),
        "brevity": score_brevity(h),
        "concrete": score_concrete(h),
        "clarity": score_clarity(h),
    }
    formula = next((fid for fid, rx in formulas if rx.search(h)), None)
    return {
        "hook": h,
        "score": sum(v[0] for v in parts.values()),
        "parts": {k: {"score": v[0], "why": v[1]} for k, v in parts.items()},
        "formula": formula,
    }


def short(s, n):
    return s if len(s) <= n else s[: n - 3] + "..."


def render(results, brief):
    out = ["rank  score  spec  gap  brev  conc  clar  formula              hook",
           "----  -----  ----  ---  ----  ----  ----  -------------------  " + "-" * 34]
    for i, r in enumerate(results, 1):
        p = r["parts"]
        out.append("%4d  %5d  %4d  %3d  %4d  %4d  %4d  %-19s  %s" % (
            i, r["score"], p["specificity"]["score"], p["curiosity"]["score"],
            p["brevity"]["score"], p["concrete"]["score"], p["clarity"]["score"],
            short(r["formula"] or "-", 19), short(r["hook"], 34)))
    if not brief:
        labels = (("specificity", "specificity"), ("curiosity", "curiosity  "),
                  ("brevity", "brevity    "), ("concrete", "concrete   "), ("clarity", "clarity    "))
        for i, r in enumerate(results, 1):
            out.append("")
            out.append("#%d  %d/100  \"%s\"" % (i, r["score"], r["hook"]))
            for key, label in labels:
                part = r["parts"][key]
                out.append("    %s %2d/20  %s" % (label, part["score"], part["why"]))
    out.append("")
    out.append("Heuristic scores. They rank hooks against each other; they do not predict reach.")
    return "\n".join(out)


def read_input(path):
    if path in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("hookscore.py: no input. Pass a file or pipe hooks in. See --help.")
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError as e:
        sys.exit("hookscore.py: cannot read %s: %s" % (path, e.strerror))


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Score X hooks 0-100 on specificity, curiosity gap, brevity, "
                    "concrete number or noun, and clarity (0-20 each). Prints a ranked "
                    "table and a one-line reason for every score.",
        epilog="Input: one hook per line. Blank lines and lines starting with # are skipped.\n\n"
               "examples:\n"
               "  python3 hookscore.py hooks.txt\n"
               "  python3 hookscore.py hooks.txt --brief --top 3\n"
               "  printf 'Hook one\\nHook two\\n' | python3 hookscore.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="file with one hook per line (default: stdin)")
    ap.add_argument("--top", type=int, default=0, help="show only the top N hooks")
    ap.add_argument("--brief", action="store_true", help="table only, no per-score reasons")
    ap.add_argument("--hooks", metavar="PATH", default=DEFAULT_HOOKS,
                    help="hooks.json for formula labels (default: next to this script)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    hooks = [ln.strip() for ln in read_input(args.file).splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not hooks:
        print("hookscore.py: no hooks found in input.", file=sys.stderr)
        return 2
    formulas = load_formulas(args.hooks)
    results = sorted((score_hook(h, formulas) for h in hooks), key=lambda r: -r["score"])
    if args.top > 0:
        results = results[: args.top]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render(results, args.brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
