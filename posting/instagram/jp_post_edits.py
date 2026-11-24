#!/usr/bin/env python3
"""JP COPY (23 Nov): ig_post_edits.py for the Japanese accounts on the Lava / Realme user 10 / emulator.
Differences: no Proton VPN switching (the phone/user is on the always-on JP proxy -> checked, never changed);
Edits app language set to English for that Android user so the English label matching works; Realme user 10
gets the video through MediaStore (content insert/write --user 10) because shell cannot write /storage/emulated/10.
usage: jp_post_edits.py <name>   (cfg/<name>.json with "jp_key")

Original: Post one localized template video to Instagram THROUGH THE EDITS APP (13 Nov 2026, owner).

Owner, 13 Nov 11:40-12:10: "upload the videos from the Edits app, not from Instagram directly"; the music named in the
script goes on in Edits; "if the music link is an original audio, use that original audio at 20-30% so it isn't audible;
for the rest use our own video". So:
  - GTA copies (gta1_jazz, gta2_xavier): the delivered file is VOICE ONLY (baked-in music removed, see out/with_music/)
    and Edits adds dennyintech's "Original audio" (the GTA script's inspiration reel, audio 39984116737869879) at ~25%.
    The audio must first be SAVED on that Instagram account; Edits lists it under Audio > Saved.
  - highway_explainer copies: our own video as it is, no added audio.
Caption = cfg caption (account's language + [bracketed meta keywords], no #/@), "(?:Add AI label|AIラベルを追加する)" on.
A post counts only when the Instagram profile's post count goes up.

usage: ig_post_edits.py <name>        name = ig_<template>_<igkey>
env STOP_BEFORE_SHARE=1                stop on Edits' "New reel" screen (testing)
"""
import atexit, datetime, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_C0 = json.load(open(f"{HERE}/cfg/{sys.argv[1]}.json")); JA = json.load(open(f"{HERE}/jp_accounts.json"))[_C0["jp_key"]]
os.environ["IG_PHONE"] = JA["phone"]; USER = int(JA.get("user", 0))
import ig_warm as g
w, DEV, PD = g.w, g.DEV, g.w.PD
EDITS = "com.instagram.basel"
GTA_AUDIO_ID = "39984116737869879"            # dennyintech "Original audio" (GTA script inspiration reel DfiFm33pMpu)
GTA_AUDIO_URL = f"https://www.instagram.com/reels/audio/{GTA_AUDIO_ID}/"
VOL_LO, VOL_HI, VOL_TARGET = 20, 30, 25

name = sys.argv[1]
C = json.load(open(f"{HERE}/cfg/{name}.json"))
HANDLE, TPL = C["handle"], C["template"]
ADD_AUDIO = TPL in ("gta1_jazz", "gta2_xavier")


def step(m): print(datetime.datetime.now().strftime("%H:%M:%S"), m, flush=True)
def sh(*a): return w.shell(*a)
def ui():
    # 13 Nov: right after a sheet opens in Edits the dump can come back empty; retry, then log why
    err = ""
    for _ in range(4):
        r = subprocess.run([PD, "ui", DEV, "--no-ocr"], capture_output=True, text=True, timeout=90)
        if r.stdout.strip():
            if "Allow the use of cookies by Instagram?" in r.stdout: return g.ui()   # 14 Nov: EU cookie pop-up -> declined there
            return r.stdout
        err = (r.stderr or "").strip()[-200:]; time.sleep(2)
    r = subprocess.run([PD, "ui", DEV], capture_output=True, text=True, timeout=120)   # OCR fallback (video playing)
    return r.stdout or ""
def tap(x, y): w.tap(x, y)
def tapc(t, pat):
    c = w.coords(t, pat)
    if c: tap(*c)
    return c
def wait(pat, secs=30, every=1.5):
    end = time.time() + secs
    while time.time() < end:
        t = ui(); g.guard(t)
        if re.search(pat, t): return t
        time.sleep(every)
    return None
def die(msg):
    try: open(f"{HERE}/out/edits_fail_{name}.txt", "w").write(ui())   # the screen at the failure
    except Exception: pass
    sys.exit(msg)


# 0. VPN = the account's language country; always back to the US afterwards
# 14 Nov: the Realme posts its own accounts (run with IG_PHONE=realme); the cfg says which phone holds the account
SERIAL = "emulator-5554" if JA["phone"] == "emulator" else DEV.split(":")[-1]
def adbsh(cmd, timeout=60, stdin=None):
    return subprocess.run(["adb", "-s", SERIAL, "shell", cmd], capture_output=True, text=True, timeout=timeout,
                          stdin=stdin).stdout
