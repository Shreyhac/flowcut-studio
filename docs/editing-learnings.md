# How to Edit a Perfect Reel — Learnings from the Fable 5 Production

Distilled from building this project end-to-end: deconstructing a reference video, cutting a fresh A-roll, building the HyperFrames composition, and reworking it through two "editor's pass" rounds. Read this before starting the next one.

## 1. Deconstruct the reference before touching anything

- Extract frames at ~2fps and whisper the audio for a timestamped transcript **before** writing a single line of composition code. Guessing the shot list from memory produces a worse video than actually looking.
- Identify the recurring **layout patterns** (full-screen A-roll vs. squircle-bottom split vs. full-bleed B-roll), the **caption style** (font pairing, pill vs. no pill, word grouping), and the **signature devices** (marker scribbles, colored frames, dotted diagrams) — these are what make a recreation read as "the same style," not just "a similar video."
- Write the shot-by-shot breakdown to a file (`video-breakdown.md` here) before building. It becomes the spec you build against and the thing you diff your output against later.

## 2. Cutting the A-roll: precision over eyeballing

- Whisper the raw take with `--word_timestamps True`. Compute gaps between consecutive words; anything over ~0.3s is a candidate cut (breath pause, hesitation, dead air).
- Cut with `ffmpeg` trim+concat on **both** the video and audio streams using the *same* in/out timestamps — never cut audio and video separately, or lip-sync drifts.
- **Re-whisper the cut file.** Never reuse pre-cut word timestamps after trimming — every timestamp after the first cut is wrong.
- Dense keyframes on the trimmed export (`-g 15 -keyint_min 15`) so the render engine can seek/scrub cleanly frame-by-frame later.

## 3. Audio cleanup that doesn't sound processed

- Denoise chain that worked without making the voice sound robotic: `highpass=f=75` (rumble) → `afftdn=nr=14:nf=-28:tn=1` (FFT noise reduction, moderate strength) → `adeclick` → `loudnorm=I=-15:TP=-1.2:LRA=9` (reel-appropriate loudness).
- Remux with `-c:v copy -c:a copy` back into the original container so video is byte-identical and only audio changes — zero risk of re-encoding drift or lip-sync shift.
- Avoid aggressive noise reduction (`nr` much above ~15) — it starts eating consonants and sounds worse than the noise it removed.

## 4. Source real assets — don't fabricate UI

- For any on-screen software/website footage (GitHub, an app, a dashboard), **screenshot the real thing** with a headless browser rather than mocking it in CSS. Playwright with `color_scheme:"dark"`, `device_scale_factor:2`, and a realistic viewport produces retina-quality captures that hold up to zooming/panning in the composition — far more convincing than a hand-drawn approximation, and it's not slower.
- Capture a few variants (different scroll positions, a full-page tall screenshot for panning) in one script run rather than one-at-a-time — cheap to over-capture, expensive to go back for a missed shot.
- When a UI element resists a simple CSS selector (e.g., an icon-only button with no visible label), inspect by SVG icon class name (`octicon-list-unordered` etc.) rather than giving up on clicking it.

## 5. Scaffold from a gold-standard project, don't start blank

- If a prior "best" composition exists in the same style family, copy its `hf/` folder wholesale (fonts, SFX, timeline conventions) and gut the assets, rather than re-deriving font stacks and CSS variables from scratch. Consistency across a portfolio of reels matters more than any single file being "clean."

## 6. The HyperFrames build loop, in order

1. **Layout before animation.** Write the static end-state HTML/CSS for each scene's "hero frame" first — the moment fully entered, not yet exiting. Add `gsap.from()` entrances after the layout is confirmed correct, never before.
2. **Lint → validate → inspect → render**, always in that order, never skip a step to save time. `inspect` catches real bugs `lint` can't see: text overflowing a container, an element parked off-canvas, two elements colliding at a specific timestamp.
3. Mark **intentional** overflow (a panned image inside a clipping frame, an oversized video inside a rounded mask) with `data-layout-allow-overflow` instead of fighting the inspector into silence.
4. Give every timed element a stable `id` — the linter needs it, and so do you when re-reading the timeline six edits later.

## 7. QA by actually looking at frames, not just watching it play

