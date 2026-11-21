#!/usr/bin/env python3
"""fetch_api.py - OPTIONAL. Read-only X API v2 lookups. Off by default.

This is the only script in the repo that touches the network, and only when
you pass --live. Without --live it prints the request it would make and
exits, so you can check it first.

  trends   GET /2/trends/by/woeid/:woeid   trending topics for a location
  metrics  GET /2/tweets?ids=...           public_metrics for post IDs you give

Needs an X API Bearer token in the environment variable X_BEARER_TOKEN. The
token is never printed, logged or written to disk. 401, 403 and 429 responses
stop the script with a plain message; there are no retries.

API access, tiers and pricing are set by X and change over time. Check the X
developer portal before you use this, and expect each --live call to count
against your plan. It reads only; it cannot post, like, follow, reply or DM.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEFAULT_BASE = "https://api.x.com/2"
TOKEN_ENV = "X_BEARER_TOKEN"
USER_AGENT = "x-agent-skill-fetch/0.1"
TIMEOUT = 20


class ApiError(Exception):
    pass


def token_status():
    return "set" if os.environ.get(TOKEN_ENV, "").strip() else "NOT set"


def get_token():
    tok = os.environ.get(TOKEN_ENV, "").strip()
    if not tok:
        raise ApiError("%s is not set. Create a Bearer token in the X developer portal, then:\n"
                       "  macOS/Linux:  export %s=...\n"
                       "  PowerShell:   $env:%s = \"...\"\n"
                       "Never paste the token into a file in this repo." % (TOKEN_ENV, TOKEN_ENV, TOKEN_ENV))
    return tok


def reset_time(headers):
    raw = headers.get("x-rate-limit-reset") if headers else None
    if raw and raw.isdigit():
        return datetime.fromtimestamp(int(raw), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return None


def api_detail(body):
    try:
        data = json.loads(body)
    except ValueError:
        return body.strip()[:200]
    parts = [str(data.get(k)) for k in ("title", "detail") if data.get(k)]
    if not parts and isinstance(data.get("errors"), list) and data["errors"]:
        parts = [str(data["errors"][0].get("message", ""))]
    return " - ".join(parts)[:300]


def http_get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if e.fp else ""
        detail = api_detail(body)
        if e.code == 401:
            msg = ("401 Unauthorized: X rejected the token. Check that %s holds a valid app "
                   "Bearer token (not an API key or secret) and has not been regenerated." % TOKEN_ENV)
        elif e.code == 403:
            msg = ("403 Forbidden: this token's access level may not include this endpoint, or the "
                   "app is not attached to a project. Check your plan in the X developer portal.")
        elif e.code == 429:
            when = reset_time(e.headers)
            msg = ("429 Too Many Requests: rate limit or usage cap reached.%s Not retrying."
                   % (" The limit resets at %s." % when if when else ""))
        else:
            msg = "HTTP %d from the X API." % e.code
        raise ApiError(msg + ("\n  API said: %s" % detail if detail else ""))
    except urllib.error.URLError as e:
        raise ApiError("Network error: %s" % getattr(e, "reason", e))
    except ValueError:
        raise ApiError("The API returned something that is not JSON.")


def trends_url(base, woeid, max_trends):
    q = urllib.parse.urlencode({"max_trends": max_trends, "trend.fields": "trend_name,tweet_count"})
    return "%s/trends/by/woeid/%d?%s" % (base.rstrip("/"), woeid, q)


def metrics_urls(base, ids):
    urls = []
    for i in range(0, len(ids), 100):  # the endpoint takes up to 100 IDs per request
        q = urllib.parse.urlencode({"ids": ",".join(ids[i:i + 100]),
                                    "tweet.fields": "public_metrics,created_at,text"})
        urls.append("%s/tweets?%s" % (base.rstrip("/"), q))
    return urls


def extract_ids(values):
    ids = []
    for v in values:
        for m in re.finditer(r"(?:status(?:es)?/)?(\d{5,25})", v):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    return ids


def dry_run(urls):
    print("DRY RUN: no network call was made. Add --live to send %s." %
          ("this request" if len(urls) == 1 else "these %d requests" % len(urls)))
    for u in urls:
        print("  GET %s" % u)
    print("  Authorization: Bearer <%s from the environment, currently %s>" % (TOKEN_ENV, token_status()))
    print("Check API access and pricing in the X developer portal before using --live.")


def cmd_trends(args):
    url = trends_url(args.base_url, args.woeid, args.max)
    if not args.live:
        dry_run([url])
        return 0
    data = http_get(url, get_token())
    trends = [{"name": t.get("trend_name"), "post_count": t.get("tweet_count")}
              for t in data.get("data", []) if t.get("trend_name")]
    if args.json:
        print(json.dumps({"woeid": args.woeid, "trends": trends}, ensure_ascii=False, indent=2))
    else:
        if not trends:
            print("No trends returned for WOEID %d." % args.woeid)
        for i, t in enumerate(trends, 1):
            count = "{:,} posts".format(t["post_count"]) if isinstance(t["post_count"], int) else "count not given"
            print("%2d. %s  (%s)" % (i, t["name"], count))
    return 0


def cmd_metrics(args):
    values = list(args.ids or [])
    if args.ids_file:
        try:
            with open(args.ids_file, encoding="utf-8-sig") as f:
                values += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        except OSError as e:
            raise ApiError("cannot read %s: %s" % (args.ids_file, e.strerror))
    ids = extract_ids(values)
    if not ids:
        raise ApiError("no post IDs found. Pass --ids 123,456 or --ids-file with IDs or post URLs.")
    urls = metrics_urls(args.base_url, ids)
    if not args.live:
        dry_run(urls)
        return 0
    token = get_token()
    rows, notes = [], []
    for u in urls:  # one request per 100 IDs; any error stops the run
        data = http_get(u, token)
        for t in data.get("data", []):
            pm = t.get("public_metrics", {})
            rows.append({
                "url": "https://x.com/i/web/status/%s" % t.get("id"),
                "text": (t.get("text") or "").replace("\r", ""),
                "views": pm.get("impression_count"),
                "likes": pm.get("like_count"),
                "reposts": pm.get("retweet_count"),
                "replies": pm.get("reply_count"),
                "bookmarks": pm.get("bookmark_count"),
                "quotes": pm.get("quote_count"),
                "date": t.get("created_at"),
            })
        for err in data.get("errors", []):
            notes.append("%s: %s" % (err.get("value") or err.get("resource_id") or "?",
                                     err.get("detail") or err.get("title") or "error"))
    if args.json:
        print(json.dumps({"posts": rows, "errors": notes}, ensure_ascii=False, indent=2))
    elif args.tsv:
        cols = ["url", "text", "views", "likes", "reposts", "replies", "bookmarks", "quotes", "date"]
        w = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r[c] is None else (r[c].replace("\n", "\\n") if c == "text" else r[c])
                        for c in cols])
    else:
        for r in rows:
            print("%s\n  views %s  likes %s  reposts %s  replies %s  bookmarks %s  %s" % (
                r["url"], *["-" if r[k] is None else r[k] for k in ("views", "likes", "reposts", "replies", "bookmarks")],
                r["date"] or ""))
        if any(r["views"] is None for r in rows):
            print("note: views (impression_count) were not returned for some posts; left blank.")
    for n in notes:
        print("not returned: %s" % n, file=sys.stderr)
    return 0


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="OPTIONAL, read-only X API v2 lookups (trends by WOEID, public_metrics for post "
                    "IDs). Off by default: without --live it only prints the request. Needs the "
                    "X_BEARER_TOKEN environment variable; the token is never printed.",
        epilog="API access and pricing are set by X and change. Check the X developer portal first.\n"
               "Errors 401/403/429 stop the run with a message. There are no retries.\n\n"
               "examples:\n"
               "  python3 fetch_api.py trends --woeid 1                  # dry run, no network\n"
               "  python3 fetch_api.py trends --woeid 23424848 --live --json > trends.json\n"
               "  python3 fetch_api.py metrics --ids-file ids.txt --live --tsv > posts.tsv\n"
               "  python3 stats.py posts.tsv\n\n"
               "WOEIDs: 1 = worldwide, 23424848 = India, 23424977 = United States.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--base-url", default=DEFAULT_BASE, help="API base URL (default %s)" % DEFAULT_BASE)
    sub = ap.add_subparsers(dest="cmd")

    t = sub.add_parser("trends", help="trending topics for a WOEID location")
    t.add_argument("--woeid", type=int, required=True, help="Yahoo WOEID, e.g. 1 for worldwide")
    t.add_argument("--max", type=int, default=20, help="max trends to request (default 20)")
    t.add_argument("--live", action="store_true", help="actually call the API (uses your quota)")
    t.add_argument("--json", action="store_true", help="print JSON (angles.py reads this)")

    m = sub.add_parser("metrics", help="public_metrics for post IDs or URLs")
    m.add_argument("--ids", type=lambda s: [x for x in re.split(r"[,\s]+", s) if x],
                   help="comma-separated post IDs or URLs")
    m.add_argument("--ids-file", metavar="PATH", help="file with one post ID or URL per line")
    m.add_argument("--live", action="store_true", help="actually call the API (uses your quota)")
    out = m.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true", help="print JSON")
    out.add_argument("--tsv", action="store_true", help="print a TSV that stats.py reads")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2
    try:
        return cmd_trends(args) if args.cmd == "trends" else cmd_metrics(args)
    except ApiError as e:
        print("fetch_api.py: %s" % e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
