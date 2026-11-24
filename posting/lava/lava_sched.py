#!/usr/bin/env python3
"""Which Lava post is due (13 Nov 2026). Pure functions on the queue and the post log, so they can be tested on temp
copies without the phone. lava_forever.py calls post_step() before every warm-up session.

Owner rules:
  - nothing posts while lava/POST_STOP exists; only items with "approved": true (Shreyansh sets them)
  - at least 1 hour between two posts on the same account; different accounts may post back to back (owner, 13 Nov 19:30)
  - every template goes on every account (the queue has one item per template x account)
  - an item that went live is never posted again; a failure before posting is retried at most 3 times
  - NOT LIVE (posted, not verified) is never retried automatically: lava_forever puts POST_STOP back
"""
import datetime, json, os
from zoneinfo import ZoneInfo
import lava_plan

HERE = os.path.dirname(os.path.abspath(__file__))
ACCOUNT_GAP = 3600
PHONE_GAP = 0         # owner 13 Nov 19:30: no phone-wide gap, only the 1 h per account
MAX_TRIES = 3
HUMAN = True          # owner 14 Nov: posts only in the account's local evening, at most 1 per account per local day
POST_WINDOW = (18.0, 23.0)
MAX_PER_DAY = 1
IG_VIA_EDITS = True  # owner 13 Nov 19:35: Lava Instagram posts go through the Edits app (dry run passed 14 Nov 13:55)


def load_posts(path):
    if not os.path.exists(path): return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _ts(r): return datetime.datetime.fromisoformat(r["ts"]).timestamp()


def _local(key, t): return datetime.datetime.fromtimestamp(t, ZoneInfo(lava_plan.TZ[key]))


def human_ok(key, tapped, now):
    """Owner 14 Nov: the account's local evening only, and at most MAX_PER_DAY posts on its local day."""
    if not HUMAN: return True
    loc = _local(key, now); h = loc.hour + loc.minute / 60
    if not (POST_WINDOW[0] <= h < POST_WINDOW[1]): return False
    return sum(1 for r in tapped if r["key"] == key and _local(key, _ts(r)).date() == loc.date()) < MAX_PER_DAY


def _post_stopped():   # 18 Nov owner: no posting on accounts in ~/masonry-tools/POST_STOP_ACCOUNTS.txt (best video < 700)
    try: return {l.strip() for l in open(__import__("os").path.expanduser("~/masonry-tools/POST_STOP_ACCOUNTS.txt")) if l.strip() and not l.startswith("#")}
    except FileNotFoundError: return set()

def pick(items, posts, now, only=None):
    """The approved item that may post now, or None. A post = an attempt that reached Post/Share (live or NOT LIVE);
    plain failures happened before posting, so they don't start a gap."""
    tapped = [r for r in posts if r.get("status") in ("live", "NOT LIVE")]
    if tapped and now - max(_ts(r) for r in tapped) < PHONE_GAP: return None
    last_acct = {}
    for r in tapped: last_acct[r["key"]] = max(last_acct.get(r["key"], 0), _ts(r))
    due = []
    for i, it in enumerate(items):
        mine = [r for r in posts if r.get("id") == it["id"]]
        if not it.get("approved"): continue
        if it.get("handle") in _post_stopped(): continue
        if only and it["key"] != only: continue
        if not human_ok(it["key"], tapped, now): continue
        if it.get("app") == "instagram" and not IG_VIA_EDITS: continue        # held: not through Edits yet
        if any(r.get("status") in ("live", "NOT LIVE") for r in mine): continue      # done, or waiting for a human
        if sum(1 for r in mine if r.get("status") == "failed") >= MAX_TRIES: continue
        if now - last_acct.get(it["key"], 0) < ACCOUNT_GAP: continue
        due.append((last_acct.get(it["key"], 0), i, it))                              # longest-idle account first
    return min(due, key=lambda x: x[:2])[2] if due else None


def post_step(log, run_post, stop_f=None, queue_f=None, posts_f=None, now=None, only=None):
    """One posting turn for lava_forever. run_post(item) -> exit code of lava_post.py (0 live, 2 NOT LIVE, 1 failed).
    Returns what happened (for the log and the tests)."""
    stop_f = stop_f or os.path.join(HERE, "POST_STOP")
    queue_f = queue_f or os.path.join(HERE, "post_queue.json")
    posts_f = posts_f or os.path.join(HERE, "lava_posts.jsonl")
    if os.path.exists(stop_f):
        log("posting: lava/POST_STOP is there - no posts"); return "stopped"
    items = json.load(open(queue_f, encoding="utf-8"))["items"]
    it = pick(items, load_posts(posts_f), now if now is not None else datetime.datetime.now().timestamp(), only)
    if not it:
        log(f"posting: nothing due ({sum(1 for i in items if i.get('approved'))} of {len(items)} approved)"); return "none"
    log(f"posting: {it['id']} -> @{it['handle']}")
    code = run_post(it)
    if code == 2:
        open(stop_f, "w").write(f"NOT LIVE: {it['id']} at {datetime.datetime.now():%Y-%m-%d %H:%M} - check @{it['handle']} by hand\n")
        log(f"posting: {it['id']} NOT LIVE - lava/POST_STOP put back"); return "notlive"
    log(f"posting: {it['id']} {'live' if code == 0 else 'failed (retried later)'}")
    return "live" if code == 0 else "failed"
