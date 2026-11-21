#!/usr/bin/env python3
"""lint.py - check X post drafts before you post them yourself.

Counts characters the way X does (URLs count as 23, most emoji and CJK
characters count as 2), then checks hashtags, line breaks, the first 100
characters, the hook, the ask at the end, and all-caps shouting.

Runs locally on text you give it. Nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOOKS = os.path.join(HERE, "hooks.json")
URL_WEIGHT = 23
FOLD = 100

# --- X character counting -------------------------------------------------
# Approximates twitter-text v3: code points in these ranges weigh 1, all
# others weigh 2, an emoji sequence weighs 2, and every URL weighs 23.
LIGHT = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))
EMOJI = ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2300, 0x23FF),
         (0x2B00, 0x2BFF), (0x3030, 0x3030), (0x303D, 0x303D), (0x3297, 0x3299))
TLDS = ("com|org|net|io|co|ai|dev|app|in|me|xyz|ly|gg|tv|so|news|blog|link|"
        "site|page|uk|us|ca|de|fr|sh|to|gl|fm|cc")
URL_RE = re.compile(
    r"https?://[^\s<>\"]+"
    r"|(?<![\w@.\-])www\.[^\s<>\"]+"
    r"|(?<![\w@.\-/])(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+(?:" + TLDS +
    r")\b(?:/[^\s<>\"]*)?",
    re.IGNORECASE,
)
HASHTAG_RE = re.compile(r"(?<![\w&#])#(\w*[^\W\d_]\w*)")
MENTION_RE = re.compile(r"(?<![\w@])@(\w{1,15})\b")


def _in(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def find_urls(text):
    spans = []
    for m in URL_RE.finditer(text):
        s, e = m.start(), m.end()
        while e > s and text[e - 1] in ".,!?:;)]}'\"":
            e -= 1
        spans.append((s, e))
    return spans


def _emoji_end(s, i):
    """Return the end index of an emoji sequence starting at s[i], else None."""
    n = len(s)
    if s[i] in "0123456789#*":  # keycap: digit + optional VS16 + U+20E3
        j = i + 1
        if j < n and s[j] == "️":
            j += 1
        return j + 1 if j < n and s[j] == "⃣" else None
    cp = ord(s[i])
    if not _in(cp, EMOJI):
        return None
    j = i + 1
    if 0x1F1E6 <= cp <= 0x1F1FF:  # two regional indicators make one flag
        return j + 1 if j < n and 0x1F1E6 <= ord(s[j]) <= 0x1F1FF else j
    while j < n:
        c = ord(s[j])
        if c in (0xFE0E, 0xFE0F, 0x20E3) or 0x1F3FB <= c <= 0x1F3FF or 0xE0020 <= c <= 0xE007F:
            j += 1
        elif c == 0x200D and j + 1 < n and _in(ord(s[j + 1]), EMOJI):
            j += 2
        else:
            break
    return j


def x_length(text):
    """Return (weighted length, url count, emoji count) using X's rules."""
    text = unicodedata.normalize("NFC", text)
    spans = find_urls(text)
    total = URL_WEIGHT * len(spans)
    pieces, last = [], 0
    for s, e in spans:
        pieces.append(text[last:s])
        last = e
    pieces.append(text[last:])
    emoji = 0
    for p in pieces:
        i = 0
        while i < len(p):
            end = _emoji_end(p, i)
            if end is not None:
                total += 2
                emoji += 1
                i = end
                continue
            total += 1 if _in(ord(p[i]), LIGHT) else 2
            i += 1
    return total, len(spans), emoji


def strip_urls(text):
    out, last = [], 0
    for s, e in find_urls(text):
        out.append(text[last:s])
        last = e
    out.append(text[last:])
    return " ".join(out)


# --- voice.md -------------------------------------------------------------
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


