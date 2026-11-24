# Engine 3b: Publishing from Android emulators

Physical phones limit how many markets you can run. Flowcut adds **Android Emulator (AVD)** devices that use the same posting and warm-up code as the phones. Each emulator is one persona in one country, with its own residential exit IP.

```mermaid
flowchart LR
  subgraph Mac
    FWD[forwarding proxy<br/>127.0.0.1:8898<br/>adds upstream auth,<br/>sticky JP session]
    UP[(residential proxy<br/>country = JP)]
  end
  subgraph AVD vw_ig_02 · Tokyo TZ
    APP[Instagram + Edits]
    V2[v2rayNG<br/>always-on VPN + lockdown<br/>HTTP → 127.0.0.1:8898]
  end
  APP --> V2 -- adb reverse tcp:8898 --> FWD --> UP --> IG[(Instagram)]
```

## Launch ([`posting/emulator/start_emulator*.sh`](../posting/emulator))
- `-no-snapshot-save` gives a clean boot every time, with no stale state baked into a snapshot.
- `-timezone Asia/Tokyo`: otherwise the emulator copies the host's time zone, and a "Japanese" phone would run on the host's clock.
- **Clipboard sharing off** (`defaults write com.android.Emulator set.clipboardSharing -int 0`), so the host clipboard never leaks into the device. The crash-report dialog is also off.
- A fixed console port per emulator (`-port 5558`), so serials stay stable (`emulator-5554`, `-5556`, `-5558`).
- Stale `*.lock` files are cleared before launch, and the script waits for `sys.boot_completed` before anything touches the device.

## Network: why `adb reverse` plus a forwarding proxy
- An emulator's network only lets ports 80/443 out reliably, and an authenticated upstream proxy can't be configured cleanly inside Android.
- So the device runs **v2rayNG as an always-on VPN with lockdown**. All its traffic goes to an HTTP proxy at `127.0.0.1:8898` *on the device*.
- **`adb reverse tcp:8898 tcp:8898`** maps that device port to the Mac. There, [`dora_fwd_proxy.py`](../posting/emulator/dora_fwd_proxy.py), a small asyncio no-auth proxy, adds the `Proxy-Authorization` header and forwards to a **residential proxy with a sticky session in the target country**. Credentials are read from `~/.flowcut/proxies` and never printed or logged.
- UDP can't traverse this path, so there are **no WebRTC/QUIC IP leaks**. Lockdown means nothing leaves if the tunnel is down.
- Each emulator has its own sticky session, so two personas never share an exit IP.
- Verification: the pre-flight runs `printf 'GET /json …' | toybox timeout 25 nc ipinfo.io 80` **inside the emulator** and requires `"country": "JP"`.

## Lessons that are now encoded
| Problem seen | Fix in code |
|---|---|
| 3 emulators at once → the emulator network daemon (`netsimd`) segfaulted and **all 3 died mid-session** | Pre-flight caps concurrent emulators at 2; `--fix` stops the scout emulator when it isn't mid-run |
| A crashed session reported "finished" with 0 reels and unlocked a post | Fewer than 5 reels → `EMPTY session`, exit 4; the readiness gate ignores it |
| Edits app missing on a fresh AVD | Installed from a local APK store; posting checks both apps are enabled per user |
| The Edits app on the emulator renders **black cover frames** (the video itself is fine) | Known GPU limitation: launch with a host GPU mode, or set a camera-roll cover for emulator posts |
| The app's language pack failed to download through a slow proxy | Switched to a faster sticky session; UI matchers accept both English and Japanese labels |

## Using the emulators with the rest of Flowcut
- They are just ADB serials: the warm-up (`jp_warm.py`), posting (`jp_post_edits.py`), readiness (`jp_ready.py`) and pre-flight (`jp_preflight.py`) code doesn't change.
- `jp_days.py` **starts the emulator 30 minutes before its slot** and lets it boot, warm up and post.
- PhoneDock can also drive the same AVDs for interactive debugging (screenshots, UI tree, taps).
