#!/usr/bin/env python3
"""22 Nov 2026 owner: is a Japanese IG account ready to post? (checked right before every post)
Ready = account >= 4 days old AND >= 60% relevant reels over its last 3 warm-up sessions AND no STOPPED/challenge
line in the last 72 h AND a finished warm-up in the last 2 h. usage: jp_ready.py [key ...] -> prints verdict per account"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ACC = json.load(open(f"{HERE}/jp_accounts.json"))
MIN_HOURS, MIN_REL, LAST_N = 84, 0.60, 3   # 22 Nov owner: 3.5 days min (7 is too long)
FALSE_STOPS = ("2026-11-24 14:58:37 [sakura]", "2026-11-24 14:30:26 [misaki]", "2026-11-24 14:30:27 [days] lava misaki", "2026-11-21 14:48:25 [miyu]", "2026-11-21 14:48:27 [days] realme miyu", "2026-11-21 15:58:00 [miyu]")   # false alarms, fixed 21 Nov (reel text "ロボット" / my manual test screen)

def check(key, now=None):
    now = now or datetime.datetime.now(); a = ACC[key]; why = []
    created = datetime.datetime.fromisoformat(a.get("created_at_ist") or a["created"] + "T12:00")
    age = round((now - created).total_seconds() / 86400, 1)
    if age * 24 < MIN_HOURS: why.append(f"only {age} days old (min {MIN_HOURS / 24})")
    ends, stops, last_end = [], [], None
    for l in open(f"{HERE}/jp_warm.log").read().splitlines():
        if f"[{key}]" not in l: continue
        ts = datetime.datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
        m = re.search(r"=== end: (\d+) reels, (\d+) relevant", l)
        if m and int(m.group(1)) >= 5: ends.append((int(m.group(1)), int(m.group(2)))); last_end = ts   # 24 Nov: a 0-reel session is not a warm-up
        if "STOPPED" in l and not l.startswith(FALSE_STOPS) and (now - ts).total_seconds() < 72 * 3600 and "proxy" not in l: stops.append(l[20:110])
    seen = sum(x for x, _ in ends[-LAST_N:]); rel = sum(y for _, y in ends[-LAST_N:])
    share = rel / seen if seen else 0
    if share < MIN_REL: why.append(f"feed only {share:.0%} on-topic over last {min(LAST_N, len(ends))} sessions (min {MIN_REL:.0%})")
    if stops: why.append(f"{len(stops)} stop/challenge in 72 h: {stops[-1]}")
    if not last_end or (now - last_end).total_seconds() > 2 * 3600: why.append("no finished warm-up in the last 2 h")
    return (not why), share, age, why

if __name__ == "__main__":
    for k in (sys.argv[1:] or list(ACC)):
        ok, share, age, why = check(k)
        print(f"{k:7} {'READY' if ok else 'not ready'}  day {age}, feed {share:.0%}" + ("" if ok else "  -> " + "; ".join(why)))
