# editing/: Reel Factory

The editing engine: a reference reel (or a brief) plus a talking-head take becomes a finished, platform-safe reel, built in HTML/GSAP and rendered with HyperFrames.

| Path | What |
|---|---|
| `CLAUDE.md` | The agent editor's instructions: the 9-stage pipeline, quality gates, safe zones, design language |
| `SAFE-ZONES.md` | Instagram/TikTok UI safe zones (a hard gate on every render) |
| `gkit/` | Template engine: templates A/B, palettes, word-onset envelope, SFX bed, plate conform, chunked render, delivery QA, pacing check |
| `example-project/` | A complete reel project: build scripts, gates (`gate_safezone.py`, `gate_voids.py`, `gate_audio.py` …), `index.html` composition |
| `review/` + `rr` | Reel Review: a local frame.io (frame-pinned notes, markup, version stacking) |
| `share/` | Cloudflare Worker + KV that serves Reel Review to clients on a private link |
| `ig-autodm/` | Comment keyword → automatic DM through the Instagram Graph API |

Full write-up: [docs/editing.md](../docs/editing.md)
