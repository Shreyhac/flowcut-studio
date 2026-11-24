#!/usr/bin/env python3
"""Instagram warm-up for our non-English IG accounts on the Redmi (12 Nov 2026).

User (12 Nov): "now we need to focus on warming insta". Each account posts in its own language (no English IG).
One session (~12 min) for one account:
  1. switch the IG app to that account
  2. open 2 niche hashtags in the account's language (deep link), watch 4-8 Reels from each
  3. scroll the Reels tab; skip off-topic / off-target-market / our own creators fast (+ "Not interested")
Likes ~25% of on-topic Reels, saves ~8%, follows max 2 per session / 5 per day (from day 2), never a blocked handle.
Rules carried over from TikTok: never engage Masonry's paid creators or own channels (warmup.blocked()), no off-target-market
content (warmup.off_target / off_target_name), stop on any challenge/limit screen.
usage: ig_warm.py <handle|next> [minutes]      (state: ig_state.json, log: ig_run.log)
"""
import datetime, importlib.util, json, os, random, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import vpn

HERE = os.path.dirname(os.path.abspath(__file__))
# 13 Nov owner: the 4 ex-Lite accounts (pt/fr/de) moved into the Realme's main Instagram app -> IG_PHONE=realme
PHONE = os.environ.get("IG_PHONE", "redmi")
_DEVS = {"redmi": ("android-device:REDMI_SERIAL", 720, 1640), "realme": ("android-device:REALME_SERIAL", 1080, 2412),
         "lava": ("android-device:LAVA_SERIAL", 720, 1600),
         "emulator": ("android-emulator:vw_ig_01", 1080, 2400)}   # 20 Nov: JP experiment account @acct_236   # 13 Nov: lava/ imports this module; it must not fall back to the Redmi
os.environ["TT_DEV"] = _DEVS[PHONE][0]
DW, DH = _DEVS[PHONE][1], _DEVS[PHONE][2]
def _x(v): return int(v * DW / 720)          # Redmi device px -> this phone's px
def _y(v): return int(v * DH / 1640)
spec = importlib.util.spec_from_file_location("w", os.path.expanduser("~/masonry-tools/tiktok-warmup/warmup.py"))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
DEV = w.DEV
IG = "com.instagram.android"
ACCTS = {} if PHONE == "lava" else json.load(open(f"{HERE}/" + ("ig_accounts.json" if PHONE == "redmi" else "realme_ig_accounts.json")))
# 21 Nov: accounts logged out of the phone (valentina/camila/sofia on the Redmi since 19 Nov) are skipped everywhere
ACCTS = {k: v for k, v in ACCTS.items() if not v.get("logged_out")}
STATE_F, LOG_F = f"{HERE}/" + ("ig_state.json" if PHONE == "redmi" else "realme_ig_state.json"), f"{HERE}/ig_run.log"
LIKE_P, SAVE_P, FOLLOW_P = 0.25, 0.08, 0.5          # 17 Nov owner: follow 3-5 niche creators a day
MAX_FOLLOW_SESSION, MAX_FOLLOW_DAY = 2, 5
COMMENT_P, MAX_COMMENT_SESSION, MAX_COMMENT_DAY = 0.08, 1, 3   # 17 Nov owner: light comments while warming (account language, no links)
STOP = re.compile(r"try again later|we restrict certain|restricted|confirm it.s you|suspicious|suspended|"
                  r"verify your|help us confirm|enter the code|we limit how often|action blocked|log in to continue", re.I)


def log(m):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {m}"
    print(line, flush=True); open(LOG_F, "a").write(line + "\n")


def ui():
    t = w.pd("ui", DEV, "--no-ocr")
    # 14 Nov: on an EU VPN (Germany/France) Instagram puts up "Allow the use of cookies by Instagram?" over everything,
    # which broke account switching on the Realme. Decline the optional cookies (the private choice) and read again.
    if t and "Allow the use of cookies by Instagram?" in t:
        m = re.search(r'"Decline optional cookies"[^\n]*?@\((\d+),(\d+)\)', t)
        if m:
            w.tap(int(m.group(1)), int(m.group(2))); time.sleep(2.5)
            t = w.pd("ui", DEV, "--no-ocr")
    return t


