#!/usr/bin/env python3
"""23 Nov 2026 owner: "need to engage with the post in 5-10 mins".
The Lava/Realme JP accounts are busy with their own warm-ups + posts at that moment, so Yui on the Redmi engages:
watches every new JP GTA post (ig_posts.jsonl), pauses the Redmi controller (pranks/PAUSE) as soon as a post lands,
and 5-10 min after the post runs jp_engage.py yui <poster> (VPN Japan -> watch full video, like, save, comment ~1 in 3 ->
VPN back to the US). A Redmi post in progress is never interrupted; a warm-up in progress is stopped (it is only scrolling).
Then the PAUSE file is removed and the watchdog restarts the controller.  usage: jp_fast_engage.py   (runs all day)"""
import datetime, json, os, random, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.join(os.path.dirname(HERE), "pranks"); PAUSE = f"{PR}/PAUSE"
LOG = f"{HERE}/jp_engage.log"; DONE_F = f"{HERE}/jp_fast_engage_done.json"
ACC = json.load(open(f"{HERE}/jp_accounts.json")); JP_HANDLES = {a["handle"] for a in ACC.values()}


def log(m):
    line = time.strftime("%Y-%m-%d %H:%M:%S") + f" [fast] {m}"; print(line, flush=True); open(LOG, "a").write(line + "\n")


def running(pat):
    return subprocess.run(["pgrep", "-f", pat], capture_output=True).returncode == 0


def new_posts(done):
    out = []
    for l in open(f"{HERE}/ig_posts.jsonl"):
        try: d = json.loads(l)
        except Exception: continue
        if d.get("acct") not in JP_HANDLES or d["name"] in done: continue
        ts = datetime.datetime.fromisoformat(d["ts"])
        if (datetime.datetime.now() - ts).total_seconds() < 40 * 60: out.append((d["name"], d["acct"], ts))
    return out


def main():
    done = json.load(open(DONE_F)) if os.path.exists(DONE_F) else []
    log("watching for new JP posts")
    while datetime.datetime.now().hour < 23:
        for name, acct, ts in new_posts(done):
            mine = not os.path.exists(PAUSE)
            if mine: open(PAUSE, "w").write("jp_fast_engage: Yui engages a new JP post")
            at = ts + datetime.timedelta(minutes=random.uniform(5, 9))
            log(f"new post {name} by @{acct} at {ts:%H:%M} -> Yui engages at {at:%H:%M} (controller paused)")
            while datetime.datetime.now() < at: time.sleep(10)
            for _ in range(60):                       # never cut a Redmi post (TikTok or IG) in half
                if not (running(r"pranks/post\.py|python3 post\.py") or running("ig_post_edits.py")): break
                time.sleep(10)
            # stop whatever the controller is in the middle of (a warm-up / stats); PAUSE keeps it from starting anything
            subprocess.run(["pkill", "-f", r"^[^ ]*[Pp]ython[^ ]* run_forever.py"]); subprocess.run(["pkill", "-f", "insta/ig_warm.py"])
            subprocess.run(["pkill", "-f", "pranks/stats.py"]); time.sleep(5)
            r = subprocess.run(["python3", f"{HERE}/jp_engage.py", "yui", acct], capture_output=True, text=True, timeout=1200)
            last = [l for l in r.stdout.splitlines() if l.strip()]
            log(f"Yui on @{acct}: exit {r.returncode} {last[-1][20:] if last else (r.stderr or '')[-200:]}")
            done.append(name); json.dump(done[-200:], open(DONE_F, "w"))
            if mine and os.path.exists(PAUSE) and "jp_fast_engage" in open(PAUSE).read(): os.remove(PAUSE)
        time.sleep(30)
    log("done for today")


if __name__ == "__main__":
    main()
