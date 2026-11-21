---
name: x-profile
description: Audits an X (Twitter) profile the user pastes against a 100-point rubric covering bio, pinned post, handle and name, banner, consistency, niche focus, and CTA and link, then lists the top 3 fixes and drafts rewrites. Use when the user asks to review, score or optimize their X profile or bio, or asks why visitors don't follow them.
---

# x-profile

Scores the profile and rewrites the weak parts. The user makes every change
on x.com themselves. This skill never edits a profile, posts, follows or DMs,
and never visits x.com.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-profile/audit.py`). On Windows use `python` or `py -3`.

## Before you start

Get the voice profile first: run `python3 skills/x-voice/voice.py find` and
use the path it prints wherever a command below says `<voice-path>`. If it
finds none, create one automatically with `python3 skills/x-voice/voice.py init`
and fill it in with the user as the x-voice skill describes. The user can also
copy the template by hand. Rewrites must sound like the user, and its niche keywords feed the niche checks.

## Inputs

The user copies these from their own profile into `profile.txt`:

```
name: <display name>
handle: @<handle>
bio: <bio text>
location: <location>
link: <the link in the profile>
banner: <describe it: colours, any text on it, any image>
pinned_date: <YYYY-MM-DD>
pinned:
<full text of the pinned post>
recent_posts:
<YYYY-MM-DD> | <post text>
<YYYY-MM-DD> | <post text>
```

- Leave a line out if unknown; those checks show as "not scored".
- Write `bio:` with nothing after it if the profile really has no bio; that
  scores 0. The same applies to every field.
- 5 to 10 recent posts with dates make the consistency checks meaningful.

## Outputs

- A score out of the points that could be scored, per criterion and check.
- The top 3 fixes, ordered by points lost.
- Drafted rewrites for the weakest parts.

## Workflow

1. **Collect the profile** in the format above. If the user pastes it loosely,
   arrange it into the keys yourself without adding anything.
2. **Score it.**
   ```bash
   python3 skills/x-profile/audit.py profile.txt --voice <voice-path>
   ```
   Use `--keywords "a, b"` if there is no voice.md.
3. **Check what was not scored** and say so. Never fill a gap with a guess.
4. **Walk through the top 3 fixes** in plain words, with the script's
   reason for each.
5. **Draft the rewrites** for whatever lost points:
   - **Bio:** 3 options, each 160 characters or fewer, each with what the
     user does, for whom, one proof point the user actually gave you, and a
     next step. Check length with
     `python3 skills/x-post/lint.py bio.txt --max 160`.
   - **Name field:** name or brand plus an optional niche keyword, 50
     characters or fewer.
   - **Pinned post:** pick their strongest recent post, or draft a new one
     with x-post.
   - **Banner:** one line of text that states the promise. Describe it; you
     cannot design the image.
6. **Re-score** with the rewrites pasted in, show before and after, and stop.
   The user updates the profile.

## The rubric (rubric.json)

| criterion | points | checks |
| --- | --- | --- |
| Bio clarity | 25 | 60 to 160 chars, says what/for whom, no empty labels, a proof point, at most 2 hashtags and 3 emoji |
| Pinned post | 15 | exists, hook in 100 chars, pinned in the last 180 days, ends with an ask |
| Handle and name | 15 | handle 12 chars or fewer, no digit strings or extra underscores, readable name, at most 2 emoji |
| Banner | 10 | custom banner set, states a promise or shows proof |
| Consistency | 10 | 3+ posts a week, 60%+ of recent posts on the niche |
| Niche focus | 15 | 3 or fewer roles in the bio, pinned matches the bio, niche keyword in name or bio |
| CTA and link | 10 | link present, next step in the bio, link goes off X |

Options: `--keywords`, `--voice`, `--today YYYY-MM-DD`, `--rubric`, `--json`.

## Rules

- Never edit the profile, post, follow, DM or log in. Hand over text.
- Never invent proof points (followers, revenue, clients, employers). Use
  only what the user gave you, or leave a `{proof}` slot and ask.
- Do not suggest changing the handle lightly: it breaks mentions and links.
  Present it as an option with that trade-off.
- Scores are heuristics on pasted text. The banner check only reads the
  user's description of it.
- Follow voice.md for tone, banned words, emoji and language.

## Output format

```
Score: <earned>/<scored> (<percent>%)   <n> points not scored: <which inputs were missing>

Top 3 fixes
1. <criterion> (-<points>): <fix>. Now: <reason>
2. ...
3. ...

Rewrites
Bio A (<chars>/160): <text>
Bio B ...
Bio C ...
Name: <text>
Pinned: <recommendation or draft>
Banner line: <text>

Re-score with Bio A: <new score>. You make the changes on x.com.
```
