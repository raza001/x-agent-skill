#!/usr/bin/env python3
"""voice.py - find, create and pre-fill voice.md, the profile every x-* skill reads.

  find   print the voice.md in use and which sections still need answers
  init   create voice.md from the built-in template if there is none.
         With --posts FILE it also puts your real posts into 'Example posts'
         and notes what they show about emoji, hashtags, language and CTAs.

Lookup order: --path, then voice.md in the current folder, then the global
profile at ~/.x-agent-skill/voice.md. init writes the global one unless you
pass --here or --path. An existing file is never overwritten without
--force, and --force keeps a .bak copy first. Runs locally.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "voice-template.md")
GLOBAL = os.path.join(os.path.expanduser("~"), ".x-agent-skill", "voice.md")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
HASHTAG_RE = re.compile(r"(?<![\w&#])#\w*[^\W\d_]\w*")
HINGLISH_RE = re.compile(r"\b(hai|hain|nahi|nahin|kya|yaar|bas|bhai|acha|accha|matlab|kuch|"
                         r"bahut|abhi|kaise|kyun|toh|aur|mera|meri|apna)\b", re.I)


def local_path():
    return os.path.join(os.getcwd(), "voice.md")


def locate(explicit):
    """Return (path or None, list of places checked)."""
    if explicit:
        return (explicit if os.path.isfile(explicit) else None), [explicit]
    checked = [local_path(), GLOBAL]
    for p in checked:
        if os.path.isfile(p):
            return p, checked
    return None, checked


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def write(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sections(text):
    """[(heading, start_line, end_line)] for every '## heading'."""
    lines = text.split("\n")
    heads = [(i, m.group(1).strip()) for i, ln in enumerate(lines)
             for m in [re.match(r"^\s{0,3}##\s+(.*?)\s*#*\s*$", ln)] if m]
    out = []
    for k, (i, name) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append((name, i, end))
    return out, lines


def body_filled(body_lines):
    body = re.sub(r"<!--.*?-->", "", "\n".join(body_lines), flags=re.S)
    for ln in body.splitlines():
        ln = re.sub(r"^\s*([-*+]|\d+[.)])\s*", "", ln).strip()
        if ln and ln != "---":
            return True
    return False


def status(path):
    secs, lines = sections(read(path))
    filled = [n for n, s, e in secs if body_filled(lines[s + 1:e])]
    empty = [n for n, s, e in secs if not body_filled(lines[s + 1:e])]
    return {"path": os.path.abspath(path), "sections": len(secs), "filled": filled, "empty": empty}


def describe(path):
    p = os.path.abspath(path)
    if os.path.normcase(p) == os.path.normcase(os.path.abspath(GLOBAL)):
        return "global profile, used in every folder"
    if os.path.normcase(p) == os.path.normcase(local_path()):
        return "this folder only"
    return "custom path"


def split_posts(raw):
    raw = raw.strip()
    if re.search(r"(?m)^\s*---\s*$", raw):
        parts = re.split(r"(?m)^\s*---\s*$", raw)
    else:
        parts = raw.splitlines()
    return [p.strip() for p in parts if p.strip()]


def observations(posts):
    n = len(posts)
    emoji = [len(EMOJI_RE.findall(p)) for p in posts]
    tags = [len(HASHTAG_RE.findall(p)) for p in posts]
    dev = sum(1 for p in posts if re.search(r"[ऀ-ॿ]", p))
    hing = sum(1 for p in posts if HINGLISH_RE.search(p))
    asks = sum(1 for p in posts if p.rstrip().endswith("?"))
    lengths = [len(p) for p in posts]

    def usage(counts, word):
        used = sum(1 for c in counts if c)
        if not used:
            return "no %s in any of your %d posts" % (word, n)
        return "%s in %d of %d posts, at most %d in one post" % (word, used, n, max(counts))

    if dev:
        lang = "Devanagari script in %d of %d posts" % (dev, n)
    elif hing:
        lang = "Hindi words in Latin script (Hinglish) in %d of %d posts" % (hing, n)
    else:
        lang = "English only in these %d posts" % n
    return {
        "Emoji policy": usage(emoji, "emoji"),
        "Hashtag policy": usage(tags, "hashtags"),
        "Language": lang,
        "Call-to-action style": "%d of %d posts end with a question; median length %d characters"
                                % (asks, n, statistics.median(lengths)),
    }


def insert_into(text, heading, new_lines, only_if_empty=True):
    """Append lines at the end of a section. Returns (text, inserted?)."""
    secs, lines = sections(text)
    for name, s, e in secs:
        if name.lower() != heading.lower():
            continue
        if only_if_empty and body_filled(lines[s + 1:e]):
            return text, False
        end = e
        while end > s + 1 and not lines[end - 1].strip():
            end -= 1
        lines[end:e] = new_lines + [""]  # replaces the old trailing blank lines
        return "\n".join(lines), True
    return text, False


def apply_posts(path, posts_file):
    try:
        posts = split_posts(read(posts_file))
    except OSError as e:
        return ["could not read %s: %s" % (posts_file, e.strerror)]
    if not posts:
        return ["%s has no posts in it" % posts_file]
    notes = []
    if len(posts) > 5:
        notes.append("used the first 5 of %d posts" % len(posts))
        posts = posts[:5]
    text = read(path)
    block = []
    for i, p in enumerate(posts):
        if i:
            block.append("---")
        block += p.split("\n")
    text, ok = insert_into(text, "Example posts", block)
    notes.append("added %d posts to 'Example posts'" % len(posts) if ok
                 else "'Example posts' already has text; left it as is")
    for heading, fact in observations(posts).items():
        text, ok = insert_into(text, heading, ["<!-- observed in your posts: %s -->" % fact])
        if ok:
            notes.append("noted under '%s': %s" % (heading, fact))
    write(path, text)
    return notes


def cmd_find(args):
    path, checked = locate(args.path)
    if not path:
        if args.json:
            print(json.dumps({"found": False, "checked": checked}, indent=2))
        else:
            print("voice.md not found.")
            print("looked in:")
            for p in checked:
                print("  " + p)
            print("create it automatically:")
            print("  python3 voice.py init           (global: %s)" % GLOBAL)
            print("  python3 voice.py init --here    (this folder only)")
            print("or copy voice-template.md from this folder to one of those places by hand.")
        return 1
    st = status(path)
    if args.json:
        print(json.dumps(dict(found=True, where=describe(path), **st), ensure_ascii=False, indent=2))
        return 0
    print(st["path"])
    print("where:  %s" % describe(path))
    print("filled: %d of %d sections" % (len(st["filled"]), st["sections"]))
    print("empty:  %s" % (", ".join(st["empty"]) if st["empty"] else "none, ready to use"))
    return 0


def cmd_init(args):
    target = args.path or (local_path() if args.here else GLOBAL)
    notes = []
    if not os.path.isfile(TEMPLATE):
        print("voice.py: template not found at %s. Reinstall the x-voice skill." % TEMPLATE, file=sys.stderr)
        return 2
    existed = os.path.isfile(target)
    if existed and not args.force:
        notes.append("already exists, not overwritten (use --force to replace it; a .bak copy is kept)")
    else:
        if existed:
            shutil.copy2(target, target + ".bak")
            notes.append("replaced; the old file is at %s.bak" % target)
        write(target, read(TEMPLATE))
        notes.append("created from the template")
    if args.posts:
        notes += apply_posts(target, args.posts)
    st = status(target)
    if args.json:
        print(json.dumps(dict(created=not existed or args.force, notes=notes, where=describe(target), **st),
                         ensure_ascii=False, indent=2))
        return 0
    print(st["path"])
    print("where:  %s" % describe(target))
    for n in notes:
        print("  - " + n)
    print("filled: %d of %d sections" % (len(st["filled"]), st["sections"]))
    if st["empty"]:
        print("next:   answer these sections: %s" % ", ".join(st["empty"]))
    return 0


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="Find, create and pre-fill voice.md, the voice profile every x-* skill reads. "
                    "Lookup order: --path, ./voice.md, then ~/.x-agent-skill/voice.md.",
        epilog="examples:\n"
               "  python3 voice.py find\n"
               "  python3 voice.py init                       # global profile\n"
               "  python3 voice.py init --here                # ./voice.md, this folder only\n"
               "  python3 voice.py init --posts my-posts.txt  # also add your posts\n\n"
               "posts file: separate posts with a line containing only ---, or put one post per line.\n"
               "Manual option: copy voice-template.md (next to this script) to one of the paths above.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("find", help="show the voice.md in use and its empty sections")
    f.add_argument("--path", help="check this file instead of the default places")
    f.add_argument("--json", action="store_true", help="print JSON")
    i = sub.add_parser("init", help="create voice.md from the template if it does not exist")
    where = i.add_mutually_exclusive_group()
    where.add_argument("--here", action="store_true", help="create ./voice.md in the current folder")
    where.add_argument("--path", help="create it at this path")
    i.add_argument("--posts", metavar="FILE", help="your real posts, to fill 'Example posts'")
    i.add_argument("--force", action="store_true", help="replace an existing file (keeps a .bak)")
    i.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)
    if args.cmd == "find":
        return cmd_find(args)
    if args.cmd == "init":
        return cmd_init(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
