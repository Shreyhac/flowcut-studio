#!/usr/bin/env python3
"""TikTok warm-up rotation on a real Android phone driven by PhoneDock.

Rotates accounts (one at a time), each session:
  - visits tracked competitor/prank creators (deep link to profile), watches 2-3 of
    their videos, likes ~15%, saves ~8%, follows a capped number per day
  - opens one partner/niche hashtag and watches a few videos
  - scrolls the For You feed for the rest of the session
Logs every video seen to seen.jsonl; state (follows, visited) in state.json.
Stops (exit 3) on CAPTCHA / verification / rate-limit screens, or if the VPN is down.

Usage: warmup.py --hours 3 --session-min 20 [--accounts maya,jake,ethan]
"""
import argparse, json, os, random, re, subprocess, sys, time, datetime

PD = "/Applications/PhoneDock.app/Contents/Resources/bin/phonedock"
# Two phones (11 Nov): TT_DEV picks the phone (default = Redmi A5). Coordinates written below are Redmi pixels (720x1640)
# and go through sx()/sy(); coordinates read from the UI are already in the phone's own pixels.
REDMI, REALME = "android-device:REDMI_SERIAL", "android-device:REALME_SERIAL"
DEV = os.environ.get("TT_DEV", REDMI)
LAVA = "android-device:LAVA_SERIAL"
ONEPLUS = "android-device:ONEPLUS_SERIAL"          # 18 Nov: OnePlus Nord CE 3 Lite (Emily @acct_105)
SIZE = {REDMI: (720, 1640), REALME: (1080, 2412), LAVA: (720, 1600), ONEPLUS: (1080, 2400)}.get(DEV, (720, 1640))
TAG = "" if DEV == REDMI else "_" + os.environ.get("TT_TAG", "realme")   # separate state + log per phone
def sx(x): return int(round(x * SIZE[0] / 720))
def sy(y): return int(round(y * SIZE[1] / 1640))
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = json.load(open(os.path.join(HERE, "seeds.json")))
STATE_F = os.path.join(HERE, f"state{TAG}.json")
SEEN_F = os.path.join(HERE, "seen.jsonl")
LOG_F = os.path.join(HERE, f"run{TAG}.log")

MAX_FOLLOWS_PER_DAY = 8      # per account
LIKE_P, SAVE_P, FOLLOW_P = 0.15, 0.08, 0.45
COMMENT_P, REPOST_P = 0.0, 0.0      # 12 Nov: the Lava controller turns these on (owner: like/comment/save/repost like a human)
COMMENTS_EN = ["this is actually so useful", "saving this for later", "wait this is genius", "ok trying this tonight", "how did I not know this", "the way this works 😭", "need this for my page", "this tip >>>", "lowkey game changer", "bookmarking this rn", "ok you convinced me", "so helpful thank you"]
MAX_FOLLOWS_PER_SESSION = 3
MIN_FOLLOW_GAP_S = 150
TABBAR = r'"Profile"[^\n]*@\(6\d\d,1[45]\d\d\)' if SIZE[0] == 720 else r'"Profile"[^\n]*@\((9\d\d|10\d\d),2[1-4]\d\d\)'   # bottom tab bar (TikTok A/B-tests the ids)
STOP_WORDS = re.compile(r"captcha|drag the slider|verify to continue|select all|"
                        r"too many (attempts|requests|tries)|you're tapping too fast|you.re going too fast|please try again later|"
                        r"suspicious|log in to tiktok|session expired|account was logged out", re.I)
DISMISS = ["Don’t allow", "Don't allow", "Not now", "Maybe later", "Cancel", "Skip", "Close", "Not interested", "OK"]


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG_F, "a") as f:
        f.write(line + "\n")


def pd(*a, timeout=60):
    try:
        return subprocess.run([PD, *a], capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def ui():
    return pd("ui", DEV, "--no-ocr")


def shell(*a):
    return pd("shell", DEV, "--", *a)


def tap(x, y):
    pd("tap", DEV, str(int(x)), str(int(y)))


def sleep(a, b=None):
    time.sleep(random.uniform(a, b) if b else a)


def load_state():
    try:
        return json.load(open(STATE_F))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(STATE_F, "w"), indent=1)


RELEVANT = {
    "maya": r"\bai\b|higgsfield|ugc|\bads?\b|chatgpt|heygen|eleven ?labs|canva|photoshoot|product photo|seedance|kling|\bveo\b|prompt|"
            r"generat|design|brand|ecommerce|e-commerce|krea|pippit|avatar|everygen|photoroom|picsart|midjourney|content creat|side hustle",
    "jake": r"\bai\b|website|\bapp\b|coding|\bcode\b|claude|lovable|replit|cursor|\bbuil[dt]|startup|saas|developer|chatgpt|vibe ?cod|"
            r"landing page|\bmcp\b|automation|no-?code|web design|prompt|agent",
    "ethan": r"prank|pranked|\bai\b|ai photo|text(ed|ing)? (my )?(mom|dad)|cantina|maybereal|fake photo|edited|photoshop|reaction",
}


