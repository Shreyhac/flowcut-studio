#!/usr/bin/env python3
"""words_env.json: whisper words + an RMS-envelope onset per word (10 ms hop).
Valley first in [s-0.12, s+0.06], then the first rise past 45% of valley->peak (a fixed
peak-minus-18 dB threshold fired on room tone in vid94).

    python3 gkit/envelope.py vid95
"""
import json, os, subprocess, sys
import numpy as np

d = sys.argv[1]
j = json.load(open(os.path.join(d, "aroll.json")))
ws = [w for s in j["segments"] for w in s["words"]]
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(d, "aroll16.wav"), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
hop = 160
n = len(x) // hop
db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12))
out = []
for w in ws:
    s, e = w["start"], w["end"]
    a = max(0, int((s - 0.12) * 100)); m = min(n - 1, int((s + 0.06) * 100)); b = min(n - 1, int(e * 100) + 1)
    v = a + int(np.argmin(db[a:m + 1]))
    lo = db[v]; pk = db[v:b + 1].max() if b > v else lo
    thr = lo + 0.45 * (pk - lo)
    k = next((i for i in range(v, b + 1) if db[i] >= thr), v)
    out.append({"w": w["word"].strip(), "s": round(s, 3), "e": round(e, 3), "on": round(k / 100.0, 3), "p": round(w.get("probability", 1), 2)})
json.dump(out, open(os.path.join(d, "words_env.json"), "w"))
print("%d words" % len(out))
for i, o in enumerate(out):
    flag = (" env%+.2f" % (o["on"] - o["s"])) if abs(o["on"] - o["s"]) > 0.06 else ""
    low = " LOWP" if o["p"] < 0.6 else ""
    print("%3d %7.3f %-16s%s%s" % (i, o["s"], o["w"], flag, low))
