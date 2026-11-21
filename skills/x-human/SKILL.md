---
name: x-human
description: Cleans AI-sounding text by removing invisible characters, normalizing typography, flagging stock phrases and structural tells with suggested fixes, and scoring the result with a local five-check heuristic. Use when the user says humanize, de-slop, "does this sound like AI", "remove the em dashes", or before any X post, thread or reply drafted by an agent is shown to the user.
---

# x-human

Cleans drafts so they read like a person wrote them. Nothing is uploaded;
both scripts run locally. This skill never posts anything.

Commands use paths from the repo root. If this skill is installed on its own,
run the scripts from this folder instead (for example
`~/.claude/skills/x-human/humanize.py`). On Windows use `python` or `py -3`.

## Before you start

Read `voice.md` first, because the fix for a flagged line must sound like the
user. If it is missing, ask the user to create it from `templates/voice.md`,
or offer to generate it from 3 of their posts.

## Inputs

- A draft file (or stdin): a post, a thread or replies.

## Outputs

- The cleaned text.
- A change report: what was removed, what was normalized, and which phrases
  and lines need a human rewrite.
- A before/after heuristic score.

## Workflow

1. **Clean the mechanical layer.**
   ```bash
   python3 skills/x-human/humanize.py draft.txt -o clean.txt --report
   ```
   This removes invisible characters and fixes typography automatically, then
   lists stock phrases with suggestions. Add `--apply` to make the swaps that
   `slop.json` marks safe (`auto: true`).
2. **Rewrite the flagged lines yourself.** Structural tells are never
   auto-fixed. For each flag, rewrite that line in the user's voice, keeping
   the meaning. Do the same for phrases marked "rewrite by hand".
3. **Score before and after.**
   ```bash
   python3 skills/x-human/detect.py draft.txt clean.txt
   ```
4. **Iterate on the weakest check** named in the output. Two rounds is normal.
   If a draft needs five, write a new draft instead.
5. **Show the user the cleaned text and the scores together**, never the
   score alone, and say what you changed.

## What humanize.py fixes automatically

- **Invisible characters** (23 classes in `slop.json`): zero-width spaces and
  joiners, word joiner, BOM, soft hyphen, Unicode tag characters, bidi marks
  and overrides, Hangul fillers, plus any other Unicode format character.
  Odd spaces (no-break, narrow, thin, ideographic) become normal spaces.
  Joiners inside emoji sequences and in Devanagari or other Indic scripts are
  kept, because removing them breaks the text.
- **Typography:** em dashes become commas (`--dash hyphen` or `--dash keep`
  to change that), en dashes become hyphens, curly quotes become straight,
  the ellipsis character becomes three dots, and bullet characters at the
  start of a line become hyphens.

## What it flags (with suggestions)

- **Stock phrases** (180+ in `slop.json`, grouped as filler, ai-tell,
  corporate, hype and x-tell): "in today's fast-paced world", "delve into",
  "game-changer", "leverage", "let that sink in"...
- **Structural tells** (15): "it's not just X, it's Y", "not only X but
  also", rule-of-three overuse, em dash overuse, "The result?" reveals,
  "Here's the thing:", emoji bullet lists, hashtag walls, engagement bait,
  shouting, thread announcements as hooks, "Imagine..." openers, "Why?
  Because...", stacks of one-word lines, and "Not X. Not Y. Z."

The lexicon is meant to be edited. If the user really says a word on the
list, delete that entry from `slop.json`.

## The five checks (detect.py)

| check | measures | low score looks like |
| --- | --- | --- |
| BURSTINESS | sentence-length variation (needs 4+ sentences) | every sentence the same length |
| SPECIFICITY | numbers, names, handles per 100 words | abstract claims, no figures |
| SLOP DENSITY | stock phrases per 100 words | lexicon vocabulary |
| FINGERPRINT | invisible chars, em dashes, curly quotes per 1,000 chars | machine typography |
| VOICE | contractions, I/you, structural tells | formal, staged reveals |

Overall = 60% of the mean + 40% of the weakest check. PASS needs 70+ with no
check under 55; 50 to 69 is REVIEW; under 50 is REWRITE. Give it one file to
score or two to compare.

## Say this honestly

detect.py is a local heuristic built on five surface signals and tuned for
English. It is **not** proof of who or what wrote a text, it does not call
any detection service, and it cannot predict what a commercial detector will
say. Never tell the user their text is "undetectable". Curly quotes are
weighted low because phone keyboards insert them.

## Rules

- Never post anything. Hand back text.
- Keep the meaning. Do not add claims, numbers or stories while cleaning.
- Keep the user's language. For Hindi or Hinglish, the phrase list mostly
  will not apply; review by hand and leave Devanagari joiners alone.
- Do not strip a word the user lists under 'Words I use' in voice.md.

## Output format

```
Cleaned text
<text>

Changes
- invisible characters: <n> removed (<classes>)
- typography: <n> fixed
- phrases: <n> flagged, <n> applied, <n> rewritten by hand
- structural: <list of tells and how each line was rewritten>

Score (detect.py, heuristic)   before -> after
BURSTINESS ... VOICE, OVERALL, verdict
```
