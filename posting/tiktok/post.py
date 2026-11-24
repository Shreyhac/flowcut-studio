#!/usr/bin/env python3
"""Post one rendered prank to TikTok with the ORIGINAL video's sound.
usage: post.py <cfg-name>     (cfg/<name>.json has acct, orig, caption; out/<name>.mp4 is the video)
Flow: switch account -> open original -> Sound -> Use sound -> gallery -> pick newest -> Next -> Next
      -> caption -> More options: AI-generated label on -> Post.  Logs to posts.jsonl"""
import importlib.util, json, re, subprocess, sys, time, datetime, os
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('w', os.path.expanduser('~/masonry-tools/tiktok-warmup/warmup.py'))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
PD, DEV = w.PD, w.DEV
name = sys.argv[1]; C = json.load(open(f'{HERE}/cfg/{name}.json'))

def sh(*a): return w.shell(*a)
def ui(): return w.ui()
def tapxy(x, y): sh('input', 'tap', str(x), str(y))
def wait(pat, secs=30):
    end = time.time() + secs
    while time.time() < end:
        t = ui()
        if re.search(pat, t): return t
        time.sleep(1.5)
    return None
def step(msg): print(datetime.datetime.now().strftime('%H:%M:%S'), msg, flush=True)

# 1. video into the gallery (newest item)
remote = f"/sdcard/DCIM/Camera/VID_{datetime.datetime.now():%Y%m%d_%H%M%S}_{name}.mp4"
# 10 Nov bug: TikTok auto-saves each posted video as DCIM/Camera/watermark-*.mp4, and adb push keeps the Mac's OLD
# mtime, so the gallery put the previous account's watermarked post first and Bethan reposted Jake's video.
# Fix: remove OUR videos from DCIM/Camera (file + MediaStore row) and stamp the pushed file with the current time.
# Only our files: VID_<date>_*.mp4 pushed since 8 Nov and TikTok's watermark-<date>-*.mp4 saves since 8 Nov
# (older Aug/Sep files on this phone are not ours - never touch them). pd shell joins args, so pass ONE string.
def _ours(fn):
    # 11 Nov: the Realme is the user's personal phone - its own camera videos are also VID_<date>_<time>.mp4, so only match
    # files WE pushed (VID_<date>_<time>_remix_*/ugc_*/...<name>) and TikTok's watermark saves.
    m = re.match(r'(?:VID_(\d{8})_\d{6}_(?:remix_|ugc_|[a-z]).*|watermark-(\d{4})-(\d\d)-(\d\d)-\d+)\.mp4$', fn)
    if not m: return False
    d = m.group(1) or (m.group(2) + m.group(3) + m.group(4))
    return d >= '20261108'
for fn in (sh('ls /sdcard/DCIM/Camera') or '').split():
    if _ours(fn):
        sh(f"content delete --uri content://media/external/video/media --where \"_data='/storage/emulated/0/DCIM/Camera/{fn}'\"")
        sh(f"rm -f '/sdcard/DCIM/Camera/{fn}'")
for _push_try in range(4):   # 21 Nov: the Redmi drops off USB for a few seconds at times -> retry the copy
    if subprocess.run([PD, 'push', DEV, f'{HERE}/out/{name}.mp4', remote], capture_output=True).returncode == 0: break
    time.sleep(15)
else:
    sys.exit('push failed 4 times (phone off USB?)')
sh(f"touch '{remote}'")
time.sleep(1)
sh('am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', 'file://' + remote)
stray = [f for f in (sh('ls /sdcard/DCIM/Camera') or '').split() if _ours(f) and f != remote.rsplit('/', 1)[1]]
if stray:
    sys.exit('gallery not clean: ' + ' '.join(stray))
step('pushed ' + remote)
# 2. account
for _try in range(3):
    if w.switch_to(C['acct']): break
    sh('am', 'force-stop', 'com.zhiliaoapp.musically'); time.sleep(3)
