#!/usr/bin/env python3
"""Warm-up for the LAVA phone's 4 accounts (12 Nov 2026) - runs on whichever Mac the Lava is plugged into.

Owner: search a KEYWORD in the search bar, watch the results, and like / comment / save / repost some of them (not all,
like a human). TikTok accounts watch English; Instagram accounts watch ONLY their language (Valeria Spanish on a Mexico
VPN, Yuna Japanese on a Japan VPN). Never our own creators/channels, never off-target-market content (warmup.blocked/off_target*).
usage: lava_warm.py <key|next> [minutes]        loop: lava_forever.py
"""
import datetime, json, os, random, re, sys, time
os.environ["TT_DEV"] = "android-device:LAVA_SERIAL"
os.environ["TT_TAG"] = "lava"
os.environ["IG_PHONE"] = "lava"          # 13 Nov: ig_warm now sets TT_DEV from IG_PHONE (default Redmi)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "insta")); sys.path.insert(0, os.path.join(HERE, "..", "tiktok-warmup"))
import ig_warm as g                      # imports warmup.py with TT_DEV = the Lava
import lava_vpn
w = g.w; lava_vpn.patch_tiktok(w)
DEV = w.DEV
ACCTS = json.load(open(os.path.join(HERE, "lava_accounts.json")))
STATE_F, LOG_F, SEEN_F = (os.path.join(HERE, f) for f in ("lava_state.json", "lava_run.log", "lava_seen.jsonl"))
IG_P = dict(like=0.30, save=0.08, comment=0.06, repost=0.03)        # per on-topic reel
# 14 Nov owner approved: reposts max 1 a day; follow 1-3 niche creators a day (only ones it just liked, max 1 a session);
# about half of each session in the Reels tab, a short home-feed scroll and stories on some sessions, the rest search.
IG_FOLLOW_P, IG_REPOST_DAY = 0.30, 1
w.LIKE_P, w.SAVE_P, w.COMMENT_P, w.REPOST_P = 0.25, 0.07, 0.05, 0.03  # TikTok, per on-topic video

def log(m):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {m}"
    print(line, flush=True); open(LOG_F, "a").write(line + "\n")
w.log = lambda m: log(m)                 # TikTok helpers log into the Lava log

def state():
    try: return json.load(open(STATE_F))
    except Exception: return {}

def ui(): return w.pd("ui", DEV, "--no-ocr")

def bump(name):
    st = state(); st[name] = st.get(name, 0) + 1; json.dump(st, open(STATE_F, "w"), ensure_ascii=False, indent=1)

def day_key(a, what): return f"ig_{what}_{a['handle']}_{datetime.date.today().isoformat()}"

def follow_target(a):  # 1-3 a day, fixed per account per day
    return random.Random(day_key(a, "follow_target")).randint(1, 3)

# ---------------- Instagram ----------------
def ig_search(kw):
    g.open_app()
    c = w.coords(ui(), r"id=search_tab(?= @)")
    if not c: return False
    w.tap(*c); w.sleep(2, 3)
    c = w.coords(ui(), r'id=action_bar_search_edit_text')
    if not c: return False
    w.tap(*c); w.sleep(1.2, 2)
    w.pd("type", DEV, kw); w.sleep(2.5, 3.5)
    t = ui(); c = w.coords(t, r'id=row_search_keyword_title')
    if c: w.tap(*c)
    else: w.shell("input", "keyevent", "KEYCODE_ENTER")
    w.sleep(4, 6)
    t = ui(); g.guard(t)
    tiles = [(int(x), int(y)) for x, y in re.findall(r'label="Reel by [^"]*" id=grid_card_layout_container @\((\d+),(\d+)\)', t)]
    if not tiles: return False
    w.tap(*(tiles[0] if random.random() < 0.5 else random.choice(tiles[:4]))); w.sleep(4, 6)
    return "clips_author_username" in ui()

def ig_comment(a):
    used = state().get("ig_comments_used", [])
    pool = [c for c in a["comments"] if c not in used[-25:]] or a["comments"]
    text = random.choice(pool)
    c = w.coords(ui(), r'Button "Add comment…" id=comment_composer_text_view') or w.coords(ui(), r'label="Comment" id=comment_button')
    if not c: return False
    w.tap(*c); w.sleep(2, 3)
    e = w.coords(ui(), r'(?:EditText|AutoCompleteTextView)[^\n]*id=(?:layout_comment_thread_edittext\w*|comment_composer\w*)')
    if not e: w.pd("key", DEV, "back"); return False
    w.tap(*e); w.sleep(0.8, 1.3); w.pd("type", DEV, text); w.sleep(1.2, 2)
    t = ui(); p = w.coords(t, r'label="Post" id=layout_comment_thread_post_button\w*') or w.coords(t, r'(?:Button|TextView) "Post"')
    ok = bool(p)
    if p: w.tap(*p); w.sleep(2, 3)
    for _ in range(4):        # 12 Nov: the comment sheet stays open over the reel (its rows have their own "Like" buttons)
        t = ui()
        if not re.search(r'ImageView label="Like" @|layout_comment_thread|EditText[^\n]*comment', t): break
        w.pd("key", DEV, "back"); w.sleep(1, 1.5)
    if ok:
        st = state(); st.setdefault("ig_comments_used", []).append(text); st["ig_comments_used"] = st["ig_comments_used"][-100:]
        json.dump(st, open(STATE_F, "w"), ensure_ascii=False, indent=1)
    return text if ok else False

