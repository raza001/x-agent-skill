# x-agent-skill

Agent skills for people who write on X (Twitter). They help you research what
works in your niche, draft posts and threads in your own voice, clean and
score drafts, and analyze how your posts perform.

They follow the open Agent Skills format (a folder with a `SKILL.md`), so the
same files work in Claude Code, OpenAI Codex CLI, Gemini CLI, Cursor and
GitHub Copilot.

**These skills never post for you.** No skill posts, likes, follows, replies
or sends DMs. Every skill ends by handing you text, and nothing is published
until you publish it yourself.

## What this is

- 10 skills. Each is a set of instructions an agent follows, plus small Python
  scripts that do the counting and checking, so results do not depend on the
  model's arithmetic.
- Local. The core scripts use only the Python 3.9+ standard library, make no
  network calls, read files or stdin, and print readable text or `--json`.
- Explicit about its limits. Heuristics are labelled as heuristics, and
  missing data is reported as missing, never filled in.

## What this is not

- Not a bot or a scheduler. Nothing automates your account.
- Not a scraper. Nothing logs in to X or collects data from it. You browse
  X yourself and paste or save what you see.
- Not a growth guarantee. Hook scores and patterns rank your options; they do
  not predict reach.
- Not an AI-detector bypass. `detect.py` is a local heuristic and proves
  nothing about who wrote a text.

## The skills

| Skill | What it does | Try saying | Scripts |
| --- | --- | --- | --- |
| `x-voice` | Creates your voice profile automatically and fills it from your posts | "Set up my voice" | `voice.py`, `voice-template.md` |
| `x-post` | Drafts one post: 5 hooks scored, 3 variants linted | "Write a post about raising my prices" | `lint.py`, `hookscore.py`, `hooks.json` |
| `x-thread` | Turns a topic or long text into a numbered thread and checks it | "Turn this newsletter into a thread" | `beats.py` |
| `x-human` | Removes AI tells: invisible characters, typography, stock phrases | "Does this sound like AI? Clean it up" | `humanize.py`, `detect.py`, `slop.json` |
| `x-viral` | Ranks posts you collected by how far each beat its author's median | "What's working in my niche? Here's my TSV" | `swipe.py` |
| `x-trending` | Filters trending topics for your niche, flags risky ones, proposes angles | "Here's what's trending, what can I post?" | `angles.py` |
| `x-stats` | Analyzes your own post performance from an export or a sheet | "Which of my posts worked last month?" | `stats.py`, `fetch_api.py` (optional) |
| `x-profile` | Scores your profile on a 100-point rubric and lists the top 3 fixes | "Audit my X profile" | `audit.py`, `rubric.json` |
| `x-reply` | Drafts 3 replies or quote posts per target post, which you send | "What should I reply to this?" | none |
| `x-plan` | Builds a 7-day plan with one thread and two reply sessions | "Plan my week on X" | none |

## Install

### Before you install

