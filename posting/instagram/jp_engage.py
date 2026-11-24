#!/usr/bin/env python3
"""21 Nov 2026 owner: after a post goes live, our OTHER Japanese accounts show activity on it:
watch the full video, like, save, comment (Japanese), repost, share (send to the sibling account).
Runs ONE account per call (device = that account's phone, from jp_accounts.json).
usage: jp_engage.py <misaki|ayaka|aoi|miyu|sakura> <poster_handle> [--no-comment] [--no-repost] [--no-share]"""
import json, os, random, re, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ACC = json.load(open(f"{HERE}/jp_accounts.json")); KEY, POSTER = sys.argv[1], sys.argv[2]
# 23 Nov owner: Yui (Redmi, English UI, Proton VPN) also engages the new JP posts within 5-10 min - light: watch, like, save,
# comment only ~1 in 3, never repost/share (an always-the-same engagement group is a pattern Instagram looks for)
REDMI_YUI = KEY == "yui"
A = {"phone": "redmi", "handle": "acct_237", "user": 0} if REDMI_YUI else ACC[KEY]
if REDMI_YUI:
    sys.argv += ["--no-repost", "--no-share"] + (["--no-comment"] if random.random() > 0.34 else [])
os.environ["IG_PHONE"] = A["phone"]
sys.path.insert(0, HERE); import ig_warm as g
w, DEV = g.w, g.DEV
LOG = f"{HERE}/jp_engage.log"; USED = f"{HERE}/jp_engage_used.json"
COMMENTS = ["めっちゃ参考になります🙏", "これ知らなかった！", "保存しました✨", "早速やってみます🔥", "わかりやすい！ありがとうございます",
            "すごすぎる…😳", "こういうの待ってました", "勉強になります🙌", "40秒は早すぎる笑", "これは真似したい！"]
def log(m):
    line = time.strftime("%Y-%m-%d %H:%M:%S") + f" [{KEY}] {m}"; print(line, flush=True); open(LOG, "a").write(line + "\n")

def proxy_ok():
    if REDMI_YUI:
        import vpn, atexit
        ok = vpn.set_country(DEV, *vpn.COUNTRY["ja"])
        atexit.register(lambda: vpn.set_country(DEV, *vpn.COUNTRY["us"]))
        return ok
    serial = "emulator-5554" if A["phone"] == "emulator" else DEV.split(":")[-1]; u = str(A.get("user", 0))
    if A["phone"] == "emulator": return True        # emulator: proxy set at boot (start_emulator.sh)
    out = subprocess.run([os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"), "-s", serial, "shell",
                          f"settings --user {u} get secure always_on_vpn_app; settings --user {u} get secure always_on_vpn_lockdown; "
                          f"ps -A -o USER,NAME | grep -c 'u{u}_.*com.v2ray.ang'"], capture_output=True, text=True, timeout=25).stdout
    l = [x.strip() for x in out.splitlines() if x.strip()]
    return len(l) >= 3 and l[0] == "com.v2ray.ang" and l[1] == "1" and l[2] != "0"

def pick_comment():
    used = json.load(open(USED)) if os.path.exists(USED) else []
    c = random.choice([x for x in COMMENTS if x not in used[-12:]] or COMMENTS)
    json.dump((used + [c])[-50:], open(USED, "w"), ensure_ascii=False); return c

def paste(text):
    w.pd("clipboard", DEV, "--set", text); w.shell("input", "keyevent", "279"); w.sleep(1.5, 2.5)

def on_post(t): return "row_feed_button_like" in t or "like_button" in t

def back_to_post():
    """close a share sheet / comment composer / keyboard on top of the post; never back out of the post itself"""
    for _ in range(4):
        t = g.ui() or ""
        if on_post(t) and not re.search(r"direct_private_share|layout_comment_thread|comment_composer|keyboard", t): return t
        if not re.search(r"direct_private_share|layout_comment_thread|comment_composer|keyboard|bottom_sheet", t): return t
        w.pd("key", DEV, "back"); w.sleep(1.2, 1.8)
    return g.ui() or ""

