#!/usr/bin/env python3
"""captions.json per template for the posting session: varied per account, CTA keyword included,
#masonry #masonryai always (hashtags, never @masonryai). Style matches ~/masonry-tools/pranks/posts.jsonl."""
import json, os

KEYS = ["ethan", "maya", "jake", "beth", "rgu", "chloe", "ava", "sophie", "emma", "lily", "grace", "nora"]
C = {
 "gta2_xavier": ("clipping", "#gta6 #clipping #contentcreator #sidehustle", [
  "GTA 6 is about to make clippers rich \U0001F633 comment \"clipping\" for the guide",
  "learn this before GTA 6 drops \U0001F62D comment \"clipping\" and I'll send it",
  "2 weeks to learn clipping. that's it \U0001F911 comment \"clipping\"",
  "the most clipped game in history is coming \U0001F440 comment \"clipping\" for the free guide",
  "you have 2 weeks. don't waste them \U0001F62E‍\U0001F4A8 comment \"clipping\"",
  "clipping + GTA 6 = \U0001F4B8 comment \"clipping\" if you want the guide",
  "AI clips a whole stream for you now?? \U0001F62D comment \"clipping\"",
  "this is how I'd start clipping before GTA 6 \U0001F447 comment \"clipping\"",
  "nobody is talking about this GTA 6 opportunity \U0001F633 comment \"clipping\"",
  "do this before GTA 6 drops, thank me later \U0001F64F comment \"clipping\"",
  "streams → viral clips in minutes \U0001F92F comment \"clipping\" for the guide",
  "GTA 6 clippers are about to eat \U0001F37D️ comment \"clipping\""]),
 "gta1_jazz": ("creator", "#gta6 #clipping #aitools #sidehustle", [
  "every day, every week, every single month \U0001F4B8 comment \"creator\" for the free guide",
  "learn clipping before GTA 6 drops \U0001F62D comment \"creator\"",
  "this is a generational opportunity fr \U0001F633 comment \"creator\" and I'll DM you",
  "GTA 6 is about to be the most clipped game ever \U0001F440 comment \"creator\"",
  "the AI watches the whole stream for you \U0001F92F comment \"creator\" for the guide",
  "2 weeks. that's all you've got ⏳ comment \"creator\"",
  "clipping before GTA 6 > anything else rn \U0001F4AF comment \"creator\"",
  "confused? comment \"creator\" and I'll send you everything \U0001F64F",
  "500 a day → 15k a month?? \U0001F62E comment \"creator\"",
  "how to learn clipping before it even drops \U0001F447 comment \"creator\"",
  "your clips, ready in minutes \U0001F62D comment \"creator\" for the free guide",
  "GTA 6 + clipping = \U0001F4B0 comment \"creator\""]),
 "highway_explainer": ("story", "#aivideo #youtubeshorts #contentcreator #sidehustle", [
  "you watched the whole thing didn't you \U0001F62D comment \"story\"",
  "31 million people watched this \U0001F633 comment \"story\" and I'll help you start",
  "this video made six figures?? \U0001F92F comment \"story\"",
  "how to make AI videos like this \U0001F447 comment \"story\"",
  "post 3 times a day and watch \U0001F440 comment \"story\" to get started",
  "the quick math on this is crazy \U0001F4B8 comment \"story\"",
  "AI made this whole episode \U0001F62D comment \"story\" for the prompt",
  "wait till the end \U0001F633 comment \"story\" and I'll DM you",
  "a highway for reckless drivers?? \U0001F602 comment \"story\"",
  "YouTube pays this much per million views?? \U0001F62E comment \"story\"",
  "this is exactly how you do it \U0001F64F comment \"story\"",
  "copy the link, paste the prompt, done \U0001F92F comment \"story\""]),
}


def write(tpl):
    kw, tags, lines = C[tpl]
    d = {k: f"{lines[i]} {tags} #masonry #masonryai" for i, k in enumerate(KEYS)}
    assert all(f'"{kw}"' in v and "#masonry " in v and v.endswith("#masonryai") and "@" not in v for v in d.values())
    p = os.path.join(os.path.expanduser(os.environ.get("MGTA_OUT", "~/masonry-tools/pranks/ugc_in")), tpl, "captions.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    return p


if __name__ == "__main__":
    import sys
    for t in (sys.argv[1:] or C):
        print(write(t))