def S(x, y):      # standard 450x1024 space (what I read off the screen while building) -> Redmi device pixels
    return int(x * 720 / 450), int(y * 1640 / 1024)


def tapd(x, y): w.tap(x, y)          # device pixels


def guard(t):
    m = STOP.search(t)
    if m: raise w.Stop("IG challenge/limit: " + m.group(0))


def state():
    try: return json.load(open(STATE_F))
    except Exception: return {}


def open_app():
    """Bring IG to a screen with the bottom tab bar (deep-linked hashtag/reel pages hide it)."""
    w.shell("monkey", "-p", IG, "-c", "android.intent.category.LAUNCHER", "1"); w.sleep(4, 6)
    for i in range(5):
        t = ui()
        if "id=profile_tab @" in t: return t
        guard(t)
        c = w.coords(t, r'Button "(?:Start over|Discard)"')      # a half-made post left behind by a failed upload
        if c: tapd(*c); w.sleep(2, 3); continue
        w.pd("key", DEV, "back"); w.sleep(1.2, 2)
        if i == 2: w.shell("monkey", "-p", IG, "-c", "android.intent.category.LAUNCHER", "1"); w.sleep(3, 4)
    w.shell("am", "force-stop", IG); w.sleep(2)
    w.shell("monkey", "-p", IG, "-c", "android.intent.category.LAUNCHER", "1"); w.sleep(8, 10)
    return ui()


def current():
    """Profile tab -> action bar title is the username."""
    t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
    if not c: open_app(); t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
    if not c: return None
    tapd(*c); w.sleep(2.5, 3.5); t = ui(); guard(t)
    m = re.search(r'TextView "([\w.]+)" id=action_bar_title', t)
    # 23 Nov (Lava, misaki): new profile layout - display name on top, the username below it
    m = m or re.search(r'TextView "([\w.]+)" id=profile_header_full_name_above_vanity', t)
    return m.group(1) if m else None


def switch_to(handle):
    if current() == handle: return True
    for _ in range(2):
        t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
        if not c: open_app(); continue
        w.shell("input", "swipe", str(c[0]), str(c[1]), str(c[0] + 1), str(c[1] + 1), "900"); w.sleep(1.5, 2.2)
        t = ui(); r = w.coords(t, rf'ViewGroup label="{re.escape(handle)}[",]')
        if r: tapd(*r); w.sleep(4, 6)
        else: w.pd("key", DEV, "back"); w.sleep(1, 2)
        if current() == handle: return True
    try:   # 18 Nov: Sofia fails 5/8 here but switches fine by hand -> keep a screenshot of what the phone showed
        import subprocess as _sp
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"), exist_ok=True)
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", f"switch_fail_{handle}_{time.strftime('%m%d_%H%M%S')}.png")
        png = _sp.run(["adb", "-s", DEV.split(":")[-1], "exec-out", "screencap", "-p"], capture_output=True, timeout=30).stdout
        open(f, "wb").write(png); log(f"  switch failed: screenshot {f}")
    except Exception: pass
    return False


