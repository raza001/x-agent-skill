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

- 9 skills. Each is a set of instructions an agent follows, plus small Python
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

Requires Python 3.9 or newer. On Windows, use `python` or `py -3` wherever
the docs say `python3`.

Clone the repo, then copy **all** the skill folders into your tool's skills
folder. Keep them together: `x-viral` and `x-stats` read
`x-post/hooks.json`, and other skills hand off to each other.

```bash
git clone https://github.com/raza001/x-agent-skill.git
```

| Tool | Personal skills folder | Copy command (macOS/Linux) |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `cp -r x-agent-skill/skills/* ~/.claude/skills/` |
| OpenAI Codex CLI | `~/.codex/skills/` | `cp -r x-agent-skill/skills/* ~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `cp -r x-agent-skill/skills/* ~/.gemini/skills/` |
| Cursor | `~/.cursor/skills/` | `cp -r x-agent-skill/skills/* ~/.cursor/skills/` |
| GitHub Copilot | `.github/skills/` inside a repository | `cp -r x-agent-skill/skills/* .github/skills/` |

Or with the `skills` CLI:

```bash
npx skills add raza001/x-agent-skill
```

On Windows (PowerShell), for example for Claude Code:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force x-agent-skill\skills\* "$HOME\.claude\skills\"
```

Skill folder locations and support differ between tools and change between
versions. If a tool does not pick the skills up, check its documentation for
the current path, and restart it after copying. Claude Code also accepts
project-level skills in `.claude/skills/`.

Commands inside each `SKILL.md` use paths from the repo root (for example
`python3 skills/x-post/lint.py draft.txt`). When the skills are installed
elsewhere, the agent runs the same script from the installed folder.

## Set up your voice

Every skill reads `voice.md` before it writes anything.

```bash
cp x-agent-skill/templates/voice.md ./voice.md
```

Fill it in: niche, audience, tone (3 adjectives), words you use, words you
never use, 3 to 5 of your real posts, topics to avoid, emoji and hashtag
policy, language (English, Hindi or Hinglish) and call-to-action style. Keep
it in the folder you run your agent from. `voice.md` is listed in
`.gitignore`, so your filled-in copy is not committed by accident.

If `voice.md` is missing, each skill asks you to create it, or offers to
draft one from 3 of your posts for you to confirm. A filled example for a
fictional creator is in [examples/voice.md](examples/voice.md).

## Script reference

Every script has `--help`, reads a file or stdin, prints readable text, and
accepts `--json`.

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
the files you point them at and print to your terminal. Your `voice.md`, and
`drafts/` and `data/` folders, are git-ignored by default.

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
├── templates/voice.md
├── skills/
│   ├── x-post/        SKILL.md, lint.py, hooks.json, hookscore.py
│   ├── x-thread/      SKILL.md, beats.py
│   ├── x-human/       SKILL.md, slop.json, humanize.py, detect.py
│   ├── x-viral/       SKILL.md, swipe.py
│   ├── x-trending/    SKILL.md, angles.py
│   ├── x-stats/       SKILL.md, stats.py, fetch_api.py (optional)
│   ├── x-profile/     SKILL.md, rubric.json, audit.py
│   ├── x-reply/       SKILL.md
│   └── x-plan/        SKILL.md
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