- **Python 3.9 or newer**, for the scripts.
  - macOS: check with `python3 --version`. If it is missing, install it from
    [python.org](https://www.python.org/downloads/) or with `brew install python`.
  - Windows: install it from [python.org](https://www.python.org/downloads/)
    or with `winget install Python.Python.3.12`, then check with
    `python --version`. Use `python` or `py -3` wherever the docs say
    `python3`. On Windows, `python3` often opens the Microsoft Store instead
    of running Python.
- **Node.js**, only for the one-command install below (it provides `npx`).

Install **all 10 skills together**. `x-viral` and `x-stats` read
`x-post/hooks.json`, and the skills hand off to each other.

### Option 1: one command (macOS, Linux and Windows)

The same command works in Terminal on macOS, in PowerShell, and in Command
Prompt:

```bash
npx skills add raza001/x-agent-skill -g -a claude-code -s "*" -y --copy
```

| Flag | What it does |
| --- | --- |
| `-g` | Installs for your user, so the skills work in every project. Without it, they go into the folder you ran the command from. |
| `-a claude-code` | Installs for Claude Code only. |
| `-s "*"` | Installs all 10 skills. |
| `-y` | Skips the prompts. |
| `--copy` | Puts real files in the Claude folder instead of links. |

The skills end up here:

| System | Folder |
| --- | --- |
| macOS / Linux | `~/.claude/skills/x-post/`, `~/.claude/skills/x-thread/`, ... |
| Windows | `C:\Users\<you>\.claude\skills\x-post\`, ... |

Check that they are there, then restart Claude Code or start a new session:

```bash
# macOS / Linux
ls ~/.claude/skills
```

```powershell
# Windows PowerShell
Get-ChildItem "$HOME\.claude\skills"
```

```bat
:: Windows Command Prompt
dir "%USERPROFILE%\.claude\skills"
```

If you run plain `npx skills add raza001/x-agent-skill` instead, it asks
questions. Pick all skills, **Claude Code** as the agent, and **Global** when
it asks where to install.

**If the skills did not land in `~/.claude/skills`:**

- **You ran it without `-g`:** it installed into `.claude/skills/` inside the
  folder you were in, and wrote a `skills-lock.json` file there.
- **You picked other agents as well:** the CLI also put copies in their
  folders, for example `~/.agents/skills/`. Run the command above to get a
  copy in the Claude folder.

Keep them current, or remove them:

```bash
npx skills list -g
npx skills update -g -y
npx skills remove x-post x-thread x-human x-viral x-trending x-stats x-profile x-reply x-plan x-voice -g -a claude-code -y
```

The remove command names the 10 skills on purpose. Do not use `-s "*"` with
`remove`: it would delete every global skill you have, not just these.

### Option 2: manual install (git clone and copy)

macOS / Linux (Terminal):

```bash
git clone https://github.com/raza001/x-agent-skill.git
mkdir -p ~/.claude/skills
cp -R x-agent-skill/skills/* ~/.claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/raza001/x-agent-skill.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\x-agent-skill\skills\* "$HOME\.claude\skills\"
```

Windows (Command Prompt):

```bat
git clone https://github.com/raza001/x-agent-skill.git
xcopy /E /I /Y "x-agent-skill\skills" "%USERPROFILE%\.claude\skills"
```

No git? On the GitHub page, click **Code > Download ZIP**, unzip it, and copy
the folders inside `skills/` into the folder for your tool.

### Other tools

Copy the same 10 folders into your tool's skills folder:

| Tool | macOS / Linux | Windows |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |
| OpenAI Codex CLI | `~/.codex/skills/` | `%USERPROFILE%\.codex\skills\` |
| Gemini CLI | `~/.gemini/skills/` | `%USERPROFILE%\.gemini\skills\` |
| Cursor | `~/.cursor/skills/` | `%USERPROFILE%\.cursor\skills\` |
| GitHub Copilot | `.github/skills/` in a repository | `.github\skills\` in a repository |

To use the `skills` CLI for another tool, run
`npx skills add raza001/x-agent-skill -g` and pick that tool from the list.

Skill folder locations and support differ between tools and change between
versions. If a tool does not pick the skills up, check its documentation for
the current path, and restart it after copying. Claude Code also reads
project-level skills from `.claude/skills/` inside a project.

Commands inside each `SKILL.md` use paths from the repo root (for example
`python3 skills/x-post/lint.py draft.txt`). When the skills are installed
elsewhere, the agent runs the same script from the installed folder.

## Set up your voice

Every skill reads `voice.md` before it writes anything. It holds your niche,
audience, tone (3 adjectives), words you use, words you never use, 3 to 5 of
your real posts, topics to avoid, emoji and hashtag policy, language
(English, Hindi or Hinglish) and call-to-action style.

### Automatic (default)

You don't need to copy anything. The first time any x-* skill runs, it
checks for `voice.md`. If there isn't one, it creates one from the built-in
template, fills in what it can from your posts, and asks you to confirm the
rest. You can also start it yourself by telling your agent "set up my
voice". Behind the scenes it runs:

```bash
python3 skills/x-voice/voice.py find                       # where is it, what is empty
python3 skills/x-voice/voice.py init                       # create it if missing
python3 skills/x-voice/voice.py init --posts my-posts.txt  # add your real posts
```

Where it is saved, and the order the skills look in:

| Order | Location | Used |
| --- | --- | --- |
| 1 | `voice.md` in the current folder | for that project only |
| 2 | macOS / Linux: `~/.x-agent-skill/voice.md` <br> Windows: `C:\Users\<you>\.x-agent-skill\voice.md` | everywhere (the default) |

`init` creates the global one (2). Add `--here` to create a per-project one
(1) instead. It never overwrites an existing file.

### Manual (if you prefer)

Copy the template yourself and fill it in with any text editor.

After `npx skills add`, the template is installed with the x-voice skill:

```bash
# macOS / Linux
mkdir -p ~/.x-agent-skill
cp ~/.claude/skills/x-voice/voice-template.md ~/.x-agent-skill/voice.md
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force "$HOME\.x-agent-skill" | Out-Null
Copy-Item "$HOME\.claude\skills\x-voice\voice-template.md" "$HOME\.x-agent-skill\voice.md"
```

```bat
:: Windows Command Prompt
mkdir "%USERPROFILE%\.x-agent-skill"
copy "%USERPROFILE%\.claude\skills\x-voice\voice-template.md" "%USERPROFILE%\.x-agent-skill\voice.md"
```

From a clone of this repo, for a per-project file:

```bash
cp x-agent-skill/skills/x-voice/voice-template.md ./voice.md
```

`voice.md` is listed in `.gitignore`, so a per-project copy is not committed
by accident. A filled example for a fictional creator is in
[examples/voice.md](examples/voice.md).

## Script reference

Every script has `--help`, reads a file or stdin, prints readable text, and
accepts `--json`. Where an example says `--voice voice.md`, use the path that
`python3 skills/x-voice/voice.py find` prints.

| Script | Example | What it prints |
| --- | --- | --- |
| `x-post/lint.py` | `python3 skills/x-post/lint.py drafts.txt --voice voice.md` | X character count (URLs = 23, emoji = 2, max 280), hashtags, lines, first-100-character check, hook, question/CTA and all-caps warnings, voice.md checks. Exit code 1 if a draft is over the limit. |
| `x-post/hookscore.py` | `python3 skills/x-post/hookscore.py hooks.txt` | Ranked table, 0 to 100 from five 0-20 scores, with a one-line reason for each |
| `x-thread/beats.py` | `python3 skills/x-thread/beats.py essay.txt` | Thread split at sentence boundaries, numbered 1/n, flags, reading time |
| `x-human/humanize.py` | `python3 skills/x-human/humanize.py draft.txt -o clean.txt --report` | Cleaned text and a change report; `--apply` makes safe phrase swaps |
| `x-human/detect.py` | `python3 skills/x-human/detect.py draft.txt clean.txt` | Five heuristic checks, before and after |
| `x-viral/swipe.py` | `python3 skills/x-viral/swipe.py posts.tsv --md swipe.md` | Posts ranked by multiple of author median, hook types, patterns |
| `x-trending/angles.py` | `python3 skills/x-trending/angles.py trending.txt --voice voice.md` | Relevance scores, risk flags, angle prompts |
| `x-stats/stats.py` | `python3 skills/x-stats/stats.py posts.csv` | Engagement rate, ranking, medians, best and worst, top-vs-rest findings |
| `x-profile/audit.py` | `python3 skills/x-profile/audit.py profile.txt --voice voice.md` | Rubric score per check and the top 3 fixes |
| `x-voice/voice.py` | `python3 skills/x-voice/voice.py init --posts my-posts.txt` | Where your voice.md is, which sections are empty; creates it if missing |
| `x-stats/fetch_api.py` | `python3 skills/x-stats/fetch_api.py trends --woeid 1` | Optional, see below. Dry run unless `--live` |

[examples/](examples/) has a sample input and the real output for every
script.

## X's rules, and why the human stays in the loop

X's Terms of Service prohibit scraping or crawling without X's written
consent, and its automation rules restrict automated posting, liking,
following, replying and messaging. These skills are built to stay clear of
all of that:

- No skill logs in, scrapes, drives a browser, or calls X except the optional
  API script, which only reads, through X's official API, with your own key.
- No skill posts or engages. You copy the text and publish it yourself.
- The research skills work on data you collect by browsing X normally.

Do not use these skills for mass replies, engagement pods, duplicate
content across accounts, or anything else X's rules forbid. Read X's Terms of
Service, Rules and Developer Agreement yourself; this README is not legal
advice.

## The optional API script

`skills/x-stats/fetch_api.py` is separate from everything else and **off by
default**.

- **What it does:** two read-only X API v2 lookups. One is trending topics
  for a location (`GET /2/trends/by/woeid/:woeid`). The other is
  `public_metrics` (views, likes, reposts, replies, bookmarks, quotes) for
  post IDs or URLs you give it (`GET /2/tweets`).
- **Off by default:** without `--live` it prints the exact request it would
  make and exits. With `--live` it sends one request (one per 100 post IDs).
- **What it needs:** an X developer account, an app, and its Bearer token in
  the `X_BEARER_TOKEN` environment variable. The token is never printed or
  written to disk. Do not commit it; `.env` files are git-ignored.
- **Cost and access:** API access tiers, limits and pricing are set by X and
  change. Check the X developer portal before using `--live`, and assume each
  call counts against your plan.
- **Errors:** 401, 403 and 429 stop the script with a plain explanation
  (including the rate-limit reset time when X sends it). There are no retry
  loops.

```bash
export X_BEARER_TOKEN=...            # PowerShell: $env:X_BEARER_TOKEN = "..."
python3 skills/x-stats/fetch_api.py trends --woeid 1 --live --json > trends.json
python3 skills/x-trending/angles.py trends.json --voice voice.md
python3 skills/x-stats/fetch_api.py metrics --ids-file ids.txt --live --tsv > posts.tsv
python3 skills/x-stats/stats.py posts.tsv
```

It is the only file in the repo with network code. To check:

```bash
grep -rnE "^\s*(import|from)\s+(urllib|http|requests|socket)" skills/
```

## Privacy

Everything runs on your machine, and there is no telemetry. The scripts read
the files you point them at and print to your terminal. Your global
`voice.md` lives in `~/.x-agent-skill/`, outside any repo. A per-project
`voice.md`, and `drafts/` and `data/` folders, are git-ignored by default.

## Limits

- **Character counts** follow X's published counting rules (weighted
  characters, URLs count 23, emoji count 2). They are tested on common cases,
  but rare scripts or brand-new emoji may differ by a character or two. X's
  composer has the final word.
- **Heuristics:** `hookscore.py`, `detect.py`, `audit.py` and the patterns in
  `swipe.py` and `stats.py` are transparent heuristics. They are tuned for
  English. For Hindi and Hinglish, character counting works but the phrase
  lists do not.
- **Small samples:** patterns from a few dozen posts are leads to test, not
  rules.
- **Keyword matching:** `angles.py` misses synonyms, and its risk lists catch
  obvious cases, not every case. The skill tells the agent to read the list
  by eye as well.

## Repo layout

```
x-agent-skill/
├── README.md
├── LICENSE
├── .gitignore
├── skills/
│   ├── x-post/        SKILL.md, lint.py, hooks.json, hookscore.py
│   ├── x-thread/      SKILL.md, beats.py
│   ├── x-human/       SKILL.md, slop.json, humanize.py, detect.py
│   ├── x-viral/       SKILL.md, swipe.py
│   ├── x-trending/    SKILL.md, angles.py
│   ├── x-stats/       SKILL.md, stats.py, fetch_api.py (optional)
│   ├── x-profile/     SKILL.md, rubric.json, audit.py
│   ├── x-reply/       SKILL.md
│   ├── x-plan/        SKILL.md
│   └── x-voice/       SKILL.md, voice.py, voice-template.md
└── examples/          sample inputs and outputs for every script
```

## Contributing

- Scripts: Python 3.9+, standard library only, no network calls (except
  `fetch_api.py`), `--help`, file or stdin input, `--json` output.
- `SKILL.md`: frontmatter with only `name` (matching the folder) and
  `description`, no tool-specific instructions, under 150 lines.
- `hooks.json`, `slop.json` and `rubric.json` are data. Improving them is the
  easiest way to help.
- Never add numbers to examples or docs that look like real data about real
  accounts.

## Credits

The structure is modeled on
[instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill).
All content here is written for X.

## License

MIT. See [LICENSE](LICENSE).
