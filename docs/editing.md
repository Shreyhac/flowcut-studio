# Engine 1: Reel Factory, the editing pipeline

Reel Factory turns **a reference reel (or a written brief) plus a talking-head A-roll** into a finished, Instagram-ready reel. The editor is an AI coding agent (Claude Code) working inside this repo. Its instructions live in [`editing/CLAUDE.md`](../editing/CLAUDE.md), and its accumulated judgement lives in a learnings log and a set of memory files. Compositions are HTML + CSS + GSAP timelines rendered to video by **HyperFrames**, so every frame is deterministic, diffable and re-renderable.

Output so far: **112 reel projects**, **105 written reel breakdowns**, 32 client films on flowcut.cc, and the whole @shreyansharora05 catalogue.

---

## The pipeline (run in this order, every video)

```mermaid
flowchart TD
  R[1 · Deconstruct the reference<br/>frames @2fps + Whisper word timestamps<br/>→ breakdown.md: beat map, shot table] --> S
  S[2 · Collect real assets<br/>Playwright captures of real pages,<br/>verify every repo / product exists] --> A
  A[3 · Prepare the A-roll<br/>cut gaps >0.3 s on video+audio together,<br/>re-whisper, denoise, keep native 4K] --> F
  F[4 · Scaffold from the newest gold-standard project] --> C
  C[5 · Compose index.html<br/>layout first, then gsap.from entrances,<br/>scene cuts on word onsets] --> G
  G[6 · Gates: lint → validate (WCAG) → inspect (layout)] --> X
  X[7 · Render + frame QA at every beat<br/>2–3 fix rounds expected] --> D
  D[8 · Deliver + open in Reel Review] --> FB
  FB[9 · Feedback round<br/>frame-pinned notes → feedback-roundN.md] --> C
```

### 1. Deconstruct the reference
- `ffprobe` the reference, extract frames at 2 fps and read every one.
- `whisper --model small --word_timestamps True` gives the exact voiceover script with word timing.
- Write `<video>-breakdown.md`: the VO script, beat map, shot-by-shot table (time, layer layout, visual), design language, asset checklist and build loop. **105 of these exist**, and they are the spec each build is diffed against.

### 2. Research and collect real assets
- Anything named on screen (a repo, product or page) is verified to exist through the GitHub API or curl, because references often show mocked UI.
- Real pages are captured with headless **Playwright** (`color_scheme="dark"`, `device_scale_factor=2`, about 760 px viewport for 1080-wide placement), over-capturing viewport and full-page in one run.
- What can't be captured is rebuilt as a pixel-accurate HTML mock. `gkit/ig_ui.py` (an Instagram profile) and `gkit/muse_ui.py` (Meta's Muse app) are live-DOM rebuilds of real UIs.

### 3. Prepare the A-roll
- Whisper the raw take, cut gaps over 0.3 s on **video and audio with the same timestamps** (separate cuts drift lip-sync), then **re-whisper the cut file**. Pre-cut timestamps are wrong after the first cut.
- Denoise chain: `highpass=f=75, afftdn=nr=14:nf=-28:tn=1, adeclick, loudnorm=I=-15:TP=-1.2:LRA=9`.
- Transcode at the master's own resolution (`-r 30, libx264 crf 17, -g 15 -keyint_min 15`). Compositions render at 2160×3840, and a 2160 source rasterises **84% sharper** than a 1080 one (measured: 95% vs ~52% of the master's detail).

### 4. Scaffold
- Copy the newest gold-standard project wholesale (fonts, SFX, conventions) and gut its scene assets. Never start from a blank `index.html`.
- Named template engines in [`gkit/`](../editing/gkit):
  - `tmpl_a.py`: the "100xEngineers" grammar (grid paper, tag pill, two-line headline, face card);
  - `tmpl_b.py`: an Apple-keynote editorial grammar (hard black/white flips);
  - `palettes.py`: 8 colourways for a batch;
  - `mkit.py`: a motion kit.

