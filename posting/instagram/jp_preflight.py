#!/usr/bin/env python3
"""24 Nov 2026 owner ("aren't you checking it prior to the posting?"): pre-flight for the Japanese IG window (~14:15 IST).
Runs 13:30 + 14:00 IST (LaunchAgent com.masonry.jppreflight) and by hand: python3 jp_preflight.py [--fix] [--quiet]
Checks, per JP device: connected + booted; Realme on Android user 10; Lava not in personal mode; Instagram + Edits enabled;
REAL internet through the Japan proxy (Lava/emulators: HTTP via nc -> ipinfo country JP; Realme user 10: VPN lock + v2rayNG
running in user 10); today's video + caption exist for every account that posts; no HOLD/STOP files left by mistake.
Mac: <= 2 emulators during the window (24 Nov: 3 at once -> netsimd segfault killed all 3; --fix stops the scout emulator
when the scout is not mid-run), memory free. Stop-rule self-test: known harmless screens must not stop a warm-up, real
challenges must. Any problem -> @owner alert in #phone-activity (silent when all OK unless run by hand)."""
import datetime, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
SERIAL = {"lava": "LAVA_SERIAL", "realme": "REALME_SERIAL", "emulator": "emulator-5554"}
SCOUT = "emulator-5556"
FIX, QUIET = "--fix" in sys.argv, "--quiet" in sys.argv
OWNER = "<@OWNER_SLACK_ID>"
os.environ["ADB_MDNS"] = "0"
bad, ok = [], []


