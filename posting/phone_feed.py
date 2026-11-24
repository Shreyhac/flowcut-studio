#!/usr/bin/env python3
"""Phone activity feed -> Slack #phone-activity (18 Nov 2026, owner: "alert whenever each account posting has finished
and when you are warming up each account ... somewhere I can check it properly ... a bot must post it, not my account").

Reads the loops' own logs (never touches the phones) and sends one line per event through a Slack INCOMING WEBHOOK, so
messages come from the app/bot and the owner gets notified:
  - post live / failed / NOT LIVE (Redmi TikTok + IG, Lava, one-off repost scripts)
  - warm-up session finished, per account (Redmi TikTok + IG, Realme himitsu, OnePlus Emily/Ken, Lava)
  - problems: challenge/CAPTCHA, logged out, VPN down, switch stopped, crash, phone off USB, loop process gone
  - daily summary at 10:00 IST (last 24 h, per account)
Webhook URL: ~/.flowcut/slack_webhook (one line, chmod 600). Until it exists, messages wait in outbox.jsonl.
Stop: touch phone_feed/STOP.  Test without sending: python3 phone_feed.py --dry (prints instead of posting).
Single instance (flock). Starts from the END of every log (no history replay)."""
import datetime, fcntl, glob, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
STATE_F, OUTBOX_F, EVENTS_F = f"{HERE}/state.json", f"{HERE}/outbox.jsonl", f"{HERE}/events.jsonl"
HOOK_F = os.path.expanduser("~/.flowcut/slack_webhook")
DRY = "--dry" in sys.argv
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")

PHONES = {"REDMI_SERIAL": "Redmi", "REALME_SERIAL": "Realme", "LAVA_SERIAL": "Lava"}   # 21 Nov 2026 owner: OnePlus no longer kept -> removed from every check
# warm-up detail logs: (path, phone, app). ig_run.log is shared: himitsu = Realme, the rest = Redmi.
WARM_LOGS = [(f"{ROOT}/tiktok-warmup/run.log", "Redmi", "TikTok"), (f"{ROOT}/tiktok-warmup/run_realme.log", "Realme", "TikTok"),
             (f"{ROOT}/insta/ig_run.log", None, "IG"),
             (f"{ROOT}/insta/lite_run.log", "Realme", "IG Lite"), (f"{ROOT}/lava/lava_run.log", "Lava", None)]
POST_JSONL = [(f"{ROOT}/pranks/posts.jsonl", "Redmi", "TikTok"), (f"{ROOT}/insta/ig_posts.jsonl", "Redmi", "IG"),
              (f"{ROOT}/lava/lava_posts.jsonl", "Lava", None)]
LOOP_LOGS = [(f"{ROOT}/pranks/run_forever.log", "Redmi"), (f"{ROOT}/insta/himitsu_warm.log", "Realme"),
             (f"{ROOT}/pranks/realme_forever.log", "Realme")]
# loop process -> (phone, pause file). Missing process with no pause file for 2 checks in a row = problem.
LOOPS = {"run_forever.py": ("Redmi", f"{ROOT}/pranks/PAUSE"), "lava_forever.py": ("Lava", f"{ROOT}/lava/PAUSE"),
         "himitsu_warm.py": ("Realme", f"{ROOT}/insta/PAUSE_himitsu"), "realme_forever.py": ("Realme", f"{ROOT}/pranks/PAUSE_realme")}

def realme_handles():
    out = {"acct_129"}
    for f in ("insta/realme_ig_accounts.json", "insta/lite_accounts.json", "pranks/realme_accounts.json"):
        try:
            d = json.load(open(f"{ROOT}/{f}")); vals = d.values() if isinstance(d, dict) else d
            out |= {v.get("handle") for v in vals if isinstance(v, dict) and v.get("handle")}
        except Exception: pass
    return out
REALME = realme_handles()
NOISE = re.compile(r"~~~~|\^\^\^\^|^\s*File \"|^\s*\|")