- Extract a frame at every beat (`ffmpeg -ss T -frames:v 1`) and read them back one by one. This is how real bugs got caught in this project:
  - Captions sitting low enough to collide with the subject's chin.
  - Two word-pop pills touching/overlapping because they were positioned with the same absolute offset.
  - A brand logo (white fill, transparent background) turning invisible on a white card — only visible once actually rendered, not from reading the SVG source.
  - A "marker scribble" animation drawn over blank space instead of the filename it was supposed to circle, because the panned image had scrolled since the scribble's coordinates were set.
- Watching the exported video top-to-bottom misses these; freeze-framing the exact beat timestamps does not.

## 8. A technically-correct first render is a draft, not the deliverable

- The first pass should nail structure, timing, and beat-matching — that's necessary but not sufficient.
- A genuine second "editor's pass" means:
  - **Transitions between every scene** — skewed wipes, flash cuts, direction alternated for rhythm. No jump cuts between full-bleed scenes.
  - **Nothing static for more than ~1 second** — marquees breathe, numbers slam with a screen-shake, dotted connector lines march, spinners actually spin, cards get subtle parallax.
  - **Curated SFX over generic/reused ones** — check the user's own SFX libraries (organized folders of licensed packs) before defaulting to whatever's already sitting in a shared assets folder. A woosh, an impact, and a shutter click are not a sound design — a glitch-open, a riser building into the first cut, a keyboard-ASMR bed under a typing terminal, and a shine-sweep on the CTA pill are.
- Expect this to take 2-3 rounds. Don't treat "editor's pass" requests as scope creep — they're the actual job.

## 9. Confidence-gated execution

- When asked to hit a confidence bar before starting an edit (e.g., "make sure you're >90% confident, then start"): front-load every doubt, ambiguity, and clarifying question *before* the edit begins, get them all answered in one pass, then execute the entire edit autonomously without pausing mid-task to re-ask something that could have been asked upfront.

## 10. Third-party/copyrighted assets need a deliberate decision, not a default

- A production folder like this accumulates: the original reference video (someone else's posted content), officially-sourced brand art/logos, "leaked" text pulled from a public repo, and licensed stock SFX. None of these are the editor's own IP.
- Before bundling a project like this to share with someone else — even privately — flag exactly which files fall into that category and let the human make an explicit, informed call on whether to include, exclude, or replace them with a "how to re-fetch this yourself" note. Don't silently include them, and don't silently strip them either.

## 11. Instagram safe zones are a hard gate, not a style choice (from vid2)

- Bottom UI band starts ~y1600/1920; top ~120px and the right rail (x>960, y900–1600) are IG chrome.
  A talking-head chin below ~1600 or a full-bleed screenshot = guaranteed re-edit request.
- **Frame 0 is the cover frame.** Compose it fully: no mid-entrance offsets, no invisible titles.
  Check it explicitly in QA (`ffmpeg -ss 0`).
- A close-up A-roll cannot sit 1:1 in a full-width squircle — scale it into a narrower centered
  card (0.8×, 864px wide in hf2) so the whole head fits above the band.
- Screenshots/screen-recs go in rounded bordered cards on textured backgrounds, never full-bleed.

## 12. Flat backgrounds read as boring; fix with radial-only depth (from vid2)

- Every dark scene: 1–2 radial glows (brand terracotta + a cool counter-color) + faint dot-grid.
- Every light scene: warm radial falloff (bright center-top → parchment edges).
- Radial only — full-screen linear gradients band visibly in H.264 dark scenes.

## 13. Hooks are layered claims, not titles (from vid2)

- A title alone doesn't stop a scroll. Stack: glitch/chromatic decode + an eyebrow pill making a
  falsifiable claim ("⚠ 90% GET THIS WRONG") + mascot motion + a scanline sweep, all inside ~1.2s.
- Chromatic-split initial state doubles as a strong cover frame; half-entered elements do not.

## 14. The repo is the transferable brain

- Local Claude memory does not travel between machines. Everything that must persist goes in
  root `CLAUDE.md` (auto-loaded), `LEARNINGS.md`, and `brain/` (mirrored memory files).
- Watch .gitignore: bare package names (`hyperframes`, `gsap`) silently ignored the skills dir;
  raw A-roll masters >100MB break GitHub pushes — ship the transcoded copy instead.
