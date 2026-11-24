"""Posting plan for views (14 Nov 2026, owner: "I just want crazy views, plan accordingly").
Our own numbers (phone reads 13 Nov): prank remixes got 0-37 views each (Ethan 37/8/22/23/30/0, Maya 6/7/7/18/8,
Beth 4/126/2/4/2), avatar UGC copies 37-96 (RGU 96/37/75, Ava 90). Hourly bursts of 9-11 posts on one account fed the
first test batch at 4 am audience time. So, on top of the owner's >= 1 h per account rule:
  1. post only in the audience's prime time (their local clock, not IST): 07-09, 12-14, 18-23
  2. at most 3 posts per account per audience-day, and at most 1 prank remix of those 3 (UGC/template formats go first)
Each loop keeps its own >= 1 h same-account check. `touch pranks/PLAN_OFF` switches 1+2 off (back to the 1 h rule only).
Numbers live in posting_plan.json so they can change without code."""
import datetime, json, os, random
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = {"windows": [[7, 9], [12, 14], [18, 23]], "max_per_day": 3, "max_remix_per_day": 1,
           "warm_windows": [[7, 9], [12, 14], [18, 23]], "awake": [7, 24], "warm_offpeak_p": 0.25,
           "audience_tz": {"en": "America/New_York", "es": "America/Mexico_City", "ja": "Asia/Tokyo",
                           "pt": "America/Sao_Paulo", "fr": "Europe/Paris", "de": "Europe/Berlin"}}


def cfg():
    try: return {**DEFAULT, **json.load(open(f"{HERE}/posting_plan.json"))}
    except Exception: return DEFAULT


def off(): return os.path.exists(f"{HERE}/PLAN_OFF")


def _local(now, lang):
    tz = ZoneInfo(cfg()["audience_tz"].get(lang, "America/New_York"))
    return now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo).astimezone(tz)


def _hh(lang, now):
    h = _local(now or datetime.datetime.now(), lang); return h.hour + h.minute / 60


def in_window(lang="en", now=None):
    if off(): return True
    return any(a <= _hh(lang, now) < b for a, b in cfg()["windows"])


def warm_eligible(langs, now=None):
    """16 Nov owner: "mostly upload and warm up at these times, as a human would do ... same for all other language
    accounts based on their regions". langs = {key: lang}. Returns the keys that may warm up now, on the audience's clock:
      peak (warm_windows, the same prime time as uploads: 07-09, 12-14, 18-23 local) -> always
      awake off-peak (07-24 local)                                                      -> 1 slot in 4 (warm_offpeak_p)
      their night (00-07 local)                                                          -> never
    Japan peaks researched 16 Nov: commute 07-08, lunch 12-13, evening 19-23 (Reels strongest 20-21).
    Empty result = the phone rests (callers sleep ~10 min). PLAN_OFF -> every key."""
    if off(): return set(langs)
    c = cfg(); a0, a1 = c["awake"]; out = set(); offpeak_ok = random.random() < c["warm_offpeak_p"]
    for k, lang in langs.items():
        hh = _hh(lang or "en", now)
        if any(a <= hh < b for a, b in c["warm_windows"]): out.add(k)
        elif a0 <= hh < a1 and offpeak_ok: out.add(k)
    return out


def under_cap(handle, name, posts, lang="en", now=None):
    """posts: [{'ts','name','acct'|'handle'}] already filtered to real (not FAILED / notlive) posts on any platform file."""
    if off(): return True
    now = now or datetime.datetime.now(); c = cfg()
    day = _local(now, lang).date()
    mine = [p for p in posts if (p.get("acct") or p.get("handle")) == handle
            and _local(datetime.datetime.fromisoformat(p["ts"]), lang).date() == day]
    if len(mine) >= c["max_per_day"]: return False
    if name.startswith("remix") and sum(p["name"].startswith("remix") for p in mine) >= c["max_remix_per_day"]: return False
    return True


def ok(handle, name, posts, lang="en", now=None):
    return in_window(lang, now) and under_cap(handle, name, posts, lang, now)


if __name__ == "__main__":   # print today's windows in IST for each audience
    c = cfg(); now = datetime.datetime.now().astimezone()
    for lang, tz in c["audience_tz"].items():
        hrs = [h for h in range(24) if in_window(lang, now.replace(hour=h, minute=0, second=0, microsecond=0))]
        wh = [h for h in range(24) if any(a <= _hh(lang, now.replace(hour=h, minute=0, second=0, microsecond=0)) < b for a, b in c["warm_windows"])]
        print(f"{lang:3} ({tz}): posts at IST hours {hrs} | peak warm-ups at IST hours {wh}")
