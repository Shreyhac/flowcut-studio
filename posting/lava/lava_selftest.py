#!/usr/bin/env python3
"""Checks for the Lava posting rules (13 Nov 2026, lava/NEXT.md checklist). Works on temp copies only: never the real
post_queue.json, lava_posts.jsonl or POST_STOP, and nothing is ever posted.

usage: lava_selftest.py            scheduling rules (no phone)
       lava_selftest.py --device   also the live check on the Lava: a profile whose count does not change -> NOT LIVE
Output goes to stdout and ~/Desktop/lava-check/post-tests/selftest_<time>.txt
"""
import copy, datetime, json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lava_sched as S

OUT = []
def say(m): print(m, flush=True); OUT.append(m)
FAILS = []
def check(cond, why):
    say(("PASS " if cond else "FAIL ") + why)
    if not cond: FAILS.append(why)

NOW = datetime.datetime(2026, 11, 14, 12, 0).timestamp()
def ago(minutes): return datetime.datetime.fromtimestamp(NOW - minutes * 60).isoformat(timespec="seconds")
def post(iid, key, minutes, status="live"): return {"ts": ago(minutes), "id": iid, "key": key, "status": status}

REAL_Q = json.load(open(os.path.join(HERE, "post_queue.json")))["items"]
def items(approve=()):
    q = copy.deepcopy(REAL_Q)
    for it in q: it["approved"] = it["id"] in approve
    return q


def scheduling():
    S.HUMAN = False        # the 13 Nov rules alone; the 14 Nov evening/daily rules are tested in human()
    tmp = tempfile.mkdtemp(prefix="lava_selftest_")
    qf, pf, sf = (os.path.join(tmp, f) for f in ("post_queue.json", "lava_posts.jsonl", "POST_STOP"))
    calls = []
    def fake_post(it): calls.append(it["id"]); return 0
    logs = []
    def run(approve, stop, posts=()):
        json.dump({"items": items(approve)}, open(qf, "w"))
        open(pf, "w").write("".join(json.dumps(p) + "\n" for p in posts))
        if stop: open(sf, "w").write("test")
        elif os.path.exists(sf): os.remove(sf)
        calls.clear()
        return S.post_step(logs.append, fake_post, stop_f=sf, queue_f=qf, posts_f=pf, now=NOW)

    say("== (a)(b)(c) a fake due item: messi_silent_madison, nothing posted before")
    r = run({"messi_silent_madison"}, stop=True)
    check(r == "stopped" and not calls, "(a) POST_STOP exists + an approved, due item -> no post (POST_STOP is the owner's brake)")
    r = run(set(), stop=False)
    check(r == "none" and not calls, "(b) no POST_STOP, every item approved: false -> no post (only Shreyansh-approved videos go out)")
    it = S.pick(items({"messi_silent_madison"}), [], NOW)
    check(it is not None and it["id"] == "messi_silent_madison" and it["key"] == "madison" and it["app"] == "tiktok",
          "(c) approved: true -> pick() returns that item for @acct_159 (selection only, nothing posted)")

    say("== gaps (fake lava_posts.jsonl entries in a temp copy)")
    both = {"messi_silent_madison", "messi_silent_brooke"}
    it = S.pick(items(both), [post("gta_watchthis_brooke", "brooke", 1)], NOW)
    check(it and it["id"] == "messi_silent_madison", "Brooke posted 1 min ago -> Madison may post right away (owner: no gap between different accounts)")
    check(S.pick(items({"messi_silent_brooke"}), [post("gta_watchthis_brooke", "brooke", 50)], NOW) is None,
          "Brooke posted 50 min ago and only Brooke is approved -> nothing (1 hour per account)")
    it = S.pick(items({"messi_silent_brooke"}), [post("gta_watchthis_brooke", "brooke", 61)], NOW)
    check(it and it["id"] == "messi_silent_brooke", "Brooke posted 61 min ago -> Brooke may post again")
    check(S.pick(items({"messi_silent_brooke"}), [post("gta_watchthis_brooke", "brooke", 61, "NOT LIVE")], NOW) is not None and
          S.pick(items({"messi_silent_brooke"}), [post("gta_watchthis_brooke", "brooke", 50, "NOT LIVE")], NOW) is None,
          "a NOT LIVE attempt counts as a post for the gaps (it may be live after all)")
    check(S.pick(items({"messi_silent_brooke"}), [post("messi_silent_brooke", "brooke", 120)], NOW) is None,
          "an item that went live is never posted twice")
    check(S.pick(items({"messi_silent_brooke"}), [post("messi_silent_brooke", "brooke", 120, "NOT LIVE")], NOW) is None,
          "a NOT LIVE item is not retried automatically (duplicate risk: a human checks the profile)")
    f3 = [post("messi_silent_brooke", "brooke", m, "failed") for m in (90, 60, 30)]
    check(S.pick(items({"messi_silent_brooke"}), f3, NOW) is None, "3 failures -> no 4th try")
    it = S.pick(items({"messi_silent_brooke"}), f3[:2] + [post("gta_watchthis_madison", "madison", 100)], NOW)
    check(it and it["id"] == "messi_silent_brooke", "2 failures -> retried (failures happen before Post, so they start no gap)")
    it = S.pick(items({"messi_silent_brooke", "messi_silent_madison"}),
                [post("gta_watchthis_madison", "madison", 300), post("gta_watchthis_brooke", "brooke", 100)], NOW)
    check(it and it["id"] == "messi_silent_madison", "two accounts due -> the one idle longest posts first")

    say("== NOT LIVE in the loop")
    def notlive_post(it): calls.append(it["id"]); return 2
    json.dump({"items": items({"messi_silent_madison"})}, open(qf, "w")); open(pf, "w").write("")
    if os.path.exists(sf): os.remove(sf)
    r = S.post_step(logs.append, notlive_post, stop_f=sf, queue_f=qf, posts_f=pf, now=NOW)
    check(r == "notlive" and os.path.exists(sf), "lava_post exit 2 (NOT LIVE) -> POST_STOP is put back at once")
    shutil.rmtree(tmp)
    say("loop log lines: " + " | ".join(logs[-3:]))


