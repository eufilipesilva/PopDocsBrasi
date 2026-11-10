#!/usr/bin/env python3
"""Estúdio PopDocs local: the same editing page, running on your own computer, without Claude.

    python3 servidor.py                 # opens http://localhost:8765
    python3 servidor.py --pasta D:/PopDocs/videos --porta 8765

It reads and writes the video folders directly and has a Render button that runs the engine (motor.py).
Only the standard library is needed for the server itself; the engine needs ffmpeg, Node + Playwright,
and the Python packages listed in INSTALAR.md.
"""
import json, os, sys, threading, subprocess, webbrowser, argparse, base64, re, time, mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

AQUI = os.path.dirname(os.path.abspath(__file__))
MOTOR = os.path.dirname(AQUI)
sys.path.insert(0, MOTOR)
import studio  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--pasta', default=os.path.join(os.path.dirname(MOTOR), 'videos'), help='pasta com os vídeos (uma subpasta por vídeo)')
ap.add_argument('--porta', type=int, default=8765)
ap.add_argument('--sem-navegador', action='store_true')
ARGS = ap.parse_args()
VIDEOS = os.path.abspath(ARGS.pasta)
RENDER = {}  # slug -> {'proc', 'log', 'started', 'ended', 'ok'}
LOCK = threading.Lock()

def vdir(slug):
    if not re.fullmatch(r'[A-Za-z0-9_\-]+', slug or ''): raise ValueError('nome de vídeo inválido')
    d = os.path.join(VIDEOS, slug)
    if not os.path.exists(os.path.join(d, 'video.json')): raise FileNotFoundError(slug)
    return d

def media_url(slug, rel):
    p = os.path.join(VIDEOS, slug, rel)
    return f'/media/{slug}/{rel}?v={int(os.path.getmtime(p))}' if os.path.exists(p) else ''

def load_video(slug):
    V = vdir(slug)
    def thumb_of(kind, key):
        if kind == 'scene': return media_url(slug, f'previas/cena-{key:02d}.jpg')
        if kind == 'foto': return media_url(slug, f'previas/foto-{key}.jpg') or media_url(slug, f'img/{key}.jpg')
        return media_url(slug, f'saidas/{slug}-thumbnail.jpg')
    vdoc, scenes, fotos = studio.files_to_docs(V, thumb_of)
    r = RENDER.get(slug)
    if r and not r.get('ended'): vdoc['render'] = {'requested': True, 'at': vdoc['render'].get('at', '')}
    return {'video': vdoc, 'scenes': dict(scenes), 'fotos': fotos}

def list_videos():
    out = []
    for d in sorted(os.listdir(VIDEOS)) if os.path.isdir(VIDEOS) else []:
        p = os.path.join(VIDEOS, d, 'video.json')
        if os.path.exists(p):
            c = studio.jload(p); out.append({'id': d, 'title': c.get('title', d), 'createdAt': c.get('createdAt', '')})
    return out

def start_render(slug):
    V = vdir(slug)
    with LOCK:
        r = RENDER.get(slug)
        if r and not r.get('ended'): return False
        log = os.path.join(V, 'saidas', 'renderizacao.log'); os.makedirs(os.path.dirname(log), exist_ok=True)
        f = open(log, 'w', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, '-u', os.path.join(MOTOR, 'motor.py'), V], stdout=f, stderr=subprocess.STDOUT, cwd=MOTOR)
        RENDER[slug] = {'proc': proc, 'log': log, 'started': time.time()}
    def wait():
        code = proc.wait(); f.close()
        RENDER[slug].update(ended=time.time(), ok=(code == 0))
        if code == 0:
            c = studio.jload(os.path.join(V, 'video.json')); c['renderedAt'] = time.strftime('%Y-%m-%dT%H:%M:%S'); studio.jsave(c, os.path.join(V, 'video.json'))
    threading.Thread(target=wait, daemon=True).start()
    return True