class Stop(Exception):
    pass


def guard(t):
    """Stop on challenge screens; dismiss harmless pop-ups."""
    if STOP_WORDS.search(t):
        raise Stop("challenge/limit screen: " + STOP_WORDS.search(t).group(0))
    if '"Dialog"' in t or "Bottom sheet" in t or "Popup" in t:
        for w in DISMISS:
            if f'"{w}"' in t:
                pd("tap", DEV, "--text", w, "--match", "exact")
                sleep(1, 2)
                return True
    return False


def vpn_ok():
    out = shell("ip", "-o", "addr", "show")
    return "tun0" in out


def coords(t, pattern):
    m = re.search(pattern + r'[^\n]*?@\((\d+),(\d+)\)', t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def current_handle(t):
    # 11 Nov: TikTok 47.7 renamed every resource id (sr3 -> t92): match the profile header's "@handle" button by text only
    m = re.search(r'Button "@([\w.]+)" id=\w+', t)
    return m.group(1) if m else None


def name_button(t):
    """The display-name button above the @handle on the profile (opens the account switcher); id-independent."""
    m = re.search(r'Button "[^"@][^"]*" id=\w+ @\((\d+),(\d+)\)[^\n]*\n(?:[^\n]*\n){0,2}?[^\n]*Button "@[\w.]+" id=', t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def go_main():
    """Back out to a screen with the bottom tab bar (Home/Profile)."""
    for _ in range(3):
        t = ui()
        if re.search(TABBAR, t):
            return t
        guard(t)
        pd("key", DEV, "back"); sleep(1.5, 2.5)
    # stacked deep-link pages: restart the app to get back to the tab bar
    shell("am", "force-stop", "com.zhiliaoapp.musically"); sleep(2)
    pd("launch", DEV, "com.zhiliaoapp.musically")
    for _ in range(10):
        sleep(3)
        t = ui()
        if re.search(TABBAR, t):
            return t
        guard(t)
    return t


def _region_blocked():
    """15 Nov: after the phones were unplugged the Redmi's VPN had silently dropped -> TikTok showed 'Services not available
    in your country or region' and every account switch failed. Detect it and reconnect the US VPN."""
    t = ui()
    if "Services not available" not in t and "not available in your country" not in t: return False
    log("  TikTok says 'Services not available in your region' -> reconnecting the US VPN")
    try:
        sys.path.insert(0, os.path.expanduser("~/masonry-tools/insta")); import vpn as _vpn
        _vpn.set_country(DEV, "United States", "US")
    except Exception as e:
        log(f"  VPN reconnect failed: {e}")
    shell("am", "force-stop", "com.zhiliaoapp.musically"); sleep(2, 3)
    shell("monkey", "-p", "com.zhiliaoapp.musically", "-c", "android.intent.category.LAUNCHER", "1"); sleep(8, 10)
    return True


def switch_to(handle, _retry=True):
    """11 Nov: one retry after a TikTok restart - a tapped switcher row sometimes doesn't register."""
    if _switch_once(handle): return True
    if _region_blocked() and _switch_once(handle): return True
    # 23 Nov: the first try fails now and then (tap on a sheet still animating) -> one soft retry before restarting TikTok
    # (a restart right after a post can cut the upload)
    pd("key", DEV, "back"); sleep(1.5, 2.5)
    if _switch_once(handle): return True
    if not _retry: return False
    log(f"  switch to @{handle} failed, restarting TikTok and retrying once")
    shell("am", "force-stop", "com.zhiliaoapp.musically"); sleep(3, 4)
    shell("monkey", "-p", "com.zhiliaoapp.musically", "-c", "android.intent.category.LAUNCHER", "1"); sleep(8, 10)
    return _switch_once(handle)


def _switch_once(handle):
    go_main()
    pd("tap", DEV, "--text", "Profile", "--match", "exact")
    sleep(2.5, 3.5)
    t = ui(); guard(t)
    if current_handle(t) == handle:
        return True
    c = name_button(t)  # account name button opens the switcher (layout varies)
    tap(*(c or (sx(360), sy(388))))
    row = None
    shell("cmd", "statusbar", "collapse")   # a pulled-down shade swallows taps
    for i in range(7):                      # wait for the "Switch account" sheet, then tap the row
        sleep(1.5, 2)
        t = ui()
        row = coords(t, r'Button label="' + re.escape(handle) + r'" id=\w+')   # placeholder names change over time: never trust a stored alias blindly
        if row: break
        if 'Switch account' not in t and i in (1, 3, 5):   # 11 Nov Realme: a profile bubble ("What's up?") ate the first tap
            t0 = ui()
            if 'Switch account' not in t0:
                c = name_button(t0); tap(*(c or (sx(360), sy(388)))); continue
            t = t0
        if 'Switch account' in t and 'label="Add account"' not in t:   # 9+ accounts: the row can sit below the fold
            # 11 Nov: scroll UP only, and only when the list is cut off - a downward swipe drags the sheet closed
            shell("input", "swipe", str(sx(360)), str(sy(1450)), str(sx(360)), str(sy(1100)), "400")
        elif 'Switch account' in t:
            break                            # whole list visible and the handle isn't in it -> try placeholder rows
    if row:
        shell("cmd", "statusbar", "collapse"); sleep(0.5, 0.8); tap(*row)
    else:
        # TikTok sometimes lists an account under a placeholder name (user123..., or a nickname): try those rows and learn the alias
        known = set(SEEDS.get("_handles", {}).values()) | OWN_HANDLES
        cands = [l for l in re.findall(r'Button label="([^"]+)" id=\w+', t) if l != "Add account" and l not in known]
        cands.sort(key=lambda l: (0 if l == ALIASES.get(handle) else 1, 0 if re.fullmatch(r"user\d+", l) else 1))   # last-known alias, then placeholder names
        for lab in cands:
            r2 = coords(ui(), r'Button label="' + re.escape(lab) + r'" id=\w+')
            if not r2: break
            tap(*r2)
            for _ in range(8):
                sleep(3); t2 = ui()
                if "Your avatar, your style" in t2: pd("key", DEV, "back"); sleep(1.5)
                if re.search(TABBAR, t2) and not current_handle(t2): pd("tap", DEV, "--text", "Profile", "--match", "exact")
                ch = current_handle(t2)
                if ch: break
            if ch == handle:
                ALIASES[handle] = lab; _save_aliases(); log(f"  learned switcher alias {lab} -> @{handle}"); return True
            if ch and ch != handle and lab != ch:
                ALIASES[ch] = lab; _save_aliases()
            # reopen the switcher for the next candidate
            t3 = ui(); c3 = name_button(t3); tap(*(c3 or (sx(360), sy(388)))); sleep(2, 3)
        _dump_switch(handle, t, "row not found"); log(f"  switcher row for @{handle} not found"); pd("key", DEV, "back"); return False
    for _ in range(12):
        sleep(3)
        t = ui()
        if current_handle(t) == handle:
            return True
        if "Your avatar, your style" in t:
            pd("key", DEV, "back"); sleep(1.5)
        guard(t)
        if re.search(TABBAR, t):  # TikTok lands on Home after a switch
            pd("tap", DEV, "--text", "Profile", "--match", "exact")
    _dump_switch(handle, t, f"landed on @{current_handle(t)}")
    return False


def _dump_switch(handle, t, why):
    """11 Nov: recurring 'could not switch' (Sophie, Lily) - keep the last screen for diagnosis."""
    try:
        open(os.path.join(HERE, f"switch_fail{TAG}.txt"), "a").write(f"=== {datetime.datetime.now():%F %T} @{handle}: {why}\n{t}\n")
    except Exception:
        pass


# 13 Nov (Lava check): in a search-results feed TikTok shows "Search · <query>" on screen. It was read as the caption and,
# because the query always matches the niche regex, every search video counted as on-topic (65 of 65). Ignore that bar.
SEARCH_BAR = re.compile(r"Search\s*·")

def read_video(t):
    who = re.search(r'label="([^"]+) profile" id=user_avatar', t) or re.search(r'"([^"]+) profile"', t)
    likes = re.search(r'Like video\. ([^"]+?) likes', t)
    caps = [c for c in re.findall(r'TextView "([^"]{20,})"', t) if not SEARCH_BAR.match(c)]
    tags = re.findall(r"#\w+", " ".join(caps))
    return {"who": who.group(1) if who else None, "likes": likes.group(1) if likes else None,
            "caption": caps[0][:200] if caps else "", "tags": tags[:10]}


def record(acct, source, info):
    info = dict(info, acct=acct, source=source, ts=datetime.datetime.now().isoformat(timespec="seconds"))
    with open(SEEN_F, "a") as f:
        f.write(json.dumps(info) + "\n")


# Off-target market filter: a reel made for a different market than the account's target audience is skipped fast and
# marked "Not interested", so the feed converges on the target niche. The patterns are deployment config, not code:
# config/off_target.json -> {"text_regex": "...", "name_regex": "..."} (see config/off_target.example.json).
_OT_F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "off_target.json")
_OT = json.load(open(_OT_F)) if os.path.exists(_OT_F) else {}
OT_TEXT = re.compile(_OT.get("text_regex") or r"(?!x)x", re.I)
OT_NAME = re.compile(_OT.get("name_regex") or r"(?!x)x", re.I)
def off_target(text):
    return bool(OT_TEXT.search(text or ""))

def not_interested():
    """Long-press the video and pick 'Not interested' so the FYP stops sending this kind of video."""
    shell("input", "swipe", str(sx(360)), str(sy(760)), str(sx(362)), str(sy(762)), "900"); sleep(1.5, 2.2)
    t = ui(); c = coords(t, r'"Not interested"')
    if c: tap(*c); sleep(1.0, 1.6); return True
    pd("key", DEV, "back"); return False

def off_target_name(*names):
    return any(OT_NAME.search(n or "") for n in names)

_BLK = {"t": 0, "s": set()}
SNAPSHOT_F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "own_handles_snapshot.json")