def voice_items(sections, *names):
    for key, body in sections.items():
        if any(n in key for n in names):
            items = []
            for line in body.splitlines():
                line = re.sub(r"^\s*([-*+]|\d+[.)])\s*", "", line).strip()
                if line and line != "---":
                    items += [x.strip().strip("\"'") for x in re.split(r"[,;]", line) if x.strip()]
            return items
    return []


def voice_text(sections, *names):
    for key, body in sections.items():
        if any(n in key for n in names):
            return body.strip()
    return ""


def policy_limit(policy):
    """'none' -> 0, 'max 2' -> 2, otherwise None (no limit understood)."""
    p = policy.lower()
    if not p:
        return None
    if re.search(r"\b(none|never|no (emoji|hashtags?)|zero)\b", p):
        return 0
    m = re.search(r"\b(?:max(?:imum)?|up to|at most|no more than)\s*(\d+)", p)
    return int(m.group(1)) if m else None


# --- craft checks ---------------------------------------------------------
WEAK_OPENERS = [
    r"so\b", r"just\b", r"i think\b", r"i feel like\b", r"hey\b", r"hi\b",
    r"hello\b", r"in today'?s\b", r"a thread\b", r"thread\b", "\U0001F9F5",
    r"here'?s a thread\b", r"let'?s talk about\b", r"i('ve| have) been thinking\b",
    r"some thoughts\b", r"quick thought\b", r"random thought\b", r"gm\b",
    r"good morning\b", r"not sure if\b", r"this might be\b", r"i (just )?wanted to\b",
    r"as (an?|the) \w+,", r"it'?s (no secret|important to)\b",
]
WEAK_RE = re.compile(r"^\s*(" + "|".join(WEAK_OPENERS) + ")", re.IGNORECASE)
CTA_RE = re.compile(
    r"\b(reply|replies|comment|tell me|let me know|drop (a|an|your)|share|repost|"
    r"retweet|bookmark|save (this|it)|follow|subscribe|sign up|join|dm me|"
    r"link (in|below)|check out|grab|download|read (more|the)|what do you think|"
    r"thoughts|agree|which (one|would)|who else|your turn)\b",
    re.IGNORECASE,
)
ACRONYMS = {"HTML", "JSON", "HTTP", "HTTPS", "NASA", "ASAP", "GDPR", "SAAS",
            "UPSC", "NEET", "IIT", "FOMO", "YOLO", "TLDR", "AMA", "LLM", "LLMS",
            "MVP", "ROI", "KPI", "B2B", "B2C", "NYC", "USA", "API", "APIS", "OKRS"}
CAPS_RE = re.compile(r"\b[A-Z][A-Z']{3,}\b")
SENT_END_RE = re.compile(r"(?<=[.!?।])\s")


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [(x["id"], x["name"], re.compile(x["match"], re.IGNORECASE))
                for x in data.get("formulas", [])]
    except (OSError, ValueError, KeyError, re.error):
        return []


def classify(line, formulas):
    for fid, name, rx in formulas:
        if rx.search(line):
            return fid, name
    return None, None


