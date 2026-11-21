#!/usr/bin/env python3
"""beats.py - split long text into an X thread, or check a thread you wrote.

Splits at sentence boundaries into posts that fit X's limit (URLs count as 23,
most emoji and CJK characters as 2), numbers them 1/n, and flags posts that are
too long, too short or open weakly, plus a missing CTA in the last post. Also
estimates reading time.

Runs locally on text you give it. Nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

URL_WEIGHT = 23
WPM = 238  # average silent reading speed for adults, words per minute

# --- X character counting (same rules as x-post/lint.py) -------------------
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


def _in(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def _emoji_end(s, i):
    n = len(s)
    if s[i] in "0123456789#*":
        j = i + 1
        if j < n and s[j] == "️":
            j += 1
        return j + 1 if j < n and s[j] == "⃣" else None
    cp = ord(s[i])
    if not _in(cp, EMOJI):
        return None
    j = i + 1
    if 0x1F1E6 <= cp <= 0x1F1FF:
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
    text = unicodedata.normalize("NFC", text)
    total, last, pieces = 0, 0, []
    for m in URL_RE.finditer(text):
        s, e = m.start(), m.end()
        while e > s and text[e - 1] in ".,!?:;)]}'\"":
            e -= 1
        pieces.append(text[last:s])
        last = e
        total += URL_WEIGHT
    pieces.append(text[last:])
    for p in pieces:
        i = 0
        while i < len(p):
            end = _emoji_end(p, i)
            if end is not None:
                total += 2
                i = end
                continue
            total += 1 if _in(ord(p[i]), LIGHT) else 2
            i += 1
    return total


# --- splitting --------------------------------------------------------------
ABBREV = re.compile(r"(\b(e\.g|i\.e|mr|mrs|ms|dr|vs|etc|jr|sr|st|no|approx|u\.s|fig)\.)$", re.I)
MARKER_RE = re.compile(r"^\s*\(?(\d{1,2})\s*/\s*(\d{1,2})?\)?[.:]?\s+")
SEP_RE = re.compile(r"(?m)^\s*---\s*$")


def split_sentences(par):
    parts = re.split(r"(?<=[.!?।])[\"')\]]?\s+", par.strip())
    out = []
    for p in parts:
        if out and ABBREV.search(out[-1]):
            out[-1] = out[-1] + " " + p
        elif p:
            out.append(p)
    return out


def fit(piece, budget):
    """Split one over-long sentence at clause marks, then at words."""
    if x_length(piece) <= budget:
        return [piece]
    chunks, cur = [], ""
    for clause in re.split(r"(?<=[,;:])\s+", piece):
        trial = (cur + " " + clause).strip()
        if x_length(trial) <= budget:
            cur = trial
            continue
        if cur:
            chunks.append(cur)
        if x_length(clause) <= budget:
            cur = clause
            continue
        cur = ""
        for word in clause.split():
            trial = (cur + " " + word).strip()
            if x_length(trial) <= budget:
                cur = trial
            else:
                if cur:
                    chunks.append(cur)
                cur = word
    if cur:
        chunks.append(cur)
    return chunks


def auto_split(text, budget):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    posts, cur = [], ""
    for idx, para in enumerate(paragraphs):
        para = re.sub(r"\s*\n\s*", " ", para)
        units = []
        for sent in split_sentences(para):
            units += fit(sent, budget)
        for k, unit in enumerate(units):
            sep = "\n\n" if (cur and k == 0) else " "
            trial = (cur + sep + unit) if cur else unit
            if x_length(trial) <= budget or not cur:
                cur = trial
            else:
                posts.append(cur)
                cur = unit
        # Paragraph ends are natural breaks: always after the first paragraph
        # (the hook gets its own post), otherwise once the post is half full.
        if cur and (idx == 0 or x_length(cur) >= budget * 0.5):
            posts.append(cur)
            cur = ""
    if cur:
        posts.append(cur)
    return posts


def presplit(text):
    if SEP_RE.search(text):
        posts = [p.strip() for p in SEP_RE.split(text) if p.strip()]
    else:
        posts, cur = [], []
        for line in text.splitlines():
            if MARKER_RE.match(line) and cur:
                posts.append("\n".join(cur).strip())
                cur = []
            cur.append(line)
        if cur:
            posts.append("\n".join(cur).strip())
    return [MARKER_RE.sub("", p, count=1).strip() for p in posts if p.strip()]


def looks_presplit(text):
    if SEP_RE.search(text):
        return True
    markers = [ln for ln in text.splitlines() if MARKER_RE.match(ln)]
    return len(markers) >= 2 and MARKER_RE.match(text.lstrip()) is not None


# --- checks -----------------------------------------------------------------
HOOK_WEAK = re.compile(
    r"^\s*(\U0001F9F5|a thread|thread\b|here'?s a thread|so\b|just\b|i think|"
    r"i('ve| have) been thinking|some thoughts|let'?s talk about|hey\b|hi\b|"
    r"in today'?s|i (just )?wanted to)", re.I)
BODY_WEAK = re.compile(
    r"^\s*(and|also|additionally|furthermore|moreover|in addition|next|so|"
    r"another thing|plus|lastly|finally|in conclusion)\b[,:]?", re.I)
CTA_RE = re.compile(
    r"\b(follow|repost|retweet|rt|bookmark|save (this|it)|share|reply|comment|"
    r"tell me|let me know|dm me|subscribe|newsletter|link|sign up|join|check out|"
    r"what do you think|which (one|would)|your turn|grab|download)\b", re.I)


def number(posts, style):
    n = len(posts)
    if style == "none":
        return list(posts)
    if style == "prefix":
        return ["%d/%d %s" % (i, n, p) for i, p in enumerate(posts, 1)]
    return ["%s %d/%d" % (p, i, n) for i, p in enumerate(posts, 1)]


def check(posts, numbered, limit, min_len):
    n = len(posts)
    report = []
    for i, (raw, out) in enumerate(zip(posts, numbered), 1):
        length = x_length(out)
        flags = []
        if length > limit:
            flags.append("TOO LONG: %d/%d" % (length, limit))
        if x_length(raw) < min_len and not (i == n and n > 1):
            flags.append("short (%d chars): merge it or make it land harder" % x_length(raw))
        first_line = raw.strip().splitlines()[0] if raw.strip() else ""
        if i == 1:
            m = HOOK_WEAK.match(first_line)
            if m:
                flags.append("weak opener ('%s'): the hook must carry post 1" % m.group(0).strip())
            first_sentence = split_sentences(first_line)[0] if first_line else ""
            if x_length(first_sentence) > 100:
                flags.append("hook's first sentence is %d chars; land it in 100"
                             % x_length(first_sentence))
        else:
            m = BODY_WEAK.match(first_line)
            if m:
                flags.append("weak opener ('%s'): start with the point" % m.group(0).strip())
        if i == n and n > 1:
            last = raw.strip()
            if not CTA_RE.search(last) and "?" not in last:
                flags.append("no CTA in the last post: ask a question, point to a "
                             "resource, or invite a follow")
        report.append({"n": i, "length": length, "text": out, "flags": flags})
    return report


def reading_time(posts):
    words = sum(len(p.split()) for p in posts)
    secs = int(round(words / WPM * 60))
    return words, secs


def fmt_secs(secs):
    return "%d s" % secs if secs < 60 else "%d min %02d s" % (secs // 60, secs % 60)


def read_input(path):
    if path in (None, "-"):
        if sys.stdin.isatty():
            sys.exit("beats.py: no input. Pass a file or pipe text in. See --help.")
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError as e:
        sys.exit("beats.py: cannot read %s: %s" % (path, e.strerror))


def main(argv=None):
    for s in (sys.stdout, sys.stderr, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Split text into an X thread at sentence boundaries, number it 1/n, "
                    "and flag posts that are too long, too short, open weakly, or a "
                    "last post with no CTA. Estimates reading time.",
        epilog="Modes:\n"
               "  split  treat the input as prose and split it (paragraph 1 becomes post 1)\n"
               "  check  input is already a thread: posts separated by --- lines or\n"
               "         starting with 1/, 2/ ... markers (old markers are replaced)\n"
               "  auto   check if the input looks pre-split, otherwise split (default)\n\n"
               "examples:\n"
               "  python3 beats.py essay.txt\n"
               "  python3 beats.py thread.txt --mode check --number prefix\n"
               "  cat notes.txt | python3 beats.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", nargs="?", help="text file (default: stdin)")
    ap.add_argument("--mode", choices=("auto", "split", "check"), default="auto")
    ap.add_argument("--number", choices=("suffix", "prefix", "none"), default="suffix",
                    help="where to put the 1/n marker (default: suffix)")
    ap.add_argument("--limit", type=int, default=280, help="characters per post (default 280)")
    ap.add_argument("--min", type=int, default=40, dest="min_len",
                    help="flag posts shorter than this (default 40)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    text = read_input(args.file).strip()
    if not text:
        print("beats.py: input is empty.", file=sys.stderr)
        return 2
    mode = args.mode
    if mode == "auto":
        mode = "check" if looks_presplit(text) else "split"
    if mode == "check":
        posts = presplit(text)
    else:
        # Reserve room for the marker; two passes in case n grows past 9.
        reserve = 0 if args.number == "none" else len(" 9/9")
        posts = auto_split(text, args.limit - reserve)
        if args.number != "none" and len(posts) > 9:
            posts = auto_split(text, args.limit - len(" %d/%d" % (len(posts), len(posts))))
    numbered = number(posts, args.number)
    report = check(posts, numbered, args.limit, args.min_len)
    words, secs = reading_time(posts)
    summary = {
        "mode": mode,
        "posts": len(posts),
        "words": words,
        "reading_time_seconds": secs,
        "flagged_posts": sum(1 for r in report if r["flags"]),
        "too_long": sum(1 for r in report if any(f.startswith("TOO LONG") for f in r["flags"])),
    }
    notes = []
    if len(posts) > 15:
        notes.append("%d posts is long; most readers drop off well before the end. "
                     "Consider cutting." % len(posts))
    if len(posts) == 1:
        notes.append("This fits in one post. It may not need to be a thread.")

    if args.json:
        print(json.dumps({"summary": summary, "posts": report, "notes": notes},
                         ensure_ascii=False, indent=2))
    else:
        print("Thread: %d posts, %d words, about %s to read  (mode: %s)"
              % (len(posts), words, fmt_secs(secs), mode))
        print("=" * 64)
        for r in report:
            status = "ok" if not r["flags"] else "check"
            print("[%d/%d]  %d/%d chars  %s" % (r["n"], len(posts), r["length"], args.limit, status))
            for line in r["text"].splitlines():
                print("    " + line)
            for flag in r["flags"]:
                print("  ! " + flag)
            print("-" * 64)
        for note in notes:
            print("note: " + note)
        print("%d of %d posts flagged." % (summary["flagged_posts"], len(posts)))
    return 1 if summary["too_long"] else 0


if __name__ == "__main__":
    sys.exit(main())