else: sys.exit('could not switch to ' + C['acct'])
step('on @' + C['acct'])
if C.get('orig'):
    # 3. original -> sound -> use sound
    author = re.search(r'tiktok\.com/@([^/]+)/', C['orig']).group(1)
    t = None
    import unicodedata   # 17 Nov: display name 'Álex' vs handle alexvidalll0 -> strip accents before comparing
    norm = lambda x: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower())
    for attempt in range(3):
        sh('am', 'force-stop', 'com.zhiliaoapp.musically'); time.sleep(2)   # fresh start: deep link opens the video itself
        sh('am', 'start', '-a', 'android.intent.action.VIEW', '-d', C['orig'], 'com.zhiliaoapp.musically')
        # 16 Nov (bowling, @acct_203): on some videos TikTok leaves the sound disc unlabelled -> also accept the cover block
        t = wait(r'label="Sound:|id=videomusiccoverblock', 40)
        who = re.search(r'label="([^"]+) profile" id=user_avatar', t or '')
        who = who.group(1) if who else ''
        if t and (norm(who)[:4] == norm(author)[:4] or norm(author).startswith(norm(who)) and len(norm(who)) >= 3): break
        step(f'wrong video on screen ({who!r}), attempt {attempt + 1}'); t = None
    if not t: sys.exit('original did not open: ' + author)
    step(f'original by @{author} ({who}) open')
    c = w.coords(t, r'Button label="Sound:[^"]*" id=\w+') or w.coords(t, r'id=videomusiccoverblock'); tapxy(*c)
    t = wait(r'"Use sound"', 30)
    if not t: sys.exit('no Use sound button')

    c = w.coords(t, r'Button "Use sound"'); tapxy(*c)
    t = wait(r'"CAMERA"', 30)
    if not t: sys.exit('camera did not open')
    snd = re.search(r'TextView "([^"]+)" id=tv_top_text', t); step('sound attached: ' + (snd.group(1) if snd else '?'))
    sound = snd

else:
    # no TikTok original (e.g. an Instagram source): the file carries its own audio; open the camera via Create
    sound = None
    sh('am', 'force-stop', 'com.zhiliaoapp.musically'); time.sleep(2)
    sh('monkey', '-p', 'com.zhiliaoapp.musically', '-c', 'android.intent.category.LAUNCHER', '1'); time.sleep(8)
    for _ in range(3):
        t = ui()
        if '"CAMERA"' in t or 'label="Create"' not in t and '"Upload"' in t: break
        c = w.coords(t, r'Button label="Create" id=\w+')
        if c: tapxy(*c)
        t = wait(r'"CAMERA"|"Upload"', 20)
        if t: break
    if not t: sys.exit('camera did not open (no-orig path)')
    step('camera open (own audio)')
time.sleep(2)
# 4. gallery -> newest tile -> Next
# 11 Nov: find the controls by id (the Realme's layout differs from the Redmi's); old Redmi coordinates are the fallback
t = ui(); tapxy(*(w.coords(t, r'id=upload_hot_area') or (w.sx(78), w.sy(1468))))
t = wait(r'"Select multiple"|id=ig4', 20) or ui(); time.sleep(2); t = ui()
tiles = [(int(x), int(y)) for x, y in re.findall(r'FrameLayout id=ig4 @\((\d+),(\d+)\)', t)]
tapxy(*(min(tiles, key=lambda c: (c[1], c[0])) if tiles else (w.sx(204), w.sy(289)))); time.sleep(1.5)   # selection circle of the newest tile
t = ui(); tapxy(*(w.coords(t, r'Button "Next[^"]*" id=\w+') or (w.sx(531), w.sy(1464))))
t = None
for _ in range(60):                                  # the editor: gallery gone, its own Next button present (22 Nov: 2-min videos take > 40 s on the Redmi -> 90 s)
    time.sleep(1.5); u = ui()
    if 'Select multiple' not in u and 'Recents' not in u and not re.search(r'Button "Next \(\d', u) and re.search(r'"Next" id=', u): t = u; break
if not t:
    open(f'{HERE}/out/post_fail_{name}.txt', 'w').write(ui() or '')   # 21 Nov: keep the screen for debugging
    sys.exit('editor did not open')
time.sleep(2); c = w.coords(t, r'(?:TextView|Button) "Next" id=\w+') or (w.sx(530), w.sy(1476)); tapxy(*c)
t = wait(r'EditText[^\n]* id=\w+|"Post" id=', 90)   # 22 Nov: slow on long videos
if not t: sys.exit('post screen did not open')
# 5. caption (Masonry hashtags early so nothing important is cut)
# type ONCE: 'fill' re-types when it can't read the field back (TikTok hides long/quoted captions) -> duplicated captions
c = w.coords(t, r'EditText[^\n]*? id=\w+'); tapxy(*(c or (w.sx(221), w.sy(328)))); time.sleep(1)
# 11 Nov: "... #masonry #masonryai" at the end lost #masonryai on 3 posts (TikTok's suggestion box after #masonry ate it).
# Put #masonryai FIRST among the hashtags and #masonry right after it, never last.
def _order(cap):
    words = cap.split(); tags = [x for x in words if x.startswith('#')]; text = [x for x in words if not x.startswith('#')]
    if not any(x.lower() == '#masonryai' for x in tags): tags = ['#masonryai'] + tags
    lead = [x for x in tags if x.lower() == '#masonryai'][:1] + [x for x in tags if x.lower() == '#masonry'][:1]
    rest = [x for x in tags if x.lower() not in ('#masonryai', '#masonry')]
    # 13 Nov (Gaurav's Lava test): TikTok allows at most 5 hashtags and silently drops the 6th+ while typing
    return ' '.join(text + (lead + rest)[:5])