def lint(text, max_len, formulas, voice):
    text = text.strip("\n")
    length, urls, emoji = x_length(text)
    lines = text.split("\n")
    blank = sum(1 for ln in lines if not ln.strip())
    no_urls = strip_urls(text)
    hashtags = ["#" + h for h in HASHTAG_RE.findall(no_urls)]
    mentions = ["@" + m for m in MENTION_RE.findall(no_urls)]
    nonblank = [ln.strip() for ln in lines if ln.strip()]
    first_line = nonblank[0] if nonblank else ""
    last_line = nonblank[-1] if nonblank else ""
    first_sentence = SENT_END_RE.split(first_line, maxsplit=1)[0]
    first_len = x_length(first_line)[0]
    sent_len = x_length(first_sentence)[0]
    fold = re.sub(r"\s*\n\s*", " / ", unicodedata.normalize("NFC", text))[:FOLD]

    errors, warnings, info = [], [], []

    if length > max_len:
        errors.append("Too long: %d/%d characters as X counts them (%d over)."
                      % (length, max_len, length - max_len))
    if max_len > 280 and length > 280:
        info.append("Over 280: only works with a long-post account, and the timeline "
                    "collapses it after the opening, so the start must carry the post.")

    # Hook and fold
    fid, fname = classify(first_line, formulas)
    if WEAK_RE.match(first_line):
        warnings.append("Missing hook: opens with filler (\"%s\"). Lead with the point."
                        % WEAK_RE.match(first_line).group(0).strip())
    if sent_len > FOLD:
        warnings.append("Missing hook: the first sentence is %d characters, so it does not "
                        "land inside the first %d. Cut it or break it." % (sent_len, FOLD))
    elif first_len > FOLD:
        info.append("First line runs %d characters; the first sentence fits in %d."
                    % (first_len, FOLD))
    if not fid:
        info.append("No formula in hooks.json matches the first line. Not an error; "
                    "check that the opener still earns the read.")

    # Hashtags, mentions, line breaks
    if len(hashtags) > 2:
        warnings.append("%d hashtags. More than 2 tends to read as spam on X." % len(hashtags))
    if length > 200 and len(nonblank) == 1:
        warnings.append("Wall of text: %d characters with no line breaks. Break it after "
                        "the hook." % length)
    if first_line.startswith("#"):
        warnings.append("Starts with a hashtag. Put the hook first.")

    # Question / CTA. The ask must be in the closing sentence, and a long
    # narrative sentence that happens to contain "share" does not count.
    has_question = "?" in no_urls
    closing = [s for s in SENT_END_RE.split(strip_urls(last_line)) if s.strip()]
    closing = HASHTAG_RE.sub("", closing[-1]).strip() if closing else ""
    ends_with_ask = "?" in closing or (bool(CTA_RE.search(closing)) and x_length(closing)[0] <= 140)
    if has_question and not ends_with_ask:
        warnings.append("Question with no CTA: you ask a question earlier but the post "
                        "ends without an ask. Close with one direct question or CTA, or "
                        "turn the opening question into a statement.")
    if not has_question and not CTA_RE.search(no_urls):
        info.append("No question or CTA. Fine for many posts; check the CTA style in voice.md.")

    # Shouting
    caps = [w for w in CAPS_RE.findall(no_urls) if w.replace("'", "") not in ACRONYMS]
    letters = [c for c in no_urls if c.isalpha() and c.isascii()]
    upper_ratio = (sum(c.isupper() for c in letters) / len(letters)) if letters else 0
    if len(letters) > 20 and upper_ratio > 0.6:
        warnings.append("All caps: %d%% of letters are capitals. It reads as shouting."
                        % round(upper_ratio * 100))
    elif len(caps) >= 2:
        warnings.append("All caps: %d shouted words (%s). Use one at most."
                        % (len(caps), ", ".join(caps[:4])))

    # voice.md
    if voice:
        low = no_urls.lower()
        for word in voice_items(voice, "never use"):
            if word and re.search(r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)", low):
                warnings.append("Uses \"%s\", which is on your 'Words I never use' list." % word)
        lim = policy_limit(voice_text(voice, "emoji"))
        if lim is not None and emoji > lim:
            warnings.append("%d emoji; voice.md emoji policy allows %d." % (emoji, lim))
        lim = policy_limit(voice_text(voice, "hashtag"))
        if lim is not None and len(hashtags) > lim:
            warnings.append("%d hashtags; voice.md hashtag policy allows %d." % (len(hashtags), lim))

    verdict = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "verdict": verdict,
        "length": length,
        "max": max_len,
        "urls": urls,
        "lines": len(lines),
        "blank_lines": blank,
        "hashtags": hashtags,
        "mentions": mentions,
        "emoji": emoji,
        "first_line": first_line,
        "first_line_length": first_len,
        "fold": fold,
        "hook_formula": fid,
        "hook_formula_name": fname,
        "ends_with_ask": ends_with_ask,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "text": text,
    }