ES_W = re.compile(r"[áéíóúñ¿¡]|\b(que|para|con|los|las|una|del|por|como|más|mas|tu|mi|esto|cómo|dinero|aquí|también|hacer|puedes|gratis|ahora|el|es|no|lo|se|y|te|comenta|mando|sígueme)\b", re.I)   # 12 Nov: short captions ("La IA no es el futuro…") failed
PT_W = re.compile(r"[ãõçáéíóú]|\b(que|para|com|uma|não|você|isso|como|mais|dinheiro|aqui|também|fazer|grátis|agora)\b", re.I)
FR_W = re.compile(r"[éèêàçù]|\b(le|la|les|des|une|est|pour|avec|vous|pas|dans|sur|qui|que|ça|c'est|tu|ton|ta|comment|gratuit|argent|aussi)\b", re.I)
DE_W = re.compile(r"[äöüß]|\b(der|die|das|und|ist|nicht|mit|für|ich|du|sie|ein|eine|auf|zu|wie|kostenlos|geld|auch|dein|deine)\b", re.I)
EN_W = re.compile(r"\b(the|and|you|this|that|with|your|for|how|what|just|get|my|is|are|to|of)\b", re.I)
def lang_ok(text, lang):
    """12 Nov 11:10 owner (angry): warm-up must be in the account's language, not English content."""
    if lang == "ja": return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))
    rx = {"es": ES_W, "pt": PT_W, "fr": FR_W, "de": DE_W}.get(lang)
    if rx is None: return True
    return len(rx.findall(text)) >= 1 and len(rx.findall(text)) >= len(EN_W.findall(text))

def reel_info(t):
    who = re.search(r'Button "([\w.]+)\s*" id=clips_author_username', t)
    cap = re.search(r'id=clips_caption_component[^\n]*\n[^\n]*ViewGroup label="([^"]*)"', t)
    return (who.group(1) if who else ""), (cap.group(1) if cap else "")


def next_reel():
    x = _x(360 + random.randint(-40, 40))
    w.shell("input", "swipe", str(x), str(_y(1250 + random.randint(-40, 40))), str(x + random.randint(-20, 20)), str(_y(380 + random.randint(-40, 40))),
            str(random.randint(220, 380))); w.sleep(1.2, 2.0)


def reel_comment(a):
    """17 Nov: one short comment in the account's language on the open on-topic reel (lists shared with ig_engage)."""
    import ig_engage
    text = ig_engage.pick_comment(a.get("lang", "es"))
    c = w.coords(ui(), r'label="Comment" id=comment_button')
    if not c: return False
    tapd(*c); w.sleep(2.5, 3.5)
    t = ui(); e = w.coords(t, r'(?:AutoCompleteTextView|EditText)[^\n]*id=(?:layout_comment_thread_edittext\w*|comment_composer\w*)')
    ok = False
    if e:
        tapd(*e); w.sleep(1, 1.5); w.pd("type", DEV, text); w.sleep(1.5, 2.5)
        t = ui(); p = w.coords(t, r'label="Post" id=layout_comment_thread_post_button\w*') or w.coords(t, r'(?:Button|TextView) "Post"')
        if p: tapd(*p); ok = True; w.sleep(2, 3)
    w.pd("key", DEV, "back"); w.sleep(1, 1.6)
    if "clips_author_username" not in ui(): w.pd("key", DEV, "back"); w.sleep(1, 1.6)
    if ok: log(f"  [{a['key']}] commented: {text}")
    return ok


