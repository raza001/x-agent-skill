#!/usr/bin/env python3
"""humanize.py - clean the machine fingerprint out of a draft.

Automatic: removes invisible characters (zero-width spaces, joiners, tag
characters, bidi marks...) and normalizes typography (em dashes, curly quotes,
ellipsis characters, bullet characters).

Flagged with suggestions: stock phrases from slop.json ("delve into",
"game-changer", "in today's fast-paced world"...) and structural tells
("it's not just X, it's Y", rule-of-three overuse...). Safe phrase swaps are
applied only with --apply. Structural tells are never rewritten; a person
should rewrite those lines.

Runs locally on text you give it. Nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEXICON = os.path.join(HERE, "slop.json")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
CF_KEEP = {0x0600, 0x0601, 0x0602, 0x0603, 0x0604, 0x0605, 0x061C, 0x06DD,
           0x070F, 0x08E2, 0x110BD, 0x110CD}


def load_lexicon(path):
    try:
        with open(path, encoding="utf-8") as f:
            lex = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("humanize.py: cannot load lexicon %s: %s" % (path, e))
    ranges = []
    for cls in lex.get("invisible", []):
        for spec in cls["codepoints"]:
            lo, _, hi = spec.partition("-")
            lo_i = int(lo.strip().upper().replace("U+", ""), 16)
            hi_i = int(hi.strip().upper().replace("U+", ""), 16) if hi else lo_i
            ranges.append((lo_i, hi_i, cls["name"], cls.get("action", "delete"), cls.get("protect")))
    lex["_ranges"] = ranges
    return lex


def is_emoji(ch):
    cp = ord(ch)
    return (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2300 <= cp <= 0x23FF
            or 0x2B00 <= cp <= 0x2BFF or cp in (0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF)


def is_indic(ch):
    return 0x0900 <= ord(ch) <= 0x0DFF


def rule_for(cp, ranges):
    for lo, hi, name, action, protect in ranges:
        if lo <= cp <= hi:
            return name, action, protect
    return None


def remove_invisibles(text, ranges):
    """Return (clean text, Counter of removed classes)."""
    out, counts = [], Counter()
    last_base = ""
    n = len(text)
    for i, ch in enumerate(text):
        cp = ord(ch)
        rule = rule_for(cp, ranges)
        if rule is None:
            if unicodedata.category(ch) == "Cf" and cp not in CF_KEEP:
                counts["other format character U+%04X" % cp] += 1
                continue
            out.append(ch)
            last_base = ch
            continue
        name, action, protect = rule
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if protect == "emoji-indic" and prev and nxt and \
                (is_emoji(prev) or is_indic(prev)) and (is_emoji(nxt) or is_indic(nxt)):
            out.append(ch)  # legitimate joiner inside an emoji or Indic cluster
            continue
        if protect == "flag-tags" and last_base == "\U0001F3F4":
            out.append(ch)  # subdivision flag tag sequence, e.g. Scotland
            continue
        if action == "keep":
            out.append(ch)
            continue
        counts[name] += 1
        if action == "space":
            out.append(" ")
        elif action == "newline":
            out.append("\n")
    return "".join(out), counts


def fix_typography(text, lex, dash):
    counts = Counter()
    if dash != "keep":
        pat = re.compile(r"[ \t]*[—―][ \t]*|[ \t]+–[ \t]+")

        def rep(m):
            name = "em dash" if m.group(0).strip() in ("—", "―") else "spaced en dash"
            counts[name] += 1
            s = m.string
            at_line_start = m.start() == 0 or s[m.start() - 1] == "\n"
            at_line_end = m.end() == len(s) or s[m.end()] == "\n"
            if at_line_start:
                return "- "
            if at_line_end:
                return ""
            return ", " if dash == "comma" else " - "

        text = pat.sub(rep, text)
        # Tidy the punctuation a dash-to-comma swap can leave behind.
        text = re.sub(r",[ \t]*,", ",", text)
        text = re.sub(r",[ \t]*([.!?;:])", r"\1", text)
        text = re.sub(r"([.!?;:])[ \t]*,", r"\1", text)
        text = re.sub(r"([(\[])[ \t]*,[ \t]*", r"\1", text)
    for rule in lex.get("typography", []):
        if rule.get("to") is None:
            continue
        for ch in rule["from"]:
            if rule.get("line_start_only"):
                pat = re.compile(r"(?m)^([ \t]*)" + re.escape(ch) + r"[ \t]*")
                found = len(pat.findall(text))
                if found:
                    counts[rule["name"]] += found
                    text = pat.sub(lambda m: m.group(1) + rule["to"] + " ", text)
            elif ch in text:
                counts[rule["name"]] += text.count(ch)
                text = text.replace(ch, rule["to"])
    return text, counts


def phrase_regex(phrase):
    body = re.escape(phrase)
    body = body.replace(r"\ ", r"\s+").replace("'", "['’]").replace(r"\-", r"[-\s]?")
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def find_phrases(text, phrases):
    urls = [m.span() for m in URL_RE.finditer(text)]
    taken, hits = [], []
    for p in sorted(phrases, key=lambda x: -len(x["phrase"])):
        for m in phrase_regex(p["phrase"]).finditer(text):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken) or any(us <= s < ue for us, ue in urls):
                continue
            taken.append((s, e))
            hits.append({"start": s, "end": e, "line": line_of(text, s), "match": m.group(0),
                         "phrase": p["phrase"], "suggest": p.get("suggest", ""),
                         "auto": bool(p.get("auto")), "category": p.get("category", "")})
    hits.sort(key=lambda h: h["start"])
    return hits


def match_case(orig, rep):
    if not rep:
        return rep
    if orig.isupper() and len(orig) > 1:
        return rep.upper()
    if orig[:1].isupper():
        return rep[:1].upper() + rep[1:]
    return rep


def apply_phrases(text, hits):
    out, last, applied = [], 0, 0
    for h in hits:
        if not h["auto"] or h["start"] < last:
            continue
        s, e = h["start"], h["end"]
        before = "".join(out) + text[last:s]
        at_sentence_start = re.search(r"(^|[.!?]\s+|\n\s*)$", before) is not None
        rep = match_case(h["match"], h["suggest"])
        if rep == "":
            # A deleted sentence-opener takes its trailing punctuation with it,
            # so "Let that sink in." does not leave an orphan ".".
            tail_rx = r"[ \t]*[,.!?;:]*[ \t]*" if at_sentence_start else r"[ \t]*,?[ \t]*"
            e += re.match(tail_rx, text[e:]).end()
            if at_sentence_start:
                rest = text[e:]
                m = re.search(r"[A-Za-z]", rest[:3])
                if m:
                    i = e + m.start()
                    text = text[:i] + text[i].upper() + text[i + 1:]
        out.append(text[last:s])
        out.append(rep)
        last = e
        applied += 1
    out.append(text[last:])
    text = "".join(out)
    text = re.sub(r"(?<=\S)[ \t]{2,}", " ", text)
    text = re.sub(r"(?<=\w)[ \t]+([,.;!?])", r"\1", text)
    text = re.sub(r"(?m)^[ \t]*[,;][ \t]*", "", text)
    text = re.sub(r"(?m)[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, applied


def find_structural(text, tells):
    found = []
    for t in tells:
        flags = re.MULTILINE | (0 if t.get("case_sensitive") else re.IGNORECASE)
        try:
            rx = re.compile(t["pattern"], flags)
        except re.error as e:
            print("humanize.py: bad pattern for %s: %s" % (t.get("id"), e), file=sys.stderr)
            continue
        ms = list(rx.finditer(text))
        if len(ms) >= t.get("min_count", 1):
            found.append({
                "id": t["id"], "name": t["name"], "count": len(ms),
                "examples": [{"line": line_of(text, m.start()),
                              "excerpt": excerpt(text, m.start(), m.end())} for m in ms[:3]],
                "why": t.get("why", ""), "fix": t.get("fix", ""),
            })
    return found


def excerpt(text, s, e, width=60):
    frag = text[s:e].replace("\n", " ").strip()
    return frag if len(frag) <= width else frag[: width - 3] + "..."


def straight_quotes(text):
    """One-to-one quote swap so patterns match without shifting positions."""
    return text.translate(str.maketrans("‘’‚‛“”„‟",
                                        "''''\"\"\"\""))


def humanize(text, lex, dash="comma", apply=False):
    stage1, inv = remove_invisibles(text, lex["_ranges"])
    # Structural tells are read before dashes are converted (so em dash
    # overuse is still visible) but with straight quotes.
    structural = find_structural(straight_quotes(stage1), lex.get("structural", []))
    stage2, typo = fix_typography(stage1, lex, dash)
    hits = find_phrases(stage2, lex.get("phrases", []))
    applied = 0
    cleaned = stage2
    if apply:
        cleaned, applied = apply_phrases(stage2, hits)
    for h in hits:
        h.pop("start", None)
        h.pop("end", None)
        h["applied"] = bool(apply and h["auto"])
    return {
        "cleaned": cleaned,
        "invisible": dict(inv),
        "typography": dict(typo),
        "phrases": hits,
        "structural": structural,
        "applied": applied,
    }


def summarize_counts(c):
    return ", ".join("%s x%d" % (k, v) for k, v in sorted(c.items(), key=lambda kv: -kv[1]))


def render_report(r, dash):
    out = ["humanize.py report", "=" * 64]
    inv_total = sum(r["invisible"].values())
    out.append("invisible characters  %d removed%s" % (
        inv_total, "  (%s)" % summarize_counts(r["invisible"]) if inv_total else ""))
    typo_total = sum(r["typography"].values())
    dash_note = {"comma": " (dashes -> comma)", "hyphen": " (dashes -> ' - ')", "keep": " (dashes kept)"}[dash]
    out.append("typography            %d fixed%s%s" % (
        typo_total, "  (%s)" % summarize_counts(r["typography"]) if typo_total else "",
        dash_note if typo_total else ""))
    out.append("stock phrases         %d flagged, %d applied%s" % (
        len(r["phrases"]), r["applied"], "" if r["applied"] or not r["phrases"]
        else "  (run with --apply to make the auto swaps)"))
    for h in r["phrases"]:
        sug = "delete" if h["suggest"] == "" else "\"%s\"" % h["suggest"]
        mode = "applied" if h["applied"] else ("auto" if h["auto"] else "rewrite by hand")
        out.append("  line %-3d %-34s -> %-20s [%s, %s]" % (
            h["line"], "\"%s\"" % h["match"], sug, h["category"], mode))
    out.append("structural tells      %d flagged (never auto-fixed; rewrite these lines)"
               % len(r["structural"]))
    for t in r["structural"]:
        out.append("  %s  x%d  %s" % (t["id"], t["count"], t["name"]))
        for ex in t["examples"]:
            out.append("      line %-3d \"%s\"" % (ex["line"], ex["excerpt"]))
        out.append("      fix: %s" % t["fix"])
    return "\n".join(out)


def read_input(path):
    if path in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("humanize.py: no input. Pass a file or pipe text in. See --help.")
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as f:  # keep a leading BOM visible
            return f.read()
    except OSError as e:
        sys.exit("humanize.py: cannot read %s: %s" % (path, e.strerror))


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Remove invisible characters, normalize typography, and flag stock "
                    "phrases and structural tells with suggested fixes.",
        epilog="Output: the cleaned text goes to stdout (or to -o FILE). The report goes to\n"
               "stderr, or to stdout when -o is used. --json puts everything in one object.\n\n"
               "examples:\n"
               "  python3 humanize.py draft.txt --report\n"
               "  python3 humanize.py draft.txt -o clean.txt --report --apply\n"
               "  cat draft.txt | python3 humanize.py --dash hyphen --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="text file (default: stdin)")
    ap.add_argument("-o", "--output", metavar="FILE", help="write the cleaned text here")
    ap.add_argument("--report", action="store_true", help="print the full change report")
    ap.add_argument("--apply", action="store_true",
                    help="also apply phrase swaps marked auto=true in slop.json")
    ap.add_argument("--dash", choices=("comma", "hyphen", "keep"), default="comma",
                    help="what em dashes become (default: comma)")
    ap.add_argument("--lexicon", metavar="PATH", default=DEFAULT_LEXICON,
                    help="slop.json to use (default: next to this script)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    lex = load_lexicon(args.lexicon)
    text = read_input(args.file)
    r = humanize(text, lex, args.dash, args.apply)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8", newline="") as f:
                f.write(r["cleaned"])
        return 0
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(r["cleaned"])
        print("wrote %s" % args.output)
        report_stream = sys.stdout
    else:
        sys.stdout.write(r["cleaned"])
        if not r["cleaned"].endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        report_stream = sys.stderr
    if args.report:
        print(render_report(r, args.dash), file=report_stream)
    else:
        print("humanize: %d invisible removed, %d typography fixes, %d phrases flagged, "
              "%d structural tells (add --report for details)" % (
                  sum(r["invisible"].values()), sum(r["typography"].values()),
                  len(r["phrases"]), len(r["structural"])), file=report_stream)
    return 0


if __name__ == "__main__":
    sys.exit(main())