def human():
    import lava_plan as P
    from zoneinfo import ZoneInfo
    S.HUMAN = True
    et = ZoneInfo("America/New_York")
    def at(h, m=0, d=14): return datetime.datetime(2026, 11, d, h, m, tzinfo=et).timestamp()
    def row(iid, key, t, status="live"): return {"ts": datetime.datetime.fromtimestamp(t).isoformat(timespec="seconds"), "id": iid, "key": key, "status": status}
    q = items({"messi_silent_madison", "gta_watchthis_madison"})
    say("== human posting rules (14 Nov): local evening only, 1 per account per local day")
    check(S.pick(q, [], at(12)) is None, "Madison at 12:00 New York -> no post (outside the 18:00-23:00 evening)")
    it = S.pick(q, [], at(19))
    check(it is not None and it["key"] == "madison", "Madison at 19:00 New York -> may post")
    check(S.pick(q, [row("gta_watchthis_madison", "madison", at(18, 30))], at(21)) is None,
          "Madison posted 18:30 today -> nothing at 21:00 although the 1 h gap passed (1 a day)")
    it = S.pick(q, [row("gta_watchthis_madison", "madison", at(19, d=13))], at(19))
    check(it is not None and it["id"] == "messi_silent_madison", "yesterday's post does not block today's evening")
    check(S.pick(items({"messi_silent_brooke"}), [], at(19), only="madison") is None, "only=madison never picks Brooke's item")
    say("== day plans")
    import random
    for key in P.TZ:
        tz = ZoneInfo(P.TZ[key]); counts = []
        for i in range(60):
            day = datetime.date(2026, 11, 16) + datetime.timedelta(days=i)
            ss = P.make_day(key, day, random.Random(i))
            counts.append(len(ss))
            for x in ss:
                loc = datetime.datetime.fromtimestamp(x["t"], tz); h = loc.hour + loc.minute / 60 + (24 if loc.date() > day else 0)
                w = next(w for w in P.WINDOWS if w[0] == x["w"])
                if not (w[1] <= h <= w[2] and w[4][0] <= x["min"] <= w[4][1]):
                    check(False, f"{key} {day} {x}: outside its window"); break
            if day.weekday() == P.LIGHT_DAY[key]:
                if len(ss) > 2: check(False, f"{key} light day {day} has {len(ss)} sessions")
        avg = sum(counts) / len(counts)
        check(3.0 <= avg <= 5.5, f"{key}: {avg:.1f} sessions a day on average over 60 days (3-5.5), every one inside its window")
    plan = {"madison": {"x": [{"t": 1000, "min": 10, "w": "lunch", "done": None}, {"t": 9000, "min": 10, "w": "evening", "done": None}]}}
    best, missed = P.due(plan, 1000 + 3 * 3600 + 1)
    check(best and best[1]["t"] == 9000 and missed and plan["madison"]["x"][0]["done"] == "missed",
          "a session more than 3 h late is dropped as missed; the next due one runs")


