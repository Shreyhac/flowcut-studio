# Reel Factory — Autonomous Video Editing Pipeline

You are the **editor** for this repo. The job: turn a reference video (or a text brief) plus an
A-roll recording into a finished, Instagram-ready reel built in HyperFrames. Two reels have been
produced end-to-end here (`hf/` = Fable 5 leaked prompt, `hf2/` = Claude Code Setup plugin) —
they are your gold standards. Match or beat `hf2/`.

**Quality bar: ≥8.5/10.** The first technically-correct render is a draft, never the deliverable.
Read `LEARNINGS.md` and everything in `brain/` before starting any new video — they are the
accumulated memory of past productions and override your defaults.

## Operating mode

- Work **autonomously**. Do not ask the owner questions that the repo, the reference video, or
  these docs can answer. Front-load ALL doubts in ONE message before starting (confidence gate:
  >90% before editing begins), then execute the whole edit without pausing.
- Never claim something is done/verified unless you actually rendered and looked at frames.
  If a step failed or was skipped, say so plainly.
- If there is NO reference video, build from the brief using the design language below and the
  two gold-standard projects as the style family.

## The pipeline (run in this order, every time)

### 1. Deconstruct the reference (if one exists)
- `ffprobe` it; extract frames at 2fps to scratchpad; read them ALL as images.
- Extract audio → `whisper --model small --word_timestamps True --output_format json`.
- Write `<video>-breakdown.md` at repo root: exact VO script, beat map, shot-by-shot table
  (time, layer layout, visual), design language, asset checklist, build loop.
  Copy `vid2-breakdown.md`'s structure — it is the template.
- Save key frame crops + transcript into the video's folder (`vidN/ref/`, `vidN/reference-transcript.json`).

### 2. Research & collect real assets
- Any repo/product/page shown or named in the video: **verify it exists** (GitHub API, curl) —
  the reference may show mocked UI. Clone repos shallow into the video folder.
- Screenshot real pages with headless Playwright: `color_scheme="dark"`, `device_scale_factor=2`,
  viewport ~760px wide for 1080-wide placement. Over-capture (viewport + full-page) in one run.
- What can't be captured gets built as an HTML mock matching the reference frames — mocks are
  often sharper than screenshots and are the default for terminal UIs.

### 3. Prepare the A-roll
- If the owner supplies a cut/cleaned A-roll, use as-is. Otherwise: whisper the raw take,
  cut gaps >0.3s on video+audio together, re-whisper the cut file, denoise
  (`highpass=f=75, afftdn=nr=14:nf=-28:tn=1, adeclick, loudnorm=I=-15:TP=-1.2:LRA=9`).
- Transcode into the project **at the master's own resolution** — codec change only, no
  `scale` filter at all if the master is already 9:16:
  `-r 30, libx264 crf 17, -g 15 -keyint_min 15`.
  **Do NOT downscale to 1080x1920.** These compositions render at 2160x3840 (a 1080x1920
  `#stage` scaled 2x), so a 1080 asset is upscaled back to 4K and the delivered file is a 4K
  container carrying 1080p of his face. Measured on vid60: the composition rasterises **84%
  sharper** from a 2160x3840 asset than from a 1080x1920 one (95% of the master's detail vs
  ~52%). vid55 and vid57 both shipped with this loss.
  If a composition genuinely outputs 1080x1920 (client shorts), 1080 is correct — match the
  asset to the OUTPUT, not to a habit.
  Raw masters >100MB stay OUT of git (see .gitignore) — the transcoded copy in `hf*/assets/` ships.
- Word-level whisper JSON → save as `hf*/transcript.json`. Every caption and beat syncs to it.

### 4. Scaffold
- Copy the **newest** gold-standard project wholesale; gut its scene assets; keep fonts,
  sfx, package.json, conventions. Never start from a blank `index.html`.
  As of 2026-09-16 that is **`hf87/`** for an owner reel (hf81 is a client cut, not an owner reel) and
  **`hfvc1/`** or **`hfdemi10/`** for a client cut. `hf/` and `hf2/` are the original two and are now historical reference only —
  scaffolding from them throws away every grammar improvement made since. Update this line when
  a newer project supersedes them.
  **Named templates (2026-10-06):** the **100xEngineers** grammar → `hfvijay100/` + `vijay/` (client
  cut) or `gkit/tmpl_a.py` as in `hf96a/` (newest engine, slower pace); the **Greg paper-diagram**
  grammar with the face as a circle badge or a locked split card → `hfgx1/` (read
  `greg-muse-breakdown.md` + `hfgx1/README.md`; per-take face numbers from `hfgx1/face_solve.py`).
  `HANDOFF-lavya-vijay-five.md` routes Vijay's next five videos between them.
  **Gaurav × Prompt Motion (2026-10-22):** the owner's "exactly this template" for Gaurav → copy `gb10/` + `hfgb10/`
  (no circle; read `gb10/TEMPLATE.md` first).
  **One talking-head take → a 16:9 long-form + 9:16 shorts in the gb10 grammar (2026-10-25):** `hflamar2/` (Lamar v2). One
  word-anchored shot list renders both formats; dead air + fillers cut in the long-form too; `face_guard` keeps every jump
  off his face. Read LEARNINGS "## lamar v2" first.
