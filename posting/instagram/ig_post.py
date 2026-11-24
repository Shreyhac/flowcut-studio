#!/usr/bin/env python3
"""Post one localized template video as an Instagram Reel from the Redmi (12 Nov 2026).

usage: ig_post.py <name>          name = ig_<template>_<igkey>; cfg/<name>.json has igkey, handle, caption, template
env STOP_BEFORE_POST=1            stop on the final screen (testing)
Flow: push video to DCIM/Camera (stamped now) -> switch IG account -> Create (+) -> newest gallery item -> Next ->
editor Next -> caption (typed once, verified) -> "Add AI label" on -> Share. Logs ig_posts.jsonl.
"""
import datetime, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ig_warm as g
w, DEV, PD = g.w, g.DEV, g.w.PD
name = sys.argv[1]
C = json.load(open(f"{HERE}/cfg/{name}.json"))
# 12 Nov owner: post from the account's language country; always return to the US (TikTok) afterwards
import atexit, vpn
_lang = json.load(open(f"{HERE}/ig_accounts.json"))[C["igkey"]]["lang"]
if not vpn.set_country(DEV, *vpn.COUNTRY[_lang]):
    vpn.set_country(DEV, *vpn.COUNTRY["us"]); sys.exit("VPN could not switch to " + vpn.COUNTRY[_lang][0])
atexit.register(lambda: vpn.set_country(DEV, *vpn.COUNTRY["us"]))
def step(m): print(datetime.datetime.now().strftime("%H:%M:%S"), m, flush=True)
def sh(*a): return w.shell(*a)
def ui(): return g.ui()
def wait(pat, secs=30):
    end = time.time() + secs
    while time.time() < end:
        t = ui(); g.guard(t)
        if re.search(pat, t): return t
        time.sleep(1.5)
    return None
def tapc(t, pat):
    c = w.coords(t, pat)
    if c: g.tapd(*c)
    return c

# 1. video into the gallery, newest item. Remove earlier uploads of ours first (only our VID_..._ig_* files).
remote = f"/sdcard/DCIM/Camera/VID_{datetime.datetime.now():%Y%m%d_%H%M%S}_{name}.mp4"
for fn in (sh("ls /sdcard/DCIM/Camera") or "").split():
    if re.match(r"VID_2026\d{4}_\d{6}_(ig_|remix_|ugc_|igtest).*\.mp4$", fn):
        sh(f"content delete --uri content://media/external/video/media --where \"_data='/storage/emulated/0/DCIM/Camera/{fn}'\"")
        sh(f"rm -f '/sdcard/DCIM/Camera/{fn}'")
subprocess.run([PD, "push", DEV, f"{HERE}/out/{name}.mp4", remote], check=True, capture_output=True)
sh(f"touch '{remote}'"); time.sleep(1)
sh("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", "file://" + remote); time.sleep(3)
step("pushed " + remote)

# 2. account
g.open_app()
for _ in range(3):
    if g.switch_to(C["handle"]): break
    sh("am", "force-stop", g.IG); time.sleep(3); g.open_app()
else: sys.exit("could not switch to " + C["handle"])
step("on @" + C["handle"])
def post_count():
    t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
    if c: g.tapd(*c); time.sleep(3); t = ui()
    m = re.search(r'TextView "([\d,.]+)" id=profile_header_familiar_post_count_value', t)
    return int(m.group(1).replace(",", "").replace(".", "")) if m else None
before = post_count(); step(f"posts before: {before}")
# 13 Nov 06:20: Lucia's 12 Nov upload was logged as killed (exit -15) but had gone live; the retry would have posted a duplicate.
# Never post when the profile already has more posts than ig_posts.jsonl records as live for this handle.
_live = sum(1 for l in open(f"{HERE}/ig_posts.jsonl") if l.strip() and json.loads(l)["acct"] == C["handle"] and not json.loads(l)["name"].endswith("__notlive"))
if before is not None and before > _live:
    sys.exit(f"UNRECORDED POST: @{C['handle']} shows {before} posts but ig_posts.jsonl has {_live} live - check the profile before posting again")

# 3. Create -> gallery
t = ui(); tapc(t, r'id=feed_tab(?= @)'); time.sleep(3); t = ui()
if not tapc(t, r'id=action_bar_left_button(?= @)'):
    tapc(t, r'label="Create New"')