### 5. Compose
- Layout before animation: static hero frames first, then `gsap.from()` entrances. Transitions handle exits.
- Scene boundaries land on **word onsets**. `gkit/envelope.py` refines Whisper times with an RMS-envelope onset per word (10 ms hop, valley then a rise past 45%).
- Nothing static for more than about 1 s: marquees breathe, numbers slam with a screen shake, connectors march.
- SFX are curated per beat from a licensed pack (glitch-open, riser into the first cut, keyboard bed under typing, shine on the CTA) at 0.16–0.34 volume (`gkit/sfx.py` reads a cue table).

### 6. Gates (zero errors before render)
`npx hyperframes lint` → `validate` (WCAG contrast) → `inspect` (layout overflow). Intentional overflow is marked with `data-layout-allow-overflow`, never silenced blindly.

The example project adds its own gates:
- `gate_safezone.py`: every element's box against the platform UI;
- `gate_voids.py`: empty, dead regions;
- `gate_plates.py`: b-roll conform;
- `gate_audio.py`: loudness and clipping;
- `hook_sweep.py`: first-second strength.

### 7. Render and frame QA
- `npx hyperframes render -q high -f 30`. On 8 GB machines, `gkit/build_chunks.py` splits the composition into frame-exact chunks on scene cuts, and `gkit/build_mix.py` muxes the audio separately so the voice is bit-exact.
- `gkit/qa.py sheets` extracts every cut, cut +2 frames and mid-scene from the **delivered** file, never the preview, and the editor reads them all. This is what catches clipped text, dead covers and elements that never enter the frame.
- `gkit/pacing.py` measures the monotony that DOM and frame gates can't see, optionally against the reference's pacing.

### 8–9. Delivery and the feedback loop: Reel Review
- `./rr out/vidN-final.mp4` opens **Reel Review**, a local frame.io ([`editing/review/`](../editing/review)):
  - scrub frame by frame;
  - draw (pin, box, arrow, pen) and comment on a frame, or leave whole-video notes;
  - **Send to editor** writes `vidN-feedback-roundN.md`, with markup frames baked into JPEGs the agent reads.
- Re-rendering stacks **v2** under the same project, so the owner can wipe v1 against v2.
- `./rr share` publishes the same player to a client on a private link: a **Cloudflare Worker + KV** ([`editing/share/`](../editing/share)), with renders stored as private GitHub release assets (no 25 MB limit, zero hosting cost). `./rr pull` brings client notes back.

---

## Hard rules the pipeline enforces

**Platform safe zones** ([`SAFE-ZONES.md`](../editing/SAFE-ZONES.md)):
- The bottom UI band starts around y1600 of 1920.
- The top 150 px, the right rail (x>960, y900–1600) and the left 60 px are no-text zones.
- **Frame 0 is the cover**, so it must be a fully composed frame.

**Design language:**
- Radial-only backgrounds (linear gradients band in H.264).
- Layered hooks: a glitch decode, an eyebrow claim pill, a mascot and a scanline inside about 1.2 s.
- Font pairing: Inter + Instrument Serif italic.

**Honesty:**
- Real footage and real UI over generated stand-ins.
- Never claim "done" without rendering and looking at frames.

## Memory that travels with the repo

Quality lives in written judgement, not just code:
- **`LEARNINGS.md`**: 14,122 lines, chronological per video. An excerpt is in [editing-learnings.md](editing-learnings.md).
- **`brain/`**: 492 memory files with per-client and per-creator rules and the specific ways past renders failed.

`sync-brain.sh export/import` moves the agent's memory store into the repo and back, so a second operator's machine inherits every lesson. When it was a manual step, it drifted to 27% coverage.

## Growth tooling around the edit

- **[`ig-autodm/`](../editing/ig-autodm)**: comment a keyword on a reel and receive a DM automatically, through the Instagram Graph API's private replies (ManyChat's mechanism, run locally with no monthly fee). It respects Meta's rules: one DM per comment, within 7 days.
