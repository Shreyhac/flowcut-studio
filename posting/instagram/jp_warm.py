#!/usr/bin/env python3
"""Human-like Instagram warm-up for the 4 new Japanese accounts (20 Nov 2026, owner-approved plan).

One session = 30-40 min, once a day, ~18:00 JST, for days 1-3 before the first post:
  home feed ~2 min -> 2 Japanese AI searches ~8 min -> 3 tracked AI-creator profiles ~10 min -> Reels tab for the rest.
Per reel: relevant = watch 10-25 s (sometimes to 45 s); off-topic = skip after 1.5-4 s; some "興味なし" (Not interested).
Likes / saves / follows are spread at random over relevant reels to hit the day's target (day 1 small, ramps to day 3).
Noise: random 20-60 s pauses, scroll back up, open comments and read, peek at a creator's profile.
Sibling (same phone) accounts follow each other on day 1. Comments (day 3) + sending a reel to the sibling (day 2+) are
NOT built yet: they are skipped with a log line until they are tested.
Hard stop: any challenge / limit / verify screen, or the proxy lock not on -> session ends, alert to #phone-activity.
Never touches Masonry creators / own channels (warmup.blocked) or our other fleet accounts.
usage: jp_warm.py <misaki|ayaka|aoi|miyu> [minutes|auto] [--dry]     (--dry = watch only, no like/save/follow/not-interested)
log: insta/jp_warm.log   per-reel: insta/jp_seen.jsonl   counters: insta/jp_state.json
"""
import datetime, json, os, random, re, sys, time, urllib.parse
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
ACC = json.load(open(f"{HERE}/jp_accounts.json"))
KEY = sys.argv[1]; A = ACC[KEY]
DRY = "--dry" in sys.argv
_m = [x for x in sys.argv[2:] if not x.startswith("--")]
MINUTES = random.uniform(30, 40) if not _m or _m[0] == "auto" else float(_m[0])
os.environ["IG_PHONE"] = A["phone"]
sys.path.insert(0, HERE); import ig_warm as g
w = g.w; DEV = g.DEV; IG = g.IG
LOG_F, SEEN_F, STATE_F = f"{HERE}/jp_warm.log", f"{HERE}/jp_seen.jsonl", f"{HERE}/jp_state.json"

KEYWORDS = ["生成AI", "AI動画", "AI動画生成", "画像生成AI", "AIツール", "AI活用術", "ChatGPT活用", "AIアート", "動画編集", "AIで作ってみた"]
REL = re.compile(r"AI|ＡＩ|ai\b|生成|動画|画像|ツール|ChatGPT|GPT|チャット|プロンプト|編集|アプリ|イラスト|Midjourney|Sora|KLING|Kling|Veo|"
                 r"Gemini|Claude|Canva|副業|便利|自動化|作ってみた|クリエイター", re.I)
TARGETS = {1: dict(like=(5, 8), follow=(1, 2), save=(1, 2), share=(0, 0)),
           2: dict(like=(8, 12), follow=(2, 3), save=(2, 3), share=(1, 1)),    # 21 Nov owner: share reels with the sibling account while warming
           3: dict(like=(10, 15), follow=(3, 4), save=(3, 3), share=(1, 2))}
STOP = re.compile(r"後でもう一度|しばらくしてから|(?<!無)制限|本人確認|アカウントを確認|停止|ロボット|セキュリティコード|確認コード|ブロック|"
                  r"一時的にロック|不審な|ログインしてください|try again later|restrict|confirm it.s you|suspicious|suspended|"
                  r"verify|help us confirm|enter the code|action blocked|log in to continue", re.I)
DISMISS = ["今はしない", "後で", "閉じる", "キャンセル", "スキップ", "OK"]


def log(m):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [{KEY}{' DRY' if DRY else ''}] {m}"
    print(line, flush=True); open(LOG_F, "a").write(line + "\n")


def alert(msg):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "phone_feed")); import phone_feed as pf
        pf.problem(A["phone"], f"jp_warm @{A['handle']}: {msg}"); pf.flush()
    except Exception as e: log(f"alert failed: {e}")


class Stop(Exception): pass