CAPTION = _order(C['caption'])
# 14 Nov owner: type like a human - write the text, then each hashtag on its own and PICK it from TikTok's suggestion
# dropdown before writing the next one. Only an exact match is tapped; no exact match -> a space ends the tag as before.
_words = CAPTION.split()
_text = ' '.join(x for x in _words if not x.startswith('#')); _tags = [x for x in _words if x.startswith('#')]
if _text: subprocess.run([PD, 'type', DEV, _text + ' '], capture_output=True); time.sleep(1.2)
for _i, _tag in enumerate(_tags):
    # 22 Nov (ethan speedbump): the space typed after an unpicked tag got lost, '#masonry' merged with the next tag and the
    # next dropdown pick replaced both -> always type a space BEFORE every tag after the first (a double space is harmless)
    subprocess.run([PD, 'type', DEV, (' ' if _i else '') + _tag], capture_output=True); time.sleep(2.2)
    _t = ui()
    _m = [l for l in _t.splitlines() if 'EditText' not in l
          and re.search(r'(?:TextView|Button|View) (?:label=)?"#?' + re.escape(_tag[1:]) + r'"', l, re.I)]
    _c = w.coords(_m[0], r'') if _m else None
    if _c:
        tapxy(*_c); time.sleep(1.2); step(f'hashtag {_tag}: picked from the dropdown')
        # 21 Nov (bethan): a picked tag sometimes came without TikTok's trailing space -> "#prank#boyfriend". Make sure one is there.
        _f = re.search(r'EditText "([^"]*)"', ui() or '')
        if not _f or not _f.group(1).endswith((' ', '\u00a0')):
            subprocess.run([PD, 'type', DEV, ' '], capture_output=True); time.sleep(0.6)
    else:
        subprocess.run([PD, 'type', DEV, ' '], capture_output=True); time.sleep(0.8); step(f'hashtag {_tag}: no exact suggestion, typed')
time.sleep(1.0)
# 22 Nov (maya poolslide lost #prank, ethan speedbump lost #masonry): a dropdown pick can delete the tag typed before it.
# Read the field back; re-type any planned tag that is missing at the end (typed, not picked, so nothing else gets replaced).
_f = re.search(r'EditText "([^"]*)"', ui() or '')
if _f:
    _have = set(re.findall(r'#\w+', _f.group(1).lower()))
    _miss = [x for x in _tags if x.lower() not in _have]
    for _x in _miss:
        sh('input', 'keyevent', 'KEYCODE_MOVE_END'); time.sleep(0.3)
        subprocess.run([PD, 'type', DEV, ' ' + _x + ' '], capture_output=True); time.sleep(1.2)
        step(f'hashtag {_x}: was missing after the dropdown picks, typed again')
def caption_has_masonry():
    """TikTok often hides the caption from accessibility (long text or quotes) -> fall back to OCR of the screen."""
    t = ui(); cap = re.search(r'EditText "(.*?)" id=\w+', t, re.S)
    if cap and 'masonryai' in cap.group(1).lower(): return True, cap.group(1)[:200]
    r = subprocess.run([PD, 'find', DEV, 'masonryai'], capture_output=True, text=True)
    if r.returncode == 0 and 'match' in r.stdout:
        return True, 'ocr: ' + (r.stdout.splitlines()[1].strip() if len(r.stdout.splitlines()) > 1 else '')
    # 11 Nov 19:10: PhoneDock's own OCR started failing ("vision failed: nilError") while its OCR binary works on a saved
    # screenshot -> run that binary ourselves
    import glob, tempfile
    try:
        png = os.path.join(tempfile.mkdtemp(), 'cap.png')
        subprocess.run([PD, 'screenshot', DEV, '-o', png], capture_output=True, timeout=60)
        for b in sorted(glob.glob(os.path.expanduser('~/Library/Application Support/PhoneDock/bin/pd-ocr-*'))):
            o = subprocess.run([b, png], capture_output=True, text=True, timeout=60)
            if o.returncode == 0:
                lines = [x['text'] for x in json.loads(o.stdout)]
                hit = [x for x in lines if 'masonryai' in x.lower()]
                return bool(hit), 'ocr2: ' + (hit[0] if hit else ' | '.join(lines[:6]))[:200]
    except Exception as e:
        return False, f'ocr2 failed: {e}'[:200]
    return False, cap.group(1)[:200] if cap else '?'
