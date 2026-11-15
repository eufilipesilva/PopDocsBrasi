#!/usr/bin/env python3
"""PopDocsBrasil video engine.

usage:  python3 motor.py <video_dir> [--teste] [step ...]
steps:  tts plan shots clips trans mix srt thumb previas   (default: all, in that order)
        celular   (not in the default list) makes a light 540p copy of the final video for phones
--teste renders a draft with a free synthetic voice (edge-tts): no ElevenLabs credits are spent.
        The draft has its own work dir and narration cache and is saved as saidas/<slug>-TESTE.mp4.

<video_dir> (kept in the project files) holds:
  video.json         title, texts, voice, music, thumbnail settings
  scenes.json        the scene list (type, on-screen fields, narration "n")
  transitions.json   one entry per boundary (created with defaults if missing)
  fotos.json         photo library: key -> {cap, credit, license, source}
  img/<key>.jpg      the photos (or img/<key>.mp4 / .webm: a short silent clip used like a photo)
  audio/<hash>.mp3   cached narration, named by text+voice (only generated when a text is new)
  saidas/            final video, subtitles, thumbnail
Heavy intermediate files go to the work dir ($POPDOCS_WORK or /tmp/popdocs-work/<slug>).
Each step only redoes scenes whose inputs changed (hashes in the work dir).
"""
import json, os, sys, re, hashlib, shutil, subprocess, urllib.request, tempfile
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 24000; FPS = 30
FX_VER = 2   # raise when the look of an effect in clips.py changes (ambient, extra photos, detail zoom): scenes that use it are redrawn
STEPS = ['tts', 'plan', 'shots', 'clips', 'trans', 'mix', 'srt', 'thumb', 'previas']
ENV = dict(os.environ, PYTHONUTF8='1', NODE_PATH=os.path.join(HERE, 'node_modules') + os.pathsep + os.environ.get('NODE_PATH', ''))

