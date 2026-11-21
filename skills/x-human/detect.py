#!/usr/bin/env python3
"""detect.py - a local, five-check heuristic for "does this read as generated?"

Scores 0-100 per check, higher reads more human:
  BURSTINESS   sentence-length variation
  SPECIFICITY  numbers, names and concrete markers per 100 words
  SLOP DENSITY stock phrases from slop.json per 100 words
  FINGERPRINT  invisible characters, em dashes, curly quotes per 1,000 chars
  VOICE        contractions, first/second person, structural tells

This is a heuristic, not proof. It cannot tell who or what wrote a text, and
it does not predict what any commercial detector will say. It runs locally
and sends nothing anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEXICON = os.path.join(HERE, "slop.json")
DISCLAIMER = ("Heuristic only: 5 surface signals, tuned for English. This is not proof of "
              "authorship and does not predict any commercial detector's verdict.")
CHECKS = ("BURSTINESS", "SPECIFICITY", "SLOP DENSITY", "FINGERPRINT", "VOICE")


def load_lexicon(path):
    try:
        with open(path, encoding="utf-8") as f:
            lex = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("detect.py: cannot load lexicon %s: %s" % (path, e))
    ranges = []
    for cls in lex.get("invisible", []):
        if cls.get("action") == "keep":
            continue
        for spec in cls["codepoints"]:
            lo, _, hi = spec.partition("-")
            lo_i = int(lo.strip().upper().replace("U+", ""), 16)
            hi_i = int(hi.strip().upper().replace("U+", ""), 16) if hi else lo_i
            ranges.append((lo_i, hi_i, cls.get("protect")))
    lex["_ranges"] = ranges
    return lex


def clamp(x):
    return max(0, min(100, int(round(x))))


def words_of(text):
    return re.findall(r"[A-Za-zÀ-ɏऀ-ॿ0-9]+(?:['’][A-Za-z]+)?", text)


def sentences_of(text):
    parts = re.split(r"(?<=[.!?।])[\"')\]]?\s+|\n+", text.strip())
    # Lines made only of hashtags, mentions or links are not sentences.
    tag_only = re.compile(r"^\s*((#|@)\w+|https?://\S+|\s)+\s*$")
    return [p for p in parts if words_of(p) and not tag_only.match(p)]


def count_invisible(text, ranges):
    n = 0
    for i, ch in enumerate(text):
        cp = ord(ch)
        for lo, hi, protect in ranges:
            if lo <= cp <= hi:
                if protect == "emoji-indic" and 0 < i < len(text) - 1:
                    a, b = ord(text[i - 1]), ord(text[i + 1])
                    if (a >= 0x1F000 or 0x0900 <= a <= 0x0DFF or a == 0xFE0F) and \
                            (b >= 0x1F000 or 0x0900 <= b <= 0x0DFF):
                        break
                if protect == "flag-tags":
                    break
                n += 1
                break
        else:
            if unicodedata.category(ch) == "Cf" and not (0xE0000 <= cp <= 0xE007F) and \
                    cp not in (0x0600, 0x0601, 0x0602, 0x0603, 0x0604, 0x0605, 0x061C, 0x06DD):
                n += 1
    return n


def phrase_hits(text, phrases):
    taken, hits = [], []
    for p in sorted(phrases, key=lambda x: -len(x["phrase"])):
        body = re.escape(p["phrase"]).replace(r"\ ", r"\s+").replace("'", "['’]")
        body = body.replace(r"\-", r"[-\s]?")
        for m in re.finditer(r"(?<!\w)" + body + r"(?!\w)", text, re.IGNORECASE):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append(m.span())
            hits.append(m.group(0).lower())
    return hits


def structural_hits(text, tells):
    found = []
    for t in tells:
        flags = re.MULTILINE | (0 if t.get("case_sensitive") else re.IGNORECASE)
        try:
            n = len(re.findall(t["pattern"], text, flags))
        except re.error:
            continue
        if n >= t.get("min_count", 1):
            found.append(t["id"])
    return found


def analyze(text, lex):
    words = words_of(text)
    n_words = max(1, len(words))
    sents = sentences_of(text)
    res = {"words": len(words), "sentences": len(sents), "checks": {}}

    # 1. Burstiness
    lens = [len(words_of(s)) for s in sents]
    if len(lens) >= 4 and statistics.mean(lens) > 0:
        cv = statistics.pstdev(lens) / statistics.mean(lens)
        score = clamp((cv - 0.15) / 0.5 * 90 + 10)
        detail = "sentence-length variation CV %.2f (%s)" % (
            cv, "varied" if cv >= 0.5 else "fairly even" if cv >= 0.3 else "very even")
        res["checks"]["BURSTINESS"] = {"score": score, "detail": detail}
    else:
        res["checks"]["BURSTINESS"] = {"score": None,
                                       "detail": "n/a: needs 4+ sentences (has %d)" % len(lens)}

    # 2. Specificity
    numbers = re.findall(r"(?<![\w.])[$₹€£]?\d[\d,.:]*%?", text)
    handles = re.findall(r"(?<!\w)@\w+", text)
    proper = []
    for s in sents:
        toks = re.findall(r"[A-Za-z][\w'-]*", s)
        proper += [t for t in toks[1:] if t[0].isupper() and not t.isupper() and t not in ("I", "I'm", "I've", "I'd", "I'll")]
    markers = len(numbers) + len(handles) + len(proper)
    rate = markers * 100.0 / n_words
    res["checks"]["SPECIFICITY"] = {
        "score": clamp(20 + rate * 16),
        "detail": "%.1f concrete markers per 100 words (%d numbers, %d names, %d handles)"
                  % (rate, len(numbers), len(proper), len(handles))}

    # 3. Slop density
    hits = phrase_hits(text, lex.get("phrases", []))
    rate = len(hits) * 100.0 / n_words
    uniq = []
    for h in hits:
        if h not in uniq:
            uniq.append(h)
    res["checks"]["SLOP DENSITY"] = {
        "score": clamp(100 - rate * 30),
        "detail": ("%d stock phrase%s (%s)" % (len(hits), "" if len(hits) == 1 else "s",
                                               ", ".join(uniq[:4]) + ("..." if len(uniq) > 4 else "")))
                  if hits else "no stock phrases from slop.json"}

    # 4. Fingerprint
    n_chars = max(1, len(text))
    inv = count_invisible(text, lex["_ranges"])
    dashes = text.count("—") + text.count("―")
    curly = sum(text.count(c) for c in "‘’“”")
    ell = text.count("…")
    weighted = (inv * 4 + dashes * 1.5 + curly * 0.2 + ell * 0.5) * 1000.0 / n_chars
    score = clamp(100 - weighted * 6)
    if inv:
        score = min(score, 40)
    parts = []
    if inv:
        parts.append("%d invisible char%s" % (inv, "" if inv == 1 else "s"))
    if dashes:
        parts.append("%d em dash%s" % (dashes, "" if dashes == 1 else "es"))
    if curly:
        parts.append("%d curly quote%s (phones add these; low weight)" % (curly, "" if curly == 1 else "s"))
    if ell:
        parts.append("%d ellipsis char%s" % (ell, "" if ell == 1 else "s"))
    res["checks"]["FINGERPRINT"] = {"score": score, "detail": ", ".join(parts) or "clean typography"}

    # 5. Voice
    contractions = len(re.findall(r"\b[A-Za-z]+['’](s|re|ve|ll|d|t|m)\b", text, re.I))
    c_rate = contractions * 100.0 / n_words
    person = len(re.findall(r"\b(i|me|my|mine|we|our|us|you|your)\b", text, re.I))
    short = any(len(words_of(s)) < 5 for s in sents)
    straight = text.translate(str.maketrans("‘’“”", "''\"\""))
    tells = structural_hits(straight, lex.get("structural", []))
    score = 40 + (25 if c_rate >= 1.5 else 12 if c_rate >= 0.5 else 0) + (15 if person else 0) \
        + (10 if short else 0) + (10 if not tells else 0) - 12 * len(tells)
    detail = "%d contraction%s, %s, %s" % (
        contractions, "" if contractions == 1 else "s",
        "first/second person" if person else "no I/you",
        ("%d structural tell%s (%s)" % (len(tells), "" if len(tells) == 1 else "s", ", ".join(tells[:3])))
        if tells else "no structural tells")
    res["checks"]["VOICE"] = {"score": clamp(score), "detail": detail}

    scored = [(k, v["score"]) for k, v in res["checks"].items() if v["score"] is not None]
    mean = statistics.mean(s for _, s in scored)
    weakest = min(scored, key=lambda kv: kv[1])
    overall = clamp(0.6 * mean + 0.4 * weakest[1])
    if overall >= 70 and weakest[1] >= 55:
        verdict = "PASS"
    elif overall >= 50:
        verdict = "REVIEW"
    else:
        verdict = "REWRITE"
    res.update({"overall": overall, "verdict": verdict, "weakest": weakest[0]})
    return res


def fmt_score(s):
    return " n/a" if s is None else "%4d" % s


def render_one(name, r):
    out = ["detect.py  (heuristic, not proof)", "file: %s   (%d words, %d sentences)"
           % (name, r["words"], r["sentences"]), "",
           "  check          score  detail"]
    for k in CHECKS:
        c = r["checks"][k]
        out.append("  %-13s  %s   %s" % (k, fmt_score(c["score"]), c["detail"]))
    out.append("")
    out.append("  overall %d   verdict %s   weakest: %s" % (r["overall"], r["verdict"], r["weakest"]))
    out.append("  (overall = 60% mean + 40% weakest check; PASS needs 70+ with no check under 55)")
    return "\n".join(out)


def render_two(names, a, b):
    out = ["detect.py  (heuristic, not proof)",
           "A: %s   (%d words)" % (names[0], a["words"]),
           "B: %s   (%d words)" % (names[1], b["words"]), "",
           "  check                A        B   change"]
    for k in CHECKS:
        sa, sb = a["checks"][k]["score"], b["checks"][k]["score"]
        delta = "" if sa is None or sb is None else "%+d" % (sb - sa)
        out.append("  %-13s  %7s  %7s   %s" % (k, fmt_score(sa).strip(), fmt_score(sb).strip(), delta))
    out.append("  %-13s  %7d  %7d   %+d" % ("OVERALL", a["overall"], b["overall"], b["overall"] - a["overall"]))
    out.append("  %-13s  %7s  %7s" % ("verdict", a["verdict"], b["verdict"]))
    out.append("")
    out.append("  B detail:")
    for k in CHECKS:
        out.append("    %-13s %s" % (k, b["checks"][k]["detail"]))
    return "\n".join(out)


def read_file(path):
    if path == "-":
        if sys.stdin.isatty():
            sys.exit("detect.py: no input on stdin. See --help.")
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        sys.exit("detect.py: cannot read %s: %s" % (path, e.strerror))


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Local heuristic score for text that reads as generated: five checks "
                    "(burstiness, specificity, slop density, fingerprint, voice), 0-100, "
                    "higher reads more human. Give two files to compare before and after. "
                    + DISCLAIMER,
        epilog="examples:\n"
               "  python3 detect.py draft.txt\n"
               "  python3 detect.py draft.txt clean.txt\n"
               "  cat draft.txt | python3 detect.py - --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("files", nargs="*", help="1 or 2 text files ('-' for stdin; default stdin)")
    ap.add_argument("--lexicon", metavar="PATH", default=DEFAULT_LEXICON,
                    help="slop.json to use (default: next to this script)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    files = args.files or ["-"]
    if len(files) > 2:
        ap.error("give 1 or 2 files")
    lex = load_lexicon(args.lexicon)
    results = []
    for path in files:
        text = read_file(path)
        if not words_of(text):
            print("detect.py: %s has no words to score." % path, file=sys.stderr)
            return 2
        results.append(analyze(text, lex))

    if args.json:
        payload = {"disclaimer": DISCLAIMER,
                   "results": [dict(file=f, **r) for f, r in zip(files, results)]}
        if len(results) == 2:
            payload["overall_change"] = results[1]["overall"] - results[0]["overall"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if len(results) == 1:
            print(render_one(files[0], results[0]))
        else:
            print(render_two(files, results[0], results[1]))
        print("")
        print(DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