def chrome_copy(seg):
    """23 Nov: put text on THIS Android user's clipboard. The Mac clipboard never reaches Realme user 10, Play Protect
    blocks ADBKeyboard, `input text` can't do Japanese -> share the text to Chrome (it opens a Google search with the
    text in the search box), select it and copy with real key events. Verified on the Realme 23 Nov 05:03."""
    adbsh(f"am start --user {USER} -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT '{seg}' com.android.chrome")
    time.sleep(6)
    # 23 Nov 15:51: a tap that missed the box made Ctrl+A select the whole results page -> copy only while the
    # search box has the keyboard up (input focused)
    for _ in range(4):
        adbsh("input tap 534 541"); time.sleep(1.8)                   # the Google search box (1080x2412 Realme)
        if "mInputShown=true" in adbsh("dumpsys input_method | grep -m1 mInputShown"):
            adbsh("input keycombination 113 29"); time.sleep(0.5); adbsh("input keycombination 113 31"); time.sleep(1)
            break
        adbsh("input keyevent 4"); time.sleep(1); adbsh("input swipe 540 700 540 1500 300"); time.sleep(1.5)   # back to the top
    else:
        step("chrome copy: search box never took focus")
    adbsh("am force-stop com.android.chrome"); time.sleep(1)

def _cap_text():
    m = re.search(r'AutoCompleteTextView "(.*?)"[^\n]*id=caption_input_text_view', ui(), re.S)
    return (m.group(1) if m else "").replace("\\n", "\n")

def adb_type(text):
    """Caption into the Instagram field on a user the clipboard can't reach, line by line (the search box is one line).
    Each line is checked in the field after pasting and retried (23 Nov: the first paste of a run went nowhere)."""
    c = w.coords(ui(), r"id=caption_input_text_view")
    if c: adbsh(f"input tap {c[0]} {c[1]}"); time.sleep(1)
    adbsh("input keycombination 113 29"); time.sleep(0.4); adbsh("input keyevent 67"); time.sleep(0.5)   # start empty
    for k, seg in enumerate(text.split("\n")):
        if k: adbsh("input keyevent 66"); time.sleep(0.5)             # newline in the caption
        if not seg.strip(): continue
        probe = seg.strip()[:12]
        for _att in range(3):
            chrome_copy(seg.replace("'", " "))
            c = w.coords(ui(), r"id=caption_input_text_view")         # closing Chrome normally returns to the New reel page
            for app in (EDITS, g.IG):
                if c: break
                adbsh(f"monkey -p {app} -c android.intent.category.LAUNCHER 1"); time.sleep(4)
                c = w.coords(ui(), r"id=caption_input_text_view")
            if not c: break
            if not re.search(r'caption_input_text_view[^\n]*focused', ui()):
                adbsh(f"input tap {c[0]} {c[1]}"); time.sleep(1.2)
            adbsh("input keycombination 113 123"); time.sleep(0.3)       # Ctrl+End: end of the WHOLE text (MOVE_END = end of the line)
            adbsh("input keyevent 279"); time.sleep(1.8)                 # paste
            if probe in _cap_text(): break
            step(f"line {k + 1} not in the caption yet, copying again ({_att + 1}/3)")

def proxy_ok():
    out = adbsh(f"am get-current-user; settings --user {USER} get secure always_on_vpn_app; settings --user {USER} get secure always_on_vpn_lockdown; "
                f"ps -A -o USER,NAME | grep -c 'u{USER}_.*com.v2ray.ang'")
    l = [x.strip() for x in out.splitlines() if x.strip()]
    return len(l) >= 4 and l[0] == str(USER) and l[1] == "com.v2ray.ang" and l[2] == "1" and l[3] != "0"
if not proxy_ok(): sys.exit(f"JP proxy / Android user {USER} not active on the {JA['phone']} - not posting")
# Edits in English for this Android user only (label matching); the system and Instagram stay Japanese
adbsh(f"cmd locale set-app-locales {EDITS} --user {USER} --locales en-US")
for _perm in ("READ_MEDIA_VIDEO", "READ_MEDIA_IMAGES", "READ_MEDIA_VISUAL_USER_SELECTED", "POST_NOTIFICATIONS"):   # 23 Nov: JP permission dialogs blocked Edits
    adbsh(f"pm grant --user {USER} {EDITS} android.permission.{_perm}")