def main():
    if not proxy_ok(): log("STOP: proxy lock not on"); sys.exit(3)
    g.open_app(); w.sleep(3, 4)
    if g.current() != A["handle"] and not g.switch_to(A["handle"]): log(f"could not switch to @{A['handle']}"); sys.exit(2)
    w.shell("am", "start", "-a", "android.intent.action.VIEW", "-d", f"https://www.instagram.com/{POSTER}/", g.IG); w.sleep(6, 8)
    tile = None
    for i in range(6):
        t = g.ui() or ""
        tile = w.coords(t, r'Button label="[^"]*(?:1行、1列|row 1, column 1)"')
        if tile: break
        w.shell("input", "swipe", "360", "1200", "360", "700", "400"); w.sleep(2, 3)
    if not tile: log(f"could not find @{POSTER}'s newest post"); sys.exit(2)
    g.tapd(*tile); w.sleep(4, 6)
    t = g.ui() or ""
    if not on_post(t): log("post did not open"); sys.exit(2)
    done = []
    watch = random.uniform(51, 58)   # video is 49 s -> always the whole video
    log(f"watching @{POSTER}'s newest post {watch:.0f}s"); time.sleep(watch); done.append("watched")
    t = g.ui() or ""
    if not on_post(t): log("post left the screen during the watch - no like/save"); sys.exit(2)   # 21 Nov owner: only like after the FULL video
    c = w.coords(t, r'Button label="(?:いいね！|Like)" id=(?:row_feed_button_like|like_button)')
    if c: g.tapd(*c); done.append("like"); w.sleep(1.5, 3)
    t = g.ui() or ""
    c = w.coords(t, r'label="(?:\[保存済み\]に追加|保存|Save|Add to Saved)" id=(?:row_feed_button_save|save_button)')
    if c:
        g.tapd(*c); done.append("save"); w.sleep(1.5, 2.5)
        t2 = g.ui() or ""
        if ("コレクション" in t2 or "Collection" in t2) and not on_post(t2): w.pd("key", DEV, "back"); w.sleep(1, 1.5)   # only a real collections sheet, not the saved toast
    if "--no-comment" not in sys.argv:
        text = pick_comment(); t = back_to_post()
        c = w.coords(t, r'label="(?:コメントする|Comment)" id=(?:row_feed_button_comment|comment_button)')
        if c:
            g.tapd(*c); w.sleep(2.5, 3.5); t = g.ui() or ""
            e = w.coords(t, r'(?:AutoCompleteTextView|EditText)[^\n]*id=(?:layout_comment_thread_edittext\w*|comment_composer\w*)')
            if e:
                g.tapd(*e); w.sleep(1, 1.5); paste(text); t = g.ui() or ""
                if text[:4] in t:
                    p = w.coords(t, r'id=layout_comment_thread_post_button\w*') or w.coords(t, r'(?:Button|TextView) "(?:投稿する|投稿|Post)"')
                    if p: g.tapd(*p); done.append(f"comment:{text}"); w.sleep(2.5, 3.5)
                    else: log("comment: no post button")
                else: log("comment: text did not paste (skipped)")
            back_to_post()
    if "--no-repost" not in sys.argv:
        t = back_to_post(); c = w.coords(t, r'Button id=reposts_ufi_icon')   # 21 Nov: the "再投稿" text label does nothing; the icon reposts
        if c:
            g.tapd(*c); w.sleep(1.5, 2.5); t = g.ui() or ""
            if "再投稿済み" in t or "元に戻す" in t: done.append("repost")
            else: log("repost: tapped but no 再投稿済み confirmation")
        else: log("repost: button not on screen (skipped)")
    if "--no-share" not in sys.argv and A.get("sibling"):
        sib = ACC[A["sibling"]]; t = back_to_post()
        c = w.coords(t, r'id=row_feed_button_share') or w.coords(t, r'label="シェア" id=direct_share_button')
        if c:
            g.tapd(*c); w.sleep(2.5, 4); s = g.ui() or ""
            tg = w.coords(s, rf'(?:TextView|Button|ViewGroup)[^\n]*"(?:{re.escape(sib["name"])}|{re.escape(sib["handle"])})\s*"')
            if not tg:
                e = w.coords(s, r'EditText[^\n]*id=search_edit_text')
                if e:
                    g.tapd(*e); w.sleep(0.8, 1.2); paste(sib["handle"]); s = g.ui() or ""
                    m = re.search(rf'TextView "{re.escape(sib["handle"])}" id=row_user_secondary_name @\((\d+),(\d+)\)', s)
                    if m:
                        y = int(m.group(2))
                        for mm in re.finditer(r'CompoundButton id=recipient_toggle @\((\d+),(\d+)\)[^\n]*\[off\]', s):
                            if abs(int(mm.group(2)) - y) < 70: tg = (int(mm.group(1)), int(mm.group(2))); break
            if tg:
                g.tapd(*tg); w.sleep(1.2, 2)
                if "keyboard" in (g.ui() or ""): w.pd("key", DEV, "back"); w.sleep(0.8, 1.2)
                b = w.coords(g.ui() or "", r'(?:Button|TextView)[^\n]*"送信"')
                if b: g.tapd(*b); w.sleep(2, 3); done.append(f"share->{sib['handle']}")
            else: log(f"share: sibling @{sib['handle']} not found (skipped)")
            back_to_post()
        else: log("share: share button not on screen (skipped)")
    log(f"on @{POSTER}: {', '.join(done)}")
    w.pd("key", DEV, "home")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; log("CRASH " + traceback.format_exc()[-500:].replace("\n", " | ")); w.pd("key", DEV, "home"); sys.exit(1)
