#!/bin/bash
# Scout emulator (22 Nov 2026): spare IG acct_151 (DE; camila could not get its email code) reads following lists for the IG scan pool. residential proxy DE sticky session.
pgrep -f "fwd_proxy.py" >/dev/null || (cd ~/masonry-tools/scout && nohup python3 fwd_proxy.py > fwd_proxy.log 2>&1 &)
export ADB_MDNS=0

rm -f ~/.android/avd/vw_scout_01.avd/*.lock
nohup ~/Library/Android/sdk/emulator/emulator -avd vw_scout_01 -no-boot-anim -no-snapshot-save -port 5556 -timezone Europe/Berlin -http-proxy http://127.0.0.1:8899 > ~/masonry-tools/vw_scout_01.log 2>&1 &