def blocked():
    """11 Nov user rule: NEVER warm up on Masonry's paid UGC creators or Masonry's own channels (inflates their paid
    views and links our accounts to them). Re-read from the tracker config every 10 min so new creators are covered.
    12 Nov: a Mac without the tracker repo falls back to own_handles_snapshot.json (handles only, committed; refreshed
    whenever the tracker IS readable). If neither can be read, warm-ups STOP instead of running unprotected."""
    if time.time() - _BLK["t"] < 600: return _BLK["s"]
    b = set()
    try:
        for c in json.load(open(os.path.expanduser("~/masonry-ugc-tracker/config/creators.json"))):
            for k in ("tiktok", "instagram", "youtube", "facebook", "tiktok_all", "instagram_all", "youtube_all", "facebook_all"):
                v = c.get(k); v = v if isinstance(v, list) else [v]
                b |= {h.lower().lstrip("@") for h in v if h and isinstance(h, str)}
        for c in json.load(open(os.path.expanduser("~/masonry-ugc-tracker/config/channels.json"))):
            if c.get("handle"): b.add(c["handle"].lower().lstrip("@"))
        try:
            old = set(json.load(open(SNAPSHOT_F)))
            if b - old: json.dump(sorted(b | old), open(SNAPSHOT_F, "w"), indent=0)
        except Exception:
            json.dump(sorted(b), open(SNAPSHOT_F, "w"), indent=0)
    except Exception as e:
        try:
            b = set(json.load(open(SNAPSHOT_F)))
            if _BLK["t"] == 0: log(f"  tracker config unreadable ({e.__class__.__name__}) - using own_handles_snapshot.json ({len(b)} handles)")
        except Exception:
            b = set(_BLK["s"])
    if len(b) < 40:
        raise Stop(f"own-creator blocklist has only {len(b)} handles (no tracker repo, no snapshot) - refusing to warm up")
    b |= {"masonryai", "getmasonryai", "masonry.so"} | {h.lower() for h in OWN_HANDLES}
    _BLK.update(t=time.time(), s=b); return b