t = wait(r'"New post"|id=gallery_grid_item_thumbnail', 20)
if not t: sys.exit("gallery did not open")
time.sleep(2); t = ui()
# the newest item must be ours: its label carries today's date; pick the first video thumbnail
vids = re.findall(r'Button label="(Selected|Unselected) Video thumbnail created on ([^"]+)" id=gallery_grid_item_thumbnail @\((\d+),(\d+)\)', t)
if not vids: sys.exit("no video in gallery")
today = (sh("date '+%B %-d, %Y'") or "").strip() or datetime.datetime.now().strftime("%B %-d, %Y")   # gallery labels use the PHONE's clock (US tz)
first = vids[0]
if today not in first[1]: sys.exit(f"newest gallery video is not ours: {first[1]}")
if first[0] != "Selected": g.tapd(int(first[2]), int(first[3])); time.sleep(2)
step("selected " + first[1])
t = ui(); tapc(t, r'Button "Next" id=next_button_textview')
t = wait(r'id=clips_right_action_button', 40)
if not t: sys.exit("editor did not open")
time.sleep(2)
# 13 Nov 06:25: an account's first Reel shows a "Video posts are now shared as reels" sheet over the editor; its OK must be
# tapped first, or the Next tap lands on the sheet and the share screen never opens (Lucia/Camila failed this way)
for _ in range(3):
    t = ui()
    if "now shared as reels" in t or "bb_primary_action_container" in t:
        tapc(t, r'Button label="OK" id=bb_primary_action_container'); time.sleep(2); continue
    break
tapc(ui(), r'id=clips_right_action_button')
t = wait(r'id=caption_input_text_view', 40)
if not t and "bb_primary_action_container" in (ui() or ""):      # the sheet can also appear after Next
    tapc(ui(), r'Button label="OK" id=bb_primary_action_container'); time.sleep(2)
    tapc(ui(), r'id=clips_right_action_button'); t = wait(r'id=caption_input_text_view', 40)
if not t: sys.exit("share screen did not open")
step("share screen")
time.sleep(2); t = ui()
if "clips_download_privacy_nux_button" in t: tapc(t, r'id=clips_download_privacy_nux_button'); time.sleep(2)

# 4. caption (type once; verify)
CAP = C["caption"].strip()   # 12 Nov 17:50 owner: NO hashtags on Instagram - keywords live in the caption text
tapc(ui(), r'id=caption_input_text_view'); time.sleep(1.5)
subprocess.run([PD, "type", DEV, CAP + " "], capture_output=True); time.sleep(2)
t = ui(); m = re.search(r'AutoCompleteTextView "(.*?)"[^\n]*id=caption_input_text_view', t, re.S)
seen = (m.group(1) if m else "").replace("\\n", "\n")   # 13 Nov: get_ui escapes line breaks as a literal \n (Yui failed the check)
step("caption: " + seen[:120])
# 12 Nov 14:25: the field shows a shortened preview ending in "…" for long captions (#masonryai is at the end):
# accept when the visible text is a long-enough prefix of what we typed
vis = seen.rstrip().rstrip("…").rstrip()
if not (len(vis) >= 30 and CAP.startswith(vis)) and vis.strip() != CAP.strip():
    sys.exit("caption check failed: " + seen[:80])
w.pd("key", DEV, "back"); time.sleep(1.5)          # close keyboard
if "id=caption_input_text_view" not in ui(): sys.exit("left the share screen while closing the keyboard")

# 5. AI label on (scroll into view if needed)
for _ in range(3):
    t = ui()
    m = re.search(r'TextView "Add AI label"[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*View @\((\d+),(\d+)\)[^\n]*\[clickable,(on|off)\]', t)
    if m: break
    w.shell("input", "swipe", "360", "1100", "360", "700", "300"); time.sleep(1.5)
if m and m.group(3) == "off":
    g.tapd(int(m.group(1)), int(m.group(2))); time.sleep(2)
    t = ui(); b = w.coords(t, r'Button "(Turn on|Add label|Continue)"')
    if b: g.tapd(*b); time.sleep(2)
t = ui(); ok = re.search(r'TextView "Add AI label"[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*\[clickable,on\]', t)
step("AI label: " + ("on" if ok else "NOT SET"))

if os.environ.get("STOP_BEFORE_POST"): sys.exit("stopped before post (debug)")
# 6. share
t = ui()
if not tapc(t, r'id=share_button(?= @)'): sys.exit("share button not found")
time.sleep(4)
for _ in range(3):        # 12 Nov 16:15: an "About Reels" sheet asks for a final Share (label="Share"); it was never tapped
    t = ui()
    if tapc(t, r'id=clips_nux_sheet_share_button(?= @)') or tapc(t, r'Button label="Share"') or tapc(t, r'Button "Share"'):
        time.sleep(4); continue
    if "id=share_button" not in t: break
    time.sleep(3)
step("share tapped")
# 3) verify: the profile's post count must go up (upload can take a minute)
ok = False
for _ in range(12):
    time.sleep(15)
    g.open_app(); n = post_count()
    if before is not None and n is not None and n > before: ok = True; break
if not ok: sys.exit(f"NOT LIVE: post count still {n} (was {before})")
step(f"shared and live: posts {before} -> {n}")
_q = remote.replace("/sdcard", "/storage/emulated/0")
sh(f"nohup sh -c \"sleep 300; content delete --uri content://media/external/video/media --where \\\"_data='{_q}'\\\"; rm -f '{remote}'\" >/dev/null 2>&1 &")
open(f"{HERE}/ig_posts.jsonl", "a").write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "name": name,
    "acct": C["handle"], "caption": CAP, "template": C.get("template")}, ensure_ascii=False) + "\n")
w.pd("key", DEV, "home")
