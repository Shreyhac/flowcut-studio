#!/usr/bin/env python3
"""
ig-autodm — ManyChat-style keyword -> auto-DM for your own Instagram account.

When someone comments a keyword (e.g. "SEND") on your recent posts/reels,
this sends them a private DM ("private reply") with the content you set.
Runs entirely on your machine. No third-party service.

Uses the Instagram API with Instagram Login (graph.instagram.com) — no
Facebook Page required. See README.md for one-time setup + how to get a token.

Meta rules this respects:
  - one DM per comment, ever
  - only within 7 days of the comment
  - DMs to people who don't follow you land in their Message Requests

Usage:
    python3 autodm.py whoami                # verify token + print account
    python3 autodm.py list-comments         # show recent comments (no sending)
    python3 autodm.py run --dry-run         # match keywords, print, send nothing
    python3 autodm.py run                    # one pass: match + send DMs
    python3 autodm.py run --loop --interval 300   # poll forever, every 5 min
    python3 autodm.py refresh-token          # extend the 60-day token
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib import request as urlrequest, parse as urlparse, error as urlerror

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
STATE_PATH = os.path.join(HERE, "state.json")
BASE = "https://graph.instagram.com"


# ----------------------------- config / state -----------------------------

def load_config():
    if not os.path.exists(CONFIG_PATH):
        die(f"No config.json found.\n"
            f"  cp {os.path.join(HERE, 'config.example.json')} {CONFIG_PATH}\n"
            f"then fill in your token, ig_user_id, keywords and reply_message.")
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    for req in ("access_token", "ig_user_id", "keywords", "reply_message"):
        if not cfg.get(req):
            die(f"config.json is missing '{req}'.")
    cfg.setdefault("graph_version", "")          # e.g. "v23.0"; blank = unversioned
    cfg.setdefault("app_secret", "")
    cfg.setdefault("public_ack", False)
    cfg.setdefault("public_ack_message", "Just sent you a DM! \U0001F4E9")
    cfg.setdefault("media_lookback", 25)
    cfg.setdefault("comments_per_media", 100)
    cfg.setdefault("once_per_user", False)
    cfg.setdefault("send_delay_seconds", 2)
    cfg["keywords"] = [k.strip().lower() for k in cfg["keywords"] if k.strip()]
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            s = json.load(f)
    else:
        s = {}
    s.setdefault("replied_comment_ids", [])
    s.setdefault("messaged_usernames", [])
    return s


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ------------------------------- http helper -------------------------------

def api_url(cfg, path):
    ver = cfg.get("graph_version") or ""
    prefix = f"/{ver}" if ver else ""
    return f"{BASE}{prefix}/{path.lstrip('/')}"


def api_get(cfg, path, params=None):
    params = dict(params or {})
    params["access_token"] = cfg["access_token"]
    url = api_url(cfg, path) + "?" + urlparse.urlencode(params)
    return _request(url, method="GET")


def api_post(cfg, path, payload):
    url = api_url(cfg, path) + "?" + urlparse.urlencode({"access_token": cfg["access_token"]})
    data = json.dumps(payload).encode("utf-8")
    return _request(url, method="POST", data=data,
                    headers={"Content-Type": "application/json"})


def _request(url, method="GET", data=None, headers=None):
    req = urlrequest.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body).get("error", {})
            msg = err.get("message", body)
            code = err.get("code", e.code)
            raise ApiError(f"[{code}] {msg}")
        except (ValueError, AttributeError):
            raise ApiError(f"[{e.code}] {body}")
    except urlerror.URLError as e:
        raise ApiError(f"network error: {e.reason}")


class ApiError(Exception):
    pass


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ------------------------------- core logic --------------------------------

def get_account(cfg):
    return api_get(cfg, cfg["ig_user_id"], {"fields": "id,username,account_type"})


def get_recent_media(cfg):
    res = api_get(cfg, f'{cfg["ig_user_id"]}/media',
                  {"fields": "id,caption,media_type,timestamp,permalink",
                   "limit": cfg["media_lookback"]})
    return res.get("data", [])


def get_comments(cfg, media_id):
    res = api_get(cfg, f"{media_id}/comments",
                  {"fields": "id,text,username,timestamp",
                   "limit": cfg["comments_per_media"]})
    return res.get("data", [])


def send_private_reply(cfg, comment_id, text):
    return api_post(cfg, f'{cfg["ig_user_id"]}/messages',
                    {"recipient": {"comment_id": comment_id},
                     "message": {"text": text}})


def send_public_reply(cfg, comment_id, text):
    return api_post(cfg, f"{comment_id}/replies", {"message": text})


def parse_ts(ts):
    # Instagram returns e.g. "2026-07-12T10:20:30+0000"
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(ts, fmt)
        except (ValueError, TypeError):
            continue
    return None


def matches_keyword(text, keywords):
    low = (text or "").lower()
    return any(kw in low for kw in keywords)


def run_pass(cfg, state, dry_run=False, own_username=None):
    keywords = cfg["keywords"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    replied = set(state["replied_comment_ids"])
    messaged_users = set(state["messaged_usernames"])

    sent = skipped = 0
    media = get_recent_media(cfg)
    print(f"Scanning {len(media)} media for keywords {keywords} ...")

    for m in media:
        try:
            comments = get_comments(cfg, m["id"])
        except ApiError as e:
            print(f"  ! could not read comments on {m['id']}: {e}")
            continue

        for c in comments:
            cid = c["id"]
            text = c.get("text", "")
            user = c.get("username", "")

            if cid in replied:
                continue
            if own_username and user == own_username:
                continue  # our own comment
            if not matches_keyword(text, keywords):
                continue

            ts = parse_ts(c.get("timestamp", ""))
            if ts and ts < cutoff:
                skipped += 1
                continue  # outside the 7-day private-reply window
            if cfg["once_per_user"] and user in messaged_users:
                replied.add(cid)          # mark handled so we don't re-check
                continue

            label = f"@{user}: {text[:60].strip()!r}"
            if dry_run:
                print(f"  WOULD DM -> {label}")
                sent += 1
                continue

            try:
                send_private_reply(cfg, cid, cfg["reply_message"])
                print(f"  DM sent  -> {label}")
                sent += 1
                replied.add(cid)
                messaged_users.add(user)
                if cfg["public_ack"] and cfg["public_ack_message"]:
                    try:
                        send_public_reply(cfg, cid, cfg["public_ack_message"])
                    except ApiError as e:
                        print(f"      (public ack failed: {e})")
                time.sleep(cfg["send_delay_seconds"])
            except ApiError as e:
                print(f"  ! DM FAILED -> {label}  ({e})")
                # Mark as handled if it's a permanent per-comment error so we
                # don't hammer it every pass. 'already sent' -> treat as done.
                if "already" in str(e).lower():
                    replied.add(cid)

    if not dry_run:
        state["replied_comment_ids"] = sorted(replied)
        state["messaged_usernames"] = sorted(messaged_users)
        save_state(state)

    print(f"Done. {'matched' if dry_run else 'sent'}={sent}, "
          f"skipped(>7d)={skipped}")
    return sent


# ------------------------------- token tools -------------------------------

def refresh_token(cfg):
    url = f"{BASE}/refresh_access_token?" + urlparse.urlencode({
        "grant_type": "ig_refresh_token",
        "access_token": cfg["access_token"],
    })
    res = _request(url)
    cfg["access_token"] = res["access_token"]
    save_config(cfg)
    days = int(res.get("expires_in", 0)) // 86400
    print(f"Token refreshed. Valid ~{days} more days.")


# --------------------------------- cli ------------------------------------

def cmd_whoami(cfg, args):
    acct = get_account(cfg)
    print(json.dumps(acct, indent=2))


def cmd_list_comments(cfg, args):
    for m in get_recent_media(cfg):
        cs = get_comments(cfg, m["id"])
        head = (m.get("caption") or "").split("\n")[0][:50]
        print(f"\n# {m['media_type']}  {m.get('timestamp','')}  {head!r}  ({len(cs)} comments)")
        for c in cs:
            hit = "  <== keyword" if matches_keyword(c.get("text",""), cfg["keywords"]) else ""
            print(f"   @{c.get('username','?')}: {c.get('text','')[:70]!r}{hit}")


def cmd_run(cfg, args):
    state = load_state()
    try:
        own = get_account(cfg).get("username")
    except ApiError:
        own = None
    if args.loop:
        print(f"Looping every {args.interval}s. Ctrl-C to stop.")
        while True:
            try:
                run_pass(cfg, state, dry_run=args.dry_run, own_username=own)
            except ApiError as e:
                print(f"pass error: {e}")
            time.sleep(args.interval)
    else:
        run_pass(cfg, state, dry_run=args.dry_run, own_username=own)


def cmd_refresh(cfg, args):
    refresh_token(cfg)


def main():
    p = argparse.ArgumentParser(description="Instagram keyword -> auto-DM (local).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    sub.add_parser("list-comments").set_defaults(func=cmd_list_comments)
    sub.add_parser("refresh-token").set_defaults(func=cmd_refresh)

    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true", help="match + print, send nothing")
    r.add_argument("--loop", action="store_true", help="keep polling on an interval")
    r.add_argument("--interval", type=int, default=300, help="loop interval seconds")
    r.set_defaults(func=cmd_run)

    args = p.parse_args()
    cfg = load_config()
    try:
        args.func(cfg, args)
    except ApiError as e:
        die(str(e))


if __name__ == "__main__":
    main()
