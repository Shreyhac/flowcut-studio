#!/usr/bin/env python3
"""Post one video from the LAVA phone (13 Nov 2026). The Lava stays separate from the Redmi/Realme posting code.

usage: lava_post.py <key> <file> [--id QUEUE_ID | --caption TEXT] [--dry-run]
       lava_post.py engage <engager_key> <poster_key>      like + save + comment on the poster's newest Instagram post

  key        madison / brooke (TikTok, US VPN), valeria (Instagram, Mexico VPN), yuna (Instagram, Japan VPN)
  --id       take caption + sound from lava/post_queue.json (default: the queue item with this key and file)
  --dry-run  do everything up to the final caption screen, screenshot it, then back out (TikTok "Discard", Instagram
             "Start over") and check that no draft is left. Never taps Post / Share.

Flow: VPN to the account's country (lava_vpn, never insta/vpn.py) -> push the file into DCIM/Camera (stamped now) ->
switch the app to the account (handle read back on screen) -> gallery: newest video, duration must match the file ->
sound from the queue for silent files (Mist - EsDeeKid, Rico Ace) -> caption typed once and read back exactly (clipboard)
-> AI-generated label on -> Post/Share -> live check: TikTok = a new video on the profile, Instagram = the post count goes
up; both re-checked after a fresh app start, else NOT LIVE.
Every control is found by its label/id in get_ui: the Lava is 720x1600 (the Redmi scripts use 720x1640 positions).
Real posts are logged to lava/lava_posts.jsonl (env LAVA_POSTS overrides, for tests). Steps go to lava/lava_post.log,
screenshots to ~/Desktop/lava-check/post-tests/.
exit: 0 = live (or dry run passed), 2 = NOT LIVE (posted but not verified: never retry blindly), 1 = failed before posting
"""
import os, sys
os.environ["TT_DEV"] = "android-device:LAVA_SERIAL"     # before anything imports warmup.py
os.environ["TT_TAG"] = "lava"
os.environ["IG_PHONE"] = "lava"
import datetime, json, random, re, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "insta")); sys.path.insert(0, HERE)
import ig_warm as g, lava_vpn, lava_queue
import vpn as _vpn                                          # only _proton_home() for the proof screenshot
w = g.w; lava_vpn.patch_tiktok(w)
DEV, PD = w.DEV, w.PD
assert DEV == "android-device:LAVA_SERIAL", DEV
TT, IG = "com.zhiliaoapp.musically", g.IG
ACCTS = json.load(open(os.path.join(HERE, "lava_accounts.json")))
POSTS_F = os.environ.get("LAVA_POSTS", os.path.join(HERE, "lava_posts.jsonl"))
LOG_F = os.path.join(HERE, "lava_post.log")
PROOF = os.path.expanduser("~/Desktop/lava-check/post-tests")
OCR = sorted(__import__("glob").glob(os.path.expanduser("~/Library/Application Support/PhoneDock/bin/pd-ocr-*")))


class Fail(Exception):
    """Failed before anything was posted: safe to retry."""


TAG = ""
def step(m):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {TAG}{m}"
    print(line, flush=True); open(LOG_F, "a").write(line + "\n")


def ui(): return w.pd("ui", DEV, "--no-ocr")
def sh(*a): return w.shell(*a)
def tapc(t, pat):
    c = w.coords(t, pat)
    if c: w.tap(*c)
    return c


def wait(pat, secs=30, guard=False):
    end = time.time() + secs
    while time.time() < end:
        t = ui()
        if guard: g.guard(t)
        if re.search(pat, t): return t
        time.sleep(1.5)
    return None


def shot(name):
    os.makedirs(PROOF, exist_ok=True)
    p = os.path.join(PROOF, f"{datetime.datetime.now():%Y%m%d_%H%M%S}_{TAG.strip(' []')}_{name}.png")
    subprocess.run([PD, "screenshot", DEV, "-o", p], capture_output=True, timeout=60)
    step(f"screenshot {p}")
    return p


def ocr(png):
    for b in OCR:
        r = subprocess.run([b, png], capture_output=True, text=True, timeout=60)
        if r.returncode == 0: return json.loads(r.stdout)
    return []


def field_text():
    """The focused text field's FULL text: select all + copy + read the phone clipboard (get_ui shortens long captions
    with '…')."""
    sh("input keycombination 113 29"); sh("input keyevent 278"); time.sleep(0.8)
    s = subprocess.run([PD, "clipboard", DEV, "--get"], capture_output=True, text=True).stdout
    sh("input keyevent 123"); time.sleep(0.4)          # MOVE_END drops the selection
    return s


def deny_permissions():
    """Camera / microphone prompts: uploads don't need them, so they are declined (least privilege)."""
    for _ in range(4):
        t = ui()
        if "id=permission_message" not in t: return
        m = re.search(r'TextView "([^"]+)" id=permission_message', t)
        if m and re.search(r"(?i)camera|pictures|record|audio|microphone", m.group(1)):
            tapc(t, r'Button "Don.t allow"'); step(f"declined: {m.group(1)}"); time.sleep(2)
        else:
            raise Fail(f"unexpected permission prompt: {m.group(1) if m else '?'}")


# ---------------- gallery ----------------
OURS = re.compile(r"VID_\d{8}_\d{6}_lava_.*\.mp4$|watermark-(\d{4})-(\d\d)-(\d\d)-\d+\.mp4$")
def push(local, iid):
    """Our earlier uploads out of DCIM/Camera (file + MediaStore row), then this one in as the newest item."""
    for fn in (sh("ls /sdcard/DCIM/Camera") or "").split():
        m = OURS.match(fn)
        if not m or (m.group(1) and m.group(1) + m.group(2) + m.group(3) < "20261113"): continue   # TikTok saves from before us
        sh(f"content delete --uri content://media/external/video/media --where \"_data='/storage/emulated/0/DCIM/Camera/{fn}'\"")
        sh(f"rm -f '/sdcard/DCIM/Camera/{fn}'")
    remote = f"/sdcard/DCIM/Camera/VID_{datetime.datetime.now():%Y%m%d_%H%M%S}_lava_{iid}.mp4"
    subprocess.run([PD, "push", DEV, local, remote], check=True, capture_output=True, timeout=600)
    sh(f"touch '{remote}'"); time.sleep(1)
    sh("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", "file://" + remote); time.sleep(3)
    left = [f for f in (sh("ls /sdcard/DCIM/Camera") or "").split() if f.startswith("VID_") and "_lava_" in f]
    if left != [remote.rsplit("/", 1)[1]]: raise Fail(f"gallery not clean: {left}")
    step(f"pushed {os.path.basename(local)} -> {remote}")
    return remote


