#!/usr/bin/env python3
"""24 Nov 2026 owner: JP account names + bios about MAKING MONEY WITH AI (keywords > hashtags; name + bio are searchable).
usage: jp_profile.py <key> [--dry]   (key from jp_accounts.json). Instagram allows 2 name changes per 14 days.
Typing: Lava/emulator = PhoneDock clipboard + PASTE key; Realme user 10 = Chrome copy (the Mac clipboard can't reach it)."""
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = sys.argv[1]; DRY = "--dry" in sys.argv
A = json.load(open(f"{HERE}/jp_accounts.json"))[KEY]
os.environ["IG_PHONE"] = A["phone"]
sys.path.insert(0, HERE); import ig_warm as g
w, DEV = g.w, g.DEV; USER = int(A.get("user", 0))
SERIAL = "emulator-5554" if A["phone"] == "emulator" else DEV.split(":")[-1]

PROFILE = {
    "misaki": ("佐藤 美咲｜AIで稼ぐ", "AIで副業、ゼロから月5万円を目指す記録💰\nAI動画・アニメ動画の作り方を毎日シェア\nコメントで「STORY」→やり方をDMします"),
    "ayaka": ("鈴木 彩花｜AI副業", "AIだけで動画を作ってお金を稼ぐ方法💸\n顔出しなし・スマホだけでOK\n収益化のコツを毎日ショート動画で発信"),
    "aoi": ("高橋 あおい｜AIでお金を稼ぐ", "会社員の副業はAIにおまかせ🤖💰\nAIアニメ動画・ショート動画で収益化\n始め方はDMで聞いてね"),
    "miyu": ("伊藤 みゆ｜AI収益化", "AIで作った動画で副収入を作る方法🎬💴\n初心者でもできるAI活用術を毎日投稿\n気になる人は「STORY」とコメントしてね"),
    "sakura": ("山本 さくら｜AI副業", "スキマ時間×AIで稼ぐ副業ノート📒✨\nAI動画づくりで月収アップを目指す\nやり方はDMでシェアします"),
}


def log(m): print(time.strftime("%H:%M:%S"), f"[{KEY}]", m, flush=True)
def adbsh(cmd): return subprocess.run(["adb", "-s", SERIAL, "shell", cmd], capture_output=True, text=True, timeout=60).stdout


def put_clip(text):
    if USER == 0:
        subprocess.run([w.PD, "clipboard", DEV, "--set", text], capture_output=True); time.sleep(0.8); return
    # Realme user 10: share to Chrome (Google search box), select + copy with real keys
    adbsh(f"am start --user {USER} -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT '{text}' com.android.chrome")
    time.sleep(6)
    for _ in range(4):
        adbsh("input tap 534 541"); time.sleep(1.8)
        if "mInputShown=true" in adbsh("dumpsys input_method | grep -m1 mInputShown"):
            adbsh("input keycombination 113 29"); time.sleep(0.5); adbsh("input keycombination 113 31"); time.sleep(1); break
        adbsh("input keyevent 4"); time.sleep(1)
    adbsh("am force-stop com.android.chrome"); time.sleep(2)


def fill_focused(text):
    """Replace the focused field's text, line by line (newline = ENTER)."""
    adbsh("input keycombination 113 29"); time.sleep(0.4); adbsh("input keyevent 67"); time.sleep(0.5)
    for i, line in enumerate(text.split("\n")):
        if i: adbsh("input keyevent 66"); time.sleep(0.5)
        put_clip(line)
        if USER != 0:          # back in Instagram after Chrome: refocus the field at its end
            c = w.coords(g.ui(), r"EditText[^\n]*\[clickable,focused")
            if c: g.tapd(*c); time.sleep(1)
            adbsh("input keycombination 113 123"); time.sleep(0.3)
        adbsh("input keyevent 279"); time.sleep(1.5)


def edit_field(label_rx, text):
    t = g.ui(); m = re.search(label_rx + r"[^\n]*\n[^\n]*EditText[^\n]*@\((\d+),(\d+)\)", t)
    if not m: log(f"field not found: {label_rx}"); return False
    g.tapd(int(m.group(1)), int(m.group(2))); time.sleep(4.5)
    t = g.ui()
    # the focused text field of the editor page (the line ends with [clickable,focused...]; coords sit before that)
    m2 = [x for x in re.finditer(r'EditText "[^"]*"[^\n]*@\((\d+),(\d+)\)[^\n]*focused', t)] or \
         [x for x in re.finditer(r'EditText[^\n]*@\((\d+),(\d+)\)[^\n]*focused', t)]
    c = (int(m2[0].group(1)), int(m2[0].group(2))) if m2 else None
    if not c: log("editor field missing"); return False
    g.tapd(*c); time.sleep(1); fill_focused(text)
    t = g.ui(); got = re.search(r'EditText "(.*?)"[^\n]*focused', t, re.S)
    got = (got.group(1) if got else "").replace("\\n", "\n")
    ok = text.split("\n")[0][:6] in got
    log(f"{'OK' if ok else 'MISMATCH'}: {got[:60]!r}")
    if ok and not DRY:
        b = w.coords(t, r'Button label="完了"') or w.coords(t, r'id=action_bar_button_action')
        if b: g.tapd(*b); time.sleep(3)
        t2 = g.ui()   # 24 Nov: a name change asks "名前を変更しますか？" (2 changes per 14 days) -> confirm
        d = w.coords(t2, r'Button "名前を変更" id=igds_alert_dialog_primary_button')
        if d: g.tapd(*d); time.sleep(4); log("name change confirmed")
    else:
        b = w.coords(t, r'Button label="キャンセル"')
        if b: g.tapd(*b); time.sleep(2)
    return ok


def main():
    name, bio = PROFILE[KEY]
    g.open_app(); time.sleep(3)
    if g.current() != A["handle"] and not g.switch_to(A["handle"]): sys.exit("could not switch")
    t = g.ui(); c = w.coords(t, r'(?:Button|TextView)[^\n]*"プロフィールを編集"')
    if not c: sys.exit("no edit-profile button")
    g.tapd(*c); time.sleep(6)
    r1 = True if '--skip-name' in sys.argv else edit_field(r'TextView "名前" id=form_field_label_top', name)
    r2 = edit_field(r'TextView "自己紹介" id=form_field_label_inline', bio)
    log(f"name {'set' if r1 else 'FAILED'}, bio {'set' if r2 else 'FAILED'}{' (dry)' if DRY else ''}")
    w.pd("key", DEV, "back"); time.sleep(1.5); w.pd("key", DEV, "home")


if __name__ == "__main__":
    main()