# 1. video into the gallery as the newest item (remove earlier uploads of ours and old Edits exports first)
remote = f"/sdcard/DCIM/Camera/VID_{datetime.datetime.now():%Y%m%d_%H%M%S}_{name}.mp4"
DISP = os.path.basename(remote)
def push_video():
    if USER == 0:
        return subprocess.run([PD, "push", DEV, f"{HERE}/out/{name}.mp4", remote], capture_output=True).returncode == 0
    # user 10: old uploads of ours out, then a new MediaStore row + its bytes
    adbsh(f"content delete --user {USER} --uri content://media/external/video/media --where \"_display_name LIKE 'VID_2026%ig_%'\"")
    adbsh(f"content insert --user {USER} --uri content://media/external/video/media --bind _display_name:s:{DISP} "
          f"--bind relative_path:s:DCIM/Camera/ --bind mime_type:s:video/mp4")
    q = adbsh(f"content query --user {USER} --uri content://media/external/video/media --projection _id:_display_name --where \"_display_name='{DISP}'\"")
    m = re.search(r"_id=(\d+)", q)
    if not m: return False
    with open(f"{HERE}/out/{name}.mp4", "rb") as fh:
        subprocess.run(["adb", "-s", SERIAL, "shell", f"content write --user {USER} --uri content://media/external/video/media/{m.group(1)}"],
                       stdin=fh, capture_output=True, timeout=300)
    sz = adbsh(f"content query --user {USER} --uri content://media/external/video/media/{m.group(1)} --projection _size")
    return str(os.path.getsize(f"{HERE}/out/{name}.mp4")) in sz
for fn in (sh("ls /sdcard/DCIM/Camera") or "").split():
    if re.match(r"VID_2026\d{4}_\d{6}_(ig_|remix_|ugc_|igtest).*\.mp4$", fn):
        sh(f"content delete --uri content://media/external/video/media --where \"_data='/storage/emulated/0/DCIM/Camera/{fn}'\"")
        sh(f"rm -f '/sdcard/DCIM/Camera/{fn}'")
for fn in (sh("ls /sdcard/Movies/Edits") or "").split():
    if fn.endswith("_bsl.mp4"):
        sh(f"content delete --uri content://media/external/video/media --where \"_data='/storage/emulated/0/Movies/Edits/{fn}'\"")
        sh(f"rm -f '/sdcard/Movies/Edits/{fn}'")
for _push_try in range(4):   # 21 Nov: the Redmi drops off USB for a few seconds at times -> retry the copy
    if push_video(): break
    time.sleep(15)
else:
    sys.exit("push failed 4 times (phone off USB?)")
if USER == 0:
    sh(f"touch '{remote}'"); time.sleep(1)
    sh("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", "file://" + remote); time.sleep(3)
step("pushed " + remote)

# 2. Instagram app: the account, its post count, the duplicate guard, and (GTA) the saved audio
g.open_app()
for _ in range(3):
    if g.switch_to(HANDLE): break
    sh("am", "force-stop", g.IG); time.sleep(3); g.open_app()
else: sys.exit("could not switch Instagram to " + HANDLE)
def post_count():
    t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
    if c: tap(*c); time.sleep(3); t = ui()
    m = re.search(r'TextView "([\d,.]+)" id=profile_header_familiar_post_count_value', t)
    return int(m.group(1).replace(",", "").replace(".", "")) if m else None
before = post_count(); step(f"on @{HANDLE}, posts before: {before}")
_live = sum(1 for l in open(f"{HERE}/ig_posts.jsonl") if l.strip() and json.loads(l)["acct"] == HANDLE and not json.loads(l)["name"].endswith("__notlive"))
if before is not None and before > _live:
    sys.exit(f"UNRECORDED POST: @{HANDLE} shows {before} posts but ig_posts.jsonl has {_live} live - check the profile before posting again")
if ADD_AUDIO:
    sh("am", "start", "-a", "android.intent.action.VIEW", "-d", GTA_AUDIO_URL, g.IG)
    t = wait(r"id=secondary_bar_save_button", 25)
    if not t: die("audio page did not open")
    if not re.search(r'id=secondary_bar_save_button[^\n]*selected', t):   # 14 Nov: label is "Save Audio" on the Realme; selected = saved
        tapc(t, r'id=secondary_bar_save_button'); time.sleep(2); t = ui()
    if not re.search(r'id=secondary_bar_save_button[^\n]*selected', t): die("could not save the GTA audio")
    c = w.coords(t, r'id=preview_button')            # stop the preview if it auto-plays
    step("GTA audio saved on @" + HANDLE)
    sh("input", "keyevent", "HOME"); time.sleep(1)