def is_blocked_video(info, raw):
    blk = blocked()
    who = re.sub(r"\s+", "", (info.get("who") or "").lower())
    if who and who.lstrip("@") in blk: return True
    return any(h.lower() in blk for h in re.findall(r"@([\w.]{3,30})", raw))


def engage_current(acct, source, watch=(8, 30), filter_relevant=False):
    """Watch the open video, maybe like/save, log it. With filter_relevant, skip off-topic videos fast.
    Off-target-market videos are always skipped in <1.2 s, never liked, and marked Not interested on the FYP."""
    t = ui(); guard(t)
    info = read_video(t)
    raw = " ".join(x for x in re.findall(r'"([^"]{2,})"', t) if not SEARCH_BAR.match(x))
    text = raw.lower()
    if off_target_name(info.get("who"), *re.findall(r"@([\w.]{3,30})", raw[:400])) or re.search(r'label="([^"]+) profile"', t) and off_target_name(re.search(r'label="([^"]+) profile"', t).group(1)):
        sleep(0.3, 0.9); ni = not_interested() if source == "fyp" else False      # off-target creator: leave, tell the FYP
        info.update(watched=0.6, liked=False, saved=False, skipped=True, off_target=True, not_interested=ni)
        record(acct, source, info)
        return info
    if is_blocked_video(info, raw):                     # our own creator / Masonry channel: leave at once, no like/save
        sleep(0.3, 0.8)
        info.update(watched=0.5, liked=False, saved=False, skipped=True, own_creator=True)
        record(acct, source, info)
        return info
    if off_target(raw):
        sleep(0.4, 1.2); ni = not_interested() if source == "fyp" else False
        info.update(watched=0.8, liked=False, saved=False, skipped=True, off_target=True, not_interested=ni)
        record(acct, source, info)
        return info
    if acct in NO_PRANK_ACCTS and re.search(r"prank|cantina|maybereal", text):   # non-prank niches: never watch/like pranks, tell the FYP
        sleep(0.4, 1.2); ni = not_interested() if source == "fyp" else False
        info.update(watched=0.8, liked=False, saved=False, skipped=True, prank=True, not_interested=ni)
        record(acct, source, info)
        return info
    relevant = bool(re.search(RELEVANT[acct], text)) or (bool(re.search(TEMPLATE_RE, text)) and not re.search(r"prank|cantina|maybereal", text) if acct not in PRANK_ACCTS else bool(re.search(TEMPLATE_RE, text)))
    info["relevant"] = relevant
    like_p = LIKE_P
    if filter_relevant and not relevant:
        w = random.uniform(0.8, 3.0); sleep(w)
        info.update(watched=round(w, 1), liked=False, saved=False, skipped=True)
        record(acct, source, info)
        return info
    if filter_relevant and relevant:
        watch, like_p = (15, 40), 0.3
    w = random.uniform(*watch)
    sleep(w)
    liked = saved = False
    if random.random() < like_p:
        c = coords(t, r'label="Like video')
        if c: tap(*c); liked = True; sleep(0.8, 1.6)
    if random.random() < SAVE_P:
        c = coords(t, r'label="Add or remove this video from Favorites')
        if c: tap(*c); saved = True; sleep(0.8, 1.6)
    commented = reposted = False
    if relevant and random.random() < COMMENT_P and globals().get('_SESS_COMMENTS', 0) < 1:   # 17 Nov: max 1 comment per session
        commented = tt_comment()
        if commented: globals()['_SESS_COMMENTS'] = globals().get('_SESS_COMMENTS', 0) + 1
    if relevant and random.random() < REPOST_P: reposted = tt_repost()
    info.update(watched=round(w, 1), liked=liked, saved=saved, commented=commented, reposted=reposted)
    record(acct, source, info)
    return info


