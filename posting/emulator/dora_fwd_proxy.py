"""23 Nov copy for the Doraemon emulator vw_ig_02: local no-auth HTTP proxy on 127.0.0.1:8898 -> residential proxy JP sticky
(session in lava/dora_proxy_session.txt; Sapporo NTT Docomo at setup). The emulator cannot reach proxy provider port 1000 directly.
Original: Local no-auth HTTP proxy on 127.0.0.1:8899 -> residential proxy MX sticky (adds Proxy-Authorization).
22 Nov 2026: the emulator's -http-proxy times out talking to proxy provider directly, so vw_scout_01 points here.
Credentials are read from ~/.flowcut/proxies (proxy-jp line, country swapped to MX); never printed."""
import asyncio, base64, os
for l in open(os.path.expanduser('~/.flowcut/proxies')):
    if l.startswith('proxy-jp '):
        _, H, P, U, PW, *_ = l.split(); break
PW = PW.split('_country-')[0] + '_country-JP_session-' + open(os.path.expanduser('~/masonry-tools/lava/dora_proxy_session.txt')).read().strip()
AUTH = b'Proxy-Authorization: Basic ' + base64.b64encode(f'{U}:{PW}'.encode()) + b'\r\n'

async def pipe(r, w):
    try:
        while (d := await r.read(65536)): w.write(d); await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except Exception: pass

async def handle(cr, cw):
    try:
        head = await cr.readuntil(b'\r\n\r\n')
        lines = head.split(b'\r\n')
        print(lines[0].decode(errors='replace')[:120], flush=True)
        lines = [x for x in lines if not x.lower().startswith(b'proxy-authorization')]
        head = lines[0] + b'\r\n' + AUTH + b'\r\n'.join(lines[1:])
        ur, uw = await asyncio.wait_for(asyncio.open_connection(H, int(P)), 30)
        uw.write(head); await uw.drain()
        await asyncio.gather(pipe(cr, uw), pipe(ur, cw))
    except Exception:
        try: cw.close()
        except Exception: pass

async def main():
    s = await asyncio.start_server(handle, '127.0.0.1', int(os.environ.get('DORA_PORT', '8898')))
    async with s: await s.serve_forever()
asyncio.run(main())