def split_drafts(raw):
    parts = re.split(r"(?m)^\s*---\s*$", raw)
    return [p.strip("\n") for p in parts if p.strip()]


def wrap(msg, indent, width=78):
    words, out, line = msg.split(), [], ""
    for w in words:
        if line and len(line) + 1 + len(w) > width - indent:
            out.append(line)
            line = w
        else:
            line = (line + " " + w) if line else w
    if line:
        out.append(line)
    return ("\n" + " " * indent).join(out)


def render(results):
    out = []
    for i, r in enumerate(results, 1):
        out.append("Draft %d of %d  %s" % (i, len(results), "-" * 50))
        status = "OK" if r["length"] <= r["max"] else "OVER"
        extra = "  (%d URL%s counted as 23 each)" % (r["urls"], "" if r["urls"] == 1 else "s") if r["urls"] else ""
        out.append("  length     %d/%d  %s%s" % (r["length"], r["max"], status, extra))
        out.append("  lines      %d (%d blank)" % (r["lines"], r["blank_lines"]))
        out.append("  hashtags   %d    mentions %d    emoji %d"
                   % (len(r["hashtags"]), len(r["mentions"]), r["emoji"]))
        out.append("  fold       first line %d chars | %s" % (r["first_line_length"], r["fold"]))
        hook = "%s (%s)" % (r["hook_formula"], r["hook_formula_name"]) if r["hook_formula"] else "no formula matched"
        out.append("  hook       %s" % hook)
        out.append("  ends with  %s" % ("a question or CTA" if r["ends_with_ask"] else "no ask"))
        for label, items in (("ERROR", r["errors"]), ("warn", r["warnings"]), ("info", r["info"])):
            for msg in items:
                out.append("  %-9s  %s" % (label, wrap(msg, 13)))
        out.append("  verdict    %s" % r["verdict"])
        out.append("")
    counts = {v: sum(1 for r in results if r["verdict"] == v) for v in ("PASS", "WARN", "FAIL")}
    out.append("%d draft(s): %d PASS, %d WARN, %d FAIL"
               % (len(results), counts["PASS"], counts["WARN"], counts["FAIL"]))
    return "\n".join(out)


def read_input(path):
    if path in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("lint.py: no input. Pass a file or pipe text in. See --help.")
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError as e:
        sys.exit("lint.py: cannot read %s: %s" % (path, e.strerror))


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Lint X post drafts: X character count (URLs = 23), hashtags, "
                    "line breaks, first-100-character fold, hook, question/CTA and all-caps.",
        epilog="Separate several drafts in one file with a line containing only ---.\n"
               "Exit code: 0 = no draft over the limit, 1 = at least one FAIL, 2 = bad input.\n\n"
               "examples:\n"
               "  python3 lint.py draft.txt\n"
               "  python3 lint.py drafts.txt --voice voice.md\n"
               "  echo \"My post\" | python3 lint.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="draft file (default: stdin)")
    ap.add_argument("--max", type=int, default=280,
                    help="character limit (default 280; long-post accounts can set e.g. 25000)")
    ap.add_argument("--voice", metavar="PATH",
                    help="voice.md to check 'Words I never use' and emoji/hashtag policy")
    ap.add_argument("--hooks", metavar="PATH", default=DEFAULT_HOOKS,
                    help="hooks.json for formula matching (default: next to this script)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    drafts = split_drafts(read_input(args.file))
    if not drafts:
        print("lint.py: input is empty.", file=sys.stderr)
        return 2
    voice = None
    if args.voice:
        try:
            voice = read_voice(args.voice)
        except OSError as e:
            print("lint.py: cannot read voice file %s: %s" % (args.voice, e.strerror), file=sys.stderr)
            return 2
    formulas = load_formulas(args.hooks)
    results = [lint(d, args.max, formulas, voice) for d in drafts]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not formulas:
            print("note: hooks.json not found or invalid; hook formulas not checked.\n")
        print(render(results))
    return 1 if any(r["verdict"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
