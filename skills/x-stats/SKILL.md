---
name: x-stats
description: Analyzes the performance of the user's own X (Twitter) posts from an exported or hand-made TSV or CSV, computing engagement rate, rankings, medians, best and worst posts, and what the top posts have in common. Use when the user asks how their posts are doing, which posts worked, what to post more of, or shares X analytics, likes, views or impressions data.
---

# x-stats

Reads the user's numbers and says what they show, and only that. Core
analysis is offline. An optional API script exists but is off by default.
This skill never posts, likes, follows, replies or DMs.

Commands use paths from the repo root. If this skill is installed on its own,
run the scripts from this folder instead (for example
`~/.claude/skills/x-stats/stats.py`). On Windows use `python` or `py -3`.

## Before you start

Get the voice profile first: run `python3 skills/x-voice/voice.py find` and
use the path it prints wherever a command below says `<voice-path>`. If it
finds none, create one automatically with `python3 skills/x-voice/voice.py init`
and fill it in with the user as the x-voice skill describes. The user can also
copy the template by hand. Recommendations must fit the user's niche and style.

## Inputs

A TSV or CSV of the user's posts with a header row. Recognized columns
(names are flexible): `url`, `text`, `views` (or `impressions`), `likes`,
`reposts` (or `retweets`), `replies`, `bookmarks`, `date`. Ways to get it:

1. **Analytics export.** If the user's account has X's analytics export,
   use that file as is. Common export column names are recognized.
2. **By hand.** The user copies numbers from their posts into a sheet and
   saves it as TSV or CSV. `1.2K` style numbers are fine. Blank means unknown.
3. **Optional API** (`fetch_api.py`, below), only if the user already has X
   API access and asks for it.

## Outputs

- Engagement rate (ER) per post = (likes + reposts + replies) / views.
- A ranking (by ER by default), medians, totals, and the best and worst posts.
- What the top 25% by ER have in common compared with the rest: length,
  lines, numbers in the hook, questions, links, hashtags, hook formula,
  weekday and hour.

## Workflow

1. **Get the file.** If the user pastes numbers in chat, write them into a
   TSV exactly as given. Never fill gaps.
2. **Run it.**
   ```bash
   python3 skills/x-stats/stats.py posts.csv
   ```
   Useful options: `--min-views 100` (ignore tiny posts in best/worst and
   patterns), `--sort bookmarks`, `--best 5`, `--top 20`, `--json`.
3. **Read the notes and missing counts first** and pass the limits on: a
   missing column, blank cells, rounded `1.2K` values, a small sample.
4. **Explain the results** in plain words: what the median post looks like,
   which posts stand out and by how much, and the top-vs-rest differences
   with their counts.
5. **Recommend 2 or 3 things to test next week**, each tied to a specific
   finding ("your two best posts both opened with a result and a number; try
   that shape twice"). Hand off to x-plan to schedule them.

## Optional: fetch_api.py (off by default)

The only script in the repo that can touch the network, and only with
`--live`. Without `--live` it prints the request and exits.

```bash
python3 skills/x-stats/fetch_api.py trends --woeid 1                     # dry run
python3 skills/x-stats/fetch_api.py metrics --ids-file ids.txt --live --tsv > posts.tsv
python3 skills/x-stats/stats.py posts.tsv
```

- Reads `X_BEARER_TOKEN` from the environment and never prints it. If it is
  not set, the script says how to set it. Never ask the user to paste a
  token into chat or into a file in the repo.
- `trends --woeid N` for trending topics (1 is worldwide, 23424848 is
  India); `--json` output feeds `x-trending/angles.py`.
- `metrics --ids ... | --ids-file ...` for `public_metrics` of posts by ID or
  URL; `--tsv` output feeds `stats.py`. Views are left blank if X does not
  return them.
- 401, 403 and 429 stop the run with a plain message; there are no retries.
- API access and pricing are set by X and change. Tell the user to check the
  X developer portal before using `--live`. Only use it when they ask.

## Rules

- Never invent, estimate or "fill in" a number. Missing stays missing.
- Use this ER formula, and say so. X's own "engagements" figure counts more
  actions (clicks, profile visits), so the numbers will not match it.
- Correlation is not cause. With fewer than about 12 posts, call patterns
  leads to test.
- Do not compare the user with other accounts unless they give that data.
- Never post, like, reply, follow or DM, and never automate a logged-in
  browser to collect stats.

## Output format

```
Data: <n> posts, <date range>, <limits from the notes>

The typical post: <median views> views, ER <median ER>
Best: <ER> "<first line>"  (why it stands out)
Worst: <ER> "<first line>"

What your top posts share (top <n> vs the other <n>)
- <finding with counts>

Try next week
1. <test tied to a finding>
2. <test tied to a finding>
```
