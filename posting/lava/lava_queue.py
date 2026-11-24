#!/usr/bin/env python3
"""Build lava/post_queue.json from the reviewed files (13 Nov 2026).

Reads ~/Desktop/lava-videos-for-review/captions.txt (written by masonry-avatar-ugc/fleet/lava_build.py deliver), copies each
video to lava/videos/<id>.mp4 (git-ignored) and writes one queue item per file with "approved": false. Re-running keeps the
"approved" flags already in the queue. Shreyansh approves by setting "approved": true.
usage: lava_queue.py            prints the queue
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REV = os.path.expanduser("~/Desktop/lava-videos-for-review")
QUEUE_F = os.path.join(HERE, "post_queue.json")
ACCTS = json.load(open(os.path.join(HERE, "lava_accounts.json")))
BY_HANDLE = {a["handle"]: k for k, a in ACCTS.items()}


def caption_ok(app, cap):
    """Owner rules. TikTok: ends with #masonry #masonryai, at most 5 hashtags. Instagram: no '#' or '@', ends with a [bracketed keyword] line."""
    if app == "tiktok":
        # 13 Nov: TikTok allows at most 5 hashtags ("Maximum 5 hashtags") and silently drops the 6th while typing
        return cap.rstrip().endswith("#masonry #masonryai") and "@masonryai" not in cap and cap.count("#") <= 5
    lines = [l for l in cap.strip().splitlines() if l.strip()]
    return "#" not in cap and "@" not in cap and bool(lines) and re.fullmatch(r"\[[^\[\]]+\]", lines[-1].strip()) is not None


def parse_captions(txt):
    """captions.txt blocks: '<file>.mp4  (<app> @<handle>)' then the caption up to the next file line or a 'sound' note."""
    items, cur = [], None
    for line in txt.splitlines():
        m = re.match(r"(\S+\.mp4)  \((tiktok|instagram) @([\w.]+)\)$", line)
        n = re.match(r"(\w+): add the sound '(.+)' inside the app", line)
        if m:
            cur = {"file": m.group(1), "app": m.group(2), "handle": m.group(3), "cap": []}; items.append(cur)
        elif n:
            for it in items:
                if it["file"].startswith(n.group(1) + "_"): it["sound"] = n.group(2)
            cur = None
        elif cur is not None:
            cur["cap"].append(line)
    return items


# 13 Nov owner: Instagram posts go through the Edits app, like Shreyansh's insta/ig_post_edits.py. Edits adds the audio:
# Volumes (Gaurav, 13 Nov 21:40): an "Original audio" from the script at 30%, a song from the script at 50-60% (55).
# GTA = the voice-only file + the GTA reference reel's "Original audio" (dennyintech) at 30%;
# Messi = the silent file + the script's song (Mist) at 55%. Both audios are saved on the account first (Instagram audio page), then
# picked from Edits' Saved tab.
EDITS = {"gta_watchthis": {"voice_file": True, "audio_id": "39984116737869879", "audio_match": "dennyintech", "volume": 30},
         "messi_silent": {"voice_file": False, "audio_id": "3975469842666153", "audio_match": "Mist", "volume": 55}}


def build():
    old = {}
    if os.path.exists(QUEUE_F):
        old = {i["id"]: i for i in json.load(open(QUEUE_F))["items"]}
    os.makedirs(os.path.join(HERE, "videos"), exist_ok=True)
    out = []
    for it in parse_captions(open(os.path.join(REV, "captions.txt"), encoding="utf-8").read()):
        iid = it["file"][:-4]
        key = BY_HANDLE[it["handle"]]
        assert ACCTS[key]["app"] == it["app"], iid
        cap = "\n".join(it["cap"]).strip()
        if not caption_ok(it["app"], cap): raise SystemExit(f"{iid}: caption breaks the owner's rules: {cap!r}")
        tpl = iid.rsplit("_", 1)[0]
        ed = EDITS[tpl] if it["app"] == "instagram" else None
        fname = it["file"]
        if ed and ed["voice_file"]:
            fname = f"{iid}_voice.mp4"; shutil.copy2(os.path.join(REV, "edits", fname), os.path.join(HERE, "videos", fname))
        dst = os.path.join(HERE, "videos", it["file"])
        shutil.copy2(os.path.join(REV, it["file"]), dst)
        prev = old.get(iid, {})
        out.append({"id": iid, "template": iid.rsplit("_", 1)[0], "key": key, "app": it["app"], "handle": it["handle"],
                    "file": f"videos/{fname}", "caption": cap, "sound": it.get("sound"),
                    **({"via": "edits", "edits_audio": {k: v for k, v in ed.items() if k != "voice_file"}} if ed else {}),
                    "approved": bool(prev.get("approved", False))})
    json.dump({"_note": "Lava posting queue. Shreyansh approves an item by setting approved: true. lava_forever posts only "
                        "approved items, and only while lava/POST_STOP does not exist. What was posted is in lava_posts.jsonl.", "items": out}, open(QUEUE_F, "w"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    for i in build():
        print(f"{i['id']:28} {i['app']:9} @{i['handle']:22} approved={i['approved']} sound={i['sound']}")