_USED_C = os.path.join(HERE, "comments_used.json")
def tt_comment():
    """Comment on the open video with a short English line never used before by this phone (12 Nov, Lava)."""
    try: used = json.load(open(_USED_C))
    except Exception: used = []
    pool = [c for c in COMMENTS_EN if c not in used[-30:]] or COMMENTS_EN
    text = random.choice(pool)
    c = coords(ui(), r'label="Read or add comments')
    if not c: return False
    tap(*c); sleep(2, 3)
    e = coords(ui(), r'EditText "Add comment')
    if not e: pd("key", DEV, "back"); return False
    tap(*e); sleep(1, 1.6); pd("type", DEV, text); sleep(1, 1.8)
    t = ui(); p = coords(t, r'label="Post[^"]*"') or coords(t, r'(?:Button|ImageView|TextView) "Post"')
    ok = False
    if p: tap(*p); ok = True; sleep(1.5, 2.5)
    pd("key", DEV, "back"); sleep(0.8, 1.2)
    if "Add comment" in ui(): pd("key", DEV, "back"); sleep(0.8, 1.2)
    if ok:
        used.append(text); json.dump(used[-100:], open(_USED_C, "w"))
        log(f"    commented: {text}")
    return ok


def tt_repost():
    c = coords(ui(), r'label="Share video')
    if not c: return False
    tap(*c); sleep(2, 3)
    r = coords(ui(), r'TextView "Repost"')
    if not r: pd("key", DEV, "back"); return False
    tap(r[0], str(int(r[1]) - 60)); sleep(1.5, 2.5)
    if "Send to" in ui(): pd("key", DEV, "back"); sleep(0.8, 1.2)
    log("    reposted"); return True


def swipe_next():
    x = random.randint(300, 420)
    pd("swipe", DEV, str(sx(x)), str(sy(random.randint(1150, 1300))), str(sx(x + random.randint(-25, 25))),
       str(sy(random.randint(320, 460))), str(random.randint(180, 320)))
    sleep(1.5, 3)


def open_link(url):
    shell("am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.zhiliaoapp.musically")


def wait_for(pattern, secs=40):
    end = time.time() + secs
    while time.time() < end:
        t = ui()
        guard(t)
        if re.search(pattern, t):
            return t
        sleep(3)
    return None


WEB_FALLBACK = re.compile(r"is on TikTok|Discover more trending creators|Something went wrong|app-launch-skeleton")
MAX_PROFILES_PER_SESSION = 8

