#!/usr/bin/env python3
"""Runs jp_warm.py for the 4 Japanese accounts once a day at ~18:00 JST (±15 min), 20-22 Nov 2026 (owner plan 20 Nov).
Per phone: its 2 accounts one after the other (random order, 8-15 min gap); Lava and Realme run in parallel.
Realme: the accounts live in Android user 10 ("Tokyo"). If the Realme is not connected / not on user 10 at start time,
it alerts #phone-activity and waits up to 45 min, then skips that day (never switches the owner's phone by itself
unless insta/REALME_AUTO_SWITCH exists).  Stop everything: touch ~/masonry-tools/insta/STOP_jp_warm
"""
import datetime, json, os, random, subprocess, sys, threading, time
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); STOP = f"{HERE}/STOP_jp_warm"; LOG = f"{HERE}/jp_warm.log"
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
SERIAL = {"lava": "LAVA_SERIAL", "realme": "REALME_SERIAL", "emulator": "emulator-5554"}
DAYS = [datetime.date(2026, 11, 20) + datetime.timedelta(days=i) for i in range(17)]   # 22 Nov owner: keep warming daily through 6 Dec
JST = ZoneInfo("Asia/Tokyo")


def log(m):
    open(LOG, "a").write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [days] {m}\n")


OWNER = "<@OWNER_SLACK_ID>"     # 20 Nov owner: "I should get a lot of alerts if the device is not connected" -> @mention = phone push


def nag(phone, m):
    alert(phone, f":rotating_light: {OWNER} {m}")


def alert(phone, m):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "phone_feed")); import phone_feed as pf
        pf.send(f":large_blue_circle: *JP warm-up* · {phone} · {m}"); pf.flush()
    except Exception as e: log(f"alert failed: {e}")


os.environ["ADB_MDNS"] = "0"     # 20 Nov: adb's mDNS code aborts on this Wi-Fi and kills the server for every phone


