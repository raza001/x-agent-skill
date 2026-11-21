---
name: x-post
description: Drafts a single X (Twitter) post in the user's own voice by writing five hook options, scoring them, and linting three full variants against X's character rules. Use when the user wants a tweet or an X post written, a hook for one, or a single post checked before they publish it themselves.
---

# x-post

Drafts one post. The human publishes it. This skill never posts, schedules,
likes, replies, follows or DMs.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-post/lint.py`). On Windows use `python` or `py -3`.

## Before you start

Read `voice.md` first. If it is missing, ask the user to create it from
`templates/voice.md`, or offer to generate it from 3 of their posts: ask them
to paste the posts, fill each section from what the posts actually show, mark
anything you inferred as a guess, and have the user confirm before you save it.

## Inputs

- The idea or topic (required).
- The goal: replies, reposts, bookmarks, profile visits or link clicks.
- Any facts, numbers or links the post must include. Only these numbers may
  appear in the post.

## Outputs

- 5 hooks, ranked by `hookscore.py`, each with a one-line reason.
- 3 full variants, each with its `lint.py` result.
- Nothing is published.

## Workflow

1. **Clarify the goal.** If the goal or the key fact is missing, ask one short
   question. Do not interrogate.
2. **Write 5 hooks** into `hooks.txt`, one per line, each from a different
   formula in `hooks.json`. Read the `template`, `purpose` and `failure_mode`
   of each formula you use.
3. **Score them.**
   ```bash
   python3 skills/x-post/hookscore.py hooks.txt
   ```
   Read the reasons. Rewrite the weakest property of the best 2 hooks and
   score again once if it helps. Drop hooks under 50 unless the user likes one.
4. **Write 3 variants** into `drafts.txt` from the top hooks, in different
   shapes: a short punch (under 140 characters), a story (4 to 6 short lines)
   and a list or steps. Put a line containing only `---` between drafts.
5. **Lint them.**
   ```bash
   python3 skills/x-post/lint.py drafts.txt --voice voice.md
   ```
   Fix every ERROR. Fix every warning unless voice.md says otherwise, and say
   why you kept it. Re-run until no draft is FAIL.
6. **Clean them.** If x-human is installed:
   ```bash
   python3 skills/x-human/humanize.py drafts.txt --report
   ```
   Rewrite any flagged line by hand, then lint again.
7. **Present** them in the format below and **wait for approval.** On
   feedback, revise and re-lint. Never post.

## Hook formulas (hooks.json)

25 formulas, each with `template`, `example`, `purpose`, `failure_mode` and a
`match` regex. The first matching formula wins, so specific ones come first.

| family  | formulas |
| --- | --- |
| proof   | result-in-timeframe, before-after, data-point, research-insider |
| story   | story-open, failure-lesson, past-self |
| utility | number-list, how-i, how-to, steal-this, framework, heres-how |
| tension | mistake, contrarian, stop-doing, warning, truth-about, curiosity-gap, comparison, prediction |
| direct  | callout, news-breakdown, question, one-liner |

## What the scripts check

`lint.py` (one or more drafts, separated by `---`):
- Length as X counts it: URLs count 23, emoji and CJK count 2, max 280
  (`--max 25000` only for accounts with long posts). Exit code 1 if any draft
  is over.
- Hashtags (more than 2 warns), mentions, emoji, line breaks, walls of text.
- The first 100 characters: the first sentence must land inside them.
- Missing hook (filler openers such as "So", "Thread:", "I've been thinking").
- A question with no CTA at the end, and all-caps shouting.
- With `--voice`: 'Words I never use', and the emoji and hashtag policy.

`hookscore.py` (one hook per line): 0 to 20 each for specificity, curiosity
gap, brevity, concrete number or noun, and clarity, giving a total out of 100.

Both accept stdin and `--json`.

## Rules

- Never post, schedule, like, reply, follow or DM. Hand over text only.
- Never invent numbers, results, quotes or stories. If a hook needs a number
  the user has not given, ask for it or write `{N}` and flag it.
- Follow voice.md: vocabulary, banned words, emoji, hashtags, language
  (Hinglish stays Hinglish, in the script the user writes in), CTA style and
  topics to avoid.
- One idea per post. Stay under 280 unless the user says they write long posts.
- No engagement bait ("like if", "RT if", "follow for more", "tag someone").
- Scores are heuristics. Never present them as predictions of reach.

## Output format

```
Goal: <goal>    Voice: <tone adjectives from voice.md>

Hooks (hookscore.py)
1. 81  <hook>    <one-line reason>
2. 77  <hook>    <one-line reason>
... (5 total)

Variant A    <formula>, <length>/280, <PASS|WARN>
<full post text>

Variant B    ...
Variant C    ...

Notes: <warnings kept on purpose, {N} placeholders that need real numbers>
Pick one or tell me what to change. I won't post anything.
```