def remove_later(remote):
    """Delete our upload 5 min later on the phone (deleting right after Post can cut an upload that is still running)."""
    q = remote.replace("/sdcard", "/storage/emulated/0")
    sh(f"nohup sh -c \"sleep 300; content delete --uri content://media/external/video/media --where \\\"_data='{q}'\\\"; rm -f '{remote}'\" >/dev/null 2>&1 &")


def seconds(local):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", local],
                                capture_output=True, text=True).stdout)


# ---------------- VPN ----------------
def set_vpn(key):
    country = ACCTS[key]["vpn"]
    for i in range(2):
        if lava_vpn.switch(country):
            t = _vpn._proton_home(DEV)
            ok = re.search(rf'TextView "{re.escape(country)}"', t) and '"Disconnect"' in t
            shot(f"vpn_{country.replace(' ', '_')}")
            w.pd("key", DEV, "home")
            if ok: step(f"VPN: connected to {country} (read back on Proton's home screen)"); return
        step(f"VPN switch to {country} failed (try {i + 1})")
    raise Fail(f"VPN could not switch to {country}")


# ---------------- TikTok ----------------
def tt_profile():
    w.go_main()
    w.pd("tap", DEV, "--text", "Profile", "--match", "exact"); time.sleep(3)
    return ui()


def tt_videos(t):
    """Videos on the profile grid (each tile has a play count)."""
    return len(re.findall(r"id=tv_play_count", t))


def tt_drafts(t):
    return bool(re.search(r'(?i)"Drafts?[^"]*"|label="Drafts?', t))


def tt_switch(handle):
    for i in range(3):
        if w.switch_to(handle):
            t = tt_profile()
            if w.current_handle(t) == handle:
                step(f"TikTok account: @{w.current_handle(t)} (read back on the profile)"); shot("account"); return t
        step(f"switch to @{handle} not confirmed (try {i + 1})")
        sh("am", "force-stop", TT); time.sleep(3)
    raise Fail(f"could not switch TikTok to @{handle}")


