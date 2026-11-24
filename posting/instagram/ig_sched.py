"""Instagram posting queue (12 Nov 2026). The video session delivers localized copies to
ig_in/<template>/<igkey>.mp4 + captions.json + READY; ingest() hard-links them into out/ig_<template>_<igkey>.mp4,
writes cfg/, appends ig_queue.txt. next_item() picks what may post now on the Redmi.
Rules (owner): >= 1 h between posts on one account; >= 45 min since ANY
post on the Redmi (TikTok posts.jsonl or IG ig_posts.jsonl); copies of one template on different accounts >= 3 h apart
(every copy has its own voice + script, owner's rule 12 Nov); template order gta2 -> gta1 -> highway."""
import datetime, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/masonry-tools/pranks")); import plan   # 14 Nov: prime time + 3/day (pranks/plan.py)
IN, Q = f"{HERE}/ig_in", f"{HERE}/ig_queue.txt"
# 14 Nov: the Realme posts its own Instagram accounts (fernanda, juliana, larissa, lea, lena) from its own queue
PHONES = {"redmi": ("ig_accounts.json", Q, "2026-11-12"),          # 12 Nov 11:05 owner: "start posting on Instagram from today itself"
          "realme": ("realme_ig_accounts.json", f"{HERE}/ig_queue_realme.txt", "2026-11-14")}
def _post_stopped():   # 18 Nov owner: no posting on accounts in ~/masonry-tools/POST_STOP_ACCOUNTS.txt (best video < 700)
    try: return {l.strip() for l in open(__import__("os").path.expanduser("~/masonry-tools/POST_STOP_ACCOUNTS.txt")) if l.strip() and not l.startswith("#")}
    except FileNotFoundError: return set()

def accts(phone="redmi"): return {k: v for k, v in json.load(open(f"{HERE}/{PHONES[phone][0]}")).items() if not v.get("logged_out")}   # 21 Nov: skip logged-out accounts
ACCTS = accts("redmi")
READY_FROM = {k: "2026-11-12" for k in ACCTS}
ORDER = ["gta2_xavier", "gta1_jazz", "highway_explainer"]
TT_POSTS = os.path.expanduser("~/masonry-tools/pranks/posts.jsonl")

def _lines(p): return [l.strip() for l in open(p)] if os.path.exists(p) else []
def _posts(p):
    out = []
    for l in _lines(p):
        try: out.append(json.loads(l))
        except Exception: pass
    return out

def ingest(log=print, phone="redmi"):
    if not os.path.isdir(IN): return 0
    A, QF = accts(phone), PHONES[phone][1]
    q = set(_lines(Q)) | set(_lines(PHONES["realme"][1])); n = 0
    for t in sorted(os.listdir(IN)):
        d = f"{IN}/{t}"
        if not os.path.exists(f"{d}/READY"): continue
        caps = json.load(open(f"{d}/captions.json")) if os.path.exists(f"{d}/captions.json") else {}
        for k, a in A.items():
            name = f"ig_{t}_{k}"; src = f"{d}/{k}.mp4"
            if name in q or not os.path.exists(src) or not caps.get(k): continue
            dst = f"{HERE}/out/{name}.mp4"
            if os.path.exists(dst): os.remove(dst)
            os.link(src, dst)
            json.dump({"igkey": k, "handle": a["handle"], "caption": caps[k], "template": t, "phone": phone}, open(f"{HERE}/cfg/{name}.json", "w"), ensure_ascii=False, indent=1)
            open(QF, "a").write(name + "\n"); n += 1; log(f"IG queued {name} -> @{a['handle']} ({phone})")
    return n

def _warmed_recently(key, now, hours=2):
    try:
        for l in reversed(open(f"{HERE}/ig_run.log").read().splitlines()[-3000:]):
            if f"[{key}] session end" in l:
                return (now - datetime.datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")).total_seconds() < hours * 3600
    except Exception: pass
    return False

def next_item(now=None, phone="redmi"):
    now = now or datetime.datetime.now()
    A, QF, ready_from = accts(phone), PHONES[phone][1], PHONES[phone][2]
    ig = [p for p in _posts(f"{HERE}/ig_posts.jsonl") if not p["name"].endswith("__notlive")]
    allp = [p for p in _posts(TT_POSTS) if p.get("acct") != "FAILED"] + ig
    ts = lambda p: datetime.datetime.fromisoformat(p["ts"])
    # 13 Nov 15:10 owner: different accounts may post back to back; only the SAME account waits 1-1.5 h (no phone-wide gap)
    done = {p["name"] for p in ig}
    fails = json.load(open(f"{HERE}/ig_fails.json")) if os.path.exists(f"{HERE}/ig_fails.json") else {}
    done |= {n for n, c in fails.items() if c >= 3}
    q = [n for n in dict.fromkeys(_lines(QF)) if n not in done and os.path.exists(f"{HERE}/out/{n}.mp4")]
    q.sort(key=lambda n: next((i for i, t in enumerate(ORDER) if n.startswith(f"ig_{t}_")), 9))
    hold = set(_lines(f"{HERE}/ig_hold.txt"))     # 15 Nov: items being debugged by hand (one name per line)
    approved = set(_lines(f"{HERE}/APPROVED.txt")) if os.path.exists(f"{HERE}/APPROVED.txt") else None   # 24 Nov owner: every video approved by him first
    for n in q:
        if n in hold: continue
        if approved is not None and n not in approved: continue
        c = json.load(open(f"{HERE}/cfg/{n}.json")); k = c["igkey"]
        if c.get("handle") in _post_stopped(): continue
        # 22 Nov owner ("post with proper warmups"): an account posts only right after a finished IG warm-up (last 2 h)
        if not _warmed_recently(k, now): continue
        if k not in A or now.date().isoformat() < ready_from: continue
        if any(p["acct"] == c["handle"] and (now - ts(p)).total_seconds() < 1 * 3600 for p in ig): continue   # owner rule: >= 1 h per account (13 Nov: a 20 h gap I invented was removed)
        # 16 Nov owner "post them now itself": names in ig_force.txt skip the prime-time/cap plan (1 h same-account gap still holds)
        if n not in set(_lines(f"{HERE}/ig_force.txt")) and not plan.ok(c["handle"], n, ig, A[k].get("lang", "en"), now): continue   # 14 Nov owner "crazy views"
        return n
    return None
