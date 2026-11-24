#!/usr/bin/env python3
"""One controller for the shared phone: post when an account is due, warm up in between, stats hourly.
- queue.txt: one cfg name per line (rendered out/<name>.mp4); posted ones are recorded in posts.jsonl
- an account posts again only after MIN_GAP minutes
- between posts: 12-min warm-up sessions on prank content, rotating accounts
usage: caffeinate -i python3 run_forever.py"""
import datetime, importlib.util, json, os, subprocess, time, traceback, random
import fcntl as _fcntl, sys as _sys   # 11 Nov 18:55: one copy only (watchdog's pgrep misses sometimes and launched duplicates)
_lockf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.run_forever.lock'), 'w')
try: _fcntl.flock(_lockf, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
except OSError: print('another run_forever is running; exiting'); _sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('w', os.path.expanduser('~/masonry-tools/tiktok-warmup/warmup.py'))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
MIN_GAP = 60 * 60   # user rule 9 Nov: at least 1 hour between posts on the same account
MAX_PER_DAY = 2               # 11 Nov 19:20 user: '2 per day per acc is fine; major target = video templates on ALL channels incl. prank channels'
DEVICE_GAP = 45 * 60          # 11 Nov: between ANY two posts on this phone
WARM_BEFORE_POST = 2 * 60 * 60   # 21 Nov owner (angry: 'how tf without warm up are you even posting'): an account posts only if it had a warm-up session in the last 2 h
SAME_VIDEO_GAP = 18 * 60 * 60 # 11 Nov: copies of one PRANK on different accounts at least 18 h apart
UGC_SAME_GAP = 8 * 60 * 60    # 11 Nov 17:50: every copy of a template has the SAME voiceover (whisper check) -> TikTok sees duplicates; 8 h apart
import sys; sys.path.insert(0, HERE); import ugc, plan
WARM_MIN = 12
STATS_EVERY = 3 * 60 * 60   # stats on 8 accounts takes ~15 min; warm-up comes first
KEY = {'acct_107': 'ethan', 'acct_171': 'maya', 'acct_137': 'jake', 'acct_202': 'rgu', 'acct_078': 'beth', 'acct_164': 'chloe', 'acct_040': 'ava', 'acct_168': 'sophie'}
# 21 Nov 2026: only these 4 English prank accounts are still logged in on the Redmi TikTok (rgu/chloe/ava/sophie were logged out 19 Nov)
ON_DEVICE = {'acct_107', 'acct_171', 'acct_137', 'acct_078'}
# everyone posts AI-photo pranks now -> warm every account on prank creators/tags
w.SEEDS['_handles']['rgu'] = 'acct_202'; w.SEEDS['_handles']['beth'] = 'acct_078'
for k in ('maya', 'jake', 'beth'):
    w.SEEDS[k] = w.SEEDS['ethan']; w.SEEDS['_tags'][k] = w.SEEDS['_tags']['ethan']
    w.RELEVANT[k] = w.RELEVANT['ethan']
w.RELEVANT['ethan'] = w.RELEVANT['maya'] = w.RELEVANT['jake'] = w.RELEVANT['beth'] = r"prank|pranked|\bai\b|ai photo|text(ed|ing)? (my )?(mom|dad|boss|bf|boyfriend)|my (mom|dad)|cantina|maybereal|fake photo|reaction|told my|pov"
w.FOLLOW_P = 0.0
# @acct_202 = ANIMATION / AI side-hustle niche (Claude x Mia series), NOT pranks
# 11 Nov user: NEVER warm up on our own paid creators or @masonryai -> seeds come from the AI/side-hustle pool (not Masonry's),
# picked by handle hints; warmup.blocked() also filters every seed list and skips their videos anywhere.
_POOL = json.load(open(os.path.expanduser('~/masonry-tools/tiktok-warmup/seeds.json')))['maya']
def _pick(*hints): return [h for h in _POOL if any(x in h for x in hints)]
w.SEEDS['rgu'] = _pick('hustle', 'money', 'bank', 'grind', 'income', 'creates', 'ai')
w.SEEDS['_tags']['rgu'] = ["printify", "amazonkdp", "aisidehustle", "facelessyoutube", "animatedshort", "sidehustleideas", "ingresosextra", "dineroextra"]
w.SEARCH_KWS['rgu'] = ["animated story short", "ai side hustle", "printify side hustle", "amazon kdp coloring book", "faceless youtube channel ai",
                       "claude ai animation", "make money with ai", "print on demand ai designs", "dinero extra con ia", "ai animation story"]
w.RELEVANT['rgu'] = r"animat|cartoon|side ?hustle|printify|print on demand|kdp|coloring book|faceless|passive income|make money|extra money|dinero extra|ingresos|\bai\b|claude|chatgpt|masonry|etsy|digital product|youtube automation"

# 10 Nov new accounts. @acct_164 "Chloe" = AI side hustles (English, Printify/KDP/Etsy); @acct_040 "Ava" = product-photo UGC like our creators
w.SEEDS['_handles']['chloe'] = 'acct_164'; w.SEEDS['_handles']['ava'] = 'acct_040'
w.SEEDS['chloe'] = _pick('hustle', 'money', 'bank', 'grind', 'income', 'working', 'work')
w.SEEDS['_tags']['chloe'] = ["printify", "amazonkdp", "aisidehustle", "sidehustleideas", "acct_108", "printondemand", "digitalproducts"]
w.SEARCH_KWS['chloe'] = ["ai side hustle", "printify side hustle", "amazon kdp coloring book", "etsy digital products ai", "print on demand ai designs",
                         "side hustle ideas 2026", "make money with ai", "passive income ideas"]
NO_PRANK = r"(?is)^(?!.*(prank|cantina|maybereal|texted my (mom|dad|boss)))"
w.RELEVANT['chloe'] = NO_PRANK + r".*(" + w.RELEVANT['rgu'] + r")"
w.SEEDS['ava'] = _pick('design', 'studio', 'ugc', 'product', 'creat', 'photo', 'shop')
w.SEEDS['_tags']['ava'] = ["productphotography", "productphotos", "aiphotography", "acct_210", "aiugc", "phonephotography", "aivideo"]
w.SEARCH_KWS['ava'] = ["product photography at home", "ai product photos", "phone product photography hacks", "small business product photos",
                       "ai photo editing", "ai video ad", "studio photos from phone", "ugc product video"]
w.RELEVANT['ava'] = NO_PRANK + r".*(product|photo|studio|small business|ugc|\bai\b|edit|campaign|ad\b|ads\b|masonry|brand|shoot|camera|lighting)"

# @acct_168 "Sophie" = AI video (Higgsfield/Kling/Veo-style creators), no pranks
w.SEEDS['_handles']['sophie'] = 'acct_168'
w.SEEDS['sophie'] = list(w.SEEDS['maya_orig'] if 'maya_orig' in w.SEEDS else json.load(open(os.path.expanduser('~/masonry-tools/tiktok-warmup/seeds.json')))['maya'])
w.SEEDS['_tags']['sophie'] = ["higgsfieldpartner", "aivideo", "aivideogenerator", "klingai", "veo3", "aiugc", "aiads", "aifilm"]
w.SEARCH_KWS['sophie'] = ["ai video generator", "higgsfield ai", "kling ai video", "veo 3 video", "ai ugc ad", "ai short film", "image to video ai", "ai video editing"]
w.RELEVANT['sophie'] = NO_PRANK + r".*(\bai\b|video|higgsfield|kling|veo|sora|runway|ugc|ad\b|ads\b|film|edit|masonry|generat|animat)"

def log(m):
    line = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + m
    print(line, flush=True); open(f'{HERE}/run_forever.log', 'a').write(line + '\n')

def posts():
    return [json.loads(l) for l in open(f'{HERE}/posts.jsonl')] if os.path.exists(f'{HERE}/posts.jsonl') else []

def last_post(acct):
    ts = [datetime.datetime.fromisoformat(p['ts']) for p in posts() if p['acct'] == acct]
    return max(ts) if ts else datetime.datetime(2000, 1, 1)

def _post_stopped():   # 18 Nov owner: no posting on accounts in ~/masonry-tools/POST_STOP_ACCOUNTS.txt (best video < 700)
    try: return {l.strip() for l in open(__import__("os").path.expanduser("~/masonry-tools/POST_STOP_ACCOUNTS.txt")) if l.strip() and not l.startswith("#")}
    except FileNotFoundError: return set()

def next_item(gap_check=True):
    done = {p['name'] for p in posts()}
    approved = {l.strip() for l in open(f'{HERE}/approved.txt')} if os.path.exists(f'{HERE}/approved.txt') else set()   # user rule: only post what the user approved
    q = [l.strip() for l in open(f'{HERE}/queue.txt') if l.strip() and not l.startswith('#')]
    now = datetime.datetime.now()
    # 11 Nov pacing (views data: unique posts 8 Nov = 190-790 each; 2nd-4th copies of one video within 1-2 h = 0-212;
    # after ~13 posts in 4 h from this phone every post sat at 0-28). Spread posts out:
    ok_posts = [p for p in posts() if p['acct'] != 'FAILED']
    last_any = max([datetime.datetime.fromisoformat(p['ts']) for p in ok_posts] or [datetime.datetime(2000, 1, 1)])
    try:   # 12 Nov: Instagram posts from this phone count for the 45-min phone gap too
        for l in open(os.path.expanduser('~/masonry-tools/insta/ig_posts.jsonl')):
            last_any = max(last_any, datetime.datetime.fromisoformat(json.loads(l)['ts']))
    except FileNotFoundError: pass
    globals()['_last_any'] = last_any
    # 13 Nov 19:20 owner: post the whole backlog now; the ONLY rule is >= 1 h between two posts on the same account
    # (no phone-wide gap, no per-day cap, no same-video gap). Fixed times get decided after the backlog is out.
    q = [n for n in q if n.startswith('ugc_')] + [n for n in q if not n.startswith('ugc_')]
    for name in q:
        if name in done or name not in approved or not os.path.exists(f'{HERE}/out/{name}.mp4'): continue
        acct = json.load(open(f'{HERE}/cfg/{name}.json'))['acct']
        if acct in _post_stopped(): continue
        if not ugc.ready(acct, now): continue
        if (now - last_post(acct)).total_seconds() < MIN_GAP: continue
        if time.time() - globals().get('warm_ok', {}).get(acct, 0) > WARM_BEFORE_POST: continue   # warm first, then post
        if gap_check and (now - last_any).total_seconds() < DEVICE_GAP: return None   # 21 Nov: back to >= 45 min between ANY two posts on this phone (18 Nov burst of 4 in 15 min)
        # 17 Nov (Gaurav: rotonda 1.2M, 'replicate asap'): names in tt_force.txt skip the daily/remix cap, but still need prime time
        _force = set(l.strip() for l in open(f'{HERE}/tt_force.txt')) if os.path.exists(f'{HERE}/tt_force.txt') else set()
        if name in _force and plan.in_window('en', now): return name
        if not plan.ok(acct, name, ok_posts, 'en', now): continue   # 14 Nov owner "crazy views": prime time + 3/day (pranks/plan.py)
        return name
    return None


def post_wait():
    """22 Nov owner ("ofc yes" - don't let warm-ups delay posts): Ethan's 22 Nov 19:23 slot was lost because the loop was
    in a 12-min warm-up / 15-min stats run when the 45-min phone gap ended. Returns seconds until a READY post (approved,
    warmed, in window) may go, when only the phone gap is left and it ends inside the window; else None."""
    if os.path.exists(f'{HERE}/POST_STOP'): return None
    try:
        if not next_item(gap_check=False): return None
    except Exception: return None
    left = DEVICE_GAP - (datetime.datetime.now() - globals()['_last_any']).total_seconds()
    if left <= 0: return 0
    return left if plan.in_window('en', datetime.datetime.now() + datetime.timedelta(seconds=left)) else None


def _pending_names():   # 21 Nov: approved, rendered, not yet posted queue items
    done = {p['name'] for p in posts()}
    ap = {l.strip() for l in open(f'{HERE}/approved.txt')} if os.path.exists(f'{HERE}/approved.txt') else set()
    return [l.strip() for l in open(f'{HERE}/queue.txt') if l.strip() and not l.startswith('#') and l.strip() not in done
            and l.strip() in ap and os.path.exists(f'{HERE}/out/{l.strip()}.mp4') and os.path.exists(f'{HERE}/cfg/{l.strip()}.json')]


NEW = {'acct_164': datetime.date(2026, 11, 10), 'acct_040': datetime.date(2026, 11, 10), 'acct_168': datetime.date(2026, 11, 10)}
NEW_MIN = 18
WL_F = f'{HERE}/warm_last_redmi.json'      # 11 Nov: rotation survives restarts
warm_last = {a: 0 for a in KEY if a in ON_DEVICE}
WO_F = f'{HERE}/warm_ok_redmi.json'   # 21 Nov: clean warm-ups survive restarts
warm_ok = json.load(open(WO_F)) if os.path.exists(WO_F) else {}   # posts need one in the last WARM_BEFORE_POST
if os.path.exists(WL_F): warm_last.update({k: v for k, v in json.load(open(WL_F)).items() if k in KEY and k in ON_DEVICE})
last_stats = time.time() - STATS_EVERY + 2 * 60 * 60   # first stats ~1h after start
st = w.load_state()
while True:
    if os.path.exists(f'{HERE}/PAUSE'):
        time.sleep(20); continue
    try:
        _pw = post_wait()
        if time.time() - last_stats > STATS_EVERY and (_pw is None or _pw > 20 * 60):
            last_stats = time.time()   # 11 Nov 23:40: set BEFORE running - a timed-out stats run re-ran in a loop 21:10-23:30 and blocked all posts
            r = subprocess.run(['python3', f'{HERE}/stats.py'], capture_output=True, text=True, timeout=1200)
            log('STATS\n' + r.stdout.strip())
        # 10 Nov: Wi-Fi dropped -> switches failed, an upload went to drafts but was logged as posted. Never act offline.
        if '1 received' not in (w.shell('ping -c1 -W5 1.1.1.1') or '') and '1 received' not in (w.shell('ping -c1 -W5 8.8.8.8') or ''):
            if not globals().get('_offline'): log('OFFLINE: phone has no internet, waiting')
            globals()['_offline'] = True; time.sleep(120); continue
        if globals().get('_offline'): log('ONLINE again'); globals()['_offline'] = False
        try: ugc.ingest(log)
        except Exception as e: log(f'UGC ingest error: {e}')
        # 12 Nov 12:25: Instagram posts go BEFORE TikTok posts (owner: IG is the major priority). localized template Reels (video session -> ~/masonry-tools/insta/ig_in) post to Instagram from 15 Nov
        ig_name = None
        try:
            sys.path.insert(0, os.path.expanduser('~/masonry-tools/insta')); import ig_sched
            ig_sched.ingest(log); ig_name = ig_sched.next_item()
        except Exception as e: log(f'IG queue error: {e}')
        # 13 Nov owner: "stop all posting" -> while pranks/POST_STOP exists nothing posts (IG or TikTok); warm-ups go on
        # 13 Nov 06:00 owner: "need to post on insta of these diff lang videos" -> insta/IG_POST_GO lets Instagram post while
        # POST_STOP still holds TikTok. Delete IG_POST_GO (or touch insta/IG_POST_STOP) to stop Instagram again.
        _ins = os.path.expanduser('~/masonry-tools/insta')
        if (os.path.exists(f'{HERE}/POST_STOP') and not os.path.exists(f'{_ins}/IG_POST_GO')) or os.path.exists(f'{_ins}/IG_POST_STOP'): ig_name = None
        if ig_name:
            log(f'IG POST {ig_name}')
            # 13 Nov owner: Instagram posts go through the Edits app (GTA copies voice-only + dennyintech original audio ~25%)
            r = subprocess.run(['python3', os.path.expanduser('~/masonry-tools/insta/ig_post_edits.py'), ig_name], capture_output=True, text=True, timeout=1800)
            log((r.stdout[-700:] + r.stderr[-400:]).strip() + f'\n  exit {r.returncode}')
            if r.returncode == 0:
                # 12 Nov owner: right after a post goes live, 2-3 of our other IG accounts like/save/comment/repost it
                er = subprocess.run(['python3', os.path.expanduser('~/masonry-tools/insta/ig_engage.py'), ig_name], capture_output=True, text=True, timeout=1800)
                log('IG ENGAGE ' + ' | '.join(l[20:] for l in er.stdout.strip().splitlines()[-4:]))
            if r.returncode != 0:
                fp = os.path.expanduser('~/masonry-tools/insta/ig_fails.json')
                fails = json.load(open(fp)) if os.path.exists(fp) else {}
                fails[ig_name] = fails.get(ig_name, 0) + 1; json.dump(fails, open(fp, 'w'))
                time.sleep(30)
            continue
        # 12 Nov user: "now we need to focus on warming insta" -> every other free slot is an Instagram warm-up session
        # (~12 min, next IG account in rotation; ~/masonry-tools/insta/ig_warm.py). Posts above always go first.
        name = None if os.path.exists(f'{HERE}/POST_STOP') else next_item()
        if name:
            log(f'POST {name}')
            r = subprocess.run(['python3', f'{HERE}/post.py', name], capture_output=True, text=True, timeout=900)
            log((r.stdout[-900:] + r.stderr[-500:]).strip() + f'\n  exit {r.returncode}')
            if r.returncode == 0:
                # 23 Nov: the next warm-up started the same second, its account switch failed and it restarted TikTok
                # while the upload (1-2 min videos) was still running -> let the upload finish first
                time.sleep(180)
            if r.returncode != 0:
                w.shell('am', 'force-stop', 'com.zhiliaoapp.musically'); time.sleep(30)
                # mark repeated failures so one bad item can't block the queue forever
                fails = json.load(open(f'{HERE}/fails.json')) if os.path.exists(f'{HERE}/fails.json') else {}
                fails[name] = fails.get(name, 0) + 1; json.dump(fails, open(f'{HERE}/fails.json', 'w'))
                if fails[name] >= 3:
                    open(f'{HERE}/posts.jsonl', 'a').write(json.dumps({'ts': datetime.datetime.now().isoformat(timespec='seconds'), 'name': name, 'acct': 'FAILED', 'note': 'gave up after 3 tries'}) + '\n')
            continue
        _pw = post_wait()
        if _pw is not None and _pw <= 16 * 60:   # 22 Nov: a warm-up now would run past the moment the post may go -> hold
            if not globals().get('_holding'): log(f'HOLD: a post may go in {int(_pw // 60) + 1} min, no warm-up until then')
            globals()['_holding'] = True; time.sleep(min(60, max(5, _pw))); continue
        globals()['_holding'] = False
        # 12 Nov 17:25 owner (P0, urgent): @acct_040 follows every TikTok account in the template-scan pool.
        # TikTok allows ~200 follows/day -> a batch of 30 every ~35 min, ahead of warm-ups (posts still go first).
        if 'acct_040' in ON_DEVICE and time.time() - globals().get('_ava_last', 0) > 60 * 60 and plan.warm_eligible({'ava': 'en'}):   # 16 Nov: follows at US prime time too   # ~30/hour (guides cite ~30 follows/hour, ~200/day; unofficial)
            globals()['_ava_last'] = time.time()
            r = subprocess.run(['python3', os.path.expanduser('~/masonry-tools/tiktok-warmup/ava_follow.py'), '30'], capture_output=True, text=True, timeout=2400)
            out = [l for l in (r.stdout or '').splitlines() if 'ava-follow' in l]
            log('AVA FOLLOW ' + (out[-1][20:] if out else f'exit {r.returncode} ' + (r.stderr or '')[-200:]))
            if out and 'nothing left' not in out[-1] and 'cap reached' not in out[-1] and 'backing off' not in out[-1]: continue
        # 12 Nov 11:55 owner: Instagram is the MAJOR priority -> 2 IG sessions for every 1 TikTok warm-up
        globals()['_slot'] = globals().get('_slot', -1) + 1
        # 21 Nov: while TikTok accounts with a post waiting still need their warm-up, TikTok warm-ups go before IG sessions
        _tt_due = {json.load(open(f'{HERE}/cfg/{n}.json'))['acct'] for n in _pending_names()} & plan.warm_eligible({a: 'en' for a in warm_last})
        _tt_due = {a for a in _tt_due if a in warm_last and time.time() - warm_ok.get(a, 0) > WARM_BEFORE_POST * 0.75}
        if globals()['_slot'] % 3 != 2 and not _tt_due:
            r = subprocess.run(['python3', os.path.expanduser('~/masonry-tools/insta/ig_warm.py'), 'next', str(random.randint(11, 14))],
                               capture_output=True, text=True, timeout=1800)
            out = [l for l in r.stdout.strip().splitlines() if l.strip()]
            if r.returncode != 4:                     # 4 = every IG account resting (their night) -> go on to TikTok
                log('IG WARM ' + (out[0][20:] if out else '?') + ' -> ' + (out[-1][20:] if out else '') + f' (exit {r.returncode})')
                if r.returncode != 0: time.sleep(60)
                continue
        # nothing due: warm the account that was warmed longest ago
        # new accounts get ~2x the turns and longer sessions; they may follow a few niche creators from day 2 (day-0 follows get reverted)
        # 16 Nov owner: warm up like a human, at the audience's prime time (US clock for these TikTok accounts)
        _ok = plan.warm_eligible({a: 'en' for a in warm_last})
        if not _ok:
            if not globals().get('_resting'): log('REST: no account is in its audience\'s hours')
            globals()['_resting'] = True; time.sleep(90); continue   # 17 Nov owner 'Redmi idle': 90 s so the next IG turn (e.g. Yui) comes quickly
        globals()['_resting'] = False
        _due = {json.load(open(f'{HERE}/cfg/{n}.json'))['acct'] for n in _pending_names()} & set(_ok)
        _due = {a for a in _due if time.time() - warm_ok.get(a, 0) > WARM_BEFORE_POST * 0.75}
        acct = max(_due or _ok, key=lambda a: (time.time() - warm_last[a]) * (1.3 if a in NEW else 1.0))   # 21 Nov: accounts with a post waiting get warmed first
        mins = NEW_MIN if acct in NEW else WARM_MIN
        if acct in NEW and datetime.date.today() > NEW[acct]:
            w.FOLLOW_P, w.MAX_FOLLOWS_PER_DAY, w.COMMENT_P = 0.35, 5, 0.05   # 17 Nov owner: follow 3-5/day + light comments
        else:
            w.FOLLOW_P, w.MAX_FOLLOWS_PER_DAY, w.COMMENT_P = 0.35, 5, 0.05   # 17 Nov owner (was 0.0 = no follows)
        log(f'WARM @{acct} {mins} min' + (' (new account)' if acct in NEW else ''))
        try:
            w.session(KEY[acct], mins * random.uniform(0.9, 1.1), st); w.save_state(st)
            warm_ok[acct] = time.time(); json.dump(warm_ok, open(WO_F, 'w'))   # 21 Nov: only a warm-up that finished cleanly unlocks a post
        except w.Stop as e:
            log(f'warm stopped: {e}')
            if 'VPN' in str(e): time.sleep(300)
            else: w.shell('am', 'force-stop', 'com.zhiliaoapp.musically'); time.sleep(120)
        warm_last[acct] = time.time(); json.dump(warm_last, open(WL_F, 'w'))
    except Exception:
        log('ERROR ' + traceback.format_exc()[-800:]); time.sleep(60)