# 3. Edits: right account, clean start
def edits_home():
    # 14 Nov: a menu left open by an earlier run comes back on relaunch and hides the home buttons -> always start Edits fresh
    sh("am", "force-stop", EDITS); time.sleep(1)
    sh("monkey", "-p", EDITS, "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(6)
    for _ in range(18):   # 24 Nov: after an account switch Edits took longer than 10 rounds to show its home (miyu)
        t = ui(); g.guard(t)
        if "id=project_plus_button" in t: return t
        if tapc(t, r'Button "Not now"'): time.sleep(2); continue                  # Google Play review prompt
        if tapc(t, r'(?:Button|TextView) "(?:許可しない|Don.t allow)"'): time.sleep(2); continue   # 23 Nov: Android notification permission (JP system UI)
        if EDITS not in (sh("dumpsys window | grep mCurrentFocus") or ""):
            sh("monkey", "-p", EDITS, "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(6); continue
        # logged out of Edits: it offers "Continue with Instagram <the Instagram app's current account>" (no password).
        # Step 2 put the Instagram app on HANDLE, so continue only if that is the account offered.
        # 24 Nov: the new Edits says "Log in with Instagram" / 「Instagramでログイン」 (miyu's post logged back in as aoi)
        if re.search(r"Continue with Instagram|Log in with Instagram|Instagramでログイン|Instagramで続ける", t):
            if re.search(rf'TextView "{re.escape(HANDLE)}" id=ig_text', t):
                tapc(t, rf'TextView "{re.escape(HANDLE)}" id=ig_text') or tapc(t, r'"(?:Continue with Instagram|Log in with Instagram|Instagramでログイン)"'); time.sleep(8); continue
            if tapc(t, r'"(?:Switch accounts|アカウントを切り替える)"'): time.sleep(4); continue
        if re.search(r"Choose an Instagram account|Instagramアカウントを選択|アカウントを選択", t):
            if tapc(t, rf'TextView "{re.escape(HANDLE)}"'): time.sleep(8); continue
            die(f"{HANDLE} is not offered in Edits' account list")
        if tapc(t, r'"Join Edits"'): time.sleep(6); continue
        if "Choose where to share" in t or "basel_postcapture" in t or "New reel" in t:
            sh("input", "keyevent", "BACK"); time.sleep(2)
            t2 = ui()
            if tapc(t2, r'Button "(?:Discard|Start over|Delete)"') or tapc(t2, r'"(?:Discard|Start over)"'): time.sleep(2)
            continue
        sh("input", "keyevent", "BACK"); time.sleep(2)
    die("Edits home did not open")

t = edits_home()
tapc(t, r'id=igds_profile_picture'); time.sleep(3); t = ui()
if not re.search(rf'TextView "{re.escape(HANDLE)}" id=ig_text', t) and tapc(t, r'id=settings_switch_accounts'):
    # 23 Nov (aoi after miyu on the Realme): both already joined Edits -> its own account list has HANDLE
    time.sleep(3); t2 = ui()
    if tapc(t2, rf'(?:TextView|Button)[^\n]*"{re.escape(HANDLE)}"'):
        time.sleep(8); t = edits_home(); tapc(t, r'id=igds_profile_picture'); time.sleep(3); t = ui()
        step("Edits: switched with its own account list")
    else:
        sh("input", "keyevent", "BACK"); time.sleep(2); t = ui()
if not re.search(rf'TextView "{re.escape(HANDLE)}" id=ig_text', t):
    # Edits' own switch list only has accounts that already joined and otherwise asks for a password, so instead:
    # log out of Edits -> "Continue with Instagram" as the Instagram app's current account (= HANDLE, step 2)
    if not tapc(t, r'id=settings_logout'): die("no Log out in Edits settings")
    time.sleep(2); t = wait(r'id=igds_alert_dialog_primary_button', 10) or die("no logout confirm")
    tapc(t, r'id=igds_alert_dialog_primary_button'); time.sleep(4)
    # 14 Nov (Realme; Gaurav saw it on the Lava too): "Remove" login info first, then a second "Log out of Edits?" dialog
    for _ in range(2):
        t = ui()
        if "id=igds_alert_dialog_primary_button" not in t: break
        tapc(t, r'id=igds_alert_dialog_primary_button'); time.sleep(6)
    t = edits_home()
    tapc(t, r'id=igds_profile_picture'); time.sleep(3); t = ui()
    if not re.search(rf'TextView "{re.escape(HANDLE)}" id=ig_text', t): die("Edits did not switch to " + HANDLE)
step("Edits on @" + HANDLE)
# 21 Nov: on the new Edits the settings page ignores the BACK key -> tap its own back arrow (top_nav_back) first
for _ in range(3):
    t = ui()
    if "id=project_plus_button" in t: break
    if not tapc(t, r'id=top_nav_back'): sh("input", "keyevent", "BACK")
    time.sleep(2)

# 4. new project from the newest gallery video
t = wait(r"id=project_plus_button", 15) or die("no New project button")
tapc(t, r"id=project_plus_button"); time.sleep(2)
t = wait(r'TextView "(?i:gallery)"', 10) or die("no Gallery option")
tapc(t, r'TextView "(?i:gallery)"'); time.sleep(3)
t = wait(r'Video thumbnail, Added on|id=permission_allow_all_button', 20)
if t and "permission_allow_all_button" in t: tapc(t, r"id=permission_allow_all_button"); time.sleep(3); t = None
t = t or wait(r'Video thumbnail, Added on', 20) or die("gallery did not open")
c = w.coords(t, r'label="Video thumbnail, Added on (?:\d+ seconds? ago|1 minute ago|\d minutes ago)" id=gallery_picker_grid_item_container')
if not c: die("our video is not the newest gallery item")
tap(*c); time.sleep(2); t = ui()
if not (tapc(t, r'Button label="(?:Next|Done|Add|Confirm)[^"]*"') or tapc(t, r'label="(?:Next|Done|Add)" ')):
    tap(int(410 * 1.6016), int(893 * 1.6016))       # the round check button (Redmi, no label)
time.sleep(4)
t = wait(r'"Add audio"|TextView "Next"', 120, every=3) or die("editor did not open")
for _ in range(60):
    if "Optimizing media" not in ui(): break
    time.sleep(2)
step("project created")

# 5. GTA: add the saved audio at ~25%
if ADD_AUDIO:
    t = ui()
    if not tapc(t, r'"Add audio"'): die("no Add audio")
    time.sleep(3)
    # 13 Nov: while the audio sheet previews songs, uiautomator cannot dump the screen -> read it with OCR
    def ui_ocr():
        r = subprocess.run([PD, "ui", DEV], capture_output=True, text=True, timeout=120); return r.stdout or ""
    t = ""
    for _ in range(10):
        t = ui_ocr()
        if re.search(r'"Saved"|label="Saved"|"For you"', t): break
        time.sleep(3)
    else: die("audio browser did not open")
    if not (tapc(t, r'label="Saved"') or tapc(t, r'"Saved"')):
        # 13 Nov: the full-height sheet shows Saved as an unlabeled bookmark ICON, the leftmost tab, left of "For you"
        fy = w.coords(t, r'"For you"')
        if not fy: die("no Saved tab")
        tap(56, fy[1])
    time.sleep(4)
    for _ in range(8):
        t = ui_ocr()
        c = w.coords(t, rf"id=audio_browser_(?:preview_)?track_\d+_{GTA_AUDIO_ID}") or w.coords(t, r'"[^"\n]*dennyintech[^"\n]*"')
        if c: break
        time.sleep(3)
    else: die("saved GTA audio not listed in Edits")
    tap(*c); time.sleep(3)
    tap(int(402 * 1.6016), int(897 * 1.6016)); time.sleep(4)   # the check button on the audio player bar
    t = wait(r'label="(?i:Audio Track)[^"]*dennyintech', 20) or die("audio track not on the timeline")
    tapc(t, r'label="(?i:Audio Track)[^"]*dennyintech'); time.sleep(2)
    t = ui(); tapc(t, r'id=clips_action_bar_volume_controls_button'); time.sleep(3)
    t = wait(r"id=volume_slider", 10) or die("volume panel did not open")
    def vol(t):
        m = (re.search(r'Button "(\d+)"[^\n]*id=volume_slider_value_field', t)            # newer panel: value is a button
             or re.search(r'id=volume_slider @[^\n]*\n[^\n]*TextView "(\d+)"', t))     # older panel: a text after the slider
        return int(m.group(1)) if m else None
    def slider(t):
        m = re.search(r'id=volume_slider @\((\d+),(\d+)\) (\d+)x', t); return tuple(map(int, m.groups())) if m else None
    cx, cy, sw = slider(t); x0 = cx - sw // 2
    # measured on the Redmi: value 0 at the track's left edge + ~0 px, 100 at ~59% of the width -> px per unit
    k = sw * 0.59 / 100
    # 13 Nov: newer Edits panels have a number field next to the slider -> type the value (exact, no dragging)
    if "volume_slider_value_field" in t:
        tapc(t, r"id=volume_slider_value_field"); time.sleep(1.5)
        subprocess.run([PD, "fill", DEV, str(VOL_TARGET), "--id", "volume_slider_value_field", "--submit"], capture_output=True, text=True)
        time.sleep(2)
    goal = x0 + int(VOL_TARGET * k)
    for attempt in range(6):
        v = vol(ui())
        if v is not None and VOL_LO <= v <= VOL_HI: break
        cur = x0 + int((v if v is not None else 100) * k)
        w.shell("input", "swipe", str(cur), str(cy), str(max(x0 + 2, goal - 60)), str(cy), "500")   # grab the thumb, go past ...
        time.sleep(0.6)
        w.shell("input", "swipe", str(max(x0 + 2, goal - 60)), str(cy), str(goal), str(cy), "600")  # ... then onto the target
        time.sleep(1.2)
        v2 = vol(ui())
        if v2 is not None: goal += int((VOL_TARGET - v2) * k)       # correct by what the slider actually shows
    v = vol(ui())
    if v is None or not (VOL_LO <= v <= VOL_HI): die(f"audio volume not in {VOL_LO}-{VOL_HI}: {v}")
    step(f"GTA audio on timeline at {v}%")
    tapc(ui(), r"id=check_button"); time.sleep(2)

# 6. export (14 Nov owner: "export videos on 1080p 60 fps on Edits before posting") -> Instagram -> caption -> AI label
#    The quality chip left of Next ("HD"/"2K"...) opens Resolution (HD = 1080p) + Frame rate (24/30/60); Back closes it.
t = ui()
if not tapc(t, r'TextView "(?:[FQU]?HD|SD|2K|4K|\d{3,4}p)"(?= @)'): die("no quality chip (HD) in the editor")
t = wait(r"id=quality_settings_fps_60", 10) or die("quality settings did not open")
tapc(t, r"id=quality_settings_resolution_1080p"); time.sleep(0.8)
tapc(t, r"id=quality_settings_fps_60"); time.sleep(0.8)
sh("input", "keyevent", "4"); time.sleep(1.5)
step("export set to HD 1080p, 60 fps")
t = ui()
if not tapc(t, r'TextView "Next"'): die("no Next in the editor")
t = wait(r"Choose where to share", 240, every=4) or die("export did not finish")
# 15 Nov owner: no Download - Edits posts straight to Instagram (the HD + 60 fps choice above is the export setting)
time.sleep(2); t = ui()
if tapc(t, r'Button "Not now"'): time.sleep(2); t = ui()
# 15 Nov (Realme): right after Download a "saved" snackbar can sit over the tiles and eat the tap -> retry the tile
for _k in range(3):
    time.sleep(3 if _k else 1); t = ui()
    if "caption_input_text_view" in t: break
    if not (tapc(t, r'View label="Instagram"') or tapc(t, r'View "Instagram"') or tapc(t, r'TextView "Instagram"')):
        die("no Instagram share target")
    t = wait(r'id=caption_input_text_view', 25)
    if t: break
t = t or wait(r'id=caption_input_text_view', 30) or die("New reel screen did not open")
if os.environ.get("STOP_AT_CAPTION"): os._exit(0)          # debug: leave the New reel page open (no VPN reset)
# 23 Nov (misaki test): a first-reel sheet "others can download your reels" covers the caption -> 次へ
for _ in range(3):
    _t = ui()
    if re.search(r"ダウンロード|download your reels", _t) and (tapc(_t, r'(?:Button|TextView) "次へ"') or tapc(_t, r'(?:Button|TextView) "Next"')):
        step("download-your-reels sheet: 次へ"); time.sleep(2)
    else: break
CAP = C["caption"].strip()
# 15 Nov (Lea, French): the typing tool left the field empty for a caption with a curly apostrophe and an emoji variant
# selector (U+FE0F) -> type plain characters (same text to a reader)
CAP = CAP.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\ufe0f", "")
if "#" in CAP or "@" in CAP: die("caption has # or @ (owner rule: no hashtags/mentions on Instagram)")
# 14 Nov (Realme): tap the field first and retry once; keep what the typing tool said for the failure message
_fill_err = ""
for _try in range(3):
    # 15 Nov (Lucia): the keyboard's "ADD TO DICTIONARY" suggestion pop-up covered the field -> close it first
    for _ in range(2):
        if "addToDictionaryButton" in ui(): sh("input", "keyevent", "4"); time.sleep(1)
    if USER != 0:
        _r = subprocess.run(["true"], capture_output=True, text=True)
        _c = w.coords(ui(), r"id=caption_input_text_view")
        if _c: g.tapd(*_c); time.sleep(1.5)
        adb_type(CAP); time.sleep(2)
    elif _try == 0:
        tapc(ui(), r"id=caption_input_text_view"); time.sleep(1.5)
        _r = subprocess.run([PD, "fill", DEV, CAP, "--id", "caption_input_text_view"], capture_output=True, text=True); time.sleep(2)
    else:
        # 15 Nov (Lucia): typing kept raising the keyboard's dictionary pop-up -> paste the caption instead (no typing)
        if "addToDictionaryButton" in ui(): sh("input", "keyevent", "4"); time.sleep(1)
        # 15 Nov (Lucia): the keyboard rewrote her all-ASCII Spanish ("te mando" -> "te Mando", "[GTA6" -> "[GTA 6") and
        # raised its dictionary pop-up. Ctrl+V of the clipboard into the field bypasses the keyboard (verified on the Redmi).
        _c = w.coords(ui(), r"id=caption_input_text_view")
        if _c:
            g.tapd(*_c); time.sleep(1)
            w.shell("input", "keycombination", "113", "29"); time.sleep(0.4)      # Ctrl+A
            w.shell("input", "keyevent", "67"); time.sleep(0.6)                    # Delete
            subprocess.run([PD, "clipboard", DEV, "--set", CAP], capture_output=True, text=True); time.sleep(1)
            w.shell("input", "keyevent", "279"); time.sleep(2)                     # 23 Nov: KEYCODE_PASTE (Ctrl+V did nothing on the Lava)
        _r = subprocess.CompletedProcess([], 0, "pasted", "")
        step("caption pasted from the clipboard")
    _fill_err = (_r.stderr or _r.stdout or "").strip()[-300:]
    t = ui(); m = re.search(r'AutoCompleteTextView "(.*?)"[^\n]*id=caption_input_text_view', t, re.S)
    seen = (m.group(1) if m else "").replace("\\n", "\n").rstrip().rstrip("…").rstrip()
    if (len(seen) >= 30 and CAP.startswith(seen)) or seen == CAP: break
    if not seen:   # 21 Nov (Lucia): Edits stopped exposing the caption text to the UI tree -> read the screen with OCR instead
        _probe = re.sub(r"[^\w ]", " ", CAP.split("\n")[0]).split()
        _probe = " ".join(_probe[:3])
        _f = subprocess.run([PD, "find", DEV, _probe], capture_output=True, text=True).stdout
        if _probe and _probe.split()[0] in _f:
            seen = "(OCR) " + _probe; break
else:
    open(f"{HERE}/out/caption_seen_{name}.txt", "w").write(seen)
    die("caption check failed: " + seen[:80] + " | fill: " + _fill_err)
step("caption: " + seen[:100].replace("\n", " / "))
if not tapc(ui(), r'Button "OK" id=action_bar_button_text'): sh("input", "keyevent", "BACK")
time.sleep(2)
for _ in range(3):
    t = ui()
    if "(?:Add AI label|AIラベルを追加する)" in t: break
    sh("input", "swipe", "360", "1200", "360", "600", "400"); time.sleep(1.5)
_in_more = False
if "(?:Add AI label|AIラベルを追加する)" not in ui() and tapc(ui(), r'TextView "More options"'):
    # 16 Nov (himitsu, a 1-day-old account): Edits shows the AI label toggle only under "More options"
    _in_more = True; time.sleep(2.5)
    for _ in range(3):
        if "(?:Add AI label|AIラベルを追加する)" in ui(): break
        sh("input", "swipe", "360", "1200", "360", "600", "400"); time.sleep(1.5)
AI_RX = r'TextView "(?:Add AI label|AIラベルを追加する)"[^\n]*\n(?:[^\n]*\n){0,4}?[^\n]*View (?:value="checked" )?@\((\d+),(\d+)\)[^\n]*\[clickable,(on|off)\]'
ok_ai = None
for _ in range(6):        # 13 Nov 17:11 (Sofia): one tap did not take (page still settling / first-time dialog) -> retry
    time.sleep(1.5); t = ui()
    m = re.search(AI_RX, t)
    if m and m.group(3) == "on": ok_ai = m; break
    f = re.search(r'id=share_button_container @\((\d+),(\d+)\) \d+x(\d+)', t)
    if m and f and int(m.group(2)) > int(f.group(2)) - int(f.group(3)) // 2 - 40:
        # 13 Nov 17:20: the Share/Save-draft footer covered the toggle (highway pages are taller) -> scroll it clear first
        sh("input", "swipe", "360", "1000", "360", "500", "400"); time.sleep(1.5); continue
    if m: tap(int(m.group(1)), int(m.group(2))); time.sleep(2.5)
    t = ui()
    if tapc(t, r'Button "(?:Turn on|Add label|Continue|OK|Got it)"'): time.sleep(2)
ok_ai = ok_ai or re.search(r'TextView "(?:Add AI label|AIラベルを追加する)"[^\n]*\n(?:[^\n]*\n){0,4}?[^\n]*\[clickable,on\]', ui())
step("AI label: " + ("on" if ok_ai else "NOT SET") + (" (under More options)" if _in_more else ""))
if not ok_ai: die("AI label could not be turned on")
if _in_more:
    sh("input", "keyevent", "BACK"); time.sleep(2.5)
    if "share_button" not in ui(): die("could not get back to the Share page from More options")
if os.environ.get("STOP_BEFORE_SHARE"): sys.exit("stopped before share (debug)")

# 7. share and verify on the profile
if not (tapc(ui(), r'id=share_button(?= @)') or tapc(ui(), r'TextView "シェア"')): die("Share button not found")
step("share tapped")
# 15 Nov (Realme): an account's FIRST reel opens an "About Reels" sheet with its own Share button
# (id=clips_nux_sheet_share_button); the page's Share behind it does nothing. Tap the sheet's Share. Then Edits may show a
# "Meta One / verified badge / Try for $0.00" upsell: NEVER tap it (paid subscription) - Back closes it.
time.sleep(3)
for _k in range(3):
    _u = ui()
    if tapc(_u, r"id=clips_nux_sheet_share_button"): step("About Reels sheet: Share tapped"); time.sleep(4); continue
    if re.search(r"Meta One|verified badge|Try for \$", _u): sh("input", "keyevent", "4"); step("Meta Verified upsell closed (not tapped)"); time.sleep(2); continue
    break
# 15 Nov (Realme): the first tap only closed the caption keyboard and the page stayed -> nothing was ever uploaded.
# Tap again only while the New reel page with its Share button is still there (so it can never post twice).
for _k in range(3):
    time.sleep(4); _u = ui()
    if not re.search(r'id=share_button(?= @)', _u) or "caption_input_text_view" not in _u: break
    if tapc(_u, r"id=clips_nux_sheet_share_button"): step("About Reels sheet: Share tapped"); continue
    w.shell("input", "keyevent", "111"); time.sleep(0.8)          # ESC: drop the keyboard focus if any
    tapc(ui(), r'id=share_button(?= @)'); step(f"share tapped again ({_k + 2})")
# 15 Nov: Realme shares never went live -> keep what the screen shows for the first ~60 s after Share
_trace = []
for _i in range(12):
    time.sleep(5)
    try:
        _u = ui(); _trace.append(f"--- +{(_i + 1) * 5}s\n" + "\n".join(re.findall(r'"[^"]{3,90}"', _u)[:25]))
    except Exception: pass
open(f"{HERE}/out/share_trace_{name}.txt", "w").write("\n".join(_trace))
ok, n = False, None
for _ in range(14):
    g.open_app(); n = post_count()
    if before is not None and n is not None and n > before: ok = True; break
    sh("input", "swipe", "360", "500", "360", "1200", "300"); time.sleep(15)
if not ok: sys.exit(f"NOT LIVE: post count still {n} (was {before})")
step(f"shared and live: posts {before} -> {n}")
open(f"{HERE}/ig_posts.jsonl", "a").write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "name": name, "acct": HANDLE,
    "caption": CAP, "template": TPL, "via": "edits", "audio": ("voice + dennyintech Original audio %s%%" % v) if ADD_AUDIO else "own video audio"},
    ensure_ascii=False) + "\n")
if USER == 0: sh("rm", "-f", remote.replace("/sdcard", "/storage/emulated/0"))
else: adbsh(f"content delete --user {USER} --uri content://media/external/video/media --where \"_display_name='{DISP}'\"")