def render_status(slug):
    r = RENDER.get(slug)
    if not r: return {'running': False}
    tail = ''
    try: tail = ''.join(open(r['log'], encoding='utf-8', errors='replace').readlines()[-14:])
    except OSError: pass
    return {'running': not r.get('ended'), 'ok': r.get('ok'), 'elapsed': int((r.get('ended') or time.time()) - r['started']), 'log': tail,
            'video': f'/media/{slug}/saidas/{slug}.mp4' if r.get('ok') else ''}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
    def file(self, path):
        if not os.path.isfile(path): return self.send(404, {'erro': 'não encontrado'})
        size = os.path.getsize(path); ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        rng = self.headers.get('Range'); start, end = 0, size - 1
        if rng and rng.startswith('bytes='):
            a, b = rng[6:].split('-'); start = int(a or 0); end = int(b) if b else size - 1
            self.send_response(206); self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        else: self.send_response(200)
        self.send_header('Content-Type', ctype); self.send_header('Accept-Ranges', 'bytes'); self.send_header('Content-Length', str(end - start + 1)); self.end_headers()
        with open(path, 'rb') as fh:
            fh.seek(start); left = end - start + 1
            while left > 0:
                chunk = fh.read(min(1 << 20, left))
                if not chunk: break
                try: self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError): break
                left -= len(chunk)
    def body(self):
        n = int(self.headers.get('Content-Length', 0)); return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        u = urlparse(self.path); p = unquote(u.path)
        try:
            if p in ('/', '/index.html'):
                html = open(os.path.join(MOTOR, 'estudio.html'), encoding='utf-8').read()
                adapter = open(os.path.join(AQUI, 'adaptador.js'), encoding='utf-8').read()
                return self.send(200, '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
                                 f'<script>{adapter}</script>{html}</body></html>', 'text/html; charset=utf-8')
            if p == '/api/videos': return self.send(200, list_videos())
            m = re.fullmatch(r'/api/video/([^/]+)', p)
            if m: return self.send(200, load_video(m.group(1)))
            m = re.fullmatch(r'/api/render/([^/]+)', p)
            if m: return self.send(200, render_status(m.group(1)))
            m = re.fullmatch(r'/transicoes/([a-z]+)\.mp4', p)
            if m: return self.file(os.path.join(AQUI, 'transicoes', m.group(1) + '.mp4'))
            m = re.fullmatch(r'/media/([A-Za-z0-9_\-]+)/((?:img|previas|saidas)/[^/]+)', p)
            if m: return self.file(os.path.join(vdir(m.group(1)), *m.group(2).split('/')))
            self.send(404, {'erro': 'não encontrado'})
        except FileNotFoundError: self.send(404, {'erro': 'vídeo não encontrado'})
        except Exception as e: self.send(500, {'erro': str(e)})
    def do_POST(self):
        p = unquote(urlparse(self.path).path)
        try:
            m = re.fullmatch(r'/api/video/([^/]+)/salvar', p)
            if m:
                V = vdir(m.group(1)); b = self.body()
                return self.send(200, {'mudancas': studio.docs_to_files(V, b.get('video', {}), b.get('scenes', {}), b.get('fotos', {}))})
            m = re.fullmatch(r'/api/video/([^/]+)/foto', p)
            if m:
                V = vdir(m.group(1)); b = self.body()
                key = re.sub(r'[^a-z0-9_]', '_', (b.get('key') or 'foto').lower())[:40] or 'foto'
                head, _, data = b['data'].partition(',')
                raw = base64.b64decode(data or head)
                import numpy as np, cv2
                from clips import still
                os.makedirs(os.path.join(V, 'img'), exist_ok=True); os.makedirs(os.path.join(V, 'previas'), exist_ok=True)
                tipo = 'video' if head.startswith('data:video') else 'foto'
                if tipo == 'video':  # any common format -> silent H.264 mp4, at most 1920 wide
                    tmp = os.path.join(V, 'img', key + '.upload'); open(tmp, 'wb').write(raw)
                    out = os.path.join(V, 'img', key + '.mp4')
                    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', tmp, '-an', '-vf', "scale='min(1920,iw)':-2", '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out])
                    os.remove(tmp)
                    if r.returncode != 0: return self.send(400, {'erro': 'não consegui ler este vídeo'})
                    im = still(out)
                else:
                    im = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                    if im is None: return self.send(400, {'erro': 'arquivo não é uma imagem'})
                    cv2.imwrite(os.path.join(V, 'img', key + '.jpg'), im, [cv2.IMWRITE_JPEG_QUALITY, 93])
                h, w = im.shape[:2]; cv2.imwrite(os.path.join(V, 'previas', f'foto-{key}.jpg'), cv2.resize(im, (480, int(480 * h / w))), [cv2.IMWRITE_JPEG_QUALITY, 80])
                F = studio.jload(os.path.join(V, 'fotos.json'), {}); F[key] = {'cap': b.get('cap', ''), 'credit': b.get('credit', ''), 'license': b.get('license', ''), 'origin': 'upload', 'tipo': tipo}
                studio.jsave(F, os.path.join(V, 'fotos.json'))
                return self.send(200, {'key': key, 'url': media_url(m.group(1), f'previas/foto-{key}.jpg')})
            m = re.fullmatch(r'/api/render/([^/]+)', p)
            if m: return self.send(200, {'iniciado': start_render(m.group(1))})
            self.send(404, {'erro': 'não encontrado'})
        except FileNotFoundError: self.send(404, {'erro': 'vídeo não encontrado'})
        except Exception as e: self.send(500, {'erro': str(e)})

if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', ARGS.porta), H)
    url = f'http://localhost:{ARGS.porta}'
    print(f'Estúdio PopDocs local em {url}\nPasta dos vídeos: {VIDEOS}\nPara fechar, aperte Ctrl+C.')
    if not ARGS.sem_navegador: threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
