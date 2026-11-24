#!/usr/bin/env python3
"""Engagement on a fresh Instagram post from our OTHER Redmi IG accounts (12 Nov 2026).

Owner: "as soon as you make a video live on insta, like it, repost it, comment something from our other accs, save also -
a sudden engagement". Kept natural: 2-3 engagers per post, each on its own language's VPN country, minutes apart, a
different native-language comment every time (never the post's CTA keyword, never the same text twice).
usage: ig_engage.py <post name from ig_posts.jsonl> [n_engagers]
"""
import datetime, json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ig_warm as g, vpn
w, DEV = g.w, g.DEV
ACCTS = g.ACCTS
LOG_F = f"{HERE}/ig_engage.log"
COMMENTS = {
    "es": ["Esto me sirve muchísimo 🙌", "Justo lo que estaba buscando", "Lo voy a probar hoy mismo 🔥", "Qué buena idea, gracias por compartir",
           "Guardado para verlo con calma", "Wow, no sabía que se podía hacer así", "Me encantó cómo lo explicas 👏", "Necesitaba ver esto hoy",
           "Muy útil, de verdad", "Increíble lo que se puede hacer con IA 😮", "Ya lo estoy intentando jaja", "Qué buen contenido 💯",
           "Esto es oro 🙏", "Lo comparto con mi amiga ahora mismo", "Súper claro, gracias!"],
    "ja": ["めっちゃ参考になります🙏", "これ知らなかった！", "保存しました✨", "早速やってみます🔥", "わかりやすい！ありがとうございます",
           "すごすぎる…😳", "こういうの待ってました", "勉強になります🙌"],
    "pt": ["Que conteúdo bom 🙌", "Vou testar hoje mesmo 🔥", "Salvei pra ver com calma", "Não sabia que dava pra fazer isso", "Muito útil, obrigada!"],
    "fr": ["Trop utile, merci 🙌", "Je teste ça aujourd'hui 🔥", "Enregistré !", "Je ne savais pas que c'était possible 😮"],
    "de": ["Super hilfreich, danke 🙌", "Probiere ich heute aus 🔥", "Gespeichert!", "Wusste nicht, dass das so einfach geht 😮"],
}
USED_F = f"{HERE}/ig_engage_used.json"


def log(m):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {m}"
    print(line, flush=True); open(LOG_F, "a").write(line + "\n")


def pick_comment(lang):
    used = json.load(open(USED_F)) if os.path.exists(USED_F) else []
    pool = [c for c in COMMENTS.get(lang, COMMENTS["es"]) if c not in used[-40:]] or COMMENTS.get(lang, COMMENTS["es"])
    c = random.choice(pool); used.append(c); json.dump(used[-200:], open(USED_F, "w"), ensure_ascii=False)
    return c


def open_latest(handle):
    """Open the poster's profile and its newest post (first grid tile)."""
    w.shell("am", "start", "-a", "android.intent.action.VIEW", "-d", f"https://www.instagram.com/{handle}/", g.IG); w.sleep(6, 8)
    tiles = []
    for i in range(6):                     # the grid loads late and may sit below suggestion cards
        t = g.ui(); g.guard(t)
        tiles = re.findall(r'label="[^"]*at row 1, column 1"[^\n]*?@\((\d+),(\d+)\)', t)
        if tiles and int(tiles[0][1]) < 1400: break
        if i >= 2: w.shell("input", "swipe", "360", "1200", "360", "600", "400")
        w.sleep(2, 3)
    if not tiles: return False
    g.tapd(int(tiles[0][0]), int(tiles[0][1])); w.sleep(5, 7)
    t = g.ui()
    return "like_button" in t or "row_feed_button_like" in t


