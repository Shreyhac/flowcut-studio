# posting/: automated publishing

Warm-up and posting to Instagram and TikTok from real Android phones and Android emulators, driven over ADB. Each account is locked to its own country.

| Path | What |
|---|---|
| `instagram/` | Warm-ups (`ig_warm.py`, `jp_warm.py`), posting through the Edits app (`ig_post_edits.py`, `jp_post_edits.py`), scheduler (`ig_sched.py`), daily cycle (`jp_days.py`), readiness gate (`jp_ready.py`), pre-flight (`jp_preflight.py`), fast engagement, views reader, VPN switch |
| `tiktok/` | Single controller loop (`run_forever.py`), warm-up engine (`warmup.py`), poster, prime-time plan |
| `lava/` | A second phone's isolated posting stack with its own VPN per account |
| `emulator/` | AVD launchers + the local forwarding proxy for per-emulator country exit |
| `phone_feed.py` | Every post, warm-up and failure → Slack, plus a daily summary |

Docs: [phone publishing](../docs/phone-publishing.md) · [emulator publishing](../docs/emulator-publishing.md) · [reliability](../docs/reliability.md)
