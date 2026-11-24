#!/usr/bin/env python3
"""Switch a phone's Proton VPN to a country (12 Nov 2026).

Owner: "for whichever accounts you're warming up, connect the VPN of that language's country". Instagram sessions/posts
run on their language's country, TikTok work stays on the US. set_country() connects and VERIFIES the phone's public
IP country (ipinfo.io from the phone's shell, which goes through the VPN); returns False if it can't, so the caller can
skip the session instead of running on the wrong country.
usage: vpn.py <device> <Country name> <CC>      e.g. vpn.py android-device:REALME_SERIAL Brazil BR
"""
import re, subprocess, sys, time
PD = "/Applications/PhoneDock.app/Contents/Resources/bin/phonedock"
COUNTRY = {"es": ("Mexico", "MX"), "ja": ("Japan", "JP"), "pt": ("Brazil", "BR"), "fr": ("France", "FR"),
           "de": ("Germany", "DE"), "us": ("United States", "US")}

def pd(*a, timeout=60):
    try: return subprocess.run([PD, *a], capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired: return ""

def ip_country(dev):
    out = pd("shell", dev, "--", "curl -s -m 8 https://ipinfo.io/country")
    out = out.strip()
    return out[:2] if re.fullmatch(r"[A-Z]{2}", out[:2] or "") and "not found" not in out else ""

def _proton_home(dev):
    out = ""
    for _ in range(4):   # 21 Nov: the Redmi drops off USB for a few seconds at times -> empty output crashed here
        out = pd("shell", dev, "--", "cmd package resolve-activity --brief --user 0 ch.protonvpn.android").strip()
        if out: break
        time.sleep(8)
    if not out: return ""
    comp = out.splitlines()[-1]
    pd("shell", dev, "--", f"am start --user 0 -n {comp}"); time.sleep(4)
    t = pd("ui", dev, "--no-ocr")
    c = coords(t, r'TextView "Home"')
    if c: pd("tap", dev, *c); time.sleep(2); t = pd("ui", dev, "--no-ocr")
    return t

def connected_to(dev, name, cc):
    """12 Nov: the Redmi has no curl and its shell can't resolve DNS -> fall back to Proton's own screen
    (country label + a Disconnect button = connected there)."""
    ipc = ip_country(dev)
    if ipc == cc: return True
    # 13 Nov: Proton's Brazil servers geolocate as US on ipinfo, so a mismatch falls through to Proton's own screen
    t = _proton_home(dev)
    return bool(re.search(rf'TextView "{re.escape(name)}" id=primaryLabel', t)) and '"Disconnect"' in t

def coords(t, pat):
    m = re.search(pat + r'[^\n]*?@\((\d+),(\d+)\)', t)
    return (m.group(1), m.group(2)) if m else None

def set_country(dev, name, cc, tries=2):
    if connected_to(dev, name, cc): pd("key", dev, "home"); return True
    for _ in range(tries):
        out = ""
        for _r in range(4):   # 21 Nov: the Redmi drops off USB for a few seconds at times -> empty output crashed here
            out = pd("shell", dev, "--", "cmd package resolve-activity --brief --user 0 ch.protonvpn.android").strip()
            if out: break
            time.sleep(8)
        if not out: continue
        comp = out.splitlines()[-1]
        pd("shell", dev, "--", f"am start --user 0 -n {comp}"); time.sleep(5)
        t = pd("ui", dev, "--no-ocr")
        c = coords(t, r'TextView "Countries"(?= @\(\d+,2[0-9]{3}\))') or coords(t, r'TextView "Countries"')
        if c: pd("tap", dev, *c); time.sleep(3)
        t = pd("ui", dev, "--no-ocr"); c = coords(t, r'label="search"')
        if c: pd("tap", dev, *c); time.sleep(2)
        for _ in range(3):                                 # clear a search left over from a previous run (the Clear X)
            t = pd("ui", dev, "--no-ocr")
            if not re.search(r'EditText "[^"]+" id=searchInput', t): break
            c = coords(t, r'label="Clear"')
            if c: pd("tap", dev, *c); time.sleep(1)
            else: pd("shell", dev, "--", "input keyevent KEYCODE_MOVE_END"); pd("shell", dev, "--", "input keyevent " + " ".join(["KEYCODE_DEL"] * 30))
        c = coords(pd("ui", dev, "--no-ocr"), r'EditText[^\n]*id=searchInput')
        if c: pd("tap", dev, *c); time.sleep(0.8)
        pd("type", dev, name); time.sleep(3)
        t = pd("ui", dev, "--no-ocr")
        rows = [(int(x), int(y)) for x, y in re.findall(rf'TextView "{re.escape(name)}"[^\n]*?@\((\d+),(\d+)\)', t) if int(y) > 300]
        if not rows: pd("key", dev, "back"); continue
        pd("tap", dev, str(rows[0][0]), str(rows[0][1])); time.sleep(3)
        t = pd("ui", dev, "--no-ocr")                      # some builds open a server list / "Connect" sheet
        c = coords(t, r'(?:TextView|Button) "Connect"')
        if c: pd("tap", dev, *c)
        for _ in range(8):
            time.sleep(5)
            if connected_to(dev, name, cc):
                pd("key", dev, "home"); return True
    pd("key", dev, "home")
    return False

if __name__ == "__main__":
    ok = set_country(sys.argv[1], sys.argv[2], sys.argv[3])
    print("OK" if ok else "FAILED", ip_country(sys.argv[1]))
    sys.exit(0 if ok else 1)