def ig_repost():
    c = w.coords(ui(), r'Button label="Repost"')
    if not c: return False
    w.tap(*c); w.sleep(2, 3)
    t = ui(); b = w.coords(t, r'(?:Button|TextView) "Repost"') if "clips_author_username" not in t else None
    if b: w.tap(*b); w.sleep(1.5, 2.5)
    if "clips_author_username" not in ui(): w.pd("key", DEV, "back"); w.sleep(1, 1.5)
    return True

def ig_watch(a, kw, n, until=None, src=None):
    rel = re.compile(a["relevant"], re.I); on = 0; last = None; stuck = 0; followed = False
    src = src or f"search:{kw}"
    for _ in range(n):
        if until and time.time() > until: break
        t = ui(); g.guard(t)
        if re.search(r'ImageView label="Like" @', t): w.pd("key", DEV, "back"); w.sleep(1, 1.5); t = ui()   # a sheet left open
        if "clips_author_username" not in t:
            w.sleep(2, 3); t = ui()
            if "clips_author_username" not in t: break
        who, cap = g.reel_info(t)
        if (who, cap) == last:                 # the swipe did not move on: never act twice on one reel (a 2nd like = unlike)
            stuck += 1
            if stuck >= 2: log(f"  [{a['handle']}] reel feed stuck - leaving"); break
            g.next_reel(); continue
        last, stuck = (who, cap), 0
        blk = who.lower() in w.blocked() or w.off_target_name(who) or w.off_target(cap)
        native = g.lang_ok(cap, a["lang"])
        good = not blk and native and bool(rel.search(cap + " " + who))
        did = []
        if blk or not native:
            w.sleep(0.8, 2.0)                                     # other language / blocked: leave fast
            if src == "reels":                                    # steer the Reels feed toward the language and niche
                c = w.coords(ui(), r'ViewGroup "Not interested"')
                if c: w.tap(*c); w.sleep(1, 1.6)
        else:
            w.sleep(*((9, 24) if good else (3, 7)))
            if good:
                on += 1
                if random.random() < IG_P["like"]:
                    c = w.coords(ui(), r'label="Like" id=like_button')
                    if c: w.tap(*c); did.append("like"); w.sleep(0.6, 1.2)
                if random.random() < IG_P["save"]:
                    c = w.coords(ui(), r'label="Save" id=save_button')
                    if c:
                        w.tap(*c); did.append("save"); w.sleep(0.8, 1.4)
                        if "Collections" in ui(): w.pd("key", DEV, "back")
                if random.random() < IG_P["comment"]:
                    r = ig_comment(a)
                    if r: did.append(f"comment:{r}")
                if (random.random() < IG_P["repost"] and state().get(day_key(a, "reposts"), 0) < IG_REPOST_DAY
                        and ig_repost()):
                    did.append("repost"); bump(day_key(a, "reposts"))
                if ("like" in did and not followed and random.random() < IG_FOLLOW_P
                        and state().get(day_key(a, "follows"), 0) < follow_target(a)):
                    c = w.coords(ui(), r'TextView "Follow" label="Follow [^"]*" id=inline_follow_button')
                    if c:
                        w.tap(*c); w.sleep(1, 2); followed = True; did.append("follow"); bump(day_key(a, "follows"))
        if did: log(f"    @{who}: {', '.join(did)}")
        open(SEEN_F, "a").write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "acct": a["handle"], "src": src,
                                            "who": who, "on": good, "blk": bool(blk), "native": native, "did": did, "cap": cap[:120]}, ensure_ascii=False) + "\n")
        g.next_reel()
    return on

def ig_tab(name):
    t = ui(); c = w.coords(t, rf"id={name}(?= @)")
    if not c: g.open_app(); t = ui(); c = w.coords(t, rf"id={name}(?= @)")
    if not c: return False
    w.tap(*c); w.sleep(3, 5); return True

