---
name: x-plan
description: Builds a realistic 7-day X (Twitter) content plan in the user's voice, mixing post types with one thread, two reply sessions and an end-of-week post-mortem question, using the user's own stats when available. Use when the user asks to plan their week on X, wants a content calendar or posting schedule, or says they don't know what to post.
---

# x-plan

Plans the week. The human writes or approves every post and publishes it
themselves. This skill never posts, schedules, likes, replies or follows.

Commands use paths from the repo root. If the skills are installed elsewhere,
use their folders instead. On Windows use `python` or `py -3`.

## Before you start

Get the voice profile first: run `python3 skills/x-voice/voice.py find` and
use the path it prints wherever a command below says `<voice-path>`. If it
finds none, create one automatically with `python3 skills/x-voice/voice.py init`
and fill it in with the user as the x-voice skill describes. The user can also
copy the template by hand. Its niche, audience, topics to avoid and CTA style shape every slot.

## Inputs

Ask for whatever is missing, in one message:

- **Time per day** the user can really spend on X.
- **Goal for the week:** reach, replies, followers, clicks to a link, or
  testing one idea.
- **Raw material:** ideas, recent wins or lessons, work in progress.
- **Optional, from other skills:**
  - x-stats output for their own posts (best post types, days and times);
  - x-viral patterns from their niche;
  - x-trending angles for this week.

## Outputs

A 7-day table with:

- a mix of post types and exactly **one thread**;
- **two reply sessions**;
- a working hook for each post;
- **one post-mortem question** for the end of the week.

## Workflow

1. **Check the data.** If x-stats results exist, run or reuse:
   ```bash
   python3 skills/x-stats/stats.py posts.csv
   ```
   Take posting days and times only from the top-vs-rest findings. If there
   is no data, say so, and pick a time the user can keep every day. Never
   quote generic "best times to post".
2. **Pick one experiment** for the week, tied to a finding or a question
   (for example "two posts open with a concrete result and a number").
3. **Fill the 7 days** with a mix of post types. A default mix, adjusted to
   the user's goal and time:

   | day | type | skill |
   | --- | --- | --- |
   | 1 | how-to or steps (utility) | x-post |
   | 2 | story or lesson + reply session 1 | x-post, x-reply |
   | 3 | the thread | x-thread |
   | 4 | opinion or contrarian take + reply session 2 | x-post, x-reply |
   | 5 | proof: a result, a number, a before and after | x-post |
   | 6 | question to the audience | x-post |
   | 7 | light, personal or behind the scenes, or rest | x-post |

   If the user has under 20 minutes a day, cut to 4 or 5 posts and keep the
   thread and both reply sessions.
4. **Write a working hook** for each post using a formula from
   `skills/x-post/hooks.json`, and score the set with
   `python3 skills/x-post/hookscore.py hooks.txt`. Use only facts the user
   gave you; mark missing details as `{N}` or `{example}`.
5. **Define the two reply sessions:** day, 20 minutes, 3 to 5 good replies,
   and the 5 to 10 accounts or topics to look at (from the user, or ask).
6. **Write the post-mortem question.** One specific question that the week's
   data can answer, plus how to answer it: export the week's posts and run
   stats.py. Example: "Did the 2 posts that opened with a number beat your
   median engagement rate?"
7. **Present** the plan and wait. Offer to draft day 1 with x-post.

## Rules

- Never post, schedule or automate anything. The plan is a document.
- Never invent numbers, best times or results. Data comes from the user's
  files or it is labelled as a guess.
- One thread and two reply sessions per week, as asked. Do not overload.
- Keep it doable in the time the user stated.
- Respect 'Topics to avoid'. Trending slots are optional and go through
  x-trending's risk check.
- Follow voice.md for language, emoji, hashtags and CTA style.

## Output format

```
Week of <date>    Goal: <goal>    Time: <minutes/day>
Experiment: <one sentence>
Posting time: <from your stats: ...> | <no data: you chose ...>

| Day | Type | Topic | Working hook | Skill |
| --- | --- | --- | --- | --- |
| Mon | how-to | ... | ... | x-post |
| ... |
| Wed | THREAD | ... | ... | x-thread |

Reply sessions
1. <day>, 20 min: <accounts or topics>, 3-5 replies (x-reply)
2. <day>, 20 min: ...

Post-mortem (end of week): <question>
How to answer it: export this week's posts, run stats.py, compare <metric>.

Want me to draft Monday's post?
```