def _wait_phone(tries=8):
    # 23 Nov: the Redmi's USB drops for 10-60 s (shared hub) -> an empty screen read is 'phone gone', not 'no caption'
    for _i in range(tries):
        if (ui() or '').strip(): return True
        step(f'phone not answering (USB drop?) - waiting ({_i + 1}/{tries})')
        try: subprocess.run(['adb', '-s', DEV.split(':')[-1], 'wait-for-device'], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired: pass
        time.sleep(8)
    return False
_wait_phone()
ok, seen = caption_has_masonry(); step('caption: ' + seen)
if not ok:
    subprocess.run([PD, 'key', DEV, 'KEYCODE_MOVE_END'], capture_output=True)
    subprocess.run([PD, 'type', DEV, ' #masonryai'], capture_output=True); time.sleep(1.5)
    _wait_phone(); ok, seen = caption_has_masonry(); step('caption (retry): ' + seen)
    if not ok:
        try:   # 22 Nov: keep the screen (UI tree + screenshot) to see why the caption can't be read
            open(f'{HERE}/out/caption_fail_{name}.txt', 'w').write(ui() or '')
            subprocess.run([PD, 'screenshot', DEV, '-o', f'{HERE}/out/caption_fail_{name}.png'], capture_output=True, timeout=60)
        except Exception: pass
        sys.exit('caption check failed')
subprocess.run([PD, 'key', DEV, 'back'], capture_output=True); time.sleep(1.5)
# 6. AI-generated content label (first tap on More options may only clear the caption focus)
for _ in range(3):
    t = ui(); mo = w.coords(t, r'Button label="More options"') or (w.sx(360), w.sy(1077))
    tapxy(*mo); time.sleep(2.5)
    if 'Allow comments' in ui(): break
for _ in range(4):
    t = ui()
    if re.search(r'Switch label="AI-generated', t): break
    subprocess.run([PD, 'swipe', DEV, str(w.sx(360)), str(w.sy(1300)), str(w.sx(360)), str(w.sy(700))], capture_output=True); time.sleep(1.5)
m = re.search(r'Switch label="AI-generated content[^\n]*@\((\d+),(\d+)\)[^\n]*\[clickable,(on|off)\]', t)
if m and m.group(3) == 'off':
    tapxy(int(m.group(1)), int(m.group(2))); time.sleep(2)
    b2 = w.coords(ui(), r'Button "Turn on"')
    if b2: tapxy(*b2); time.sleep(2)
t = ui()
step('label line: ' + (re.search(r'[^\n]*AI-generated content[^\n]*', t).group(0)[:160] if 'AI-generated content' in t else 'not found'))
t = ui(); ok = re.search(r'Switch label="AI-generated content[^\n]*\[clickable,on\]', t); step('AI label: ' + ('on' if ok else 'NOT SET'))
if 'Allow comments' in ui():          # More options sheet still open over the post screen
    subprocess.run([PD, 'key', DEV, 'back'], capture_output=True); time.sleep(2)
if os.environ.get('STOP_BEFORE_POST'): sys.exit('stopped before post (debug)')
# 7. post
t = wait(r'Button "Post" id=\w+', 20)
if not t: sys.exit('Post button not visible - left on screen for a human')
if not caption_has_masonry()[0]: sys.exit('caption lost before posting')
c = w.coords(t, r'Button "Post" id=\w+'); tapxy(*c); time.sleep(6)
step('posted')
# 11 Nov: don't leave our upload in the phone's gallery (the Realme is the user's personal phone)
# delete 5 min later in the background on the phone: deleting 20 s after Post can cut an upload that is still running
# (Bethan gta1 12:55 never went live). The next post's start-up cleanup also removes it.
_q = remote.replace('/sdcard', '/storage/emulated/0')
sh(f"nohup sh -c \"sleep 300; content delete --uri content://media/external/video/media --where \\\"_data='{_q}'\\\"; rm -f '{remote}'\" >/dev/null 2>&1 &")
open(f'{HERE}/posts.jsonl', 'a').write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec='seconds'), "name": name, "acct": C['acct'], "orig": C.get('orig'), "caption": CAPTION, "sound": sound.group(1) if sound else None}) + '\n')