def tt_add_sound(sound):
    title, artists = [s.strip() for s in sound.split(" - ", 1)]
    first = artists.split(",")[0].strip()
    # 13 Nov 21:00: TikTok may pre-attach a suggested song (pill "Mozart/Requi..."); one tap on the pill did not always
    # open the sheet -> retry, falling back to the pill's spot at the top centre
    for attempt in range(3):
        if not tapc(ui(), r'TextView "[^"]*" id=tv_top_text'): w.tap(350, 172)
        if wait(r'ImageView label="Search"', 12): break
    else: raise Fail("sound sheet did not open")
    tapc(ui(), r'ImageView label="Search" id=\w+'); time.sleep(2)
    if not wait(r"EditText[^\n]*id=\w+", 10): raise Fail("sound search field missing")
    w.pd("type", DEV, f"{title} {first}"); time.sleep(1)
    # 13 Nov 21:25: Enter only showed suggestions; the results need the "Search" button next to the field
    if not tapc(ui(), r'Button "Search" id=tv_search_action'): sh("input", "keyevent", "KEYCODE_ENTER")
    time.sleep(7)
    # the results list is not in the accessibility tree: OCR it. A row = title line, then "artist & artist" ~50 px lower
    want = re.compile(r"\s*(?:&|,)\s*".join(re.escape(a.strip()) for a in artists.split(",")), re.I)
    for attempt in range(2):
        png = shot("tt_sound_results")
        rows = ocr(png)
        hit = None
        for i, r in enumerate(rows):
            if want.search(r["text"]):
                above = [x for x in rows[:i] if 25 < r["y"] - x["y"] < 90 and re.search(rf"\b{re.escape(title)}\s*$", x["text"], re.I)]
                if above: hit = r; break
        if hit: break
        w.shell("input", "swipe", "360", "1200", "360", "800", "300"); time.sleep(2)
    if not hit: raise Fail(f"sound '{sound}' not found in TikTok's results")
    w.tap(626, hit["y"] + hit["height"] // 2); time.sleep(4)        # the row's red check button (right edge)
    w.tap(360, 400); time.sleep(3)                                   # close the sound sheet (tap above it)
    t = ui(); m = re.search(r'TextView "([^"]*)" id=tv_top_text', t)
    if not m or m.group(1).strip().lower() != title.lower(): raise Fail(f"sound not attached (editor shows {m.group(1) if m else '?'})")
    step(f"sound attached: {m.group(1)} ({artists})")


def tt_caption(cap):
    tapc(ui(), r"EditText[^\n]*? id=\w+"); time.sleep(1)
    words = cap.split(); text = " ".join(x for x in words if not x.startswith("#")); tags = [x for x in words if x.startswith("#")]
    for attempt in range(2):
        sh("input keycombination 113 29"); sh("input keyevent 67"); time.sleep(0.8)      # empty field
        # 15 Nov (owner rule, as pranks/post.py step 5): type the text, then EACH hashtag and tap the exact tag in
        # TikTok's suggestion dropdown before typing the next; no exact suggestion -> a space ends the tag
        if text: w.pd("type", DEV, text + " "); time.sleep(1.2)
        for tag in tags:
            w.pd("type", DEV, tag); time.sleep(2.2)
            hit = [l for l in ui().splitlines() if "EditText" not in l
                   and re.search(r'(?:TextView|Button|View) (?:label=)?"#?' + re.escape(tag[1:]) + r'"', l, re.I)]
            c = w.coords(hit[0], r"") if hit else None
            if c: w.tap(*c); time.sleep(1.2); step(f"hashtag {tag}: picked from the dropdown")
            else: w.pd("type", DEV, " "); time.sleep(0.8); step(f"hashtag {tag}: no exact suggestion, typed")
        time.sleep(1)
        got = field_text()
        if " ".join(got.split()) == " ".join(cap.split()): step(f"caption read back exactly: {got.strip()!r}"); return
        step(f"caption read back differs (try {attempt + 1}): {got!r}")
    raise Fail("caption check failed")


def tt_ai_label():
    for _ in range(3):
        tapc(ui(), r'Button label="More options"'); time.sleep(2.5)
        if "Allow comments" in ui(): break
    t = ui()
    for _ in range(4):
        if re.search(r'Switch label="AI-generated', t): break
        sh("input", "swipe", "360", "1300", "360", "700", "400"); time.sleep(1.5); t = ui()
    m = re.search(r'Switch label="AI-generated content[^\n]*@\((\d+),(\d+)\)[^\n]*\[clickable,(on|off)\]', t)
    if not m: raise Fail("AI-generated switch not found")
    if m.group(3) == "off":
        sw = re.search(r'Switch label="AI-generated content[^\n]*\n(?:[^\n]*\n){0,4}?[^\n]*Switch[^\n]*@\((\d+),(\d+)\)', t)
        w.tap(*(map(int, sw.groups()) if sw else (int(m.group(1)), int(m.group(2))))); time.sleep(2)
        tapc(ui(), r'Button "Turn on"'); time.sleep(2)
    t = ui(); on = re.search(r'Switch label="AI-generated content[^\n]*\[clickable,on\]', t)
    if not on: raise Fail("AI-generated label could not be turned on")
    step("AI-generated label: on")
    w.pd("key", DEV, "back"); time.sleep(2)
    if not re.search(r'Button "Post" id=', ui()): raise Fail("left the post screen after the AI label")


def tt_discard():
    """Back out of the post screen without saving: post screen -> editor -> (menu 'Discard' when the editor has changes,
    e.g. an added sound; without changes TikTok goes straight back) -> gallery -> main."""
    discarded = False
    for _ in range(5):
        w.pd("key", DEV, "back"); time.sleep(2.5)
        t = ui()
        if tapc(t, r'TextView "Discard"'): discarded = True; time.sleep(3); t = ui()
        if re.search(r'"Select multiple"|Button "Next \(\d', t): break
    else:
        raise Fail("could not back out to the gallery")
    step("backed out to the gallery" + (" (Discard)" if discarded else " (no edits, so no Discard menu)"))
    t = tt_profile()
    if tt_drafts(t): raise Fail("a TikTok draft was left behind")
    step(f"no TikTok draft on @{w.current_handle(t)}'s profile"); shot("tt_profile_after_discard")


def tt_post(key, it, dry):
    a = ACCTS[key]; local = os.path.join(HERE, it["file"])
    remote = push(local, it["id"])
    t = tt_switch(a["handle"])
    before = tt_videos(t)
    if tt_drafts(t): raise Fail("the profile already has a TikTok draft: check it by hand first")
    step(f"videos on the profile before: {before}")
    sh("am", "force-stop", TT); time.sleep(2)              # 13 Nov: a stuck splash layer blocked the gallery until a fresh start
    w.go_main()
    tapc(ui(), r'Button label="Create"'); time.sleep(5)
    deny_permissions()
    if not tapc(ui(), r"id=upload_hot_area"): raise Fail("no Upload button on the camera screen")
    t = wait(r'"Select multiple"|id=ipj', 20)
    if not t: raise Fail("gallery did not open")
    time.sleep(2); t = ui()
    tiles = sorted(((int(x), int(y)) for x, y in re.findall(r"FrameLayout id=ipj @\((\d+),(\d+)\)", t)), key=lambda c: (c[1], c[0]))
    durs = re.findall(r'TextView "(\d+):(\d\d)" id=\w+ @\((\d+),(\d+)\)', t)
    if not tiles or not durs: raise Fail("no video in the gallery")
    first = min(durs, key=lambda d: (int(d[3]), int(d[2]))); fs = int(first[0]) * 60 + int(first[1])
    if abs(fs - seconds(local)) > 1.5: raise Fail(f"newest gallery video is {fs}s, the file is {seconds(local):.1f}s")
    w.tap(*tiles[0]); time.sleep(2)
    if not wait(r'Button "Next \(1\)"', 8): w.tap(*tiles[0]); time.sleep(2)
    t = wait(r'Button "Next \(1\)"', 8)
    if not t: raise Fail("could not select the video")
    step(f"selected the newest video ({fs}s = {os.path.basename(local)})")
    tapc(t, r'Button "Next \(1\)"')
    t = wait(r'id=tv_top_text[\s\S]*"Next" id=|"Next" id=[\s\S]*id=tv_top_text', 60)
    if not t: raise Fail("editor did not open")
    time.sleep(2)
    if it.get("sound"): tt_add_sound(it["sound"])
    else:
        # 15 Nov: TikTok now pre-attaches a suggested song to files with their own audio -> tap the X next to the pill
        for _ in range(3):
            t = ui(); m = re.search(r'TextView "([^"]*)" id=tv_top_text', t)
            if not m or m.group(1) == "Add sound": break
            step(f"TikTok pre-attached '{m.group(1)}': removing it")
            # the X sits just right of the title; the pill shrinks with short titles ("Deep" -> X at ~440, not 523)
            c = re.search(r'TextView "[^"]*" id=tv_top_text @\((\d+),(\d+)\) (\d+)x', t)
            x = int(c.group(1)) + int(c.group(3)) // 2 + 42 if c else 523
            cl = re.search(r'label="Close"[^\n]*@\((\d+),(\d+)\)', t)
            if cl and abs(int(cl.group(2)) - 172) < 40 and abs(int(cl.group(1)) - x) < 60: x = int(cl.group(1))
            w.tap(x, 172)
            time.sleep(3)
        if m and m.group(1) != "Add sound": raise Fail(f"a sound got attached to a file with its own audio: {m.group(1)}")
    tapc(ui(), r'TextView "Next" id=\w+')        # never "Story" (quick publish) next to it
    t = wait(r'Button "Post" id=', 40)
    if not t or not re.search(r"EditText[^\n]*id=", t): raise Fail("post screen did not open")
    tt_caption(it["caption"])
    w.pd("key", DEV, "back"); time.sleep(1.5)         # keyboard
    if not re.search(r'Button "Post" id=', ui()): raise Fail("left the post screen while closing the keyboard")
    tt_ai_label()
    tapc(ui(), r"EditText[^\n]*? id=\w+"); time.sleep(1)       # final read-back on the final screen
    final = field_text().strip(); w.pd("key", DEV, "back"); time.sleep(1.5)
    if final != it["caption"]: raise Fail(f"caption changed on the final screen: {final!r}")
    step(f"FINAL SCREEN @{a['handle']}: caption {final!r}"); shot("final_caption_screen")
    if dry:
        tt_discard(); sh(f"rm -f '{remote}'"); return "dry-run ok"
    t = ui()
    if not re.search(r'Button "Post" id=', t): raise Fail("Post button not visible")
    tapc(t, r'Button "Post" id=\w+'); step("Post tapped"); time.sleep(8)
    remove_later(remote)
    return tt_verify(a["handle"], before)


def tt_verify(handle, before, tries=12, gap=20):
    n = None
    for _ in range(tries):
        t = tt_profile(); n = tt_videos(t)
        if w.current_handle(t) == handle and n > before: break
        time.sleep(gap)
    else:
        return f"NOT LIVE: @{handle} still shows {n} videos (was {before})"
    sh("am", "force-stop", TT); time.sleep(3)                     # confirm again after a fresh app start
    t = tt_profile(); n2 = tt_videos(t)
    if not (w.current_handle(t) == handle and n2 > before): return f"NOT LIVE: gone after an app restart ({n2}, was {before})"
    shot("tt_live_profile")
    return f"live: @{handle} videos {before} -> {n2}"


# ---------------- Instagram ----------------
def ig_count():
    t = ui(); c = w.coords(t, r"id=profile_tab(?= @)")
    if c: w.tap(*c); time.sleep(3); t = ui()
    m = re.search(r'TextView "([\d,.]+)" id=profile_header_familiar_post_count_value', t)
    return (int(m.group(1).replace(",", "").replace(".", "")) if m else None), t


def ig_switch(handle):
    g.open_app()
    for i in range(3):
        if g.switch_to(handle) and g.current() == handle:
            step(f"Instagram account: @{g.current()} (read back in the profile's title bar)"); shot("account"); return
        step(f"switch to @{handle} not confirmed (try {i + 1})")
        sh("am", "force-stop", IG); time.sleep(3); g.open_app()
    raise Fail(f"could not switch Instagram to @{handle}")


def ig_add_sound(sound):
    title, artists = [s.strip() for s in sound.split(" - ", 1)]
    first = artists.split(",")[0].strip()
    if not tapc(ui(), r'Button label="Add audio"'): raise Fail("no Add audio button")
    t = wait(r"id=row_search_edit_text", 20)
    if not t: raise Fail("audio picker did not open")
    tapc(t, r"EditText[^\n]*id=row_search_edit_text"); time.sleep(1.5)
    w.pd("type", DEV, f"{title} {first}"); time.sleep(5)
    pat = rf'Button label="Select track {re.escape(title)} by {re.escape(artists)}[,"]'
    t = wait(pat, 20)
    if not t: raise Fail(f"track '{sound}' not found")
    tapc(t, pat); time.sleep(3)
    t = wait(r"id=audio_bar_select_tap_target", 15)
    if not t or not tapc(t, rf'Button label="Select track {re.escape(title)} by[^"]*" id=audio_bar_select_tap_target'):
        raise Fail("could not confirm the track")
    t = wait(r"id=music_editor_done_button", 20)
    if not t: raise Fail("audio trim screen did not open")
    st = re.search(r'TextView "([^"]+)"[^\n]*id=song_title', t); ar = re.search(r'TextView "([^"]+)" id=track_artist', t)
    if not (st and st.group(1).lower() == title.lower() and ar and first.lower() in ar.group(1).lower()):
        raise Fail(f"wrong track picked: {st.group(1) if st else '?'} / {ar.group(1) if ar else '?'}")
    tapc(t, r'Button label="Done" id=music_editor_done_button'); time.sleep(3)
    if not wait(r"id=clips_right_action_button", 15): raise Fail("did not return to the editor after the sound")
    step(f"sound attached: {st.group(1)} ({ar.group(1)})")


def ig_caption(cap):
    tapc(ui(), r"id=caption_input_text_view"); time.sleep(1.5)
    for attempt in range(3):
        for _ in range(2):      # 15 Nov (Lucia): the keyboard's "ADD TO DICTIONARY" pop-up covered the field
            if "addToDictionaryButton" in ui(): sh("input", "keyevent", "4"); time.sleep(1); tapc(ui(), r"id=caption_input_text_view"); time.sleep(1)
        sh("input keycombination 113 29"); sh("input keyevent 67"); time.sleep(0.8)
        w.pd("type", DEV, cap + " "); time.sleep(2)
        got = field_text()
        if got.strip() == cap: step(f"caption read back exactly: {got.strip()!r}"); return
        step(f"caption read back differs (try {attempt + 1}): {got!r}")
    raise Fail("caption check failed")


AI_RX = r'TextView "Add AI label"[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*View[^\n]*?@\((\d+),(\d+)\)[^\n]*\[clickable,(on|off)\]'
def ig_ai_label():
    m = None
    for _ in range(3):
        t = ui(); m = re.search(AI_RX, t)        # 13 Nov Lava: the toggle line carries value="checked" before the '@'
        if m: break
        sh("input", "swipe", "360", "1100", "360", "700", "300"); time.sleep(1.5)
    if not m: raise Fail("Add AI label toggle not found")
    if m.group(3) == "off":
        w.tap(int(m.group(1)), int(m.group(2))); time.sleep(2)
        b = w.coords(ui(), r'Button "(Turn on|Add label|Continue)"')
        if b: w.tap(*b); time.sleep(2)
    m = re.search(AI_RX, ui())
    if not (m and m.group(3) == "on"): raise Fail("AI label could not be turned on")
    step("AI label: on")


def ig_drafts():
    """Instagram shows unfinished reels as 'Drafts' on the profile's grid."""
    n, t = ig_count()
    return bool(re.search(r'(?i)"Drafts?\b|label="Drafts?\b', t)), t


def ig_discard():
    w.pd("key", DEV, "back"); time.sleep(2.5)                    # share screen -> editor
    w.pd("key", DEV, "back"); time.sleep(2.5)                    # editor -> "Save draft?" sheet
    t = wait(r'Button "Start over"|Button "Discard"', 10)
    if not t: raise Fail("Instagram's discard sheet did not open")
    tapc(t, r'Button "(?:Start over|Discard)"'); time.sleep(3)
    step("backed out: Start over (no draft)")
    tapc(ui(), r'label="Cancel" id=action_bar_cancel'); time.sleep(2)
    g.open_app()
    d, t = ig_drafts()
    if d: raise Fail("an Instagram draft was left behind")
    step("no Instagram draft on the profile"); shot("ig_profile_after_discard")


def ig_live_count(handle):
    if not os.path.exists(POSTS_F): return 0
    rows = [json.loads(l) for l in open(POSTS_F) if l.strip()]
    return sum(1 for r in rows if r.get("handle") == handle and r.get("status") == "live")


def ig_post(key, it, dry):
    a = ACCTS[key]; local = os.path.join(HERE, it["file"])
    remote = push(local, it["id"])
    ig_switch(a["handle"])
    before, t = ig_count()
    step(f"posts on the profile before: {before}")
    if before is None: raise Fail("could not read the post count")
    if not dry and before > ig_live_count(a["handle"]):           # lesson from Lucia (12 Nov): never post a duplicate
        raise Fail(f"UNRECORDED POST: @{a['handle']} shows {before} posts but lava_posts.jsonl has {ig_live_count(a['handle'])}")
    d, _ = ig_drafts()
    if d: raise Fail("the profile already has an Instagram draft: check it by hand first")
    t = ui(); tapc(t, r"id=feed_tab(?= @)"); time.sleep(3); t = ui()
    if not tapc(t, r"id=action_bar_left_button(?= @)"): tapc(t, r'label="Create New"')
    t = wait(r'"New post"|id=gallery_grid_item_thumbnail', 20, guard=True)
    if not t: raise Fail("gallery did not open")
    time.sleep(2); t = ui()
    vids = re.findall(r'Button label="(Selected|Unselected) Video thumbnail created on ([^"]+)" id=gallery_grid_item_thumbnail @\((\d+),(\d+)\)', t)
    if not vids: raise Fail("no video in the gallery")
    today = (sh("date '+%B %-d, %Y'") or "").strip()
    first = vids[0]
    if today not in first[1]: raise Fail(f"newest gallery video is not ours: {first[1]}")
    lab = re.search(rf'id=gallery_grid_item_thumbnail @\({first[2]},{first[3]}\)[^\n]*\n(?:[^\n]*\n){{0,3}}?[^\n]*TextView "(\d+):(\d\d)" id=gallery_grid_item_label', t)
    if lab and abs(int(lab.group(1)) * 60 + int(lab.group(2)) - seconds(local)) > 1.5:
        raise Fail(f"newest gallery video is {lab.group(1)}:{lab.group(2)}, the file is {seconds(local):.1f}s")
    if first[0] != "Selected": w.tap(int(first[2]), int(first[3])); time.sleep(2)
    step(f"selected the newest video ({first[1]}, {lab.group(1) + ':' + lab.group(2) if lab else '?'} = {os.path.basename(local)})")
    tapc(ui(), r'Button "Next" id=next_button_textview'); time.sleep(4)
    deny_permissions()
    t = wait(r"id=clips_right_action_button", 40)
    if not t: raise Fail("editor did not open")
    time.sleep(2)
    for _ in range(3):        # an account's first Reel: "Video posts are now shared as reels" sheet
        t = ui()
        if "now shared as reels" in t or "bb_primary_action_container" in t:
            tapc(t, r'Button label="OK" id=bb_primary_action_container'); time.sleep(2); continue
        break
    if it.get("sound"): ig_add_sound(it["sound"])
    tapc(ui(), r"id=clips_right_action_button")
    t = wait(r"id=caption_input_text_view", 40)
    if not t and "bb_primary_action_container" in (ui() or ""):
        tapc(ui(), r'Button label="OK" id=bb_primary_action_container'); time.sleep(2)
        tapc(ui(), r"id=clips_right_action_button"); t = wait(r"id=caption_input_text_view", 40)
    if not t: raise Fail("share screen did not open")
    time.sleep(2)
    if "clips_download_privacy_nux_button" in ui(): tapc(ui(), r"id=clips_download_privacy_nux_button"); time.sleep(2)
    return ig_finish(a, it, before, remote, dry)


def ig_finish(a, it, before, remote, dry):
    """Instagram's share screen (from the Instagram editor or from Edits): caption, AI label, final read-back, Share, live check."""
    ig_caption(it["caption"])
    w.pd("key", DEV, "back"); time.sleep(1.5)
    if "id=caption_input_text_view" not in ui(): raise Fail("left the share screen while closing the keyboard")
    ig_ai_label()
    for _ in range(3):        # the caption field sits at the top: scroll back up to read it on the final screen
        if re.search(r"id=caption_input_text_view @\(\d+,(\d+)\)", ui()): break
        sh("input", "swipe", "360", "500", "360", "1200", "300"); time.sleep(1.5)
    tapc(ui(), r"id=caption_input_text_view"); time.sleep(1.2)
    final = field_text().strip(); w.pd("key", DEV, "back"); time.sleep(1.5)
    if "id=caption_input_text_view" not in ui(): raise Fail("left the share screen after the final read-back")
    if final != it["caption"]: raise Fail(f"caption changed on the final screen: {final!r}")
    step(f"FINAL SCREEN @{a['handle']}: caption {final!r}"); shot("final_caption_screen")
    if dry:
        if it.get("via") == "edits":         # back out of Instagram's share screen, then drop Edits' export
            for _ in range(3): w.pd("key", DEV, "back"); time.sleep(2)
            sh("am", "force-stop", IG); sh("am", "force-stop", EDITS); time.sleep(2); g.open_app()
            d, _ = ig_drafts()
            if d: raise Fail("an Instagram draft was left behind")
            step("backed out of Edits' share; no Instagram draft on the profile"); sh(f"rm -f '{remote}'"); return "dry-run ok"
        ig_discard(); sh(f"rm -f '{remote}'"); return "dry-run ok"
    t = ui()
    if not tapc(t, r"id=share_button(?= @)"): raise Fail("share button not found")
    step("Share tapped"); time.sleep(4)
    for _ in range(4):        # final confirmation sheets ("About Reels", share to ...)
        t = ui()
        if tapc(t, r"id=clips_nux_sheet_share_button(?= @)") or tapc(t, r'Button label="Share"') or tapc(t, r'Button "Share"'):
            time.sleep(4); continue
        if tapc(t, r'Button "Not now"'): time.sleep(2); continue
        if "id=share_button" not in t: break
        if "caption_input_text_view" in t:      # 15 Nov (Realme): the 1st tap only closed the keyboard -> nothing uploaded
            sh("input", "keyevent", "111"); time.sleep(0.8)
            if tapc(ui(), r"id=share_button(?= @)"): step("Share tapped again (the New reel page was still open)")
        time.sleep(3)
    remove_later(remote)
    return ig_verify(a["handle"], before)


# ---------------- Instagram through the Edits app ----------------
# 13 Nov owner: Lava Instagram posts go through Edits (like insta/ig_post_edits.py on the Redmi). Mapped on the Lava
# (720x1600) on 13 Nov 22:05, first real post: messi_silent_valeria. Edits adds the script's audio: "Original audio" at
# 30%, a song at 55% (Gaurav: music 50-60%). The audio is saved on the account first (Instagram audio page) and then
# picked from Edits' Saved tab (the bookmark icon, leftmost tab).
EDITS = "com.instagram.basel"


def ui_any():
    """uiautomator dump, or OCR when the screen is animating (Edits' audio sheet previews songs)."""
    t = ui()
    return t if t.strip() else (w.pd("ui", DEV) or "")


def save_audio(audio_id):
    sh("am", "start", "-a", "android.intent.action.VIEW", "-d", f"https://www.instagram.com/reels/audio/{audio_id}/", IG)
    t = wait(r"id=secondary_bar_save_button", 25)
    if not t: raise Fail("audio page did not open")
    if not re.search(r"id=secondary_bar_save_button[^\n]*selected", t):
        tapc(t, r"id=secondary_bar_save_button"); time.sleep(2.5); t = ui()
    if not re.search(r"id=secondary_bar_save_button[^\n]*selected", t): raise Fail("could not save the audio")
    m = re.search(r'TextView "([^"]*)"[^\n]*id=song_title', t)
    step(f"audio {audio_id} saved on the account ({m.group(1) if m else '?'})")
    w.pd("key", DEV, "home"); time.sleep(1)


def edits_home(handle):
    sh("monkey", "-p", EDITS, "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(7)
    for _ in range(12):
        t = ui(); g.guard(t)
        if "id=project_plus_button" in t: return t
        if tapc(t, r'Button "Not now"'): time.sleep(2); continue
        if "Continue with Instagram" in t:       # logged out: continue as the Instagram app's account (= handle)
            if re.search(rf'TextView "{re.escape(handle)}" id=ig_text', t):
                tapc(t, r'"Continue with Instagram"'); time.sleep(9); continue
            if tapc(t, r'"Switch accounts"'): time.sleep(4); continue
        if "Choose an Instagram account" in t:
            if tapc(t, rf'TextView "{re.escape(handle)}"'): time.sleep(9); continue
            raise Fail(f"{handle} is not offered in Edits")
        if tapc(t, r'TextView "Join Edits"'): time.sleep(9); continue     # Gaurav approved joining, 13 Nov 21:35
        if EDITS not in (sh("dumpsys window | grep mCurrentFocus") or ""):
            sh("monkey", "-p", EDITS, "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(7); continue
        w.pd("key", DEV, "back"); time.sleep(2)
        t2 = ui()
        if tapc(t2, r'Button "(?:Discard|Start over|Delete)"') or tapc(t2, r'"(?:Discard|Start over)"'): time.sleep(2)
    raise Fail("Edits home did not open")


def edits_account(handle):
    """Edits must be on the same account as the Instagram app (step before): check, else log out and continue."""
    t = edits_home(handle)
    tapc(t, r"id=igds_profile_picture"); time.sleep(3); t = ui()
    if not re.search(rf'TextView "{re.escape(handle)}" id=ig_text', t):
        if not tapc(t, r"id=settings_logout"):
            for _ in range(4):
                sh("input", "swipe", "360", "1200", "360", "500", "300"); time.sleep(1.5)
                if tapc(ui(), r"id=settings_logout"): break
            else: raise Fail("no Log out in Edits settings")
        # 13 Nov Lava: "Remove saved login info?" -> Keep (no password needed later), then "Log out of Edits?" -> Log out
        for _ in range(3):
            time.sleep(2); t = wait(r"id=igds_alert_dialog_headline", 10)
            if not t: break
            if "Remove saved login" in t: tapc(t, r'Button "Keep" id=igds_alert_dialog_secondary_button'); continue
            if "Remember login" in t: tapc(t, r'Button "Remember"') or tapc(t, r'"Remember"'); continue   # 14 Nov variant
            if "Log out" in t: tapc(t, r'Button "Log out" id=igds_alert_dialog_primary_button'); time.sleep(6); break
            raise Fail("unexpected dialog while logging out of Edits")
        t = edits_home(handle)
        tapc(t, r"id=igds_profile_picture"); time.sleep(3); t = ui()
        if not re.search(rf'TextView "{re.escape(handle)}" id=ig_text', t): raise Fail(f"Edits did not switch to {handle}")
    step(f"Edits account: {handle} (read back in Edits settings)")
    w.pd("key", DEV, "back"); time.sleep(2)


def edits_project(local):
    t = wait(r"id=project_plus_button", 15)
    if not t: raise Fail("no New project button in Edits")
    tapc(t, r"id=project_plus_button"); time.sleep(2.5)
    t = wait(r'TextView "Gallery"', 10)
    if not t: raise Fail("no Gallery option")
    tapc(t, r'TextView "Gallery"'); time.sleep(3.5)
    t = wait(r"Video thumbnail, Added on", 20)
    if not t: raise Fail("Edits gallery did not open")
    c = w.coords(t, r'label="Video thumbnail, Added on (?:\d+ seconds? ago|1 minute ago|[1-4] minutes ago)" id=gallery_picker_grid_item_container')
    first = re.search(r'label="(Video|Photo) thumbnail, Added on ([^"]+)" id=gallery_picker_grid_item_container', t)
    if not c or not first or first.group(1) != "Video": raise Fail(f"our video is not the newest gallery item ({first.group(2) if first else '?'})")
    w.tap(*c); time.sleep(2.5)
    t = ui()
    if not (tapc(t, r'View label="Done"') or tapc(t, r'Button label="(?:Next|Done|Add)')): raise Fail("no Done after picking the video")
    time.sleep(6)
    for _ in range(60):
        t = ui()
        if "Optimizing media" not in t and "audio track" in t.lower(): break
        time.sleep(4)
    else: raise Fail("Edits editor did not open")
    m = re.search(r'TextView "(\d\d):(\d\d)"[^\n]*id=full_duration_time_stamp', t)
    if m and abs(int(m.group(1)) * 60 + int(m.group(2)) - seconds(local)) > 1.5:
        raise Fail(f"Edits project is {m.group(1)}:{m.group(2)}, the file is {seconds(local):.1f}s")
    step(f"Edits project from the newest gallery video ({m.group(1) + ':' + m.group(2) if m else '?'} = {os.path.basename(local)})")


def edits_audio(ea):
    want, vol = ea["audio_match"], int(ea["volume"])
    t = ui()
    if not tapc(t, r'label="(?i:Audio Track) \\n Add audio"') and not tapc(t, r'TextView "Add audio"'): raise Fail("no Add audio")
    time.sleep(4)
    for _ in range(8):
        t = ui_any()
        if re.search(r'"For you"', t): break
        time.sleep(3)
    else: raise Fail("Edits audio sheet did not open")
    fy = w.coords(t, r'"For you"'); w.tap(60, fy[1]); time.sleep(4)            # Saved = bookmark icon, leftmost tab
    for _ in range(6):
        t = ui_any(); c = w.coords(t, rf'Text(?:View)? "{re.escape(want)}[^"]*"')
        if c: break
        time.sleep(3)
    else: raise Fail(f"saved audio '{want}' not listed in Edits")
    w.tap(300, c[1]); time.sleep(4)
    w.tap(643, 1398); time.sleep(5)                                            # the check on the audio player bar
    t = ui()
    m = re.search(r'label="(?i:Audio Track) \\n ([^"]+)"', t)
    if not m or want.lower() not in m.group(1).lower(): raise Fail(f"audio not on the timeline ({m.group(1) if m else '?'})")
    tapc(t, r'label="(?i:Audio Track) \\n [^"]+"'); time.sleep(3)
    if not tapc(ui(), r"id=clips_action_bar_volume_controls_button"): raise Fail("no Volume button")
    time.sleep(3)
    t = wait(r"id=volume_slider", 10)
    if not t: raise Fail("volume panel did not open")
    if "volume_slider_value_field" in t:        # panel version 1: a number field next to the slider -> type it
        tapc(t, r"id=volume_slider_value_field"); time.sleep(1.5)
        w.pd("fill", DEV, str(vol), "--id", "volume_slider_value_field", "--submit"); time.sleep(2)
        got = vol_value(ui())
    else:                                       # panel version 2 (13 Nov, Yuna): slider + text value, taps do nothing -> drag
        m = re.search(r"id=volume_slider @\((\d+),(\d+)\) (\d+)x", t); cx, cy, sw = map(int, m.groups())
        x0 = cx - sw // 2; got = vol_value(t); k = 4.3                 # ~4.3 px per unit, measured on the Lava
        cur = x0 + int(0.59 * sw) if got == 100 else x0 + int(got * k)   # thumb at 100 sits at ~59% of the track
        for _ in range(8):
            if got is not None and abs(got - vol) <= 2: break
            goal = max(x0 + 2, min(x0 + sw - 2, cur + int((vol - got) * k)))
            sh("input", "swipe", str(cur), str(cy), str(goal), str(cy), "600"); time.sleep(1.5)
            new = vol_value(ui())
            if new is not None and new != got and goal != cur: k = abs(goal - cur) / abs(new - got)
            cur, got = goal, new
    if got is None or abs(got - vol) > 2: raise Fail(f"volume reads {got}, wanted {vol}")
    if not (tapc(ui(), r"id=check_button") or tapc(ui(), r'View label="OK"')): raise Fail("no OK on the volume panel")
    time.sleep(2)
    vol = got
    step(f"Edits audio: {want} at {vol}% (read back in the volume field)")


def edits_quality():
    """Owner 14 Nov: export 1080p. 60 fps is greyed out on the Lava (SC9863A encoder: 'limited to 30'), so 1080p 30."""
    if not tapc(ui(), r'TextView "(?:HD|FHD|2K|4K)"(?= @\(\d+,9\d\))'): raise Fail("no quality button in Edits")
    t = wait(r"id=quality_settings_resolution_1080p", 10)
    if not t: raise Fail("Edits quality panel did not open")
    if re.search(r"id=quality_settings_resolution_1080p[^\n]*disabled", t): raise Fail("1080p is disabled in Edits")
    tapc(t, r"id=quality_settings_resolution_1080p"); time.sleep(1)
    t = ui()      # 15 Nov owner: 60 fps when Edits offers it; the Lava greys it out ("limited to 30") -> 30
    fps = 60 if re.search(r"id=quality_settings_fps_60(?![^\n]*disabled)", t) else 30
    tapc(t, rf"id=quality_settings_fps_{fps}"); time.sleep(1)
    tapc(ui(), r'TextView "(?:HD|FHD|2K|4K)"(?= @\(\d+,9\d\))'); time.sleep(2)     # same button closes the panel
    t = ui()
    if "quality_settings_resolution_1080p" in t: w.tap(360, 1000); time.sleep(2); t = ui()
    if not re.search(r'TextView "FHD"(?= @\(\d+,9\d\))', t): raise Fail("Edits export is not FHD")
    step(f"Edits export: 1080p (FHD), {fps} fps")


def vol_value(t):
    m = (re.search(r'Button "(\d+)"[^\n]*id=volume_slider_value_field', t)
         or re.search(r'id=volume_slider @[^\n]*\n[^\n]*TextView "(\d+)"', t))
    return int(m.group(1)) if m else None


def ig_post_edits(key, it, dry):
    a = ACCTS[key]; local = os.path.join(HERE, it["file"]); ea = it["edits_audio"]
    remote = push(local, it["id"])
    ig_switch(a["handle"])
    before, t = ig_count()
    step(f"posts on the profile before: {before}")
    if before is None: raise Fail("could not read the post count")
    if not dry and before > ig_live_count(a["handle"]):
        raise Fail(f"UNRECORDED POST: @{a['handle']} shows {before} posts but lava_posts.jsonl has {ig_live_count(a['handle'])}")
    save_audio(ea["audio_id"])
    edits_account(a["handle"])
    edits_project(local)
    edits_audio(ea)
    edits_quality()
    t = wait(r'TextView "(?:Export|Next)"(?= @\(\d+,9\d\))', 20)        # either label; appears after the panel closes
    if not t or not tapc(t, r'TextView "(?:Export|Next)"(?= @\(\d+,9\d\))'): raise Fail("no Export/Next in Edits")
    t = wait(r"Choose where to share", 240)
    if not t: raise Fail("Edits export did not finish")
    time.sleep(2); t = ui()
    if tapc(t, r'Button "Not now"'): time.sleep(2); t = ui()
    for k in range(3):            # 15 Nov (Realme): a snackbar over the tiles ate the tap -> retry the tile
        if k: time.sleep(3); t = ui()
        if "caption_input_text_view" in t: break
        if not (tapc(t, r'View label="Instagram"') or tapc(t, r'View "Instagram"') or tapc(t, r'TextView "Instagram"')):
            raise Fail("no Instagram share target in Edits")
        t = wait(r"id=caption_input_text_view", 30)
        if t: break
    t = t or wait(r"id=caption_input_text_view", 60)
    if not t: raise Fail("Instagram's New reel screen did not open")
    time.sleep(2)
    return ig_finish(a, it, before, remote, dry)


def ig_verify(handle, before, tries=40, gap=15):     # 14 Nov: a 74 s Edits reel took >6 min to show up
    n = None
    for i in range(tries):
        time.sleep(gap)
        # 15 Nov: Valeria's reel was live (24 views) while the profile kept showing the old count for 20 min, and the
        # retry made a duplicate -> fresh app start every 4th check so the count is re-read from the server
        if i % 4 == 3: sh("am", "force-stop", IG); time.sleep(3)
        g.open_app(); n, _ = ig_count()
        if g.current() == handle and n is not None and n > before: break
    else:
        return f"NOT LIVE: @{handle} post count still {n} (was {before})"
    sh("am", "force-stop", IG); time.sleep(3); g.open_app()
    n2, _ = ig_count()
    if not (n2 is not None and n2 > before): return f"NOT LIVE: count back to {n2} after an app restart (was {before})"
    shot("ig_live_profile")
    return f"live: @{handle} posts {before} -> {n2}"


# ---------------- engagement ----------------
def engage(ekey, pkey):
    """The other Instagram account likes, saves and comments (in the post's language, never repeated) on the poster's
    newest post. Runs from the engager's own VPN country."""
    import ig_engage
    global TAG; TAG = f"[engage {ekey}] "
    e, p = ACCTS[ekey], ACCTS[pkey]
    set_vpn(ekey); ig_switch(e["handle"])
    if not ig_engage.open_latest(p["handle"]): raise Fail(f"could not open @{p['handle']}'s newest post")
    time.sleep(random.uniform(8, 18)); done = []
    t = ui(); c = w.coords(t, r'label="Like" id=(?:like_button|row_feed_button_like)')
    if c: w.tap(*c); done.append("like"); time.sleep(2)
    t = ui(); c = w.coords(t, r'label="(?:Save|Add to Saved)" id=(?:save_button|row_feed_button_save)')
    if c:
        w.tap(*c); done.append("save"); time.sleep(2)
        if "Collections" in ui(): w.pd("key", DEV, "back"); time.sleep(1.5)
    sf = os.path.join(HERE, "lava_state.json")
    st = json.load(open(sf)) if os.path.exists(sf) else {}
    used = st.get("engage_comments_used", [])
    pool = [x for x in ig_engage.COMMENTS[p["lang"]] if x not in used] or ig_engage.COMMENTS[p["lang"]]
    text = random.choice(pool)
    t = ui(); c = w.coords(t, r'Button "Add comment…" id=comment_composer_text_view') or w.coords(t, r'label="Comment" id=(?:comment_button|row_feed_button_comment)')
    if c:
        w.tap(*c); time.sleep(3)
        t = ui(); f = w.coords(t, r"(?:AutoCompleteTextView|EditText)[^\n]*id=(?:layout_comment_thread_edittext\w*|comment_composer\w*)")
        if f:
            w.tap(*f); time.sleep(1.2); w.pd("type", DEV, text); time.sleep(2)
            t = ui(); b = w.coords(t, r'label="Post" id=layout_comment_thread_post_button\w*') or w.coords(t, r'(?:Button|TextView) "Post"')
            if b:
                w.tap(*b); done.append(f"comment:{text}"); time.sleep(3)
                st = json.load(open(sf)) if os.path.exists(sf) else {}
                st["engage_comments_used"] = (st.get("engage_comments_used", []) + [text])[-60:]
                json.dump(st, open(sf, "w"), ensure_ascii=False, indent=1)
        w.pd("key", DEV, "back"); time.sleep(1.5)
    step(f"on @{p['handle']}: {', '.join(done) or 'nothing'}")
    w.pd("key", DEV, "home")
    return done


# ---------------- main ----------------
def item_for(key, file, iid=None, caption=None):
    q = json.load(open(os.path.join(HERE, "post_queue.json")))["items"]
    if iid: it = next(i for i in q if i["id"] == iid)
    else: it = next((i for i in q if i["key"] == key and os.path.basename(i["file"]) == os.path.basename(file)), None)
    if it is None:
        it = {"id": os.path.basename(file)[:-4], "key": key, "app": ACCTS[key]["app"], "handle": ACCTS[key]["handle"],
              "file": os.path.abspath(file), "caption": caption, "sound": None}
    it = dict(it)
    if caption: it["caption"] = caption
    if it["app"] == "instagram":   # 15 Nov (Lea): curly quotes / U+FE0F made the typed caption come out empty
        it["caption"] = (it["caption"].replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
                         .replace("\u201d", '"').replace("\ufe0f", ""))
    if it["key"] != key: raise SystemExit(f"{it['id']} belongs to {it['key']}, not {key}")
    if not it.get("caption"): raise SystemExit("no caption")
    if not lava_queue.caption_ok(it["app"], it["caption"]): raise SystemExit(f"caption breaks the owner's rules: {it['caption']!r}")
    if it["app"] == "instagram" and not g.lang_ok(it["caption"], ACCTS[key]["lang"]):
        raise SystemExit(f"Instagram caption is not {ACCTS[key]['lang']}: {it['caption']!r}")
    return it


def run(key, file, iid=None, caption=None, dry=False):
    global TAG; TAG = f"[{key}] "
    it = item_for(key, file, iid, caption)
    step(f"{'DRY RUN ' if dry else ''}{it['id']} -> {ACCTS[key]['app']} @{ACCTS[key]['handle']} (VPN {ACCTS[key]['vpn']}, sound {it.get('sound')})")
    status = None
    try:
        set_vpn(key)
        post = tt_post if ACCTS[key]["app"] == "tiktok" else (ig_post_edits if it.get("via") == "edits" else ig_post)
        status = post(key, it, dry)
    except (Fail, w.Stop) as e:
        status = f"failed: {e}"
        shot("failed")
        if not dry:   # put the app back on a neutral screen; a half-made post is discarded by the next run's open_app
            w.pd("key", DEV, "home")
    step(f"RESULT {status}")
    if not dry: record(it, key, status)
    return status


def record(it, key, status, path=None):
    """One line per real attempt in lava_posts.jsonl: status live / NOT LIVE / failed (lava_sched reads it)."""
    st = "live" if status.startswith("live") else ("NOT LIVE" if status.startswith("NOT LIVE") else "failed")
    row = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "id": it["id"], "key": key, "app": ACCTS[key]["app"],
           "handle": ACCTS[key]["handle"], "caption": it["caption"], "sound": it.get("sound"), "status": st, "detail": status}
    open(path or POSTS_F, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
    if st == "NOT LIVE": step(f"logged NOT LIVE for {it['id']} in {path or POSTS_F}")
    return row


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "engage":
        try: engage(a[1], a[2]); sys.exit(0)
        except (Fail, w.Stop) as e: step(f"engage failed: {e}"); sys.exit(1)
    dry = "--dry-run" in a; a = [x for x in a if x != "--dry-run"]
    iid = cap = None
    if "--id" in a: i = a.index("--id"); iid = a[i + 1]; del a[i:i + 2]
    if "--caption" in a: i = a.index("--caption"); cap = a[i + 1]; del a[i:i + 2]
    s = run(a[0], a[1], iid, cap, dry)
    sys.exit(0 if s.startswith("live") or s == "dry-run ok" else (2 if s.startswith("NOT LIVE") else 1))