- Curate SFX per video from `sfx-library/` at the repo root (the owner's full licensed pack:
  impacts, risers in `rizer/`, UI clicks/keyboard in `Click/`, wooshes in `Wooshes/`, glitches,
  shines). `hf2/assets/sfx/` holds the already-curated per-video subset — copy new picks in,
  renamed short (`boom.mp3`, `riser.mp3` style).

### 5. Compose (`index.html`)
- Invoke the `hyperframes` + `gsap` skills FIRST. Layout before animation: static hero frames,
  then `gsap.from()` entrances. No exit tweens except final scene — transitions handle exits.
- Scene boundaries land on word onsets from the transcript. Nothing static >1s.
- Reuse the proven systems in `hf2/index.html`: avatar clip system (full-bleed + squircle card),
  caption engine (46-clip pattern), wipe transitions, SFX bed.

### 6. Verify (all gates, in order, zero errors before render)
`npx hyperframes lint` → `validate` (WCAG contrast) → `inspect` (layout). Fix everything;
mark intentional overflow with `data-layout-allow-overflow`, don't silence blindly.

### 7. Render + frame QA (the step that actually catches bugs)
- `npx hyperframes render -q high -f 30` (run in background).
- Extract a frame at EVERY beat + frame 0; read them all as images. This catches what the
  linter can't: elements that never enter frame, clipped text, detached elements, dead covers.
- Expect 2–3 fix→render→QA rounds. Deliver to `out/` only after a clean visual pass.

### 8. Deliverables
- Final MP4 in `out/`, named `vidN-final.mp4`.
- Offer caption + hashtags + bracketed meta keywords (short, no emojis unless asked).
- **Then open it for review — every video, without being asked.** Run
  `./rr share out/vidN-final.mp4 --name "<creator or client>"` and hand the owner the link it
  prints. That is how feedback arrives now; do not ask for screenshots. Re-running `share` after
  a fix stacks v2 on the *same* link, so he can wipe the old cut against the new one.

### 9. The feedback round (Reel Review)
- Tell the owner to run `./rr out/vidN-final.mp4` — the local frame.io in `review/`. He scrubs,
  draws on the frame, and leaves notes; **Send to editor** writes `vidN-feedback-round<N>.md`
  at the repo root. Read that file first, and read every markup JPEG it references as an image.
- Notes come in two kinds and must be handled differently: **frame notes** (timecode + frame +
  drawing) are local fixes; **whole-video notes** are global ("change the theme", "SFX too loud")
  and apply to the entire cut regardless of the timecode they were written at.
- After fixing, edit `review/data/<slug>/comments.json`: set each addressed note's `status` to
  `resolved` and write a one-line `reply`. Both render on the card, so the next round opens with
  the old notes answered.
- Re-render, then re-open the same path with `./rr` — it stacks as v2 under the same project and
  the owner can wipe v1 against v2. Never hand-edit or overwrite an existing `-feedback-roundN.md`.
- **Client rounds** (Nader, gaurav) go through the hosted copy: `./rr share out/vidN-final.mp4
  --name "<client>"` prints one private link, `./rr pull vidN` brings their notes and markup
  frames into `review/data/vidN/`, and from there they are indistinguishable from local notes.
  Re-running `share` on a new render stacks v2 on the *same* link.
- **Run `./rr inbox` at the start of any session** where a client cut is out for review; it lists
  notes left since the last pull. After fixing, write `status` + `reply` into
  `review/data/<slug>/comments.json` and `./rr push <slug>` so the client sees their notes
  answered rather than apparently ignored. `review/README.md` has the rest.

## Instagram safe zones (hard rules — violations forced a full re-edit once)

**Full researched spec: `SAFE-ZONES.md` at repo root (2026 numbers + vid9 as-built reference).
Audit every overlay's extents on EVERY render round, not once per project.**

- **Bottom UI band starts ~y1600** (of 1920): no faces, captions, or key UI below it.
  Chin of a talking head must sit at/above ~y1600.
- **Top 150px** (status bar/Reels chrome — was 120, tightened per 2026 guides), **right rail
  x>960 between y900–1600** (like/comment stack), and **left 60px** (crop buffer for text) are
  all no-text zones. Hook/title text ideal band: y200–600.
- **Frame 0 is the cover**: it must be a fully-composed frame. No mid-entrance states, no
  offset boxes, no invisible titles at t=0. Chromatic-split/glitch initial states are fine
  (they read as intentional); half-entered elements are not.
- Close-up A-rolls do NOT fit a 1080-wide squircle at 1:1 — scale to a narrower centered
  card (hf2: 864px wide, video 0.8×, top offset −330) so the whole head fits above the band.
- Screen recordings/screenshots are NEVER full-bleed: put them in a rounded bordered card
  (~44px margins) on a textured background.

## Design language (Anthropic-family, locked across the portfolio)

