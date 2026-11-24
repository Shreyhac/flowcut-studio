# ugc/: AI-presenter video automation

Re-makes one approved master video per persona: her own face, voice, room and first line, with the same hook, screen recordings, cuts and call to action.

| Path | What |
|---|---|
| `pipeline/gen.sh <key> frame\|faces\|react1\|chain` | Paid generation steps; stops on the first failed submit, never tops up |
| `pipeline/make.py <key> vo\|slices\|pip\|build\|render\|final` | Free local stages: best-of-3 TTS with a Whisper check, onset-snapped cuts, PiP, FFmpeg composite |
| `pipeline/alphafix.py` | Repairs holes in the reaction cut-out and fails the build if any frame is still broken |
| `fleet/` | Shared helpers: TTS, Whisper alignment, captions, per-account renders, QA |
| `qa/review_hwy.sh <video> <outdir>` | Side-by-side review against the approved master, reaction crops, loudness, transcript |

Full write-up: [docs/ugc-automation.md](../docs/ugc-automation.md)
