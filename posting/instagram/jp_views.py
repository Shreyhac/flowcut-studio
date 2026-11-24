#!/usr/bin/env python3
"""24 Nov 2026 owner: views table for every Japanese IG video (target 1,000+ within 2-3 days).
Reads each JP account's logged-out reels page (latest 12 reels, ~/masonry-template-scan/scan/ig_page.py) and names each
reel from ig_posts.jsonl (closest post time, within 3 h). Appends every reading to out/jp_views.jsonl.
usage: jp_views.py [--md]      (--md = markdown table)"""
import datetime, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
import types   # ig_page.py runs its CLI at import time -> load only the code above its `users = ...` line
_src = open(os.path.expanduser("~/masonry-template-scan/scan/ig_page.py")).read()
ig_page = types.ModuleType("ig_page"); exec(_src[:_src.index("\nusers = ")], ig_page.__dict__)
EXTRA = ["acct_237", "acct_129"]          # the other Japanese accounts
handles = [a["handle"] for a in json.load(open(f"{HERE}/jp_accounts.json")).values()] + EXTRA
posts = [json.loads(l) for l in open(f"{HERE}/ig_posts.jsonl") if l.strip()]
now = datetime.datetime.now(); rows = []
for h in handles:
    r = ig_page.read(h); time.sleep(1.5)
    if r.get("status") != "ok": rows.append(dict(acct=h, code="-", name=f"READ FAILED ({r.get('status')} {r.get('http', '')})", views=None, age_h=None)); continue
    mine = [p for p in posts if p.get("acct") == h]
    for code, v in sorted(r["reels"].items(), key=lambda x: -x[1]["ts"]):
        t = datetime.datetime.fromtimestamp(v["ts"])
        best = min(mine, key=lambda p: abs((datetime.datetime.fromisoformat(p["ts"]) - t).total_seconds()), default=None)
        name = best["name"] if best and abs((datetime.datetime.fromisoformat(best["ts"]) - t).total_seconds()) < 3 * 3600 else "?"
        rows.append(dict(acct=h, code=code, name=name, views=v["views"], posted=t.isoformat(timespec="minutes"),
                         age_h=round((now - t).total_seconds() / 3600, 1)))
with open(f"{HERE}/out/jp_views.jsonl", "a") as f:
    f.write(json.dumps(dict(ts=now.isoformat(timespec="seconds"), rows=rows), ensure_ascii=False) + "\n")
if "--md" in sys.argv:
    print("| Account | Video | Posted (IST) | Age | Views | vs 1,000 |\n|---|---|---|---|---|---|")
    for x in rows:
        ok = "" if x["views"] is None else ("✅" if x["views"] >= 1000 else f"{x['views'] / 10:.0f}%")
        print(f"| @{x['acct']} | {x['name']} | {x.get('posted', '-')[5:].replace('T', ' ')} | {x['age_h']} h | {x['views'] if x['views'] is not None else '-'} | {ok} |")
else:
    for x in rows: print(x)
