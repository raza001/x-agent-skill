---
name: x-thread
description: Turns a topic, notes or a long piece of text into a numbered X (Twitter) thread in the user's voice, then checks every post for length, weak openers and a missing call to action. Use when the user asks for a thread, wants to turn an article, newsletter or transcript into posts, or wants an existing thread checked before they publish it.
---

# x-thread

Writes and checks threads. The human publishes them. This skill never posts,
schedules, likes, replies, follows or DMs.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-thread/beats.py`). On Windows use `python` or `py -3`.

## Before you start

Read `voice.md` first. If it is missing, ask the user to create it from
`templates/voice.md`, or offer to generate it from 3 of their posts (fill it
from what the posts show, mark guesses, and have the user confirm).

## Inputs

- A topic, rough notes, or long text (article, newsletter, transcript).
- Optional: the goal of the thread and the CTA the user wants at the end.

## Outputs

- One thread, numbered `1/n`, every post within 280 characters as X counts
  them, with the `beats.py` check results.
- Nothing is published.

## Workflow

1. **Pick a shape.** Choose one and say which:
   - **story**: moment, tension, turning point, result, lesson.
   - **listicle**: promise of N items, one item per post, a recap.
   - **how-to**: outcome, steps in order, common mistake, result.
   - **contrarian**: the common belief, why it fails, the better view, proof.
2. **Write the opener (post 1).** It stands alone: a hook from
   `skills/x-post/hooks.json` plus a promise of what the thread delivers. No
   "A thread", "Thread:" or a lone thread emoji. If x-post is installed, score
   2 or 3 candidate openers with
   `python3 skills/x-post/hookscore.py hooks.txt`.
3. **Write the body.** One idea per post. Each post should make sense if it
   is the only one someone sees. Keep paragraphs short. Use only facts and
   numbers the user gave you or that are in their source text.
4. **Write the closer.** Recap in one line, then one CTA in the user's CTA
   style (a question, a follow for the next one, or a link they asked for).
5. **Number and check.** Write the thread into `thread.txt` (posts separated
   by a line containing only `---`), or pass prose straight in, and run:
   ```bash
   python3 skills/x-thread/beats.py thread.txt
   ```
   For long source text, let the script do the first split:
   ```bash
   python3 skills/x-thread/beats.py source.txt --mode split
   ```
   Then rewrite the split posts into real beats. A mechanical split is a
   starting point, not a thread.
6. **Fix every flag** and run beats.py again until nothing is TOO LONG and
   every remaining flag is deliberate.
7. **Clean it.** If x-human is installed, run
   `python3 skills/x-human/humanize.py thread.txt --report` and rewrite
   flagged lines.
8. **Present** it in the format below and wait for approval. Never post.

## What beats.py does

- **split mode:** splits prose at sentence boundaries into posts under the
  limit, leaving room for the `1/n` marker. Paragraph 1 always becomes post 1.
  Over-long sentences are split at commas, then at words.
- **check mode:** takes posts separated by `---` lines, or starting with
  `1/`, `2/` markers, and re-numbers them.
- **auto (default):** check mode if the input looks pre-split, otherwise split.
- Flags: TOO LONG, short (under 40 characters), a weak opener on post 1
  (filler, "A thread") or on body posts ("Also", "Additionally", "And"), a
  hook whose first sentence runs past 100 characters, and no CTA in the last
  post.
- Prints words and reading time at 238 words per minute.
- Options: `--number suffix|prefix|none`, `--limit`, `--min`, `--json`.
  Exit code 1 if any post is too long.

## Rules

- Never post, schedule, like, reply, follow or DM.
- Never invent numbers, results, quotes or events. If a beat needs a number
  the user has not given, ask or write `{N}` and flag it.
- Follow voice.md for vocabulary, banned words, emoji, hashtags, language
  and CTA style.
- 5 to 12 posts is a sensible range. Over 15, suggest cutting. If it fits in
  one post, say so and offer x-post instead.
- No engagement bait ("like and RT if", "follow for part 2" with no part 2).
- Hashtags: none in the body. At most what voice.md allows, at the end.

## Output format

```
Shape: <story|listicle|how-to|contrarian>    Posts: <n>    Read: <time>

1/n  (<chars>/280)
<post text>

2/n  (<chars>/280)
<post text>
...

Check: <n> posts, <flags fixed>, <flags kept on purpose and why>
Notes: <{N} placeholders that need real numbers, if any>
Want changes? I won't post anything.
```