def visit_creator(acct, handle, st, today):
    """Returns False when TikTok served the web fallback page (soft profile-open limit)."""
    if off_target_name(handle):
        log(f"  [{acct}] @{handle} is off-target: not opened"); return None
    if handle.lower().lstrip("@") in blocked():
        log(f"  [{acct}] @{handle} is a Masonry creator/own channel: not opened"); return None
    open_link(f"https://www.tiktok.com/@{handle}")
    sleep(4, 6)
    t0 = ui()
    if WEB_FALLBACK.search(t0):
        log(f"  [{acct}] @{handle}: TikTok served the web page instead of the profile (soft limit)")
        go_main()
        return False
    t = wait_for(r'id=tv_play_count|"Follow"|"Message"|This account is private|Couldn.t find', 45)
    if not t or "Couldn" in t or "private" in t:
        log(f"  [{acct}] @{handle}: profile not loaded/private, skipped")
        return
    fol = re.search(r'"([\d.,]+[KM]?)" id=\w+ @\([^)]*\)[^\n]*\n[^\n]*"Followers"', t)
    tiles = [(int(x), int(y)) for x, y in re.findall(r'id=tv_play_count @\((\d+),(\d+)\)', t)]
    day = st.setdefault(acct, {}).setdefault("follows", {}).setdefault(today, [])
    followed_all = st[acct].setdefault("followed", [])
    did_follow = False
    n = 0
    sess = st.setdefault("_session", {"follows": 0, "last": 0})
    if (handle not in followed_all and len(day) < MAX_FOLLOWS_PER_DAY and sess["follows"] < MAX_FOLLOWS_PER_SESSION
            and time.time() - sess["last"] > MIN_FOLLOW_GAP_S and random.random() < FOLLOW_P):
        c = coords(t, r'TextView "Follow" id=\w+')
        if c:
            sleep(1, 3); tap(*c); sleep(1.5, 2.5)
            day.append(handle); followed_all.append(handle); did_follow = True
            sess["follows"] += 1; sess["last"] = time.time()
    if tiles:
        x, y = random.choice(tiles[:3])
        tap(x, y - sy(120))
        sleep(4, 6)
        n = random.randint(2, 3)
        for i in range(n):
            engage_current(acct, f"profile:{handle}", watch=(10, 35))
            if i < n - 1:
                swipe_next()
        pd("key", DEV, "back"); sleep(1.5, 2.5)
    st[acct].setdefault("visited", []).append(handle)
    log(f"  [{acct}] @{handle}: watched {n}, follow={'yes' if did_follow else 'no'}")
    return True


OWN_HANDLES = set(json.load(open(os.path.join(HERE, "own_handles.json")))) if os.path.exists(os.path.join(HERE, "own_handles.json")) else set()   # the fleet's own accounts (deployment config)
ALIASES = {}   # switcher shows some accounts by another name (learned ones persist in aliases.json)
_AF = os.path.join(HERE, "aliases.json")
try: ALIASES.update(json.load(open(_AF)))
except Exception: pass
def _save_aliases():
    try: json.dump(ALIASES, open(_AF, "w"), indent=1)
    except Exception: pass
SEARCH_KWS = {}   # per-account keyword lists (set by the controller)
SEARCH_KW = ["ai prank", "text prank", "pranking my dad", "pranking my mom", "ai photo prank", "texting my dad prank",
             "prank on dad", "cantina prank", "ai prank on parents", "fake photo prank"]

def type_query(keyword):
    """11 Nov 18:30: char-by-char 'input text' dropped letters on the Redmi (TikTok's suggestion list redraws between
    keys: 'make money...' became 'm '). Type the whole string, read the field back, clear + retry; PhoneDock type last."""
    for attempt in range(3):
        if attempt < 2 and re.fullmatch(r"[A-Za-z0-9 ]+", keyword):
            shell("input", "text", keyword.replace(" ", "%s"))
        else:                               # Japanese / accents / apostrophes: adb 'input text' can't, PhoneDock can
            pd("type", DEV, keyword)
        sleep(0.8, 1.3)
        m = re.search(r'EditText "([^"]*)"', ui())
        if m and m.group(1).strip().lower() == keyword.strip().lower(): return True
        shell("input", "keyevent", "KEYCODE_MOVE_END"); shell("input", "keyevent", *(["KEYCODE_DEL"] * 70)); sleep(0.4, 0.7)
    return False