def watch_reels(a, n, src, st, today):
    rel = re.compile(a["relevant"], re.I)
    on = 0
    for _ in range(n):
        t = ui(); guard(t)
        if "clips_author_username" not in t:
            w.sleep(2, 3); t = ui()
            if "clips_author_username" not in t: log(f"  [{a['key']}] {src}: no reel on screen"); return on
        who, cap = reel_info(t)
        blk = who.lower() in w.blocked() or w.off_target_name(who) or w.off_target(cap)
        native = lang_ok(cap, a["lang"])
        good = bool(rel.search(cap + " " + who)) and not blk and native
        if not native and not blk: blk = None      # other-language reel: leave fast, "Not interested" below
        if blk or blk is None:
            w.sleep(0.6, 1.4)
            c = w.coords(t, r'ViewGroup "Not interested"')
            if c: tapd(*c); w.sleep(1, 1.6)
        else:
            w.sleep(*((10, 26) if good else (3, 8)))
            if not good and src == "reels" and random.random() < 0.25:     # steer the feed toward the niche
                c = w.coords(ui(), r'ViewGroup "Not interested"')
                if c: tapd(*c); w.sleep(1, 1.6)
            if good:
                on += 1
                if random.random() < LIKE_P:
                    c = w.coords(ui(), r'label="Like" id=like_button')
                    if c: tapd(*c); w.sleep(0.6, 1.2)
                if random.random() < SAVE_P:
                    c = w.coords(ui(), r'label="Save" id=save_button')
                    if c: tapd(*c); w.sleep(0.8, 1.4); w.pd("key", DEV, "back") if "Collections" in ui() else None
                ck = f"comments_{a['key']}_{today}"
                if (random.random() < COMMENT_P and st.get("_sess_comments", 0) < MAX_COMMENT_SESSION and st.get(ck, 0) < MAX_COMMENT_DAY
                        and reel_comment(a)):
                    st[ck] = st.get(ck, 0) + 1; st["_sess_comments"] = st.get("_sess_comments", 0) + 1
                fk = f"follows_{a['key']}_{today}"
                if (a.get("follow_from", "") <= today and random.random() < FOLLOW_P and st.get("_sess_follows", 0) < MAX_FOLLOW_SESSION
                        and st.get(fk, 0) < MAX_FOLLOW_DAY):
                    c = w.coords(ui(), r'TextView "Follow" label="Follow [^"]*" id=inline_follow_button')
                    if c:
                        tapd(*c); w.sleep(1, 2); st[fk] = st.get(fk, 0) + 1; st["_sess_follows"] = st.get("_sess_follows", 0) + 1
                        log(f"  [{a['key']}] followed @{who}")
        open(f"{HERE}/ig_seen.jsonl", "a").write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "acct": a["handle"],
                                                              "src": src, "who": who, "on": good, "blk": blk, "cap": cap[:120]}, ensure_ascii=False) + "\n")
        next_reel()
    return on


def hashtag(a, tag, st, today):
    w.shell("am", "start", "-a", "android.intent.action.VIEW", "-d",
            f"https://www.instagram.com/explore/tags/{urllib.parse.quote(tag)}/", IG); w.sleep(6, 9)
    t = ui(); guard(t)
    tiles = [(int(x), int(y)) for x, y in re.findall(r'label="Reel by [^"]*" id=grid_card_layout_container @\((\d+),(\d+)\)', t) if int(y) < _y(1300)]
    if not tiles: log(f"  [{a['key']}] #{tag}: no reels"); return
    tapd(*random.choice(tiles[:4])); w.sleep(4, 6)
    k = random.randint(6, 10); on = watch_reels(a, k, f"tag:{tag}", st, today)
    log(f"  [{a['key']}] #{tag}: {k} reels, {on} on-topic")
    w.pd("key", DEV, "back"); w.sleep(1, 2); w.pd("key", DEV, "back"); w.sleep(1, 2)


def reels_tab(a, minutes, st, today):
    t = ui(); c = w.coords(t, r"id=clips_tab(?= @)")
    if not c: open_app(); t = ui(); c = w.coords(t, r"id=clips_tab(?= @)")
    if not c: return
    tapd(*c); w.sleep(4, 6)
    end, n, on = time.time() + minutes * 60, 0, 0
    while time.time() < end:
        on += watch_reels(a, 1, "reels", st, today); n += 1
    log(f"  [{a['key']}] reels tab: {n} reels, {on} on-topic")