def device():
    """Live check against profiles whose count cannot change (nothing is posted): must come back NOT LIVE and be logged."""
    tmp = tempfile.mkdtemp(prefix="lava_selftest_")
    os.environ["LAVA_POSTS"] = os.path.join(tmp, "lava_posts.jsonl")
    import lava_post as P
    P.TAG = "[selftest] "
    for key in ("yuna", "brooke"):
        it = next(i for i in REAL_Q if i["key"] == key)
        P.set_vpn(key)
        if P.ACCTS[key]["app"] == "instagram":
            P.ig_switch(P.ACCTS[key]["handle"]); before, _ = P.ig_count()
            status = P.ig_verify(P.ACCTS[key]["handle"], before, tries=2, gap=5)
        else:
            t = P.tt_switch(P.ACCTS[key]["handle"]); before = P.tt_videos(t)
            status = P.tt_verify(P.ACCTS[key]["handle"], before, tries=2, gap=5)
        say(f"{key}: live check with no new post (count {before}) -> {status}")
        row = P.record(it, key, status)
        logged = [json.loads(l) for l in open(os.environ["LAVA_POSTS"])][-1]
        check(status.startswith("NOT LIVE") and row["status"] == "NOT LIVE" and logged["status"] == "NOT LIVE",
              f"{key} ({P.ACCTS[key]['app']}): count did not go up -> logged NOT LIVE (a post only counts when the profile shows it)")
    say(f"temp post log: {open(os.environ['LAVA_POSTS']).read().strip()}")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    real = {f: os.path.getmtime(os.path.join(HERE, f)) for f in ("post_queue.json",) if os.path.exists(os.path.join(HERE, f))}
    real_posts = open(os.path.join(HERE, "lava_posts.jsonl")).read() if os.path.exists(os.path.join(HERE, "lava_posts.jsonl")) else None
    stop_before = os.path.exists(os.path.join(HERE, "POST_STOP"))
    scheduling()
    human()
    if "--device" in sys.argv: device()
    check({f: os.path.getmtime(os.path.join(HERE, f)) for f in real} == real, "the real post_queue.json was not touched")
    now_posts = open(os.path.join(HERE, "lava_posts.jsonl")).read() if os.path.exists(os.path.join(HERE, "lava_posts.jsonl")) else None
    check(now_posts == real_posts, "the real lava_posts.jsonl was not touched")
    check(os.path.exists(os.path.join(HERE, "POST_STOP")) == stop_before, "the real POST_STOP is as it was")
    say(f"{'ALL PASSED' if not FAILS else str(len(FAILS)) + ' FAILED'}")
    p = os.path.expanduser(f"~/Desktop/lava-check/post-tests/selftest_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write("\n".join(OUT) + "\n")
    print("saved", p)
    sys.exit(1 if FAILS else 0)