def search_feed(acct, keyword, n=(5, 9)):
    """Like a person: tap Search, type the keyword, open the first video, scroll the results feed."""
    go_main(); pd("tap", DEV, "--text", "Home", "--match", "exact"); sleep(2, 3)
    t = ui()
    tops = sorted(((int(y), int(x)) for x, y in re.findall(r'label="Search"[^\n]*?@\((\d+),(\d+)\)', t)))   # top-right button, not the in-video search bar
    c = (tops[0][1], tops[0][0]) if tops and tops[0][0] < sy(400) else coords(t, r'id=m_y')
    if not c: log(f"  [{acct}] search: no search button"); return
    tap(*c); sleep(2, 3)
    t = ui(); e = coords(t, r'EditText')
    if e: tap(*e); sleep(0.6, 1.0)
    if not type_query(keyword):
        log(f"  [{acct}] search '{keyword}': typing failed"); go_main(); return
    sleep(0.5, 1.0); shell("input", "keyevent", "KEYCODE_ENTER")
    t = wait_for(r'id=cover|tv_play_count|"Videos"', 25)
    if not t: log(f"  [{acct}] search '{keyword}': no results"); go_main(); return
    v = coords(t, r'"Videos"')
    if v and random.random() < 0.6: tap(*v); sleep(2.5, 3.5); t = ui()
    tiles = []
    for _ in range(4):                      # the tab label shows before the result tiles load: wait for the tiles themselves
        tiles = [(int(x), int(y)) for x, y in re.findall(r'id=cover @\((\d+),(\d+)\)', t) if sy(300) < int(y) < sy(1400)]
        if tiles: break
        sleep(2.5, 3.5); t = ui()
    if not tiles:
        tiles = [(int(x), int(y) - sy(120)) for x, y in re.findall(r'id=tv_play_count @\((\d+),(\d+)\)', t)]
    if not tiles: log(f"  [{acct}] search '{keyword}': no tiles"); go_main(); return
    tap(*tiles[0] if random.random() < 0.6 else random.choice(tiles[:4])); sleep(3, 4.5)
    if not wait_for(r'Like video', 20): log(f"  [{acct}] search '{keyword}': video did not open"); go_main(); return
    k = random.randint(*n); on = 0
    for i in range(k):
        info = engage_current(acct, f"search:{keyword}", watch=(10, 32), filter_relevant=True); on += bool(info.get("relevant"))
        swipe_next(); sleep(0.8, 1.6)
    log(f"  [{acct}] search '{keyword}': {k} videos, {on} on-topic")
    pd("key", DEV, "back"); sleep(1, 1.6); pd("key", DEV, "back")

def watch_tag(acct, tag):
    import urllib.parse
    open_link(f"https://www.tiktok.com/tag/{urllib.parse.quote(tag)}")
    t = wait_for(r'id=cover @', 45)
    tiles = [(int(x), int(y)) for x, y in re.findall(r'id=cover @\((\d+),(\d+)\)', t or "") if int(y) > sy(500)]
    tiles = [c for c in tiles if c[1] < sy(1400)]
    if not tiles:
        log(f"  [{acct}] #{tag}: no tiles found"); pd("key", DEV, "back"); return
    tap(*random.choice(tiles[:6])); sleep(4, 6)
    if not wait_for(r'Like video', 20):
        log(f"  [{acct}] #{tag}: video did not open"); go_main(); return
    for i in range(random.randint(3, 5)):
        engage_current(acct, f"tag:{tag}", watch=(10, 30)); swipe_next()
    pd("key", DEV, "back"); sleep(1, 2); pd("key", DEV, "back"); sleep(1, 2)
    log(f"  [{acct}] #{tag}: watched")


def fyp(acct, minutes):
    go_main()
    pd("tap", DEV, "--text", "Home", "--match", "exact"); sleep(2, 3)
    end = time.time() + minutes * 60
    n = 0
    rel = 0
    while time.time() < end:
        i = engage_current(acct, "fyp", filter_relevant=True); swipe_next(); n += 1
        rel += 1 if i.get("relevant") else 0
    log(f"  [{acct}] For You: {n} videos, {rel} on-topic (rest skipped in <3s)")


# 11 Nov user: focus warm-ups on the content we ALSO give our human UGC creators (the avatar templates: GTA 6 clipping,
# faceless AI-video / YouTube Shorts side hustles, AI content creation); pranks are not ROI-driven, keep them small.
TEMPLATE_KWS = ["gta 6 clipping", "how to start clipping", "clipping side hustle", "make money clipping streams",
                "ai video side hustle", "faceless youtube channel ai", "ai story video youtube shorts", "how to make ai videos",
                "content creator side hustle", "ai content creation tips"]
