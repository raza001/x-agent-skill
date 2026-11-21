# Examples

A sample input and the real output for every script. All accounts, posts,
IDs and numbers here are made up for demonstration; they are not data about
real people. The creator in `voice.md` is fictional.

Run any of these from the repo root to reproduce the `.out.txt` files. On
Windows, use `python` instead of `python3`.

| Script | Input | Command | Output |
| --- | --- | --- | --- |
| lint.py | `x-post/drafts.txt` | `python3 skills/x-post/lint.py examples/x-post/drafts.txt --voice examples/voice.md` | `x-post/lint.out.txt` |
| hookscore.py | `x-post/hooks.txt` | `python3 skills/x-post/hookscore.py examples/x-post/hooks.txt` | `x-post/hookscore.out.txt` |
| beats.py (split) | `x-thread/essay.txt` | `python3 skills/x-thread/beats.py examples/x-thread/essay.txt` | `x-thread/beats-essay.out.txt` |
| beats.py (check) | `x-thread/thread.txt` | `python3 skills/x-thread/beats.py examples/x-thread/thread.txt --number prefix` | `x-thread/beats-thread.out.txt` |
| humanize.py | `x-human/ai-draft.txt` | `python3 skills/x-human/humanize.py examples/x-human/ai-draft.txt -o examples/x-human/ai-draft.clean.txt --apply --report` | `x-human/humanize.out.txt`, `x-human/ai-draft.clean.txt` |
| detect.py | `x-human/ai-draft.txt` | `python3 skills/x-human/detect.py examples/x-human/ai-draft.txt` | `x-human/detect.out.txt` |
| detect.py (compare) | `ai-draft.txt` and `ai-draft.rewrite.txt` | `python3 skills/x-human/detect.py examples/x-human/ai-draft.txt examples/x-human/ai-draft.rewrite.txt` | `x-human/detect-compare.out.txt` |
| swipe.py | `x-viral/posts.tsv` | `python3 skills/x-viral/swipe.py examples/x-viral/posts.tsv --md examples/x-viral/swipe.md` | `x-viral/swipe.out.txt`, `x-viral/swipe.md` |
| angles.py | `x-trending/trending.txt` | `python3 skills/x-trending/angles.py examples/x-trending/trending.txt --voice examples/voice.md` | `x-trending/angles.out.txt` |
| stats.py | `x-stats/posts.csv` | `python3 skills/x-stats/stats.py examples/x-stats/posts.csv` | `x-stats/stats.out.txt` |
| fetch_api.py (dry run) | `x-stats/post-ids.txt` | `python3 skills/x-stats/fetch_api.py metrics --ids-file examples/x-stats/post-ids.txt` | `x-stats/fetch_api-dryrun.out.txt` |
| audit.py | `x-profile/profile.txt` | `python3 skills/x-profile/audit.py examples/x-profile/profile.txt --voice examples/voice.md --today 2026-11-21` | `x-profile/audit.out.txt` |

Notes:

- `x-human/ai-draft.txt` deliberately contains invisible characters (a BOM,
  a zero-width space, a soft hyphen, a word joiner and a no-break space). It
  also contains a joiner inside an emoji and one inside a Devanagari word,
  which humanize.py must keep.
- `x-human/ai-draft.rewrite.txt` is a hand rewrite. It shows the step the
  script cannot do: structural tells need a person.
- `x-viral/posts.tsv` writes line breaks inside posts as `\n`, which is the
  documented format.
- `fetch_api-dryrun.out.txt` was made without `--live`, so no request was
  sent.