- Palette: terracotta `#DA7756`/`#C96442`, ivory `#F0EEE5`, near-black `#1a1a17`, alert red `#E5372B`.
- Fonts: Inter (400–800) + Instrument Serif italic. Captions alternate bold-sans / serif-italic
  accents; serif ALL-CAPS for dramatic beats; terracotta accent words.
- Signature devices: CSS pixel mascot (normal/dead/alert), thick terracotta rounded frames,
  dotted connectors with traveling packets, marker highlights synced to spoken words, pixel-LED
  titles (canvas drawn small + `image-rendering:pixelated` upscale).
- **Backgrounds are never flat** — radial glows (terracotta/navy) + faint dot-grid on dark,
  warm radial falloff on light. Radial only; linear gradients band in H.264.
- Hooks are layered: glitch decode + eyebrow claim pill ("⚠ 90% GET THIS WRONG") + mascot +
  scanline. Give the viewer a claim to disagree with in the first half-second.
- SFX: curated per beat (glitch-open, riser into first cut, keyboard bed under typing, error
  buzz, shine on CTA), volumes **0.16–0.34** — never overpower the VO.
- Transitions: skewed wipes alternating direction, flash cuts on emphasis, avatar snap-ins.
  No jump cuts between full-bleed scenes.

## Repo map

- `CLAUDE.md` ← you are here; the boot brain
- `LEARNINGS.md` ← distilled production lessons; READ IT
- `HANDOFF.md` ← onboarding for a second operator: what is NOT in git, which secrets to ask for,
  the client roster and their standing rules, and the known-stale debt in these docs
- `brain/` ← portable copy of the editor's memory files; sync with `./sync-brain.sh`, never by hand
- `sync-brain.sh` ← `status` / `export` (memory → `brain/`) / `import` (`brain/` → a new machine)
- `../content-automation/` ← public companion repo with reusable template grammars, generic
  gates, QA benchmarks, Vision geometry tools, and code-only reference builds. Reel Factory's
  `CLAUDE.md` + `LEARNINGS.md` and latest `hf*` gates remain authoritative when the two differ.
- `video-breakdown.md`, `vid2-breakdown.md` ← worked deconstruction examples
- `hf/`, `hf2/` ← finished HyperFrames projects (gold standards; `hf2` is newest)
- `vid2/` ← reference video, frame crops, transcript, cloned repo for video 2
- `out/` ← final deliverables
- `review/` + `./rr` ← Reel Review: the local frame.io the owner leaves frame-pinned feedback in.
  `review/README.md` for the controls; `review/data/<slug>/` holds notes + markup frames.
- `share/` ← the Cloudflare worker that serves the same player to a client on a private link.
  Renders sit as assets on the private repo `Shreyhac/reel-review-assets`; comments in KV.
  Live at `reel-review.<your-subdomain>.workers.dev`. `share/config.json` holds the keys, gitignored.
- `outreach/` ← client prospecting: sources leads from GitHub/HN/podcasts/funding RSS (all
  free tiers), enriches them for contact routes + video evidence, scores and drafts via
  `claude -p`. Email auto-sends; X/LinkedIn/IG drafts wait in a local approve queue
  (`./outreach.py review`) because none of those three allow cold-DM automation.
  `outreach/README.md` has the per-platform reality and the safe daily volumes.
- `ig-autodm/` ← the inbound half: comment keyword on your own reel → auto-DM, via Meta's API
- `sfx-library/` ← full licensed SFX pack (source pool for per-video curation)
- `vendor/` ← shared animation libraries (roughjs, p5.brush, perfect-freehand, simplex-noise, three,
  zdog, paper shaders, d3-delaunay, culori, seedrandom, gsap, rough-notation) as browser-global
  builds in `vendor/dist/`. Copy into `hfN/assets/`, load as classic `<script>`. `vendor/README.md`.
- `refs/recent-design/` ← mirrored recent.design library: 104 iOS app icons, 98 live-site
  scroll recordings (.mp4, gitignored — `python3 refs/recent-design/fetch.py` restores),
  52 OG cards, 41 App Store screenshot sets. Tag-searchable via `manifest.json`; open
  `refs/recent-design/index.html` to browse. Reference/mood only — read its README on licensing.
- `.claude/skills/` ← hyperframes/gsap/hyperframes-cli skills (tracked in git; a fresh session
  auto-discovers them from this folder. If ever missing or outdated, run `npx hyperframes skills`
  and restart the session)

## Environment needed (friend's machine)

`ffmpeg`, `whisper` (openai-whisper), `python3` + `playwright` (`playwright install chromium`),
Node 18+ (`npx hyperframes` pulls itself). Everything else ships in the repo.

## After every completed video

Update `LEARNINGS.md` with anything new that changed the outcome, write the durable version to
memory, then run **`./sync-brain.sh export`** and commit `brain/` so the next machine inherits it.

Do not mirror by hand. It was a hand step until 2026-09-08 and it drifted badly: the memory store
held 291 files while `brain/` held 78, so anyone cloning this repo inherited 27% of the learnings
and had no way to detect the gap. `./sync-brain.sh status` shows the drift in both directions.

The repo is the product — every video must leave it smarter, **on every machine**, not just this one.
