#!/usr/bin/env python3
"""Keeps the Lava warming up on a human schedule (owner approved 14 Nov 2026, see lava_plan.py): each account has its
own day plan on its own country's clock; one session at a time, the phone idles between sessions.
Posting happens only inside a session of that account, when lava_sched allows it (approved, due, the account's local
evening, at most 1 a day, 1 h per account, no POST_STOP): a few minutes of scrolling, the post, then the rest of the session.
After an Instagram post goes live, the other Instagram account engages with it 1-3 h later (a queued job).
Pause everything: touch lava/PAUSE.  Stop posting only: touch lava/POST_STOP.  Single instance (flock).  Logs: lava_run.log
See the plan: python3 lava_plan.py"""
import fcntl, os, random, subprocess, sys, time, datetime, json
HERE = os.path.dirname(os.path.abspath(__file__))
lock = open(os.path.join(HERE, ".lava_forever.lock"), "w")
try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError: sys.exit("lava_forever already running")
def log(m): open(os.path.join(HERE, "lava_run.log"), "a").write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {m}\n")
PD = "/Applications/PhoneDock.app/Contents/Resources/bin/phonedock"
sys.path.insert(0, HERE); import lava_sched, lava_plan as P
IG_KEYS = ["valeria", "yuna"]
plan = {}


def warm(key, minutes):
    return subprocess.run([sys.executable, os.path.join(HERE, "lava_warm.py"), key, str(minutes)], timeout=60 * 60).returncode


def run_post(it):
    r = subprocess.run([sys.executable, os.path.join(HERE, "lava_post.py"), it["key"], it["file"], "--id", it["id"]], timeout=40 * 60)
    if r.returncode == 0 and it["app"] == "instagram":          # owner: the other IG account likes, saves, comments
        other = [k for k in IG_KEYS if k != it["key"]][0]
        t = time.time() + random.randint(3600, 3 * 3600)        # owner 14 Nov: 1-3 h later, not right away
        P.add_job(plan, {"kind": "engage", "key": other, "target": it["key"], "t": round(t)}); P.save(plan)
        log(f"engage: @{other} on @{it['key']}'s post at {datetime.datetime.fromtimestamp(t):%H:%M}")
    return r.returncode


def post_due(key):
    if os.path.exists(os.path.join(HERE, "POST_STOP")): return False
    items = json.load(open(os.path.join(HERE, "post_queue.json"), encoding="utf-8"))["items"]
    return lava_sched.pick(items, lava_sched.load_posts(os.path.join(HERE, "lava_posts.jsonl")), time.time(), key) is not None


while True:
    if os.path.exists(os.path.join(HERE, "PAUSE")): time.sleep(60); continue
    if "LAVA_SERIAL" not in subprocess.run([PD, "devices"], capture_output=True, text=True).stdout:
        log("Lava not connected - waiting"); time.sleep(120); continue
    now = time.time()
    plan = P.ensure(P.load(), now)
    for j in P.jobs_due(plan, now):
        log(f"engage: @{j['key']} on @{j['target']}'s newest post")
        subprocess.run([sys.executable, os.path.join(HERE, "lava_post.py"), "engage", j["key"], j["target"]], timeout=20 * 60)
        j["done"] = round(time.time()); P.save(plan)
    best, missed = P.due(plan, time.time())
    for k, s in missed: log(f"[{k}] {s['w']} session at {P.fmt(s['t'], P.TZ[k])} local missed (phone busy or off)")
    P.save(plan)
    if not best: time.sleep(60); continue
    key, s = best
    log(f"[{key}] plan: {s['w']} session, {P.fmt(s['t'], P.TZ[key])} local, {s['min']} min")
    rc = 0
    try:
        if post_due(key):
            first = random.randint(3, 5)
            rc = warm(key, first)
            if rc != 3:
                lava_sched.post_step(log, run_post, only=key)
                rc = warm(key, max(3, s["min"] - first - 3))
        else:
            rc = warm(key, s["min"])
    except Exception as e: log(f"[{key}] session error: {e!r}")
    s["done"] = round(time.time()); P.save(plan)
    if rc == 3: log("STOP signal (challenge/limit) - resting 3 h"); time.sleep(3 * 3600)
