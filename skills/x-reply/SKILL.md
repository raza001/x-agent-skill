---
name: x-reply
description: Drafts replies and quote posts on X (Twitter) that add something real, giving three options per target post in the user's voice, with no spam, engagement bait or pile-ons. Use when the user pastes someone's post and asks what to reply, wants a quote-post take, or is planning a reply session in their niche; the user always sends the reply themselves.
---

# x-reply

Writes replies worth reading. The human picks, edits and sends. This skill
never replies, quotes, likes, follows or DMs on anyone's behalf.

If you use the optional checks below, commands use paths from the repo root.
If the skills are installed elsewhere, use their folders instead. On Windows
use `python` or `py -3`.

## Before you start

Get the voice profile first: run `python3 skills/x-voice/voice.py find` and
use the path it prints wherever a command below says `<voice-path>`. If it
finds none, create one automatically with `python3 skills/x-voice/voice.py init`
and fill it in with the user as the x-voice skill describes. The user can also
copy the template by hand. Its tone, vocabulary, banned words, language and topics to avoid apply to replies.

## Inputs

- The target post: its full text, the author, and any thread context the
  user can paste. If you only have a summary, ask for the actual text.
- Reply or quote post (default: reply).
- Optional: what the user knows or has done that relates to it. This is the
  raw material for a good reply.

## Outputs

- 3 options per target post, each built on a different move.
- A one-line note on any target you advise skipping, and why.
- Nothing is sent.

## Workflow

1. **Decide whether to reply at all.** Skip, and say why, if the post is a
   pile-on or dunk in progress, is about a tragedy, is bait ("reply with
   your..."), is harassment, or touches the user's 'Topics to avoid'.
2. **Read what the post is doing:** asking a question, making a claim,
   sharing a win, venting, sharing news, or sharing a resource. The reply
   should fit it. A win wants specific credit, not advice.
3. **Write 3 options**, each with a different move:
   - **Add:** a specific fact, example or number from the user's own
     experience that extends the point.
   - **Ask:** one sharp question that moves the conversation forward and is
     easy to answer.
   - **Angle:** a respectful disagreement, a caveat, or a different lens.
     Disagree with the idea, never the person.
   For a quote post, the user's own take must stand alone for someone who
   never opens the original.
4. **Keep them short.** Under 200 characters is a good target and 280 is
   the limit. Optional length check (put a line containing only `---`
   between options):
   ```bash
   python3 skills/x-post/lint.py replies.txt --voice <voice-path>
   ```
   Hook warnings matter less for replies; length, all-caps and banned
   words still apply.
5. **Clean them.** If x-human is installed:
   `python3 skills/x-human/humanize.py replies.txt --report`.
6. **Present** in the format below. The user picks one, edits it, and sends
   it from their own account.

## Reply sessions (used by x-plan)

A session is about 20 minutes: the user opens their own feed or a list of 5
to 10 accounts in their niche, pastes the posts they want to answer, and
you draft options for each. Aim for 3 to 5 good replies, not 30 quick ones.

## Rules

- Never send, schedule, like, follow, DM or automate anything.
- No spam: no copy-paste replies across many posts, no links to the user's
  own work unless the post asks for resources and the link answers it.
- No engagement bait ("follow me for more", "check my pinned").
- No pile-ons, dunks or ratio attempts. No mocking.
- No empty praise ("Great post!", "So true!"). Every option adds something.
- Never invent experience, numbers, credentials or quotes for the user. If
  the Add option needs a real detail, ask for it or leave `{your example}`.
- Do not @mention extra people to pull them into a thread.
- Reply in the language of the thread unless voice.md says otherwise
  (Hinglish stays Hinglish).
- If the user has a stake (their product, employer, client), the reply
  should say so plainly.

## Output format

```
Target: @<author>: "<first line of their post>"
Read: <what the post is doing>    Verdict: reply | skip (<reason>)

A. Add (<chars>)
<text>

B. Ask (<chars>)
<text>

C. Angle (<chars>)
<text>

Pick one and edit it to taste. You send it; I won't.
```
