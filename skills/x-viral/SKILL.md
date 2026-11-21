---
name: x-viral
description: Analyzes X (Twitter) posts the user collected by hand to find what is working in their niche, ranking each post by how far it beat its author's usual engagement and naming the hook formula it used. Use when the user asks what is working on X, wants a swipe file, wants to reverse-engineer posts or accounts, or asks why a post did numbers.
---

# x-viral

Research on what works in a niche, from data the user collects. This skill
never logs in, scrapes, fetches, posts, likes, follows or replies. The user
browses x.com in their own browser and saves what they see.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-viral/swipe.py`). On Windows use `python` or `py -3`.
`swipe.py` reads `../x-post/hooks.json`, so install x-post alongside it, or
pass `--hooks PATH`.

## Before you start

Read `voice.md` first, so the niche and audience shape which posts matter.
If it is missing, ask the user to create it from `templates/voice.md`, or
offer to generate it from 3 of their posts.

## Inputs

A TSV (or CSV) the user fills in by hand while browsing x.com. Give them this
header and ask for at least 3 posts per account (5 or more is better), from
4 or more accounts in their niche, including each account's ordinary posts
and not just its hits:

```
author	date	text	likes	reposts	replies	views
```

- Copy numbers as X shows them: `1.2K`, `3,400` and `48K` all work.
- Write line breaks inside a post as `\n`. Real line breaks are also handled.
- Dates like `2026-10-01 08:15`. Optional extra columns: `url`, `bookmarks`.
- Leave a cell blank if a number is not visible. Never guess it.

## Outputs

- A ranked swipe file: each post's engagement as a multiple of its author's
  median, its hook formula, views and author.
- Patterns: hook types in the top 25% against all posts, length, line count,
  numbers in the hook, questions, links, and posting weekday and hour.
- Optional markdown swipe file (`--md`) with full text and space for notes.

## Workflow

1. **Set up collection.** Give the user the header above and the guidance on
   which accounts and how many posts. If they paste raw text instead of a
   table, put it in the TSV yourself, using only numbers that appear in what
   they pasted.
2. **Run the analysis.**
   ```bash
   python3 skills/x-viral/swipe.py posts.tsv --md swipe.md
   ```
3. **Read the notes first.** Missing values, rounded `1.2K` values and
   authors without enough posts for a baseline all limit what the ranking
   can say. Repeat those limits to the user.
4. **Explain the top posts.** For each of the top 3 to 5, name the hook
   formula (see `skills/x-post/hooks.json` for its purpose and failure
   mode), the structure, and the likely reason it beat the author's usual
   posts. Label these as your reading, not as fact.
5. **Summarize the patterns** in plain language, with the counts behind
   them ("3 of the top 3 put a number in the first line, against 2 of the
   other 11").
6. **Turn it into ideas.** Offer 3 to 5 post ideas in the user's voice that
   use a winning structure on the user's own topic and experience. Hand off
   to x-post or x-thread to draft them.

## How the ranking works

- engagement = likes + reposts + replies (whichever of these columns exist).
- multiple = post engagement / median engagement of that author's posts in
  the file. 3.0x means three times that author's typical post.
- Authors with fewer than `--min-posts` posts (default 3) get no multiple.
  Their posts are listed separately by raw engagement.
- The hook is the first line, matched against `hooks.json`. The first match
  wins; `unclassified` means no formula matched.
- Options: `--top N`, `--min-posts N`, `--hooks PATH`, `--md FILE`, `--json`.

## Rules

- No logging in, scraping, browser automation or API calls. The user collects
  the data.
- Never invent or estimate a missing number. Blank means unknown.
- Never copy someone's post as the user's own. Reuse structure, never
  wording; ideas must come from the user's own experience.
- Do not reproduce a full post in a public deliverable without crediting the
  author.
- Small samples are noisy. Say "lead to test", not "rule".
- Patterns are correlations in this file only, not causes, and not a
  prediction of reach.

## Output format

```
Data: <n> posts, <n> authors, <limits from the notes>

Top posts
1. 9.8x  @author  <hook formula>
   "<first line>"
   Why it likely worked: <structure, specificity, timing; marked as reading>

Patterns (top <n> vs the other <n>)
- <pattern with counts>

Ideas for you (in your voice)
1. <idea>  (structure borrowed from #1, your topic)

Next: draft one with x-post or x-thread?
```