def ts_of(line):
    try: return datetime.datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception: return time.time()


PROBLEM = re.compile(r"STOPPED|challenge|captcha|CAPTCHA|logged out|log in again|Traceback|CRASH|warm stopped|"
                     r"VPN down|VPN .*FAILED|could not switch|NOT LIVE|UNRECORDED|ERROR|suspended|banned|"
                     r"try again later|action blocked", re.I)
OPEN = re.compile(r"\[(\w+)\] (?:session start as @([\w.]+) \(([\d.]+) min\)|IG session @([\w.]+) \((\w+)\) (\d+) min|"
                  r"(tiktok|instagram) session @([\w.]+) \(([^)]*)\) (\d+) min)")
CLOSE = re.compile(r"\[(\w+)\] session end(?:; follows today: (\d+))?")


# 18 Nov owner: "I don't remember the account names - write e.g. (Spanish account) next to each one".
LANG = {"en": "English", "es": "Spanish", "ja": "Japanese", "pt": "Portuguese", "fr": "French", "de": "German"}
STATIC_LABELS = {   # TikTok accounts (no lang field in their configs): language + persona/niche
    "acct_107": "English prank account · Ethan", "acct_078": "English prank account · Bethan",
    "acct_105": "English prank account · Emily", "acct_171": "English AI-UGC account · Maya",
    "acct_137": "English AI-builder account · Jake", "acct_072": "English AI-creative account · Ken",
    "acct_202": "English avatar-UGC account · RGU", "acct_164": "English avatar-UGC account · Chloe",
    "acct_040": "English avatar-UGC account · Ava", "acct_168": "English avatar-UGC account · Sophie",
    "acct_167": "English account · Emma", "acct_169": "English account · Lily", "acct_166": "English account · Grace",
    "acct_129": "Japanese Doraemon account · Himitsu", "acct_165": "Vaibhav's experiment account",
}
def build_labels():
    lab = {}
    for f in ("insta/ig_accounts.json", "insta/realme_ig_accounts.json", "insta/lite_accounts.json", "lava/lava_accounts.json"):
        try:
            for key, v in json.load(open(f"{ROOT}/{f}")).items():
                if isinstance(v, dict) and v.get("handle"):
                    lab[v["handle"]] = f"{LANG.get(v.get('lang'), v.get('lang') or '?')} account · {key.capitalize()}"
        except Exception: pass
    lab.update(STATIC_LABELS)
    return lab
LABELS = build_labels()
def labelled(text):
    return re.sub(r"@([\w.]*\w)", lambda m: f"@{m.group(1)} ({LABELS[m.group(1)]})" if m.group(1) in LABELS else m.group(0), text)


