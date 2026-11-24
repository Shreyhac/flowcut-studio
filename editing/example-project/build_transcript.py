#!/usr/bin/env python3
"""vid87 — whisper words -> transcript.json, mishears fixed BY INDEX.

whisper small is the timing source; whisper medium (vid87/aroll-medium.json)
is the wording check.  Against script #8 of scripts-12-new.md and the take:

   7/8   'who will'  -> 'Google'     (one word, two tokens; medium hears Google)
   9     'send'      -> 'sent'
  35/36  'his side'  -> 'your site'
  60/61  'Come in'   -> 'Comment'    (one word, two tokens)
  62     'bots'      -> 'BOTS'       (the comment keyword, as typed)

Fixed by index and asserted, never by string map.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUR = 16.867

d = json.load(open(os.path.join(ROOT, "vid87", "aroll.json")))
W = [dict(w=x["word"].strip(), s=round(x["start"], 3), e=round(x["end"], 3))
     for s in d["segments"] for x in s["words"]]
assert len(W) == 68, "whisper gave %d words, expected 68" % len(W)


def expect(i, word):
    if W[i]["w"] != word:
        sys.exit("word %d is %r, expected %r — the mishear moved" % (i, W[i]["w"], word))


expect(7, "who"); expect(8, "will"); expect(9, "send")
expect(35, "his"); expect(36, "side")
expect(60, "Come"); expect(61, "in"); expect(62, "bots")
W[9]["w"] = "sent"
W[35]["w"] = "your"; W[36]["w"] = "site"
W[62]["w"] = "BOTS"
# merge two-token mishears into one word, spanning both
W[7] = dict(w="Google", s=W[7]["s"], e=W[8]["e"]); del W[8]
# indices shifted by one after the first merge
W[59] = dict(w="Comment", s=W[59]["s"], e=W[60]["e"]); del W[60]
assert len(W) == 66
expect(6, "simple,"); expect(15, "money."); expect(58, "this."); expect(59, "Comment")
expect(60, "BOTS"); expect(65, "taken.")

for i, w in enumerate(W):
    if w["e"] <= w["s"]:
        w["e"] = round(W[i + 1]["s"] if i + 1 < len(W) else w["s"] + 0.12, 3)
assert W[-1]["e"] <= DUR

text = " ".join(w["w"] for w in W)
json.dump(dict(words=W, text=text, duration=DUR),
          open(os.path.join(HERE, "transcript.json"), "w"), indent=1)
print("%d words -> transcript.json" % len(W))
print(text)