def ui():
    t = g.ui() or ""
    # 24 Nov: "フォローする前にこのアカウントを確認してください" = IG's review sheet for a TARGET account that changed its
    # username (misaki stopped on it at 14:30 after following @acct_147) -> not a challenge; キャンセル (DISMISS) closes it
    m = STOP.search(re.sub(r'"[^"]*(?:のリール動画|さんのリール|キャプション|フォロワーの数は制限|フォローする前に|公開情報を確認)[^"]*"', "", t))   # don't trip on words inside captions / IG's verified-account follower notice (21 Nov)
    cap = A.get("_cap", "")
    # 21 Nov: miyu was stopped by "ロボット" in a reel creator's profile-picture text (@acct_160). A real challenge
    # replaces the reel or sits in a dialog -> on a plain reel screen (no dialog) the words are reel content, not a challenge.
    on_reel = "clips_author_username" in t and not re.search(r"Dialog|dialog_container|bottom_sheet(?!_camera_container)", t)   # 24 Nov: reels page always has bottom_sheet_camera_container
    if m and m.group(0) not in cap and not on_reel:
        try:   # 24 Nov: keep the screen of every stop (2 false stops today had to be guessed)
            os.makedirs(f"{HERE}/out/jp_stops", exist_ok=True); open(f"{HERE}/out/jp_stops/{KEY}_{time.strftime('%Y%m%d_%H%M%S')}.txt", "w").write(t)
        except Exception: pass
        raise Stop("challenge/limit screen: " + m.group(0))
    if re.search(r"Dialog|ボトムシート|bottom_sheet|dialog_container", t):
        for d in DISMISS:
            c = w.coords(t, rf'(?:Button|TextView) "{d}"')
            if c: g.tapd(*c); w.sleep(1, 2); return g.ui() or ""
    return t


def proxy_ok():
    """Safety lock on for THIS account's Android user + the proxy app running in that user.
    20 Nov: the old check read `dumpsys connectivity`, which takes ~60 s on the two-user Realme and timed out -> false STOPs."""
    import subprocess
    serial = "emulator-5554" if A["phone"] == "emulator" else DEV.split(":")[-1]
    u = str(A.get("user", 0))
    try:
        out = subprocess.run([os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"), "-s", serial, "shell",
                              f"settings --user {u} get secure always_on_vpn_app; settings --user {u} get secure always_on_vpn_lockdown; "
                              f"ps -A -o USER,NAME | grep -c 'u{u}_.*com.v2ray.ang'"],
                             capture_output=True, text=True, timeout=25).stdout
    except Exception: return False
    l = [x.strip() for x in out.splitlines() if x.strip()]
    return len(l) >= 3 and l[0] == "com.v2ray.ang" and l[1] == "1" and l[2] != "0"


def state():
    try: return json.load(open(STATE_F))
    except Exception: return {}


def save_state(st): json.dump(st, open(STATE_F, "w"), ensure_ascii=False, indent=1)


def fleet():
    hs = {a["handle"] for a in ACC.values()}
    for f in ("ig_accounts.json", "realme_ig_accounts.json", "../lava/lava_accounts.json"):
        try:
            d = json.load(open(os.path.join(HERE, f)))
            hs |= {v["handle"] for v in (d.values() if isinstance(d, dict) else d) if isinstance(v, dict) and v.get("handle")}
        except Exception: pass
    return {h.lower() for h in hs}


def tracked_pool():
    p = json.load(open(os.path.join(os.path.dirname(HERE), "ugc-search/pools/scan_pool.json")))
    ai = [h for h in p["instagram"] if p["verdicts"].get(f"instagram:{h}") == "KEEP" and re.search(r"ai|gpt|prompt|tool|video|edit|creat", h, re.I)]
    blk, fl = w.blocked(), fleet()
    return [h for h in ai if h.lower() not in blk and h.lower() not in fl and not w.off_target_name(h)]


SKIP_LABEL = re.compile(r"^AIコンテンツ$|他\d+人の要素|リール動画|オリジナル音源|^音源|プロフィール写真")
JA = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def is_ja(text):
    """20 Nov: one katakana (#fypシ) made a French reel 'Japanese' -> need 3+ Japanese characters in the caption itself."""
    return len(JA.findall(text)) >= 3