def now(): return datetime.datetime.now()


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def send(text):
    text = labelled(text)
    rec = {"ts": now().isoformat(timespec="seconds"), "text": text}
    if DRY: print(text, flush=True); return
    open(OUTBOX_F, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")


def flush():
    if DRY or not os.path.exists(OUTBOX_F) or not os.path.exists(HOOK_F): return
    url = open(HOOK_F).read().strip()
    rows = [json.loads(l) for l in open(OUTBOX_F) if l.strip()]
    if not rows: return
    if len(rows) > 40:   # first flush after a long wait: say how many were skipped, send the newest 40
        rows = [{"text": f":information_source: {len(rows) - 40} older events skipped (feed was waiting for the webhook)"}] + rows[-40:]
    left = []
    for i, r in enumerate(rows):
        try:
            req = urllib.request.Request(url, json.dumps({"text": r["text"]}).encode(), {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20).read(); time.sleep(1.1)   # Slack webhooks: ~1 msg/s
        except Exception as e:
            left = rows[i:]; open(f"{HERE}/feed.err", "a").write(f"{now():%F %T} send failed: {e}\n"); break
    open(OUTBOX_F, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in left))


def event(kind, phone, app, handle, detail):
    open(EVENTS_F, "a").write(json.dumps({"ts": now().isoformat(timespec="seconds"), "kind": kind, "phone": phone,
                                          "app": app, "handle": handle, "detail": detail}, ensure_ascii=False) + "\n")


def new_lines(st, path):
    """Lines appended since the last read. First sight of a file = start at its end."""
    try: size = os.path.getsize(path)
    except OSError: return []
    off = st["off"].get(path)
    if off is None or off > size:   # first sight: skip history only for files that existed when the feed first started
        st["off"][path] = (0 if st.get("init_done") else size) if off is None else 0; off = st["off"][path]
    if off == size: return []
    with open(path, "rb") as f: f.seek(off); data = f.read()
    cut = data.rfind(b"\n") + 1          # only whole lines
    st["off"][path] = off + cut
    return data[:cut].decode("utf-8", "replace").splitlines()


_last_problem = {}
def problem(phone, msg):
    if NOISE.search(msg): return
    key = (phone, re.sub(r"\d+", "N", msg)[:80])
    if time.time() - _last_problem.get(key, 0) < 30 * 60: return      # same problem at most once per 30 min
    _last_problem[key] = time.time()
    send(f":warning: *Problem* · {phone} · {msg.strip()[:300]}"); event("problem", phone, None, None, msg.strip()[:300])


def scan_warm(st):
    for path, phone0, app0 in WARM_LOGS:
        for line in new_lines(st, path):
            m = OPEN.search(line)
            if m:
                key = m.group(1)
                if m.group(2): handle, mins, app = m.group(2), float(m.group(3)), "TikTok"
                elif m.group(4): handle, mins, app = m.group(4), float(m.group(6)), "IG"
                else: handle, mins, app = m.group(8), float(m.group(10)), "TikTok" if m.group(7) == "tiktok" else "IG"
                phone = phone0 or ("Realme" if handle in REALME else "Redmi")
                st["open"][f"{path}|{key}"] = {"handle": handle, "phone": phone, "app": app0 if app0 and app0 != "TikTok" else app,
                                              "t0": ts_of(line), "plan": mins, "seen": 0, "ontopic": 0, "follows": 0, "likes": 0}
                continue
            m = CLOSE.search(line)
            if m:
                s = st["open"].pop(f"{path}|{m.group(1)}", None)
                if not s: continue
                el = ts_of(line) - s["t0"]; mins = round(el / 60) if 0 < el < 3 * 3600 else round(s["plan"])
                bits = [f"{mins} min"]
                if s["seen"]: bits.append(f"{s['seen']} videos ({s['ontopic']} on-topic)" if s["ontopic"] else f"{s['seen']} videos")
                if s["follows"]: bits.append(f"{s['follows']} follows")
                if s["likes"]: bits.append(f"{s['likes']} likes")
                if m.group(2): bits.append(f"follows today {m.group(2)}")
                send(f":fire: *Warm-up done* · @{s['handle']} · {s['phone']} {s['app']} · " + ", ".join(bits))
                event("warm", s["phone"], s["app"], s["handle"], {"min": mins, "seen": s["seen"], "follows": s["follows"]})
                continue
            m = re.search(r"\[(\w+)\]", line)
            s = st["open"].get(f"{path}|{m.group(1)}") if m else None
            if s:
                r = re.search(r"(\d+) (?:reels|videos)(?:, (\d+) on-topic)?", line)
                if r: s["seen"] += int(r.group(1)); s["ontopic"] += int(r.group(2) or 0)
                w = re.search(r"watched (\d+)", line)
                if w: s["seen"] += int(w.group(1))
                if re.search(r"followed @|follow=yes", line): s["follows"] += 1
                if re.search(r"\bliked\b", line): s["likes"] += 1
            if PROBLEM.search(line) and not re.search(r"switch to @\S+ failed, restarting TikTok and retrying once|switcher row", line):
                phone = phone0 or ("Realme" if "[himitsu]" in line else "Redmi")
                problem(phone, line[20:] if line[:4].isdigit() else line)


def scan_posts(st):
    for path, phone_d, app0 in POST_JSONL:
        for line in new_lines(st, path):
            phone = phone_d
            try: r = json.loads(line)
            except Exception: continue
            handle = r.get("acct") or r.get("handle") or "?"
            if handle == "FAILED":
                send(f":x: *Post gave up* · {phone} · `{r.get('name')}` failed 3 times"); event("post_failed", phone, app0, None, r.get("name")); continue
            status = r.get("status", "live"); phone = "Realme" if (app0 == "IG" and handle in REALME) else phone
            app = app0 or ("IG" if r.get("app") == "instagram" else "TikTok")
            name = r.get("name") or r.get("id") or "?"
            if status == "live":
                send(f":white_check_mark: *Posted* · @{handle} · {phone} {app} · `{name}`"); event("post", phone, app, handle, name)
            elif status == "failed":
                send(f":x: *Post failed* · @{handle} · {phone} {app} · `{name}` (will retry)"); event("post_failed", phone, app, handle, name)
            else:
                send(f":rotating_light: *Post {status}* · @{handle} · {phone} {app} · `{name}`: check by hand"); event("post_failed", phone, app, handle, name)


def scan_loops(st):
    for path, phone in LOOP_LOGS:
        pend = st["pending_post"].get(path)
        for line in new_lines(st, path):
            m = re.match(r"\S+ \S+ (IG )?POST (\S+)$", line)
            if m: st["pending_post"][path] = pend = {"name": m.group(2), "app": "IG" if m.group(1) else "TikTok"}; continue
            m = re.match(r"\s+exit (-?\d+)$", line)
            if m and pend:
                if m.group(1) != "0":
                    send(f":x: *Post failed* · {phone} {pend['app']} · `{pend['name']}` (exit {m.group(1)}; loop retries, gives up after 3)")
                    event("post_failed", phone, pend["app"], None, pend["name"])
                st["pending_post"][path] = pend = None; continue
            if re.search(r"exit [1-9]\d*:", line) or (PROBLEM.search(line) and not re.search(
                    r"switch to @\S+ failed, restarting TikTok and retrying once|switcher row|backing off|ONLINE again", line)):
                problem(phone, line[20:] if line[:4].isdigit() else line)
    for p in sorted(glob.glob(f"{ROOT}/lava/post_*.log") + glob.glob(f"{ROOT}/insta/repost_*.log")):   # one-off post scripts
        for line in new_lines(st, p):
            m = re.search(r"\[(\w+)\] RESULT (live|NOT LIVE)(.*)", line)
            if m and m.group(2) == "live" and "lava" in p: continue   # lava_post.py also writes lava_posts.jsonl -> reported there
            if m: send(f"{':white_check_mark:' if m.group(2) == 'live' else ':rotating_light:'} *One-off post {m.group(2)}* · {m.group(1)}{m.group(3)} ({os.path.basename(p)})")


def check_health(st):
    try: out = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=20).stdout
    except Exception: out = None
    if out is not None:
        for serial, phone in PHONES.items():
            ok = re.search(rf"^{serial}\s+device$", out, re.M) is not None
            # 22 Nov owner (Slack noise): the Redmi drops off USB for ~1 min many times a day and comes back by itself ->
            # alert only when a phone is still missing 2+ min later; "back" only after such an alert
            st.setdefault("phone_gone_since", {})
            if not ok:
                since = st["phone_gone_since"].setdefault(serial, time.time())
                if time.time() - since >= 120 and st["phone_ok"].get(serial, True):
                    problem(phone, "phone off USB for 2+ min (cable/hub?)"); st["phone_ok"][serial] = False
            else:
                st["phone_gone_since"].pop(serial, None)
                if not st["phone_ok"].get(serial, True): send(f":large_green_circle: {phone} back on USB")
                st["phone_ok"][serial] = True
    try:   # 22 Nov: a LONG internet outage on the Redmi (> 6 min) still alerts; 2-min blips after posts/VPN switches don't
        last = open(os.path.expanduser("~/masonry-tools/pranks/run_forever.log")).read().splitlines()[-1]
        if "OFFLINE" in last and time.time() - ts_of(last) > 360 and st.get("offline_alerted") != last[:19]:
            problem("Redmi", "no internet for 6+ min (Wi-Fi/VPN?)"); st["offline_alerted"] = last[:19]
    except Exception: pass
    for script, (phone, pause) in LOOPS.items():
        if os.path.exists(pause) or not st["loop_seen"].get(script):
            alive = subprocess.run(["pgrep", "-f", f"^[^ ]*[Pp]ython[^ ]* {script}"], capture_output=True).returncode == 0
            if alive: st["loop_seen"][script] = True
            st["loop_miss"][script] = 0; continue
        alive = subprocess.run(["pgrep", "-f", f"^[^ ]*[Pp]ython[^ ]* {script}"], capture_output=True).returncode == 0
        st["loop_miss"][script] = 0 if alive else st["loop_miss"].get(script, 0) + 1
        if st["loop_miss"][script] == 2: problem(phone, f"loop {script} is not running (no pause file)")


