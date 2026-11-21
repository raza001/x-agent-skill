---
name: x-voice
description: Creates and maintains voice.md, the voice profile every x-* skill reads, by making it automatically from a built-in template when it is missing, pre-filling it from the user's own posts, and filling the rest in with the user. Use when the user wants to set up or update their voice or writing style, when another x-* skill finds no voice.md, or before the first post, thread or reply is drafted.
---

# x-voice

Sets up the voice profile that keeps every draft sounding like the user.
This skill never posts anything and never invents facts about the user.

Commands use paths from the repo root. If this skill is installed on its own,
run the script from this folder instead (for example
`~/.claude/skills/x-voice/voice.py`). On Windows use `python` or `py -3`.

## Where voice.md lives

`voice.py` looks in this order and uses the first file it finds:

1. `--path FILE`, if given.
2. `voice.md` in the current folder: a profile for this project only.
3. `~/.x-agent-skill/voice.md`: the global profile, used in every folder.
   On Windows this is `C:\Users\<you>\.x-agent-skill\voice.md`.

## Inputs

- Nothing, to create an empty profile.
- Optional: 3 to 5 of the user's real posts, pasted or in a file.

## Outputs

- A `voice.md` at a known path, with every section filled in and confirmed
  by the user.

## Workflow

1. **Find it.**
   ```bash
   python3 skills/x-voice/voice.py find
   ```
   The first line is the path; other skills pass it to `--voice`. The output
   also lists the sections that are still empty.
2. **Create it if it is missing**. Do this automatically, without asking the
   user to copy anything:
   ```bash
   python3 skills/x-voice/voice.py init
   ```
   This writes the global profile. Use `--here` instead if the user wants a
   profile for this folder only. Tell the user the path it printed.
3. **Pre-fill it from posts.** Ask for 3 to 5 of their real posts, save them
   to `my-posts.txt` (a line containing only `---` between posts), then run:
   ```bash
   python3 skills/x-voice/voice.py init --posts my-posts.txt
   ```
   This adds the posts to 'Example posts' and writes what the posts show
   (emoji, hashtags, language, how they end) as comments under those
   sections. Comments do not count as answers.
4. **Fill the empty sections with the user.** Take the list from `find`.
   Propose an answer for each section from the posts, mark each one as a
   guess, and ask the user to confirm or correct it in one message. Then
   write the confirmed answers into the file under each heading.
5. **Check it.** Run `voice.py find` again until it says
   `empty: none, ready to use`, then go back to the task the user asked for.

## Manual option

If the user prefers to do it by hand, they copy the template themselves and
fill it in:

```bash
# macOS / Linux, global profile
mkdir -p ~/.x-agent-skill
cp ~/.claude/skills/x-voice/voice-template.md ~/.x-agent-skill/voice.md
```

```powershell
# Windows PowerShell, global profile
New-Item -ItemType Directory -Force "$HOME\.x-agent-skill" | Out-Null
Copy-Item "$HOME\.claude\skills\x-voice\voice-template.md" "$HOME\.x-agent-skill\voice.md"
```

From a clone of the repo, the template is at
`skills/x-voice/voice-template.md`; copy it to `./voice.md` for a
per-project profile.

## What voice.py does

- `find`: prints the path in use, global or this-folder, and which of the
  11 sections are filled. Exit code 1 if there is no voice.md.
- `init`: creates voice.md from `voice-template.md`. It never overwrites an
  existing file; `--force` replaces it and keeps a `.bak` copy.
- `init --posts FILE`: fills 'Example posts' (up to 5) only if that section
  is empty, and adds observations as comments.
- `--json` on both commands.

## Rules

- Never invent niche, audience, tone or facts. Guesses are marked as guesses
  and confirmed by the user before they go in the file.
- Never overwrite a voice.md without the user's go-ahead.
- voice.md is private. Never commit it, paste it into public places, or
  send it anywhere.
- Keep answers short, in the user's words, and in the user's language.

## Output format

```
Voice profile: <path> (<global | this folder only>)
Filled: <n>/11

Proposed answers (guesses from your posts, please confirm or fix):
- Niche: ...
- Tone: ..., ..., ...
- ...

Once you confirm, I'll save them and get back to <the original task>.
```