JP_TRACKED_F = os.path.join(HERE, "jp_tracked.json")


def jp_tracked():
    try: return json.load(open(JP_TRACKED_F))["handles"]
    except Exception: return []


def add_jp_tracked(who):
    """20 Nov: every Japanese AI creator met on a relevant reel joins the tracked list (never blocked / fleet / SA)."""
    try:
        d = json.load(open(JP_TRACKED_F))
        if who and who not in d["handles"]:
            d["handles"].append(who); json.dump(d, open(JP_TRACKED_F, "w"), ensure_ascii=False, indent=1)
    except Exception: pass


AUDIT_DIR = os.path.join(HERE, "out", "jp_audit")


def audit_shot(kind, who):
    """20 Nov: keep a small screenshot of ~1 in 3 reel decisions so accuracy can be measured by hand."""
    try:
        import subprocess
        d = os.path.join(AUDIT_DIR, datetime.date.today().isoformat()); os.makedirs(d, exist_ok=True)
        f = os.path.join(d, f"{KEY}_{datetime.datetime.now():%H%M%S}_{kind}_{(who or 'none')[:30]}")
        serial = "emulator-5554" if A["phone"] == "emulator" else DEV.split(":")[-1]
        png = subprocess.run([os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"), "-s", serial, "exec-out", "screencap", "-p"],
                             capture_output=True, timeout=20).stdout
        open(f + ".png", "wb").write(png)
        subprocess.run(["sips", "-Z", "560", "-s", "format", "jpeg", f + ".png", "--out", f + ".jpg"], capture_output=True, timeout=20)
        os.remove(f + ".png"); return f + ".jpg"
    except Exception: return None


VISION_ON = os.path.join(HERE, "JP_VISION_ON")      # 20 Nov: on only after it is tested; delete the file to turn it off
VLM = "qwen3-vl:2b-instruct"                           # same model as Lavya's feed_training.py


def vision(serial):
    """Look at the frame of a reel that has no usable caption (20 Nov owner: get content accuracy to 90%+).
    Returns dict(japanese, ai_creative, off_target) or None. Never raises; ~3-6 s on the Mac mini."""
    if not os.path.exists(VISION_ON): return None
    try:
        import subprocess, base64, urllib.request
        tmp = f"/tmp/jpv_{KEY}.png"
        png = subprocess.run([os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"), "-s", serial, "exec-out", "screencap", "-p"],
                             capture_output=True, timeout=20).stdout
        open(tmp, "wb").write(png)
        subprocess.run(["sips", "-Z", "512", "-s", "format", "jpeg", tmp, "--out", tmp + ".jpg"], capture_output=True, timeout=20)
        img = base64.b64encode(open(tmp + ".jpg", "rb").read()).decode()
        schema = {"type": "object", "properties": {"japanese": {"type": "boolean"}, "ai_creative": {"type": "boolean"},
                  "off_target": {"type": "boolean"}}, "required": ["japanese", "ai_creative", "off_target"]}
        prompt = ("This is a screenshot of an Instagram Reel. Answer with JSON only. "
                  "japanese: is the on-screen text or the person/setting clearly Japanese? "
                  "ai_creative: is the video about AI tools, AI-generated images/video, ChatGPT, apps, video editing, "
                  "design or digital creativity/tech tips? "
                  "off_target: is it clearly made for a different market than a Japanese audience (language, setting)?")
        body = json.dumps({"model": VLM, "prompt": prompt, "images": [img], "stream": False, "think": False,
                           "keep_alive": "15m", "format": schema, "options": {"temperature": 0}}).encode()
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", body, {"Content-Type": "application/json"})
        out = json.loads(json.loads(urllib.request.urlopen(req, timeout=30).read())["response"])
        return {k: bool(out.get(k)) for k in ("japanese", "ai_creative", "off_target")}
    except Exception as e:
        log(f"  vision skipped: {str(e)[:80]}"); return None


def reel_info(t):
    """(author, caption, ai_tag). Instagram's "AIコンテンツ" chip and "…、他N人の要素" sit where the caption is:
    20 Nov dry run read them as the caption (a non-Japanese reel counted as Japanese AI) -> skip them."""
    who = re.search(r'Button "([\w.]+)\s*" id=clips_author_username', t)
    cap, ai_tag = "", False
    if who:
        for m in re.finditer(r'ViewGroup label="([^"]+)"', t[who.end():]):
            lab = m.group(1)
            if lab == "AIコンテンツ": ai_tag = True; continue
            if SKIP_LABEL.search(lab): continue
            cap = lab; break
    return (who.group(1) if who else ""), cap, ai_tag


def swipe_next():
    g.next_reel()


def swipe_back():
    x = g._x(360 + random.randint(-40, 40))
    w.shell("input", "swipe", str(x), str(g._y(420 + random.randint(-30, 30))), str(x), str(g._y(1250 + random.randint(-30, 30))),
            str(random.randint(250, 400))); w.sleep(1.2, 2)


class Session:
    def __init__(self):
        self.st = state(); self.today = datetime.datetime.now(ZoneInfo("Asia/Tokyo")).date()
        self.day = min(3, max(1, (self.today - datetime.date.fromisoformat(A["created"])).days + 1))
        self.target = {k: random.randint(*v) for k, v in TARGETS[self.day].items()}
        self.done = dict(like=0, follow=0, save=0, share=0); self.share_failed = False; self.t0 = time.time(); self.end = self.t0 + MINUTES * 60
        self.seen = 0; self.rel = 0; self.last_follow = 0; self.blk = w.blocked(); self.fleet = fleet()
        self.next_proxy_check = time.time() + 300
        self.next_ok = {}; self.reel_time = 0.0

    def left(self): return self.end - time.time()

    def p(self, kind):
        """Chance of doing `kind` on this relevant reel so the day's target spreads over the whole session.
        20 Nov: misaki liked 4 reels in 2 min -> estimate seconds/reel from REEL time only (home feed excluded, prior 22 s),
        cap 0.35, and keep a random 60-180 s gap between two actions of the same kind."""
        r = self.target[kind] - self.done[kind]
        if r <= 0 or time.time() < self.next_ok.get(kind, 0): return 0
        rate = (self.rel + 2) / (self.seen + 4)
        per = (self.reel_time + 22 * 4) / (self.seen + 4)
        est = max(1, self.left() / per * rate)
        return min(0.35, r / est)

    def check_proxy(self):
        if time.time() >= self.next_proxy_check:
            if not proxy_ok():
                time.sleep(20)
                if not proxy_ok(): raise Stop("proxy lock not on (2 checks)")
            self.next_proxy_check = time.time() + 300

    def act(self, kind, t, who):
        # 20 Nov: like_button is a ViewGroup on some screens and an ImageView on others -> ayaka got 0 likes in 86 reels
        pat = {"like": r'(?:ViewGroup|ImageView|Button) label="いいね！" id=like_button',
               "save": r'(?:ViewGroup|ImageView|Button) label="保存" id=save_button',
               "follow": r'(?:TextView|Button) "フォロー" label="[^"]*" id=inline_follow_button'}[kind]
        if not w.coords(t, pat): log(f"  {kind}: button not found on @{who}")
        c = w.coords(t, pat)
        if not c: return False
        if DRY: log(f"  (dry) would {kind} @{who}"); return False
        g.tapd(*c); w.sleep(0.8, 1.6); self.done[kind] += 1
        self.next_ok[kind] = time.time() + random.uniform(60, 180)
        log(f"  {kind} @{who} ({self.done[kind]}/{self.target[kind]})")
        if kind == "save":
            t2 = ui()
            if "コレクション" in t2 and "bottom_sheet" in t2: w.pd("key", DEV, "back"); w.sleep(0.8, 1.2)
        return True

    def share_to_sibling(self, t, who):
        """21 Nov owner: like a real user, send a reel to the sibling account.
        IG share sheet (checked on the Lava 21 Nov): search_edit_text -> rows with row_user_secondary_name = handle and a
        CompoundButton recipient_toggle -> a 送信 button appears. The Japanese keyboard turns typed romaji into kana, so the
        handle is PASTED (phonedock clipboard + KEYCODE_PASTE). Any surprise -> back out without sending, no 2nd try."""
        sib = ACC[A["sibling"]]["handle"]
        c = w.coords(t, r'label="シェア" id=direct_share_button')
        if not c: log("  share: no share button"); return False
        if DRY: log(f"  (dry) would share @{who}'s reel with @{sib}"); return False
        g.tapd(*c); w.sleep(2.5, 4)
        sheet = g.ui() or ""; ok = False; why = ""
        name = ACC[A["sibling"]].get("name", "")
        # 21 Nov: on the Realme's Tokyo user the clipboard doesn't reach the app -> first look for the sibling among the
        # suggested recipients (by display name or handle) and tap it; the paste-and-search path is the fallback
        sug = None
        for lab in [x for x in (name, sib) if x]:
            sug = w.coords(sheet, rf'(?:TextView|Button|ViewGroup)[^\n]*"{re.escape(lab)}\s*"')
            if sug: break
        e = w.coords(sheet, r'EditText[^\n]*id=search_edit_text')
        if sug:
            g.tapd(*sug); w.sleep(1.2, 2); sheet = g.ui() or ""
            s_btn = w.coords(sheet, r'(?:Button|TextView)[^\n]*"送信"')
            if not s_btn: why = "picked sibling from suggestions but no 送信 button"
            else:
                g.tapd(*s_btn); w.sleep(2, 3); after = g.ui() or ""
                ok = "direct_private_share" not in after or bool(re.search(r'送信済み|送信しました', after))
                if not ok: why = "送信 tapped but the sheet stayed open"
        elif not e: why = "no search box"
        else:
            g.tapd(*e); w.sleep(0.8, 1.4)
            w.pd("clipboard", DEV, "--set", sib); w.shell("input", "keyevent", "279"); w.sleep(2.5, 4)
            sheet = g.ui() or ""
            if f'"{sib}"' not in sheet: why = "handle did not paste / no result"
            else:
                m = re.search(rf'TextView "{re.escape(sib)}" id=row_user_secondary_name @\((\d+),(\d+)\)', sheet)
                tg = None
                if m:
                    y = int(m.group(2))
                    for mm in re.finditer(r'CompoundButton id=recipient_toggle @\((\d+),(\d+)\)[^\n]*\[off\]', sheet):
                        if abs(int(mm.group(2)) - y) < 70: tg = (int(mm.group(1)), int(mm.group(2))); break
                if not tg: why = "no toggle on the sibling row"
                else:
                    g.tapd(*tg); w.sleep(1.2, 2)
                    if "keyboard" in (g.ui() or ""): w.pd("key", DEV, "back"); w.sleep(0.8, 1.2)   # keyboard can hide 送信
                    sheet = g.ui() or ""
                    s_btn = w.coords(sheet, r'(?:Button|TextView)[^\n]*"送信"')
                    if not s_btn: why = "no 送信 button after selecting"
                    else:
                        g.tapd(*s_btn); w.sleep(2, 3); after = g.ui() or ""
                        ok = "direct_private_share" not in after or bool(re.search(r'送信済み|送信しました', after))
                        if not ok: why = "送信 tapped but the sheet stayed open"
        for _ in range(4):                                  # back to the reel
            if "clips_author_username" in (g.ui() or "") and "direct_private_share" not in (g.ui() or ""): break
            w.pd("key", DEV, "back"); w.sleep(1, 1.6)
        if ok:
            self.done["share"] += 1; self.next_ok["share"] = time.time() + random.uniform(120, 300)
            log(f"  shared @{who}'s reel with sibling @{sib} ({self.done['share']}/{self.target['share']})")
        else:
            self.share_failed = True; log(f"  share: not sent to @{sib} ({why}) - skipped this session")
            try:   # keep what the share sheet showed, to fix the selectors
                os.makedirs(f"{HERE}/out", exist_ok=True)
                open(f"{HERE}/out/share_fail_{KEY}_{time.strftime('%H%M%S')}.txt", "w").write(sheet)
            except Exception: pass
        return ok

    def not_interested(self, t):
        if DRY: return
        c = w.coords(t, r'id=clips_ufi_more_button_component')
        if not c: return
        g.tapd(*c); w.sleep(1.2, 2)
        c = w.coords(ui(), r'"興味なし"')
        if c: g.tapd(*c); w.sleep(1, 1.6); log("  興味なし (not interested)")
        else: w.pd("key", DEV, "back"); w.sleep(0.8, 1.2)

    def peek_comments(self, t):
        c = w.coords(t, r'label="コメントする" id=comment_button')
        if not c: return
        g.tapd(*c); w.sleep(4, 10)
        if random.random() < 0.5:
            w.shell("input", "swipe", str(g._x(360)), str(g._y(1300)), str(g._x(360)), str(g._y(900)), "350"); w.sleep(2, 5)
        w.pd("key", DEV, "back"); w.sleep(1, 1.6)
        if "clips_author_username" not in ui(): w.pd("key", DEV, "back"); w.sleep(1, 1.5)

    def peek_profile(self, t):
        c = w.coords(t, r'id=clips_author_username')
        if not c: return
        g.tapd(*c); w.sleep(3, 5)
        w.shell("input", "swipe", str(g._x(360)), str(g._y(1300)), str(g._x(360)), str(g._y(700)), "400"); w.sleep(2, 5)
        w.pd("key", DEV, "back"); w.sleep(1.2, 2)
        if "clips_author_username" not in ui(): w.pd("key", DEV, "back"); w.sleep(1, 1.5)

    def watch(self, src, force_rel=False):
        """One reel. Returns False if no reel is on screen."""
        self.check_proxy()
        t_reel = time.time()
        t = ui()
        if "clips_author_username" not in t:
            w.sleep(2, 3); t = ui()
            if "clips_author_username" not in t: return False
        who, cap, ai_tag = reel_info(t); A["_cap"] = cap
        blk = who.lower() in self.blk or who.lower() in self.fleet or w.off_target_name(who) or w.off_target(cap)
        jp = is_ja(cap)
        rel = (not blk) and (force_rel or (jp and bool(REL.search(cap + " " + who))))
        vis = None
        if not blk and not force_rel and len(cap.strip()) < 8:      # no usable caption: look at the frame instead
            t0v = time.time(); vis = vision("emulator-5554" if A["phone"] == "emulator" else DEV.split(":")[-1])
            if vis:
                if vis["off_target"]: blk = True
                jp = jp or vis["japanese"]
                rel = (not blk) and vis["japanese"] and vis["ai_creative"]
                log(f"  vision @{who or '?'}: {vis} ({time.time() - t0v:.1f}s)")
        self.seen += 1; self.rel += rel
        if blk or (not jp and not force_rel):
            w.sleep(1.5, 4)
            if random.random() < (0.20 if src == "reels" else 0.10): self.not_interested(t)   # 20 Nov: steer a new feed off Nepali/Turkish/etc faster
            kind = "blocked" if blk else "off"
        elif not rel:                                   # Japanese but not AI: general interest, watch a little
            w.sleep(*((8, 15) if random.random() < 0.2 else (3, 8))); kind = "general"
        else:
            dwell = random.uniform(25, 45) if random.random() < 0.15 else random.uniform(10, 25)
            half = dwell * random.uniform(0.4, 0.7); time.sleep(half)
            r = random.random()
            if r < 0.08: self.peek_comments(t); t = ui()
            elif r < 0.13: self.peek_profile(t); t = ui()
            time.sleep(max(0, dwell - half - 4))
            t = ui() if "clips_author_username" not in t else t
            liked = False
            if random.random() < self.p("like"): liked = self.act("like", t, who)
            if random.random() < self.p("save"): self.act("save", t, who)
            if A.get("sibling") and not self.share_failed and random.random() < self.p("share"): self.share_to_sibling(ui(), who)
            if ((liked or DRY) and time.time() - self.last_follow > 120 and random.random() < self.p("follow")
                    and self.act("follow", ui(), who)):
                self.last_follow = time.time()
            kind = "rel"
            if is_ja(cap) and not force_rel: add_jp_tracked(who)
        shot = audit_shot(kind, who) if random.random() < 0.33 else None
        open(SEEN_F, "a").write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "acct": A["handle"], "src": src,
                                            "who": who, "kind": kind, "ai_tag": ai_tag, "cap": cap[:100], "vision": vis, "shot": shot}, ensure_ascii=False) + "\n")
        self.reel_time += time.time() - t_reel
        if random.random() < 0.03:
            swipe_back(); w.sleep(3, 6); log("  scrolled back up")
        if random.random() < 0.05:
            s = random.uniform(20, 60); log(f"  pause {s:.0f}s"); time.sleep(s)
        swipe_next()
        return True

    def run_reels(self, src, until, force_rel=False, max_n=None):
        n = 0
        while time.time() < min(until, self.end) and (max_n is None or n < max_n):
            if not self.watch(src, force_rel): break
            n += 1
        return n

    def open_url(self, url):
        w.shell("am", "start", "-a", "android.intent.action.VIEW", "-d", url, IG); w.sleep(6, 9)
        return ui()

    def home(self):
        g.open_app(); t = ui(); c = w.coords(t, r"id=feed_tab(?= @)")
        if c: g.tapd(*c); w.sleep(2, 3)
        end = time.time() + random.uniform(60, 120)
        while time.time() < end:
            w.sleep(2, 7); w.shell("input", "swipe", str(g._x(360)), str(g._y(1250)), str(g._x(360 + random.randint(-30, 30))),
                                   str(g._y(random.randint(450, 650))), str(random.randint(250, 450)))
        log("  home feed done")

    def search(self, kw):
        t = self.open_url(f"https://www.instagram.com/explore/tags/{urllib.parse.quote(kw)}/")
        tiles = [(int(x), int(y)) for x, y in re.findall(r'label="[^"]*のリール動画[^"]*" id=grid_card_layout_container @\((\d+),(\d+)\)', t)]
        if not tiles: log(f"  search {kw}: no reels"); return
        g.tapd(*random.choice(tiles[:6])); w.sleep(4, 6)
        n = self.run_reels(f"search:{kw}", time.time() + random.uniform(200, 280))
        log(f"  search {kw}: {n} reels"); w.pd("key", DEV, "back"); w.sleep(1, 2); w.pd("key", DEV, "back"); w.sleep(1, 2)

    def tracked(self, h):
        """20 Nov: profiles load slowly over the proxy and the reel tiles are NOT in the accessibility tree ->
        wait for the real header, open the リール tab, tap a first-row tile by its position inside clips_grid_recyclerview."""
        self.open_url(f"https://www.instagram.com/{h}/")
        t = ""
        for _ in range(8):
            t = ui()
            if "profile_header_familiar_followers_value" in t or "非公開" in t or "見つかりません" in t: break
            w.sleep(2, 3)
        if "profile_header_familiar_followers_value" not in t or "非公開" in t:
            log(f"  tracked @{h}: not readable, skipped"); w.pd("key", DEV, "back"); w.sleep(1, 2); return False
        c = w.coords(t, r'ImageView label="リール[^"]*" id=profile_tab_icon_view')
        if not c: log(f"  tracked @{h}: no reels tab"); w.pd("key", DEV, "back"); w.sleep(1, 2); return False
        g.tapd(*c); m = None
        for _ in range(6):
            w.sleep(2, 3); t = ui()
            m = re.search(r'GridView id=clips_grid_recyclerview @\((\d+),(\d+)\) (\d+)x(\d+)', t)
            if m: break
        if not m: log(f"  tracked @{h}: no reels grid"); w.pd("key", DEV, "back"); w.sleep(1, 2); return False
        cx, cy, gw, gh = map(int, m.groups()); top = cy - gh // 2; tw = gw // 3
        tile_h = min(int(tw * 16 / 9), gh)
        x = cx - gw // 2 + tw * random.randint(0, 2) + tw // 2 + random.randint(-20, 20)
        y = top + tile_h // 2 + random.randint(-30, 30)
        g.tapd(x, y); w.sleep(4, 6)
        n = self.run_reels(f"tracked:{h}", self.end, force_rel=True, max_n=random.randint(3, 6))
        log(f"  tracked @{h}: {n} reels"); w.pd("key", DEV, "back"); w.sleep(1, 2); w.pd("key", DEV, "back"); w.sleep(1, 2)
        return n > 0

    def sibling_follow(self):
        if not A.get("sibling"): return
        sib = ACC[A["sibling"]]["handle"]; k = f"sib_follow_{KEY}"
        if self.st.get(k): return
        t = self.open_url(f"https://www.instagram.com/{sib}/")
        c = w.coords(t, r'(?:Button|TextView) "(?:フォロー|フォローバック|フォローバックする|フォローする)"')   # 21 Nov: a sibling who already follows you shows フォローバック
        if not c: log(f"  sibling @{sib}: no フォロー button (already following?)"); return
        if DRY: log(f"  (dry) would follow sibling @{sib}"); return
        g.tapd(*c); w.sleep(2, 3); self.st[k] = self.today.isoformat(); save_state(self.st); log(f"  followed sibling @{sib}")
        w.pd("key", DEV, "back"); w.sleep(1, 2)

    def reels_tab(self):
        g.open_app(); t = ui(); c = w.coords(t, r"id=clips_tab(?= @)")
        if not c: log("  no reels tab"); return
        g.tapd(*c); w.sleep(4, 6)
        n = self.run_reels("reels", self.end); log(f"  reels tab: {n} reels")

    def run(self):
        log(f"=== session {MINUTES:.1f} min, day {self.day}, targets {self.target}")
        for i in range(3):                                   # 20 Nov: one slow reading right after a user switch killed aoi's session
            if proxy_ok(): break
            log(f"  proxy check {i + 1}/3 failed, retrying in 20 s"); time.sleep(20)
        else: raise Stop("proxy lock not on before start (3 checks)")
        g.open_app()
        cur = g.current()
        if cur != A["handle"] and not g.switch_to(A["handle"]): raise Stop(f"could not switch to @{A['handle']} (on @{cur})")
        self.home()
        self.sibling_follow()   # 21 Nov: until done (state key); misaki/miyu had not followed their sibling on day 1
        for kw in random.sample(KEYWORDS, 2):
            if self.left() < 60: break
            self.search(kw)
        jp = [h for h in jp_tracked() if h.lower() not in self.blk and h.lower() not in self.fleet]
        pool = random.sample(jp, min(4, len(jp))) + random.sample(tracked_pool(), 6); ok = 0   # 20 Nov: Japanese AI creators first
        for h in pool:                                   # 3 readable profiles; a renamed/private one is replaced
            if ok >= 3 or self.left() < 120: break
            ok += bool(self.tracked(h))
        if self.left() > 30: self.reels_tab()
        if self.day >= 3: log("  (comments not built yet - skipped)")
        if self.seen < 5:   # 24 Nov: sakura's emulator lost its network (netsimd crash) -> 0 reels counted as a finished warm-up -> post tried
            log(f"=== EMPTY session: only {self.seen} reels loaded in {(time.time()-self.t0)/60:.1f} min (network/proxy/device problem) - NOT a warm-up")
            alert(f"@{A['handle']}: warm-up loaded only {self.seen} reels (network/device problem) - no post"); sys.exit(4)
        log(f"=== end: {self.seen} reels, {self.rel} relevant, done {self.done} of {self.target}, {(time.time()-self.t0)/60:.1f} min")
        if not DRY:
            st = state(); d = st.setdefault(f"{KEY}_{self.today}", {})
            for k, v in self.done.items(): d[k] = d.get(k, 0) + v
            save_state(st)


if __name__ == "__main__":
    try:
        Session().run()
    except Stop as e:
        log(f"STOPPED: {e}"); alert(str(e)); w.pd("key", DEV, "home"); sys.exit(3)
    except Exception:
        import traceback; log("CRASH " + traceback.format_exc()[-800:].replace("\n", " | ")); w.pd("key", DEV, "home"); sys.exit(1)
    w.pd("key", DEV, "home")