def daily_summary(st):
    t = now()
    if t.hour != 10 or st.get("summary_day") == t.date().isoformat(): return
    st["summary_day"] = t.date().isoformat(); since = t - datetime.timedelta(hours=24)
    rows = [json.loads(l) for l in open(EVENTS_F)] if os.path.exists(EVENTS_F) else []
    rows = [r for r in rows if datetime.datetime.fromisoformat(r["ts"]) >= since]
    acc = {}
    for r in rows:
        if not r.get("handle"): continue
        a = acc.setdefault((r["phone"], r["app"], r["handle"]), {"posts": 0, "fails": 0, "sessions": 0, "min": 0})
        if r["kind"] == "post": a["posts"] += 1
        elif r["kind"] == "post_failed": a["fails"] += 1
        elif r["kind"] == "warm": a["sessions"] += 1; a["min"] += r["detail"].get("min", 0)
    probs = sum(1 for r in rows if r["kind"] == "problem")
    lines = [f"*Daily phone summary* (last 24 h to {t:%d %b %H:%M} IST): {sum(a['posts'] for a in acc.values())} posts, "
             f"{sum(a['sessions'] for a in acc.values())} warm-up sessions, {probs} problems"]
    for (phone, app, h), a in sorted(acc.items()):
        bits = []
        if a["posts"]: bits.append(f"{a['posts']} posted")
        if a["fails"]: bits.append(f"{a['fails']} failed")
        if a["sessions"]: bits.append(f"{a['sessions']} warm-ups / {a['min']} min")
        lines.append(f"• {phone} {app} @{h}: " + ", ".join(bits))
    if len(lines) == 1: lines.append("• nothing ran")
    send("\n".join(lines))


def main():
    lk = open(f"{HERE}/.lock", "w")
    try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if not DRY: print("phone_feed already running"); sys.exit(0)
    st = load(STATE_F, {})
    for k in ("off", "open", "pending_post", "phone_ok", "loop_miss", "loop_seen"): st.setdefault(k, {})
    if not st.get("started"): send(":robot_face: Phone activity feed is on: posts, warm-ups and problems for every account on the 4 phones.")
    st["started"] = True
    last_health = 0
    while not os.path.exists(f"{HERE}/STOP"):
        try:
            scan_posts(st); scan_warm(st); scan_loops(st)
            if time.time() - last_health > 300: check_health(st); last_health = time.time()
            daily_summary(st)
        except Exception as e:
            open(f"{HERE}/feed.err", "a").write(f"{now():%F %T} {type(e).__name__}: {e}\n")
        st["init_done"] = True
        json.dump(st, open(STATE_F, "w"))
        flush()
        if DRY and "--once" in sys.argv: break
        time.sleep(20)


if __name__ == "__main__":
    main()