def adb(serial, cmd, t=30):
    try: return subprocess.run([ADB, "-s", serial, "shell", cmd], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return f"ERR {e}"


def state(serial):
    try: return subprocess.run([ADB, "-s", serial, "get-state"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception: return ""


def check_device(phone, keys, user):
    s = SERIAL[phone]; tag = f"{phone} ({', '.join(keys)})"
    if state(s) != "device":
        if phone == "emulator":
            ok.append(f"{tag}: emulator off now (jp_days starts it 30 min before its slot)"); return
        bad.append(f"{tag}: NOT CONNECTED"); return
    if adb(s, "getprop sys.boot_completed") != "1": bad.append(f"{tag}: not fully booted"); return
    if phone == "realme" and adb(s, "am get-current-user") != str(user):
        bad.append(f"{tag}: on Android user {adb(s, 'am get-current-user')}, needs user {user} (Tokyo)"); return
    if phone == "lava" and adb(s, "pm list packages -d | grep -c com.instagram.android") not in ("", "0"):
        bad.append(f"{tag}: in personal mode (Instagram disabled) - jp_days switches it, but check"); return
    for pkg in ("com.instagram.android", "com.instagram.basel"):
        if pkg not in adb(s, f"pm list packages --user {user} -e {pkg}"): bad.append(f"{tag}: {pkg} missing/disabled in user {user}")
    if phone == "realme":
        out = adb(s, f"settings --user {user} get secure always_on_vpn_app; settings --user {user} get secure always_on_vpn_lockdown; "
                     f"ps -A -o USER,NAME | grep -c 'u{user}_.*com.v2ray.ang'").splitlines()
        if len(out) < 3 or out[0].strip() != "com.v2ray.ang" or out[1].strip() != "1" or out[2].strip() == "0":
            bad.append(f"{tag}: Japan proxy lock/app NOT active in user {user} ({out})")
        else: ok.append(f"{tag}: user {user}, proxy lock on, v2rayNG running")
        return
    r = adb(s, "printf 'GET /json HTTP/1.0\\r\\nHost: ipinfo.io\\r\\nUser-Agent: curl/8\\r\\n\\r\\n' | toybox timeout 25 nc ipinfo.io 80", t=40)
    ip = re.search(r'"ip": "([^"]+)"', r); cc = re.search(r'"country": "([A-Z]+)"', r)
    if not cc: bad.append(f"{tag}: NO INTERNET through the proxy ({r[-80:]!r})")
    elif cc.group(1) != "JP": bad.append(f"{tag}: internet exits in {cc.group(1)} ({ip.group(1) if ip else '?'}), not Japan")
    else: ok.append(f"{tag}: internet OK via Japan {ip.group(1)}")


def check_videos(acc):
    try: posted = {json.loads(l).get("name") for l in open(f"{HERE}/ig_posts.jsonl") if l.strip()}
    except Exception: posted = set()
    for k in acc:
        if os.path.exists(f"{HERE}/HOLD_post_{k}"): ok.append(f"{k}: post HELD on purpose ({open(f'{HERE}/HOLD_post_{k}').read().strip()[:60]})"); continue
        todo = [n for n in (f"ig_highway_jp_{k}", f"ig_gta6split_jp_{k}") if n not in posted and os.path.exists(f"{HERE}/cfg/{n}.json")]
        if not todo: ok.append(f"{k}: nothing new to post (needs a new video for the next post)"); continue
        n = todo[0]; c = json.load(open(f"{HERE}/cfg/{n}.json"))
        if not os.path.exists(f"{HERE}/out/{n}.mp4") or os.path.getsize(f"{HERE}/out/{n}.mp4") < 1_000_000: bad.append(f"{k}: {n}.mp4 missing/broken")
        elif not c.get("caption", "").strip(): bad.append(f"{k}: {n} has no caption")
        else: ok.append(f"{k}: next post {n} ready")
    if os.path.exists(f"{HERE}/STOP_jp_warm"): bad.append("STOP_jp_warm exists - no warm-ups will run today")
    if os.path.exists(f"{HERE}/STOP_jp_post"): ok.append("posting on approval hold (STOP_jp_post): only owner-approved videos post")   # 24 Nov owner rule


def check_mac():
    devs = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
    emus = re.findall(r"^(emulator-\d+)\s+device", devs, re.M)
    if len(emus) > 2:
        scout_busy = subprocess.run(["pgrep", "-f", "scout/following.py|scout_daily.sh"], capture_output=True).returncode == 0
        if FIX and SCOUT in emus and not scout_busy:
            subprocess.run([ADB, "-s", SCOUT, "emu", "kill"], capture_output=True, timeout=30)
            ok.append(f"{len(emus)} emulators running -> stopped the scout emulator (its next run restarts it)")
        else: bad.append(f"{len(emus)} emulators running ({', '.join(emus)}) - 3 at once crashed all of them on 24 Nov")
    else: ok.append(f"{len(emus)} emulator(s) running")
    m = re.search(r"free percentage: (\d+)%", subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout)
    if m and int(m.group(1)) < 20: bad.append(f"Mac memory low ({m.group(1)}% free)")
    if subprocess.run(["pgrep", "-f", "insta/jp_days.py"], capture_output=True).returncode != 0: bad.append("jp_days.py is NOT running")
    if subprocess.run(["pgrep", "-f", "jp_fast_engage.py"], capture_output=True).returncode != 0:
        if FIX:
            subprocess.Popen(f"cd {HERE} && nohup python3 jp_fast_engage.py >> jp_fast_engage.out 2>&1 &", shell=True)
            ok.append("jp_fast_engage was not running -> started (Yui engages new posts in 5-10 min)")
        else: bad.append("jp_fast_engage.py (Yui's 5-10 min engagement) is NOT running")


# screens seen in real sessions: (ui text, must_stop)
FIXTURES = [
    ('TextView "フォローする前にこのアカウントを確認してください" @(1,1)\nTextView "安全のため、フォローする前にこのアカウントの公開情報を確認してください。"', False),
    ('TextView "このアカウントのフォロワーの数は制限されています"', False),
    ('ViewGroup label="「Claude Code」をほぼ無制限かつ …" @(1,1)\nFrameLayout id=bottom_sheet_camera_container', False),   # 24 Nov sakura false stop
    ('TextView "この操作は制限されています"', True),
    ('TextView "しばらくしてからもう一度実行してください"', True),
    ('TextView "アカウントを確認してください" @(1,1)\nButton "次へ"', True),
    ('TextView "ロボットではないことを確認"', True),
    ('TextView "セキュリティコードを入力"', True),
]


def check_stop_rules():
    src = open(f"{HERE}/jp_warm.py").read()
    stop_src = re.search(r'^STOP = (re\.compile\(.*?, re\.I\))', src, re.S | re.M).group(1)
    filt = re.search(r"STOP\.search\(re\.sub\((r'[^']+'), \"\", t\)\)", src).group(1)
    STOP = eval(stop_src); F = eval(filt)
    for text, must in FIXTURES:
        hit = STOP.search(re.sub(F, "", text))
        if bool(hit) != must:
            bad.append(f"stop rule self-test FAILED: {'would stop on harmless' if hit else 'would NOT stop on real challenge'} screen {text[:50]!r}")
    if not any("self-test" in b for b in bad): ok.append(f"stop rules: {len(FIXTURES)}/{len(FIXTURES)} screens judged right")


def main():
    acc = json.load(open(f"{HERE}/jp_accounts.json")); phones = {}
    for k, a in acc.items(): phones.setdefault(a["phone"], []).append(k)
    for p, ks in phones.items(): check_device(p, ks, int(acc[ks[0]].get("user", 0)))
    check_videos(acc); check_mac(); check_stop_rules()
    now = datetime.datetime.now().strftime("%H:%M")
    print(f"JP pre-flight {now}: {len(bad)} problem(s)")
    for b in bad: print("  ✗", b)
    for o in ok: print("  ✓", o)
    open(f"{HERE}/jp_preflight.log", "a").write(f"{datetime.datetime.now():%F %T} {len(bad)} problems: {bad}\n")
    if "--noalert" not in sys.argv and (bad or not QUIET):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "phone_feed")); import phone_feed as pf
            pf.send((f":rotating_light: {OWNER} *JP pre-flight {now}*: {len(bad)} problem(s) before the Japan window\n" + "\n".join("• " + b for b in bad))
                    if bad else f":white_check_mark: *JP pre-flight {now}*: all {len(ok)} checks OK"); pf.flush()
        except Exception as e: print("alert failed:", e)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
