---
name: x-trending
description: Turns a list of trending X (Twitter) topics into content angles for the user's niche by scoring each topic's relevance, flagging risky ones such as politics or tragedy, and proposing a hot take, an explainer and a personal angle for each relevant topic. Use when the user pastes what is trending, asks what they could post about today, or wants to newsjack a trend in their niche.
---

# x-trending

Finds the trends worth joining and the angle to join them with. The human
decides and publishes. This skill never posts, likes, replies, follows or DMs.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-trending/angles.py`). On Windows use `python` or `py -3`.

## Before you start

Get the voice profile first: run `python3 skills/x-voice/voice.py find` and
use the path it prints wherever a command below says `<voice-path>`. If it
finds none, create one automatically with `python3 skills/x-voice/voice.py init`
and fill it in with the user as the x-voice skill describes. The user can also
copy the template by hand. Its niche, 'Words I use', audience and 'Topics to avoid' drive the filter.
If the user declines a profile, ask for 5 to 10 niche keywords instead.

## Inputs

- The trending list, from one of:
  - **Paste (default).** The user copies the Explore / Trending tab on x.com
    into `trending.txt`. Category lines, topic lines, "Trending with ..."
    and "12.5K posts" lines are all understood.
  - A plain list (one topic per line) or a TSV with a `topic` header.
  - **Optional API**, only if the user has set it up and asks for it:
    `python3 skills/x-stats/fetch_api.py trends --woeid 1 --live --json > trends.json`
    (see x-stats).
- Niche keywords: from `voice.md`, from `--keywords`, or both.

## Outputs

- Every topic with a relevance score (0 to 100), its volume if given, the
  keywords it matched, and a RISK flag where it applies.
- For each relevant topic, 3 angles in the user's voice: a hot take, an
  explainer and a personal experience.
- A list of risky topics for the user to decide on.

## Workflow

1. **Get the list.** Ask the user to paste it into `trending.txt`, or take
   the pasted text and save it yourself, unchanged.
2. **Score it.**
   ```bash
   python3 skills/x-trending/angles.py trending.txt --voice <voice-path>
   ```
   Add `--keywords "a, b, c"` to widen the filter, or `--min 20` to see more.
3. **Second pass by eye.** Keyword matching misses synonyms. Read the
   zero-score topics and pull in any that clearly fit the niche (for example
   "Payment outage" for a SaaS founder). Say which ones you added and why.
4. **Ask what a trend is about** when it is not obvious from the label. A
   trending label does not say why it is trending. Never guess the story.
5. **Handle risk.** For every RISK topic, show the flag and let the user
   decide. Default to skipping tragedy. Anything on 'Topics to avoid' is out.
6. **Write 3 angles per relevant topic** (up to 5 topics), using the
   script's prompts as a starting point:
   - **Hot take:** a clear position the user can defend, from their niche.
   - **Explainer:** what the user's audience needs to know, in plain words.
   - **Personal experience:** how it touched the user's own work. Ask the
     user for the real detail; do not make one up.
7. **Present** them in the format below and wait. To draft one, hand off to
   x-post (single post) or x-thread.

## What angles.py does

- Parses Explore-tab pastes, plain lists, TSVs and fetch_api.py JSON.
- Splits hashtags (`#BuildInPublic` becomes build in public) and matches
  keywords by phrase, stem, and "Trending with" related terms.
- Flags risk by keyword: politics, tragedy, controversy, religion, health,
  X's own "Politics" category, and the user's 'Topics to avoid'. These lists
  are blunt; they catch obvious cases, not all of them.
- Options: `--keywords`, `--voice`, `--min` (default 30), `--json`.

## Rules

- Never post, reply, quote, like or follow.
- Never invent facts about a trend, numbers, quotes or what someone said.
  If the user has not told you what happened, say you do not know.
- No newsjacking tragedy for reach. No jokes about victims.
- Politics, religion and controversy only if the user explicitly opts in,
  and only in their voice.
- Trends move in hours. Remind the user to check the topic is still live
  and the facts still hold before posting.
- Follow voice.md: vocabulary, banned words, emoji, hashtags, language.

## Output format

```
Relevant trends (from <n> topics; keywords from voice.md)

1. <topic>  [<volume> posts]  relevance <score>
   Hot take:   <angle>
   Explainer:  <angle>
   Personal:   <angle, or the question to ask the user for their real detail>

Added by eye: <topic> (why it fits)
Risky, your call: <topic> (<flag>)
Skipped: <topic> (on your avoid list)

Want me to draft one with x-post or x-thread? I won't post anything.
```