TEMPLATE_TAGS = ["clipping", "gta6", "aivideo", "facelessyoutube", "contentcreator", "aicontent", "youtubeshorts"]
TEMPLATE_RE = r"clip|gta|stream|faceless|youtube|shorts|ai video|aivideo|content creat|side ?hustle|ugc|creator"
PRANK_ACCTS = {"ethan", "maya", "jake", "beth"}
# 11 Nov user: "warm up with Spanish, Japanese etc. as well, like our UGC creators - not just English".
# Same template topics in the languages our human UGC creators post in (target-market languages only).
TEMPLATE_KWS_INTL = {
    "es": ["clipping gta 6", "como ganar dinero con clips", "canal de youtube sin mostrar la cara con ia", "videos con ia para tiktok",
           "ideas de negocio con inteligencia artificial", "como hacer videos con ia"],
    "pt": ["como ganhar dinheiro com cortes", "canal dark com ia", "como fazer videos com ia", "renda extra com inteligencia artificial"],
    "ja": ["切り抜き 副業", "AI動画 作り方", "顔出しなし YouTube", "AI 副業 稼ぐ", "ショート動画 作り方"],
    "fr": ["comment faire des videos avec l'ia", "side hustle ia", "chaine youtube sans visage ia", "gagner de l'argent avec l'ia"],
    "de": ["ki videos erstellen", "nebenverdienst mit ki"],
}
TEMPLATE_TAGS_INTL = ["ia", "inteligenciaartificial", "videosconia", "rendaextra", "dinheirocomia", "AI動画", "副業", "切り抜き", "iagenerative", "kivideo"]
TEMPLATE_RE += r"|ia\b|inteligencia|dinero|dinheiro|renda|vid[eé]os? con|副業|動画|切り抜き|gagner|ki[- ]"


def session(acct, minutes, st):
    handle = SEEDS["_handles"][acct]
    if not vpn_ok():
        raise Stop("VPN (tun0) is down")
    if not switch_to(handle):
        raise Stop(f"could not switch to @{handle}")
    log(f"[{acct}] session start as @{handle} ({minutes:.0f} min)")
    globals()['_SESS_COMMENTS'] = 0
    st["_session"] = {"follows": 0, "last": 0}
    today = datetime.date.today().isoformat()
    end = time.time() + minutes * 60
    visited = set(st.get(acct, {}).get("visited", []))
    blk = blocked()
    clean = [h for h in SEEDS[acct] if h.lower().lstrip("@") not in blk and not off_target_name(h)]   # never open a Masonry creator's / own profile
    pool = [h for h in clean[:150] if h not in visited] or clean[:150]
    random.shuffle(pool)
    # ~60% of the session on tracked creators, one hashtag, rest For You
    creators_until = time.time() + minutes * 60 * (0.30 if acct in PRANK_ACCTS else 0.40)   # less niche-creator time, more template topics
    opened = 0
    for h in pool:
        if time.time() > creators_until or opened >= MAX_PROFILES_PER_SESSION:
            break
        opened += 1
        ok = visit_creator(acct, h, st, today); save_state(st)
        if ok is False:
            log(f"  [{acct}] no more profile opens this session")
            break
        sleep(8, 20)
    lang = random.choice(list(TEMPLATE_KWS_INTL))
    kws = [random.choice(TEMPLATE_KWS), random.choice(TEMPLATE_KWS_INTL[lang])] + random.sample(SEARCH_KWS.get(acct, SEARCH_KW), 1)   # EN template + other-language template + niche
    random.shuffle(kws)
    for kw in kws:          # search first, then scroll the results (human pattern)
        search_feed(acct, kw)
    r = random.random()
    watch_tag(acct, random.choice(TEMPLATE_TAGS) if r < 0.4 else random.choice(TEMPLATE_TAGS_INTL) if r < 0.65 else random.choice(SEEDS["_tags"][acct]))
    left = (end - time.time()) / 60
    if left > 1:
        fyp(acct, left)
    save_state(st)
    log(f"[{acct}] session end; follows today: {len(st[acct]['follows'].get(today, []))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=3)
    ap.add_argument("--session-min", type=float, default=20)
    ap.add_argument("--accounts", default="maya,jake,ethan")
    ap.add_argument("--no-follow", action="store_true", help="watch/like/save only (fresh accounts: TikTok silently reverts follows)")
    a = ap.parse_args()
    accts = a.accounts.split(",")
    global FOLLOW_P
    if a.no_follow:
        FOLLOW_P = 0.0
    st = load_state()
    shell("svc", "power", "stayon", "usb")
    stop_at = time.time() + a.hours * 3600
    log(f"=== warm-up start: {accts}, {a.hours}h, {a.session_min} min sessions")
    i = 0
    try:
        while time.time() < stop_at:
            acct = accts[i % len(accts)]
            mins = min(a.session_min * random.uniform(0.85, 1.15), (stop_at - time.time()) / 60)
            if mins < 3:
                break
            session(acct, mins, st)
            i += 1
            sleep(20, 60)
    except Stop as e:
        log(f"!!! STOPPED: {e}  (needs a human: check the phone)")
        save_state(st); sys.exit(3)
    finally:
        save_state(st)
    log("=== warm-up finished")


if __name__ == "__main__":
    main()