def adb(serial, *a):
    try: return subprocess.run([ADB, "-s", serial, *a], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception: return ""


def lava_personal():
    return adb(SERIAL["lava"], "shell", "pm list packages -d | grep -c com.instagram.android") not in ("", "0")


def to_work_mode():
    """20 Nov: the owner uses the Lava in 'personal' mode (social apps off, English, India time) -> back to work mode + reboot."""
    subprocess.run([os.path.expanduser("~/masonry-tools/lava/lava_mode.sh"), "work"], capture_output=True, timeout=120)
    adb(SERIAL["lava"], "reboot"); time.sleep(40)
    for _ in range(30):
        if adb(SERIAL["lava"], "shell", "getprop sys.boot_completed") == "1": break
        time.sleep(5)
    time.sleep(40)
    ok = not lava_personal()
    log(f"lava: switched to work mode -> {'ok' if ok else 'FAILED'}")
    return ok


def ready(phone, user, switch=True):
    s = SERIAL[phone]
    if adb(s, "get-state") != "device":
        if phone == "emulator":                       # 20 Nov: the experiment emulator is started on demand
            subprocess.run([os.path.expanduser("~/masonry-tools/lava/start_emulator.sh")]); time.sleep(90)
            if adb(s, "get-state") == "device": return None
        return "not connected"
    cur = adb(s, "shell", "am", "get-current-user")
    if cur != str(user):
        if switch and phone == "realme" and os.path.exists(f"{HERE}/REALME_AUTO_SWITCH"):
            adb(s, "shell", "am", "switch-user", str(user)); time.sleep(25)
            if adb(s, "shell", "am", "get-current-user") == str(user): return None
        return f"on Android user {cur}, needs user {user} (Tokyo)"
    if phone == "lava" and lava_personal():
        if not switch: return "in YOUR personal mode (it will switch to work mode + restart at start time)"
        alert(phone, "Lava was in personal mode -> switching to work mode (Japanese, Tokyo time, apps on) and restarting")
        if not to_work_mode(): return "still in personal mode (switch failed)"
    return None


DONE_F = f"{HERE}/jp_days_done.json"


def started_today(k, day):
    """20 Nov: the LaunchAgent restarts this program after a crash/reboot -> never start the same account twice a day."""
    try: return json.load(open(DONE_F)).get(f"{k}_{day}", False)
    except Exception: return False


def mark_started(k, day):
    try: d = json.load(open(DONE_F))
    except Exception: d = {}
    d[f"{k}_{day}"] = datetime.datetime.now().isoformat(timespec="seconds"); json.dump(d, open(DONE_F, "w"), indent=1)


def sleep_until(t):
    while datetime.datetime.now(JST) < t:
        if os.path.exists(STOP): return False
        time.sleep(min(30, max(1, (t - datetime.datetime.now(JST)).total_seconds())))
    return True


def phone_day(phone, keys, day):
    keys = [k for k in keys if not started_today(k, day)]
    if not keys: log(f"{phone} {day}: all accounts already warmed today"); return
    start = datetime.datetime.combine(day, datetime.time(18, 0), JST) + datetime.timedelta(minutes=random.uniform(-15, 15))
    if datetime.datetime.now(JST) > start + datetime.timedelta(minutes=60): log(f"{phone} {day}: start time passed, skipped"); return
    log(f"{phone} {day}: start {start:%H:%M} JST, order {keys}")
    user = 10 if phone == "realme" else 0
    ist = start.astimezone(ZoneInfo("Asia/Kolkata"))
    # 20 Nov owner: nag every 5 min from 30 min before the warm-up until the device is ready
    for before in range(30, 0, -5):
        if not sleep_until(start - datetime.timedelta(minutes=before)): return
        why = ready(phone, user, switch=False)
        if why and not (phone == "realme" and os.path.exists(f"{HERE}/REALME_AUTO_SWITCH") and "needs user" in why):
            nag(phone, f"{phone.title()} warm-up at {ist:%-I:%M %p} IST (in {before} min) but it is {why}. "
                       + ("Plug it in." if "connected" in why else "Fix it please."))
            log(f"{phone}: nag {before} min before ({why})")
    if not sleep_until(start): return
    for i in range(10):                                   # up to ~45 min waiting for the phone
        why = ready(phone, user)
        if not why: break
        nag(phone, f"{phone.title()} warm-up is DUE NOW but it is {why}. Retry {i + 1}/10, skipped in {45 - i * 4.5:.0f} min.")
        log(f"{phone}: not ready ({why})"); time.sleep(270)
        if os.path.exists(STOP): return
    else:
        nag(phone, f"{phone.title()} warm-up SKIPPED today ({why})"); return
    for n, k in enumerate(keys):
        if os.path.exists(STOP): return
        mark_started(k, day)
        alert(phone, f"warm-up started for @{json.load(open(f'{HERE}/jp_accounts.json'))[k]['handle']}")
        r = subprocess.run(["caffeinate", "-i", "python3", f"{HERE}/jp_warm.py", k, "auto"], capture_output=True, text=True, timeout=3 * 3600)
        last = [l for l in r.stdout.splitlines() if "=== end" in l or "STOPPED" in l or "CRASH" in l]
        log(f"{phone} {k}: exit {r.returncode} {last[-1][20:] if last else ''}")
        alert(phone, f"@{k}: " + (last[-1].split('] ', 1)[-1] if last else f"exit {r.returncode}"))
        if r.returncode == 3: alert(phone, "STOP screen or proxy problem: the other account on this phone is skipped today"); back_to_owner(phone); return
        if r.returncode == 0: maybe_post(phone, k)
        if n == 0:
            gap = random.uniform(8, 15) * 60; log(f"{phone}: gap {gap/60:.0f} min"); time.sleep(gap)
    back_to_owner(phone)


POSTED = []          # (poster key) posted today -> engaged by the Lava accounts after the day's sessions


def maybe_post(phone, k):
    """23 Nov owner: the new JP accounts post their GTA6 split video today, right after a warm-up, only when READY
    (jp_ready.check). One post per account; ig_posts.jsonl is the record. Stop posting only: touch insta/STOP_jp_post."""
    # 23 Nov owner: next post = the highway explainer (Japanese). Templates in order; the first one with a cfg that this
    # account has not posted yet goes up. One post per account per day.
    if os.path.exists(f"{HERE}/STOP_jp_post"): return
    if os.path.exists(f"{HERE}/HOLD_post_{k}"):   # 24 Nov: per-account hold (e.g. a fresh Instagram action limit)
        log(f"{phone} {k}: post held ({open(f'{HERE}/HOLD_post_{k}').read().strip()[:80]})"); return
    try: posted = [json.loads(l) for l in open(f"{HERE}/ig_posts.jsonl") if l.strip()]
    except Exception: posted = []
    handle = json.load(open(f"{HERE}/jp_accounts.json"))[k]["handle"]
    today = datetime.date.today().isoformat()
    if any(p.get("acct") == handle and p.get("ts", "").startswith(today) for p in posted):
        log(f"{phone} {k}: already posted today"); return
    done = {p.get("name") for p in posted}
    name = next((n for n in (f"ig_highway_jp_{k}", f"ig_gta6split_jp_{k}") if n not in done and os.path.exists(f"{HERE}/cfg/{n}.json")), None)
    if not name: log(f"{phone} {k}: nothing new to post (highway video not delivered yet?)"); return
    sys.path.insert(0, HERE); import importlib, jp_ready; importlib.reload(jp_ready)
    ok, share, age, why = jp_ready.check(k)
    if not ok: log(f"{phone} {k}: not posting yet ({'; '.join(why)})"); return
    log(f"{phone} {k}: READY (day {age}, feed {share:.0%}) -> posting {name}")
    try:
        r = subprocess.run(["caffeinate", "-i", "python3", f"{HERE}/jp_post_edits.py", name], capture_output=True, text=True, timeout=2400)
        out = (r.stdout + r.stderr).strip().splitlines()
    except Exception as e:
        r, out = None, [f"crash: {e}"]
    open(f"{HERE}/out/jp_post_{name}.log", "a").write("\n".join(out) + "\n")
    live = r is not None and r.returncode == 0 and any("shared and live" in l for l in out)
    log(f"{phone} {k}: post {'LIVE' if live else 'FAILED'} - {out[-1][:150] if out else ''}")
    alert(phone, (f":white_check_mark: @{k} GTA6 video is LIVE" if live else f":x: @{k} post failed: {out[-1][:150] if out else '?'}"))
    if live: POSTED.append(k)


def engage_today():
    """After the day's warm-ups: the Lava accounts (full watch -> like/save/comment/share work there) engage each new post."""
    acc = json.load(open(f"{HERE}/jp_accounts.json"))
    for k in POSTED:
        engagers = [x for x in ("misaki", "ayaka") if x != k]
        log(f"engage @{acc[k]['handle']} with {engagers}")
        subprocess.run(["python3", f"{HERE}/jp_engage_run.py", acc[k]["handle"], *engagers], timeout=3 * 3600)
    POSTED.clear()


def back_to_owner(phone):
    """20 Nov owner: auto-switch the Realme to Tokyo for the warm-up, then switch back to the owner's main user (WhatsApp)."""
    if phone == "realme" and os.path.exists(f"{HERE}/REALME_AUTO_SWITCH"):
        adb(SERIAL[phone], "shell", "am", "switch-user", "0"); time.sleep(15)
        cur = adb(SERIAL[phone], "shell", "am", "get-current-user")
        log(f"realme: switched back to main user -> user {cur}")
        alert(phone, "warm-up done, Realme switched back to your main user" if cur == "0" else f"could NOT switch Realme back (user {cur})")


def main():
    acc = json.load(open(f"{HERE}/jp_accounts.json"))
    phones = {}
    for k, a in acc.items(): phones.setdefault(a["phone"], []).append(k)
    log(f"=== jp_days start {phones}")
    for day in DAYS:
        if os.path.exists(STOP): break
        if datetime.datetime.now(JST).date() > day: continue
        th = [threading.Thread(target=phone_day, args=(p, random.sample(ks, len(ks)), day)) for p, ks in phones.items()]
        for t in th: t.start()
        for t in th: t.join()
        if POSTED: engage_today()
    log("=== jp_days done")


if __name__ == "__main__":
    main()
