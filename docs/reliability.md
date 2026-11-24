# Reliability engineering

Unattended posting across many devices fails in boring ways: a cable, a VPN, a new popup, a renamed button. Flowcut's rule is to **catch it before the posting window, not during it**, and to turn every failure into a test.

## Pre-flight ([`posting/instagram/jp_preflight.py`](../posting/instagram/jp_preflight.py))
A macOS **LaunchAgent** runs it twice before each market's window (e.g. T-45 and T-15 min) with `--fix --quiet`. You can also run it by hand.

| Check | How |
|---|---|
| Device connected and booted | `adb get-state`, `getprop sys.boot_completed` |
| Right Android user | `am get-current-user` must equal the account's user (e.g. 10) |
| Apps present **and enabled** in that user | `pm list packages --user N -e` for Instagram + Edits |
| Country lock on the phone | `always_on_vpn_app` + `always_on_vpn_lockdown`, and the VPN process running *in that user* |
| **Real egress country** (emulators, isolated phone) | `nc ipinfo.io 80` from the device shell → `"country"` must match |
| Today's video + caption ready | the file exists and is > 1 MB, the caption is non-empty |
| No forgotten kill switch | `STOP_*` files reported (an approval hold is shown as expected) |
| Host health | at most 2 emulators (auto-fix), memory free > 20%, schedulers running (auto-start) |
| **Stop-rule self-test** | see below |

Any failure triggers an `@owner` alert in Slack with one line per problem. All OK → silent (or one green line when run by hand).

## Challenge detection that doesn't cry wolf
Warm-ups must stop instantly on a real security challenge and must not stop on harmless screens. Three real false stops shaped the rule:
1. 「フォローする前にこのアカウントを確認」 ("check this account before following") is about the *other* account, not a challenge. It's now filtered out of the tree before matching.
2. A reel caption containing 「無制限」 ("unlimited") matched 「制限」 ("restricted"). The rule now uses a **negative lookbehind**: `(?<!無)制限`.
3. A `bottom_sheet_camera_container` node is always present on the Reels page, and it was mistaken for a sheet. The check is now `bottom_sheet(?!_camera_container)`.

## Failures become fixtures
- Every stopped session saves its full screen dump to `out/jp_stops/<account>_<time>.txt`.
- The pre-flight pulls the live `STOP` regex and filter **out of `jp_warm.py` itself** and runs them against a fixture list of real screens: harmless ones must not stop, real challenges must. Today: 8/8.
- A new false stop becomes a new fixture, so the same class of bug can't come back silently.

## The readiness gate ([`jp_ready.py`](../posting/instagram/jp_ready.py))
An account may post only when **all** of these are true:
- it is at least 84 h old;
- at least 60% of its recent feed is on-niche (from the per-reel log);
- no real challenge or stop in the last 72 h (known false stops are whitelisted by timestamp);
- it finished a warm-up of at least 5 reels within the last 2 h.

## Human approval gate
- The scheduler's `next_item()` skips any queue item that isn't in **`APPROVED.txt`**.
- Videos go to the approver only after the automated QA in [ugc-automation.md](ugc-automation.md#qa-before-anything-posts), so the human reviews a candidate that already passed every machine check.

## Operational hygiene
- Single-instance locks (`fcntl.flock`) on every long-running loop, plus a watchdog that restarts dead loops.
- Append-only JSONL for posts, sessions, seen reels and view readings, so any day can be reconstructed.
- File-based kill switches (`STOP`, `PAUSE`, `HOLD`) checked at every step, not just at start.
- Backups of a script are taken before every behaviour change (`*.bak_<date>.py` in the working tree, not shipped here).