def H(*objs):
    h = hashlib.sha1()
    for o in objs: h.update(json.dumps(o, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()[:16]

def fhash(path):
    if not os.path.exists(path): return None
    st = os.stat(path); return f'{st.st_size}-{int(st.st_mtime)}'

def run(cmd, **kw):
    print('  $', ' '.join(map(str, cmd))[:160], flush=True)
    subprocess.run(cmd, check=True, env=ENV, **kw)

def eleven_key():
    k = os.environ.get('ELEVENLABS_API_KEY')
    p = os.path.join(os.path.expanduser('~'), '.popdocs', 'elevenlabs.txt')
    if not k and os.path.exists(p): k = open(p).read().strip()
    return k  # None in the Claude environment, where the proxy adds the key

class Video:
    def __init__(self, vdir, teste=False):
        self.V = os.path.abspath(vdir); self.teste = teste
        self.cfg = json.load(open(f'{self.V}/video.json'))
        self.slug = self.cfg['slug']
        self.WD = os.environ.get('POPDOCS_WORK', os.path.join(tempfile.gettempdir(), 'popdocs-work', self.slug)) + ('-teste' if teste else '')
        self.out = self.slug + ('-TESTE' if teste else '')
        os.makedirs(self.WD, exist_ok=True); os.makedirs(f'{self.V}/saidas', exist_ok=True); os.makedirs(f'{self.V}/audio', exist_ok=True)
        self.S = json.load(open(f'{self.V}/scenes.json'))
        self.fotos = json.load(open(f'{self.V}/fotos.json')) if os.path.exists(f'{self.V}/fotos.json') else {}
        hp = f'{self.WD}/hashes.json'
        self.hashes = json.load(open(hp)) if os.path.exists(hp) else {}

    def save_hashes(self): json.dump(self.hashes, open(f'{self.WD}/hashes.json', 'w'), indent=0)
    def w(self, *p): return os.path.join(self.WD, *p)

    # ---------- scenes as rendered (photo caption/credit resolved from the library) ----------
    def resolved(self):
        out = []
        for s in self.S:
            s = dict(s)
            bg = s.get('bg')
            if bg:
                if not self.bgpath(bg):
                    print(f'  ! foto ou vídeo "{bg}" não encontrado em img/; cena fica sem foto'); s.pop('bg')
                else:
                    f = self.fotos.get(bg, {})
                    if f.get('modo') in ('pb', 'cor', 'tom'): s['fotoModo'] = f['modo']
                    for k, v in (('foco', 'fotoFoco'), ('enquadrar', 'fotoEnq'), ('recorte', 'fotoRecorte')):   # framing: scene overrides library
                        if s.get(k) or f.get(k): s[v] = s.get(k) or f.get(k)
                    if s['t'] != 'title': s.setdefault('cap', f.get('cap', ''))
                    s.setdefault('credit', f.get('credit', ''))
                    if self.cfg.get('ambiente'): s['amb'] = self.cfg['ambiente']; s['fxv'] = FX_VER   # living texture over photos and background clips
                    extra = []   # more photos in the same scene ('bgs'): each one framed and credited from the library
                    for k2 in s.pop('bgs', None) or []:
                        f2 = self.fotos.get(k2, {}); p2 = self.bgpath(k2)
                        if not p2: print(f'  ! foto extra "{k2}" não encontrada em img/'); continue
                        if p2.lower().endswith(('.mp4', '.webm', '.mov', '.m4v')): print(f'  ! "{k2}" é vídeo: fotos extras precisam ser imagens'); continue
                        e = {'key': k2, 'auto': True, 'hash': fhash(p2), 'cap': f2.get('cap', ''), 'credit': f2.get('credit', ''), 'date': f2.get('date', '')}   # each photo shows its own caption and credit
                        if f2.get('modo') in ('pb', 'cor', 'tom'): e['fotoModo'] = f2['modo']
                        for k, v in (('foco', 'fotoFoco'), ('enquadrar', 'fotoEnq'), ('recorte', 'fotoRecorte')):
                            if f2.get(k): e[v] = f2[k]
                        extra.append(e)
                    if extra: s['fundos'] = extra; s['fxv'] = FX_VER
                    if s.get('zoom'): s['fxv'] = FX_VER
            out.append(s)
        return out

    def bgpath(self, key):
        sys.path.insert(0, HERE); from clips import find_bg
        return find_bg(f'{self.V}/img', key)

    def prepare(self):
        for t in ('frame.html', 'spy.html', 'thumb.html'): shutil.copy(f'{HERE}/templates/{t}', self.w(t))
        for t in ('shots.js', 'spyshots.js', 'clips.py', 'trans.py'): shutil.copy(f'{HERE}/{t}', self.w(t))
        ENV['POPDOCS_IMG'] = os.path.join(self.V, 'img')
        json.dump(self.resolved(), open(self.w('scenes.json'), 'w'), ensure_ascii=False)
        json.dump(self.meta(), open(self.w('meta.json'), 'w'), ensure_ascii=False)
        json.dump(self.cores(), open(self.w('cores.json'), 'w'), ensure_ascii=False)

    def cores(self):
        sys.path.insert(0, HERE); from deftrans import CORES_PADRAO
        return {**CORES_PADRAO, **{k: v for k, v in (self.cfg.get('cores') or {}).items() if v}}

    def meta(self):
        c = self.cfg
        m = {k: c.get(k, '') for k in ('brand', 'titleKick', 'title', 'subtitle', 'endTitle', 'endNote', 'endCredits', 'photoTag')}
        m['cores'] = self.cores(); return m

    def meta_of(self, t):
        """The video-wide texts one scene type really shows. Used in the cache key, so that editing the final
        credits only redraws the closing scene and editing the title only redraws the opening."""
        m = self.meta(); own = {'title': ('titleKick', 'title', 'subtitle'), 'end': ('endTitle', 'endNote', 'endCredits')}
        drop = [k for tt, ks in own.items() if tt != t for k in ks]
        return {k: v for k, v in m.items() if k not in drop}

    # ---------- 1b. draft narration with a free voice (no credits) ----------
    def tts_teste(self):
        try: import edge_tts, asyncio
        except ImportError: sys.exit('  ! falta o pacote edge-tts. Rode: pip install edge-tts')
        voice = self.cfg.get('voz_teste', 'pt-BR-AntonioNeural'); os.makedirs(self.w('aud'), exist_ok=True); os.makedirs(f'{self.V}/audio-teste', exist_ok=True)
        for i, s in enumerate(self.S):
            if not s.get('n'): continue
            key = H(s['n'], voice, 'edge-tts'); mp3 = f'{self.V}/audio-teste/{key}.mp3'
            if not os.path.exists(mp3):
                asyncio.run(edge_tts.Communicate(s['n'], voice).save(mp3 + '.part')); os.replace(mp3 + '.part', mp3)
                print(f'  voz de teste: cena {i}', flush=True)
            wav = self.w('aud', f'{i:02d}.wav')
            wk = f'{key}@{self.ritmo():.3f}'
            if self.hashes.get(f'wav{i:02d}') != wk or not os.path.exists(wav):
                run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp3, *self.tempo(), '-ac', '1', '-ar', str(SR), wav])
                self.hashes[f'wav{i:02d}'] = wk
        self.save_hashes()

    # ---------- 1. narration ----------
    def tts(self):
        if self.teste: return self.tts_teste()
        voice = self.cfg['voice_id']; model = self.cfg.get('voice_model', 'eleven_multilingual_v2')
        vs = self.cfg.get('voice_settings', {"stability": 0.5, "similarity_boost": 0.75})
        os.makedirs(self.w('aud'), exist_ok=True)
        for i, s in enumerate(self.S):
            if not s.get('n'): continue
            key = H(s['n'], voice, model, vs); mp3 = f'{self.V}/audio/{key}.mp3'   # cached by content: reordering scenes costs nothing
            if not os.path.exists(mp3):
                body = json.dumps({"text": s['n'], "model_id": model, "voice_settings": vs}).encode()
                r = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                                           data=body, headers={"Content-Type": "application/json", **({"xi-api-key": eleven_key()} if eleven_key() else {})})
                data = urllib.request.urlopen(r, timeout=180).read(); open(mp3 + '.part', 'wb').write(data); os.replace(mp3 + '.part', mp3)
                print(f'  voz gerada: cena {i} ({len(s["n"])} caracteres)', flush=True)
            wav = self.w('aud', f'{i:02d}.wav')
            wk = f'{key}@{self.ritmo():.3f}'
            if self.hashes.get(f'wav{i:02d}') != wk or not os.path.exists(wav):
                run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp3, *self.tempo(), '-ac', '1', '-ar', str(SR), wav])
                self.hashes[f'wav{i:02d}'] = wk
        self.save_hashes()

    def ritmo(self):
        """Narration speed ('ritmo_voz' in video.json, 1.0 = as recorded). Applied when the cached audio is converted,
        keeping the pitch, so changing it costs no credits."""
        try: return min(1.5, max(0.8, float(self.cfg.get('ritmo_voz') or 1)))
        except (TypeError, ValueError): return 1.0
    def tempo(self): return ['-filter:a', f'atempo={self.ritmo():.3f}'] if abs(self.ritmo() - 1) > 0.004 else []

    # ---------- 2. timing plan + narration track ----------
    def plan(self):
        sys.path.insert(0, HERE); from align import build_plan
        plan, narr = build_plan(self.S, self.w('aud'), SR)
        json.dump(plan, open(self.w('plan.json'), 'w'), ensure_ascii=False)
        if not self.teste or not os.path.exists(f'{self.V}/saidas/{self.slug}.mp4'):   # a draft only fills the Studio timings while there is no final video
            os.makedirs(f'{self.V}/previas', exist_ok=True); json.dump(plan, open(f'{self.V}/previas/plan.json', 'w'), ensure_ascii=False)
        sf.write(self.w('narr.wav'), narr, SR)
        total = plan[-1]['start'] + plan[-1]['dur']
        print(f'  duração total {total:.1f}s ({int(total//60)}min{int(total%60):02d}s), {sum(len(p["subs"]) for p in plan)} legendas')
        if not os.path.exists(f'{self.V}/transitions.json'):
            from deftrans import default_transitions
            json.dump(default_transitions(self.S, self.cfg), open(f'{self.V}/transitions.json', 'w'), ensure_ascii=False, indent=1)
            print('  transições padrão criadas')

    def scene_keys(self):
        P = json.load(open(self.w('plan.json'))); R = self.resolved()
        tpl = fhash(f'{HERE}/templates/frame.html')
        keys = []
        for i, s in enumerate(R):
            keys.append(H(s, P[i], tpl, self.meta_of(s['t']), fhash(self.bgpath(s['bg'])) if s.get('bg') else None))
        return keys

    # ---------- 3. still frames of each scene state + subtitles ----------
    def shots(self):
        self.prepare(); keys = self.scene_keys()
        todo = [i for i, k in enumerate(keys) if self.hashes.get(f'shot{i:02d}') != k or not os.path.exists(self.w('png', f'{i:02d}_0.png'))]
        if todo:
            run(['node', 'shots.js', *map(str, todo)], cwd=self.WD)
            for i in todo: self.hashes[f'shot{i:02d}'] = keys[i]
            self.save_hashes()
        print(f'  {len(todo)} cenas redesenhadas')

    # ---------- 4. one clip per scene ----------
    def clips(self):
        self.prepare(); keys = self.scene_keys()
        todo = [i for i, k in enumerate(keys) if self.hashes.get(f'clip{i:02d}') != k or not os.path.exists(self.w('clips', f'{i:02d}.mp4'))]
        if todo:
            run([sys.executable, 'clips.py', *map(str, todo)], cwd=self.WD)
            for i in todo: self.hashes[f'clip{i:02d}'] = keys[i]
            self.save_hashes()
        print(f'  {len(todo)} clipes renderizados')

    # ---------- 5. transitions + subtitles burned in ----------
    def trans(self):
        self.prepare()
        T = json.load(open(f'{self.V}/transitions.json'))
        json.dump(T, open(self.w('transitions.json'), 'w'), ensure_ascii=False)
        sys.path.insert(0, self.WD); os.chdir(self.WD)
        import importlib; tr = importlib.import_module('trans'); importlib.reload(tr)
        spyk = fhash(f'{HERE}/templates/spy.html')
        # overlays (spy transitions)
        spec = []
        for i, t in enumerate(T):
            if t['kind'] in tr.OVK:
                k = H(t, tr.half(i), spyk, self.cores())
                if self.hashes.get(f'ov{i:02d}') != k or not os.path.exists(self.w('ov', f'{i:02d}', '000.png')):
                    spec.append({'id': f'{i:02d}', 'kind': t['kind'], 'frames': 2 * tr.half(i), 'params': t.get('params', {}), '_k': k})
        if spec:
            for s in spec: shutil.rmtree(self.w('ov', s['id']), ignore_errors=True)
            json.dump(spec, open(self.w('ovspec.json'), 'w'), ensure_ascii=False)
            run(['node', 'spyshots.js', 'ovspec.json'], cwd=self.WD)
            for s in spec: self.hashes[f"ov{s['id']}"] = s['_k']
        # scenes whose clip, neighbours or boundary transitions changed
        n = len(self.S); todo = []
        for i in range(n):
            k = H(self.hashes.get(f'clip{i:02d}'), self.hashes.get(f'clip{i-1:02d}'), self.hashes.get(f'clip{i+1:02d}'),
                  T[i - 1] if i > 0 else None, T[i] if i < n - 1 else None,
                  self.hashes.get(f'ov{i-1:02d}'), self.hashes.get(f'ov{i:02d}'), fhash(f'{HERE}/trans.py'), self.cores())
            if self.hashes.get(f'tr{i:02d}') != k or not os.path.exists(self.w('trans', f'{i:02d}.mp4')): todo.append((i, k))
        if todo:
            run([sys.executable, 'trans.py', '--edges', *[str(i) for i, _ in todo]], cwd=self.WD)
            for i, k in todo: self.hashes[f'tr{i:02d}'] = k
        self.save_hashes()
        print(f'  {len(todo)} cenas com transição refeitas')

    def music_loop(self, file, length, out):
        """Repeat one music file (4 s crossfade between repeats) to `length` seconds."""
        src = file if os.path.isabs(file) else f"{self.V}/{file}"
        ln = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
        loops = int(length // (ln - 4)) + 1
        ins = sum([['-i', src] for _ in range(loops)], [])
        if loops == 1: fc = '[0]'
        else:
            fc = ''; cur = '[0]'
            for k in range(1, loops):
                nxt = f'[x{k}]'; fc += f'{cur}[{k}]acrossfade=d=4{nxt};'; cur = nxt
            fc += cur
        fc += f'atrim=0:{length}[m]'
        run(['ffmpeg', '-loglevel', 'error', '-y', *ins, '-filter_complex', fc, '-map', '[m]', '-ar', '48000', '-ac', '2', out])
        return out

    # ---------- 6. final mix ----------
    def mix(self):
        P = json.load(open(self.w('plan.json'))); total = P[-1]['start'] + P[-1]['dur']
        open(self.w('trans', 'list.txt'), 'w').write(''.join(f"file '{i:02d}.mp4'\n" for i in range(len(self.S))))
        run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', self.w('trans', 'list.txt'), '-c', 'copy', self.w('video.mp4')])
        # music: one track for the whole video ('music'), or one per section ('musicas': [{cena, file, credit}], cena = first scene, 1-based)
        segs = self.cfg.get('musicas') or [dict(self.cfg['music'], cena=1)]
        starts = [P[s['cena'] - 1]['start'] if s.get('cena', 1) > 1 else 0 for s in segs]; ends = starts[1:] + [total]
        parts = []
        for k, s in enumerate(segs):   # each section is longer by the 3 s crossfade, so every change starts exactly on its scene
            parts.append(self.music_loop(s['file'], ends[k] - starts[k] + (3 if k < len(segs) - 1 else 0), self.w(f'music_part{k}.wav')))
        ins = sum([['-i', p] for p in parts], []); fc = '[0]'
        if len(parts) > 1:
            fc = ''; cur = '[0]'
            for k in range(1, len(parts)):
                nxt = f'[y{k}]'; fc += f'{cur}[{k}]acrossfade=d=3{nxt};'; cur = nxt
            fc += cur
        fc += f'atrim=0:{total},afade=t=in:d=2,afade=t=out:st={total-7}:d=7[m]'
        run(['ffmpeg', '-loglevel', 'error', '-y', *ins, '-filter_complex', fc, '-map', '[m]', '-ar', '48000', '-ac', '2', self.w('music_bed.wav')])
        cites = self.cite_track(P, total)   # original sound of 'clip' scenes; music goes to zero under them
        vol = self.cfg.get('music_volume', 0.20)
        out = f"{self.V}/saidas/{self.out}.mp4"
        run(['ffmpeg', '-loglevel', 'error', '-y', '-i', self.w('video.mp4'), '-i', self.w('narr.wav'), '-i', self.w('music_bed.wav'), *(['-i', cites] if cites else []), '-filter_complex',
             f"[1:a]aresample=48000,loudnorm=I={float(self.cfg.get('lufs', -14))}:TP=-1.5:LRA=11,aformat=channel_layouts=stereo,apad,asplit=2[n][sc];[2:a]volume={vol}[mu];"
             "[mu][sc]sidechaincompress=threshold=0.02:ratio=5:attack=40:release=700:makeup=1[duck];"
             + ("[3:a]aformat=sample_rates=48000:channel_layouts=stereo,apad[ct];[n][duck][ct]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[a]" if cites else
                "[n][duck]amix=inputs=2:normalize=0:duration=shortest,alimiter=limit=0.95[a]"),
             '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.2f}', '-movflags', '+faststart', out])
        print('  vídeo final:', out)

    def cite_track(self, P, total):
        """Scenes of type 'clip' keep the clip's own sound (field "som": false turns it off).
        Builds cites.wav with those sounds at their place in the timeline and silences the music bed under them."""
        R = self.resolved(); SRM = 48000; spans = []
        track = np.zeros((int(total * SRM) + SRM, 2), np.float32)
        for i, s in enumerate(R):
            if s['t'] != 'clip' or not s.get('bg') or s.get('som') is False: continue
            src = self.bgpath(s['bg']); a0 = P[i]['start']; d = P[i]['dur']; wav = self.w(f'cite{i:02d}.wav')
            run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(float(s.get('vin', 0) or 0)), '-t', f'{d:.2f}', '-i', src, '-vn',
                 '-af', f"loudnorm=I=-16:TP=-1.5:LRA=11,volume={float(s.get('vol', 1.0))},afade=t=in:d=0.15,afade=t=out:st={max(0, d - 0.3):.2f}:d=0.3",
                 '-ar', str(SRM), '-ac', '2', wav])
            if not os.path.exists(wav) or os.path.getsize(wav) < 1000: print(f'  ! cena {i}: o vídeo não tem som'); continue
            x, _ = sf.read(wav, dtype='float32', always_2d=True); k = int(a0 * SRM); x = x[:len(track) - k]
            track[k:k + len(x)] += x; spans.append((a0, a0 + d))
        if not spans: return None
        m, msr = sf.read(self.w('music_bed.wav'), dtype='float32', always_2d=True)
        t = np.arange(len(m)) / msr; env = np.ones(len(m), np.float32); ramp = 0.6
        for a, b in spans:
            g = np.clip(np.maximum((a - t) / ramp, (t - b) / ramp), 0, 1); env = np.minimum(env, g)
        sf.write(self.w('music_bed.wav'), m * env[:, None], msr)
        sf.write(self.w('cites.wav'), track[:int(total * SRM)], SRM)
        print(f'  {len(spans)} trecho(s) com som original; música zerada embaixo'); return self.w('cites.wav')

    def celular(self):
        """A light copy of the final video for phones and messaging apps (540p, small file)."""
        src = f"{self.V}/saidas/{self.out}.mp4"; out = f"{self.V}/saidas/{self.out}-celular.mp4"
        if not os.path.exists(src): sys.exit('  ! renderize o vídeo antes de fazer a cópia para celular')
        run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-vf', 'scale=-2:540', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '30',
             '-c:a', 'aac', '-b:a', '64k', '-ac', '1', '-movflags', '+faststart', out])
        print(f'  cópia para celular: {out} ({os.path.getsize(out) / 1e6:.1f} MB)')

    def srt(self):
        P = json.load(open(self.w('plan.json')))
        def ts(t):
            ms = int(round(t * 1000)); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
        out = []; k = 0
        for s in P:
            for a, b, t in s['subs']:
                k += 1; out.append(f"{k}\n{ts(s['start']+a)} --> {ts(s['start']+b)}\n{t}\n")
        open(f"{self.V}/saidas/{self.slug}-legendas.srt", 'w').write("\n".join(out)); print('  legendas:', k)

    def thumb(self):
        import cv2
        T = dict(self.cfg.get('thumb', {}))
        if not T.get('photo'): print('  sem foto de thumbnail em video.json'); return
        sys.path.insert(0, HERE); from clips import treat, still
        src = self.bgpath(T['photo'])
        if not src: print(f"  ! foto da thumbnail \"{T['photo']}\" não encontrada"); return
        im = still(src, float(T.get('t', 1.0))); h, w = im.shape[:2]
        cx = float(T.get('face_x', 0.5)); cw = int(min(w, h * 0.62 * 0.95)); x0 = int(max(0, min(w - cw, cx * w - cw / 2)))
        cv2.imwrite(self.w('thumb_face.png'), treat(im[0:int(h * 0.95), x0:x0 + cw], self.cores(), clahe=2.0, modo=self.fotos.get(T['photo'], {}).get('modo')))
        T['photo'] = 'thumb_face.png'; T['cores'] = self.cores(); shutil.copy(f'{HERE}/templates/thumb.html', self.w('thumb.html'))
        js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720}});"
              "await p.goto(require('url').pathToFileURL(require('path').join(process.cwd(),'thumb.html')).href);await p.evaluate(T=>window.setT(T)," + json.dumps(T, ensure_ascii=False) + ");"
              "await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);await p.locator('#t').screenshot({path:'thumb.png'});await b.close()})();")
        open(self.w('thumbshot.js'), 'w').write(js); run(['node', 'thumbshot.js'], cwd=self.WD)
        im = cv2.imread(self.w('thumb.png')); cv2.imwrite(f"{self.V}/saidas/{self.slug}-thumbnail.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print('  thumbnail pronta')

    # ---------- 9. small previews for the Studio ----------
    def previas(self):
        import cv2
        os.makedirs(f'{self.V}/previas', exist_ok=True)
        for i in range(len(self.S) if not self.teste or not os.path.exists(f'{self.V}/saidas/{self.slug}.mp4') else 0):   # a draft never replaces the previews of the final video
            p = self.w('edges', f'{i:02d}_last.png')
            if os.path.exists(p):
                cv2.imwrite(f'{self.V}/previas/cena-{i:02d}.jpg', cv2.resize(cv2.imread(p), (480, 270), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 80])
        sys.path.insert(0, HERE); from clips import still, IMG_EXT, VID_EXT
        for f in os.listdir(f'{self.V}/img'):
            key, ext = os.path.splitext(f)
            if ext.lower() not in IMG_EXT + VID_EXT: continue
            out = f'{self.V}/previas/foto-{key}.jpg'
            if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(f'{self.V}/img/{f}'): continue
            im = still(f'{self.V}/img/{f}')
            if im is None: continue
            h, w = im.shape[:2]
            cv2.imwrite(out, cv2.resize(im, (480, int(480 * h / w)), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print('  prévias atualizadas')

if __name__ == '__main__':
    if not sys.flags.utf8_mode:  # Windows opens files as cp1252 by default; the project files are UTF-8
        sys.exit(subprocess.call([sys.executable, '-X', 'utf8'] + sys.argv))
    args = [a for a in sys.argv[2:] if a != '--teste']; teste = '--teste' in sys.argv
    v = Video(sys.argv[1], teste=teste)
    steps = args or (['tts', 'plan', 'shots', 'clips', 'trans', 'mix', 'previas'] if teste else STEPS)
    print(f'== passos: {" ".join(steps)}', flush=True)
    for st in steps:
        print(f'== {st}', flush=True); getattr(v, st)()