def engage_one(key, poster, post_lang):
    a = ACCTS[key]
    name, cc = vpn.COUNTRY[a["lang"]]
    if not vpn.set_country(DEV, name, cc): log(f"  [{key}] VPN {name} failed - skip"); return False
    g.open_app()
    if not g.switch_to(a["handle"]): log(f"  [{key}] could not switch"); return False
    if not open_latest(poster): log(f"  [{key}] could not open @{poster}'s latest post"); return False
    w.sleep(8, 18)                                                   # watch a bit first
    done = []
    t = g.ui(); c = w.coords(t, r'label="Like" id=(?:like_button|row_feed_button_like)')
    if c: g.tapd(*c); done.append("like"); w.sleep(1.5, 3)
    t = g.ui(); c = w.coords(t, r'label="(?:Save|Add to Saved)" id=(?:save_button|row_feed_button_save)')
    if c:
        g.tapd(*c); done.append("save"); w.sleep(1.5, 2.5)
        if "Collections" in g.ui() or "New collection" in g.ui(): w.pd("key", DEV, "back"); w.sleep(1, 2)
    # comment in the POST's language (Yui's post gets Japanese, Spanish posts Spanish)
    text = pick_comment(post_lang)
    t = g.ui(); c = w.coords(t, r'Button "Add comment…" id=comment_composer_text_view') or \
                   w.coords(t, r'label="Comment" id=(?:comment_button|row_feed_button_comment)')
    if c:
        g.tapd(*c); w.sleep(2.5, 3.5)
        t = g.ui(); e = w.coords(t, r'(?:AutoCompleteTextView|EditText)[^\n]*id=(?:layout_comment_thread_edittext\w*|comment_composer\w*)')
        if e:
            g.tapd(*e); w.sleep(1, 1.5)
            w.pd("type", DEV, text); w.sleep(1.5, 2.5)
            t = g.ui(); p = w.coords(t, r'label="Post" id=layout_comment_thread_post_button\w*') or w.coords(t, r'(?:Button|TextView) "Post"')
            if p: g.tapd(*p); done.append(f"comment:{text}"); w.sleep(2.5, 3.5)
        w.pd("key", DEV, "back"); w.sleep(1.5, 2)
        if "like_button" not in g.ui() and "row_feed_button_like" not in g.ui(): w.pd("key", DEV, "back"); w.sleep(1.5, 2)
    t = g.ui(); c = w.coords(t, r'Button label="Repost"')
    if c and random.random() < 0.6:
        g.tapd(*c); w.sleep(2, 3); done.append("repost")
        t = g.ui(); b = w.coords(t, r'(?:Button|TextView) "(?:Repost|Share|Done)"')
        if b and "like_button" not in t and "row_feed_button_like" not in t: g.tapd(*b); w.sleep(2, 3)
    log(f"  [{key}] on @{poster}: {', '.join(done) or 'nothing'}")
    w.pd("key", DEV, "home")
    return bool(done)


def main(post_name, n=None):
    posts = [json.loads(l) for l in open(f"{HERE}/ig_posts.jsonl")]
    p = next((x for x in reversed(posts) if x["name"] == post_name), None)
    if not p: log(f"no such post {post_name}"); return
    poster = p["acct"]; pk = next(k for k, a in ACCTS.items() if a["handle"] == poster); plang = ACCTS[pk]["lang"]
    # 21 Nov owner: Japanese posts get their activity from our Japanese accounts on the Lava/Realme/emulator (jp_engage.py),
    # and only accounts still logged in on the Redmi IG may engage (valentina/camila/sofia were logged out 19 Nov)
    if plang == "ja": log(f"ENGAGE {post_name}: Japanese post -> handled by jp_engage.py on the Japanese phones"); return
    LOGGED_IN = {"lucia", "yui"}
    others = [k for k in ACCTS if k != pk and k in LOGGED_IN and ACCTS[k]["lang"] == plang]
    if not others: log(f"ENGAGE {post_name}: no logged-in {plang} account on the Redmi to engage - skipped"); return
    random.shuffle(others)
    same = [k for k in others if ACCTS[k]["lang"] == plang]      # same-language accounts first (more natural)
    order = same + [k for k in others if k not in same]
    n = n or random.randint(2, 3)
    log(f"ENGAGE {post_name} (@{poster}) with {order[:n]}")
    try:
        for k in order[:n]:
            try: engage_one(k, poster, plang)
            except w.Stop as e: log(f"  [{k}] stopped: {e}"); break
            w.sleep(60, 180)                                         # minutes apart, not a burst of identical actions
    finally:
        vpn.set_country(DEV, *vpn.COUNTRY["us"])


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
