#!/usr/bin/env python3
"""Short preview clips of every transition, for the Studio's transition picker.

    python3 previas_transicoes.py <video_dir> [out_dir] [kind ...]

Uses two frames from the video's last render (a photo scene, then a text scene) and the
video's colors. Writes <out_dir>/<kind>.mp4 (480x270). Default out_dir: estudio_local/transicoes.
"""
import json, os, sys, shutil, subprocess, tempfile, importlib
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from motor import Video, ENV  # noqa: E402
from deftrans import KINDS  # noqa: E402

FPS = 30; W, H = 1920, 1080; PW, PH = 480, 270
SAMPLE = {  # example text for the transitions that show words
    'redact': {}, 'stamp': {}, 'terminal': {'lines': ['> acessar /arquivos/popdocs', '> abrir capitulo_02.dossie'], 'ok': 'CAPÍTULO 02 ENCONTRADO'},
    'search': {'query': 'jensen huang nvidia'},
}

def main():
    v = Video(sys.argv[1])
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2] in KINDS else os.path.join(HERE, 'estudio_local', 'transicoes')
    only = [k for k in sys.argv[2:] if k in KINDS] or list(KINDS)
    os.makedirs(out, exist_ok=True)
    S = v.S
    a = next((i for i, s in enumerate(S) if s.get('bg') and s['t'] != 'title' and os.path.exists(v.w('edges', f'{i:02d}_last.png'))), None)
    b = next((i for i in range(len(S)) if not S[i].get('bg') and S[i]['t'] in ('fact', 'quote', 'name') and os.path.exists(v.w('edges', f'{i:02d}_first.png'))), None)
    if a is None or b is None: sys.exit('Renderize o vídeo uma vez antes de gerar as prévias das transições.')
    A = cv2.imread(v.w('edges', f'{a:02d}_last.png')).astype(np.float32); B = cv2.imread(v.w('edges', f'{b:02d}_first.png')).astype(np.float32)
    tmp = tempfile.mkdtemp(prefix='popdocs-prev-')
    for f in ('trans.py', 'spyshots.js'): shutil.copy(os.path.join(HERE, f), tmp)
    shutil.copy(os.path.join(HERE, 'templates', 'spy.html'), tmp)
    json.dump([{}, {}, {}], open(os.path.join(tmp, 'scenes.json'), 'w'))
    json.dump([{'start': 0, 'dur': 10, 'subs': [], 'steps': [0]}] * 3, open(os.path.join(tmp, 'plan.json'), 'w'))
    json.dump(v.cores(), open(os.path.join(tmp, 'cores.json'), 'w'))
    os.chdir(tmp); sys.path.insert(0, tmp)
    tr = importlib.import_module('trans')
    frames = {k: max(2, int(round(max(KINDS[k][1], .6) * FPS))) for k in only}
    spec = [{'id': k, 'kind': k, 'frames': frames[k], 'params': SAMPLE.get(k, {})} for k in only if k in tr.OVK]
    if spec:
        json.dump(spec, open('ovspec.json', 'w'), ensure_ascii=False)
        subprocess.run(['node', 'spyshots.js', 'ovspec.json'], check=True, env=ENV)
    for k in only:
        n = frames[k]
        pr = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{PW}x{PH}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', os.path.join(out, k + '.mp4')], stdin=subprocess.PIPE)
        small = lambda f: cv2.resize(np.clip(f, 0, 255).astype(np.uint8), (PW, PH), interpolation=cv2.INTER_AREA).tobytes()
        for _ in range(int(.4 * FPS)): pr.stdin.write(small(A))
        for j in range(n):
            p = (j + .5) / n; ov = None
            fn = f'ov/{k}/{j:03d}.png'
            if k in tr.OVK and os.path.exists(fn):
                o = cv2.imread(fn, cv2.IMREAD_UNCHANGED).astype(np.float32)
                ov = (o[:, :, :3], o[:, :, 3:4] / 255.0) if o.shape[2] == 4 else (o, np.ones((H, W, 1), np.float32))
            pr.stdin.write(small(tr.T(k, A, B, p, j, ov, SAMPLE.get(k, {}))))
        for _ in range(int(.6 * FPS)): pr.stdin.write(small(B))
        pr.stdin.close(); pr.wait(); print(k, end=' ', flush=True)
    print('\nprévias em', out)
    shutil.rmtree(tmp, ignore_errors=True)

if __name__ == '__main__':
    main()