def ig_stories(key, a):
    """Watch a few stories from accounts it follows (none until it follows someone)."""
    if not ig_tab("feed_tab"): return
    t = ui(); g.guard(t)
    others = [(m.group(1), int(m.group(2)), int(m.group(3))) for m in
              re.finditer(r'Button label="([\w.]+)\'s story, [^"]*" @\((\d+),(\d+)\)', t) if m.group(1) != a["handle"]
              and m.group(1).lower() not in w.blocked() and not w.off_target_name(m.group(1))]
    if not others: return
    who, x, y = others[0] if random.random() < 0.6 else random.choice(others[:4])
    w.tap(x, y); w.sleep(3, 5); n = random.randint(2, 5)
    for _ in range(n):
        w.sleep(3, 7); w.tap(650, 800)                         # right edge: next story
    for _ in range(3):
        if "id=feed_tab @" in ui(): break
        w.pd("key", DEV, "back"); w.sleep(1.2, 2)
    log(f"  [{key}] stories: {n + 1} from @{who} on")

def ig_home(key, minutes):
    """A short home-feed scroll, no actions (how most people open the app)."""
    if not ig_tab("feed_tab"): return
    end, n = time.time() + minutes * 60, 0
    while time.time() < end:
        g.guard(ui()); w.sleep(2, 7)
        x = 360 + random.randint(-40, 40)
        w.shell("input", "swipe", str(x), str(1150 + random.randint(-40, 40)), str(x + random.randint(-20, 20)),
                str(450 + random.randint(-40, 40)), str(random.randint(250, 450))); n += 1
    log(f"  [{key}] home feed: {n} scrolls")

def ig_reels(key, a, minutes):
    if not ig_tab("clips_tab"): return
    w.sleep(2, 3); on = ig_watch(a, "", 400, until=time.time() + minutes * 60, src="reels")
    log(f"  [{key}] reels tab: {minutes:.0f} min, {on} on-topic")

def ig_search_part(key, a, until):
    for kw in random.sample(a["keywords"], len(a["keywords"])):
        if time.time() > until: break
        if not ig_search(kw): log(f"  [{key}] '{kw}': no reels"); continue
        n = random.randint(6, 11); on = ig_watch(a, kw, n, until=until + 60)
        log(f"  [{key}] '{kw}': {n} reels, {on} on-topic")
        w.sleep(3, 8)

def ig_session(key, a, minutes):
    if not g.switch_to(a["handle"]): log(f"  [{key}] could not switch Instagram to @{a['handle']}"); return
    end = time.time() + (minutes - 1) * 60
    if random.random() < 0.6: ig_stories(key, a)
    if random.random() < 0.6: ig_home(key, random.uniform(0.5, 1.5))
    left = (end - time.time()) / 60
    reels_min = max(2.0, left * random.uniform(0.4, 0.6))
    if random.random() < 0.5:
        ig_reels(key, a, reels_min); ig_search_part(key, a, end)
    else:
        ig_search_part(key, a, end - reels_min * 60); ig_reels(key, a, max(1.5, (end - time.time()) / 60))
    st = state(); log(f"  [{key}] today: follows {st.get(day_key(a, 'follows'), 0)}/{follow_target(a)}, reposts {st.get(day_key(a, 'reposts'), 0)}")

# ---------------- TikTok ----------------
def tt_session(key, a, minutes):
    w.RELEVANT[key] = a["relevant"]; w.NO_PRANK_ACCTS.add(key)
    w.go_main()
    if not w.switch_to(a["handle"]): log(f"  [{key}] could not switch TikTok to @{a['handle']}"); return
    t0 = time.time()
    for kw in random.sample(a["keywords"], len(a["keywords"])):
        w.search_feed(key, kw, n=(6, 10))
        if (time.time() - t0) / 60 > minutes - 1.5: break
        w.sleep(3, 8)

def session(key, minutes=12):
    a = ACCTS[key]; st = state()
    log(f"[{key}] {a['app']} session @{a['handle']} ({a['lang']}, VPN {a['vpn']}) {minutes:.0f} min")
    if not lava_vpn.switch(a["vpn"]):    # 13 Nov: a failure is a turn, or next_key() picks this account forever
        st[f"last_{key}"] = time.time(); json.dump(st, open(STATE_F, "w"), ensure_ascii=False, indent=1)
        log(f"  [{key}] VPN could not switch to {a['vpn']} - skipped"); return
    try:
        (ig_session if a["app"] == "instagram" else tt_session)(key, a, minutes)
    finally:
        st = state(); st[f"last_{key}"] = time.time(); json.dump(st, open(STATE_F, "w"), ensure_ascii=False, indent=1)
        log(f"[{key}] session end")

def next_key():
    st = state(); return min(ACCTS, key=lambda k: st.get(f"last_{k}", 0))

if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 else "next"
    k = next_key() if k == "next" else k
    try: session(k, float(sys.argv[2]) if len(sys.argv) > 2 else 12)
    except w.Stop as e: log(f"[{k}] STOPPED: {e}"); sys.exit(3)