def session(key, minutes=12):
    a = ACCTS[key]; st = state(); st["_sess_follows"] = 0
    today = datetime.date.today().isoformat()
    log(f"[{key}] IG session @{a['handle']} ({a['lang']}) {minutes:.0f} min")
    if not w.vpn_ok(): raise w.Stop("VPN down")
    # 12 Nov owner: run each IG account on its language's country (es->MX, ja->JP, pt->BR, fr->FR, de->DE)
    name, cc = vpn.COUNTRY[a["lang"]]
    if not vpn.set_country(DEV, name, cc):
        st[f"last_{key}"] = time.time(); json.dump(st, open(STATE_F, "w"), indent=1)   # 13 Nov: a failure is a turn, or the rotation sticks
        log(f"  [{key}] VPN could not switch to {name} - session skipped"); vpn.set_country(DEV, *vpn.COUNTRY["us"]); return
    log(f"  [{key}] VPN {name} ({vpn.ip_country(DEV)})")
    try:
        _session_body(a, key, minutes, st, today)
    finally:
        w.pd("key", DEV, "home")
        ok = vpn.set_country(DEV, *vpn.COUNTRY["us"])
        log(f"  [{key}] VPN back to US: {'ok' if ok else 'FAILED'}")
        if not ok: raise w.Stop("VPN could not return to US")


def _session_body(a, key, minutes, st, today):
    open_app()
    if not switch_to(a["handle"]):
        st[f"last_{key}"] = time.time(); json.dump(st, open(STATE_F, "w"), indent=1)   # 13 Nov: a failure is a turn
        log(f"  [{key}] could not switch to @{a['handle']}"); return
    t0 = time.time()
    # 12 Nov 11:10: NO Reels tab - on the US VPN it serves English content. Only hashtags in the account's language.
    tags = random.sample(a["tags"], len(a["tags"]))
    for tag in tags:
        hashtag(a, tag, st, today)
        if (time.time() - t0) / 60 > minutes - 1.5: break
    st.pop("_sess_follows", None); st.pop("_sess_comments", None); st[f"last_{key}"] = time.time()
    json.dump(st, open(STATE_F, "w"), indent=1)
    log(f"[{key}] session end")


MIN_GAP_MIN = 30
MAX_SESSIONS_DAY = 4


def next_key():
    """16 Nov owner: warm up at the audience's prime time (pranks/plan.warm_eligible). None = every account is resting."""
    st = state()
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pranks")); import plan
    ok = plan.warm_eligible({k: a.get("lang", "en") for k, a in ACCTS.items()})
    # 16 Nov: with only one account in its hours (e.g. Japan at night in Europe) it got 3 sessions in an hour -> bot-like.
    # A human opens the app a few times a day: at least MIN_GAP between two sessions of the same account.
    ok = {k for k in ok if time.time() - st.get(f"last_{k}", 0) >= MIN_GAP_MIN * 60}
    # 23 Nov owner ("gtg for 4 warmups"): with only Yui + Lucia logged in on the Redmi each got 12 sessions/day -> max 4 a day
    try:
        today = time.strftime("%Y-%m-%d"); lines = open(LOG_F).read().splitlines()[-6000:]
        ok = {k for k in ok if sum(1 for l in lines if l.startswith(today) and f"[{k}] session end" in l) < MAX_SESSIONS_DAY}
    except Exception: pass
    return min(ok, key=lambda k: st.get(f"last_{k}", 0)) if ok else None


if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 else "next"
    k = next_key() if k == "next" else k
    if k is None:
        log("rest: no Instagram account is in its audience's hours"); sys.exit(4)
    try:
        session(k, float(sys.argv[2]) if len(sys.argv) > 2 else 12)
    except w.Stop as e:
        log(f"[{k}] STOPPED: {e}"); w.pd("key", DEV, "home"); sys.exit(3)
    except Exception:
        # 16 Nov: Yui/Valentina/Lucia exited 1 after "session end" with no reason logged and the VPN possibly left abroad
        # (the next TikTok warm-up is a US account) -> log the traceback and always try to put the VPN back to the US
        import traceback
        log(f"[{k}] CRASH " + traceback.format_exc()[-700:].replace("\n", " | "))
        try: log(f"  [{k}] VPN back to US after crash: {'ok' if vpn.set_country(DEV, *vpn.COUNTRY['us']) else 'FAILED'}")
        except Exception as e2: log(f"  [{k}] VPN back to US after crash FAILED: {e2}")
        sys.exit(1)
