#!/usr/bin/env python3
"""Publish the posting log for the dashboard's Automated accounts page (22 Nov 2026).

The dashboard is built on the VPS, which cannot see this Mac's ~/masonry-tools/pranks files, so the page showed a
14 Nov copy for 8 days. This writes the same dict tracker/automated.py read_feed() builds and pushes it as the only
file on branch `automated-feed` of Shreyhac/masonry-ugc-tracker (git plumbing: the working copy is never touched;
Vercel ignores that branch). The VPS run's `git fetch origin` picks it up. LaunchAgent com.masonry.publishfeed, hourly.
"""
import ast, datetime, json, os, subprocess, sys

SRC = os.path.expanduser('~/masonry-tools/pranks')
REPO = os.path.expanduser('~/masonry-ugc-tracker')
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def lines(p):
    p = os.path.join(SRC, p)
    return [l.strip() for l in open(p) if l.strip() and not l.startswith('#')] if os.path.exists(p) else []


def accts():
    for node in ast.parse(open(os.path.join(SRC, 'ugc.py')).read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'ACCTS' for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit('ACCTS not found')


def git(*a, inp=None):
    r = subprocess.run(['git', '-C', REPO, *a], input=inp, capture_output=True, text=True, timeout=120)
    if r.returncode: raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


feed = {
    'read_at': datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
    'source': 'live',
    'accounts': [{'key': k, 'handle': v[0], 'phone': v[1], 'from': v[2]} for k, v in accts().items()],
    'log': [json.loads(l) for l in open(os.path.join(SRC, 'posts.jsonl')) if l.strip()],
    'approved': lines('approved.txt'),
    'queue': {'redmi': lines('queue.txt'), 'realme': lines('queue_realme.txt')},
    'stopped': lines('../POST_STOP_ACCOUNTS.txt'),
}
blob = git('hash-object', '-w', '--stdin', inp=json.dumps(feed, ensure_ascii=False))
# 23 Nov: Vercel builds every branch push as a preview and emailed a failure each hour (this tree has no site).
# The skip setting must be inside the deployed commit (Vercel root dir = site), so ship site/vercel.json with it.
vj = git('hash-object', '-w', '--stdin', inp='{"git": {"deploymentEnabled": false}}\n')
site = git('mktree', inp=f'100644 blob {vj}\tvercel.json\n')
tree = git('mktree', inp=f'100644 blob {blob}\tautomated_feed.json\n040000 tree {site}\tsite\n')
commit = git('commit-tree', tree, '-m', f"automated feed {feed['read_at']} IST ({len(feed['log'])} log rows)")
git('push', '-q', '-f', 'origin', f'{commit}:refs/heads/automated-feed')
print(f"{feed['read_at']} pushed automated-feed: {len(feed['log'])} log rows, {len(feed['accounts'])} accounts")
