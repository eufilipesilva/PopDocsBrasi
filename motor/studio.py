#!/usr/bin/env python3
"""Bridge between a video folder and the Estúdio (its database documents).
Used by the Claude flow (ArtifactData batches) and by the local Studio (estudio_local/servidor.py).

  python3 studio.py export <video_dir> <out_dir> [assets.json]
      -> out_dir/batch_N.json : ArtifactData batch writes (videos/<slug>, scenes, fotos)
         assets.json maps preview files to uploaded asset URLs: {"scene:00": url, "foto:ktli": url, "thumb": url}
  python3 studio.py import <video_dir> <dump_dir>
      dump_dir is an ArtifactData out_dir dump (videos/<slug>.json, videos/<slug>/scenes/*.json, videos/<slug>/fotos/*.json).
      Rewrites scenes.json, transitions.json, fotos.json and the editable parts of video.json; prints what changed.
"""
import json, os, sys, glob, shutil, time, tempfile

META_KEYS = ('t', 'n', 'bg', 'dur', 'pre', 'post')
VIDEO_EDIT = ('title', 'subtitle', 'titleKick', 'brand', 'archive', 'photoTag', 'endTitle', 'endNote', 'endCredits', 'music_volume', 'thumb', 'cores', 'music', 'musicas', 'checagem', 'ambiente', 'ritmo_voz', 'gancho')

def jload(p, default=None):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default

def jsave(obj, p):
    json.dump(obj, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def work_dir(cfg):
    return os.environ.get('POPDOCS_WORK', os.path.join(tempfile.gettempdir(), 'popdocs-work', cfg['slug']))

def keep_order(new, old):
    """`new` with its keys in the order they have in `old` (new keys go last), so that saving does not shuffle the files."""
    if not isinstance(old, dict): return new
    return {**{k: new[k] for k in old if k in new}, **{k: v for k, v in new.items() if k not in old}}

def files_to_docs(V, thumb_of=None):
    """Video folder -> (video doc, [(scene id, scene doc)], {foto key: foto doc}).
    thumb_of(kind, key) returns the preview URL for 'scene' (key = index), 'foto' (key = foto key) or 'thumb'."""
    thumb_of = thumb_of or (lambda kind, key: '')
    cfg = jload(f'{V}/video.json'); S = jload(f'{V}/scenes.json', [])
    T = jload(f'{V}/transitions.json', []); F = jload(f'{V}/fotos.json', {})
    plan = jload(os.path.join(work_dir(cfg), 'plan.json')) or jload(f'{V}/previas/plan.json')
    vdoc = dict(cfg)
    vdoc.update(thumbUrl=thumb_of('thumb', None), render={'requested': False, 'at': cfg.get('renderedAt', '')}, dirty=False,
                createdAt=cfg.get('createdAt', time.strftime('%Y-%m-%dT%H:%M:%S')))
    scenes = []
    for i, s in enumerate(S):
        d = {'t': s['t'], 'n': s.get('n', ''), 'bg': s.get('bg', ''), 'order': i, 'f': {k: v for k, v in s.items() if k not in META_KEYS},
             'trans': {k: v for k, v in (T[i] if i < len(T) else {}).items() if k in ('kind', 'dur', 'params')},
             'thumb': thumb_of('scene', i), 'dirty': False, 'deleted': False}
        if not s.get('n'): d['f']['dur'] = s.get('dur', 5)
        for k in ('pre', 'post'):
            if k in s: d[k] = s[k]
        if plan and i < len(plan): d['start'] = round(plan[i]['start'], 2); d['len'] = plan[i]['dur']
        scenes.append((f's{i:03d}', d))
    fotos = {k: {**f, 'thumb': thumb_of('foto', k), 'origin': f.get('origin', 'commons'), 'dirty': False} for k, f in F.items()}
    return vdoc, scenes, fotos

def docs_to_files(V, vdoc, scene_docs, foto_docs):
    """Studio documents -> video folder files. Keeps a copy of the previous files in historico/. Returns a list of changes."""
    cfg = jload(f'{V}/video.json')
    live = sorted([d for d in scene_docs.values() if not d.get('deleted')], key=lambda d: d.get('order', 0))
    S, T = [], []
    for d in live:
        s = {'t': d['t']}; s.update(d.get('f') or {})
        s['n'] = d.get('n', '')
        if d.get('bg'): s['bg'] = d['bg']
        if s['n']: s.pop('dur', None)
        for k in ('pre', 'post'):
            if k in d: s[k] = d[k]
        S.append(s)
        T.append({k: v for k, v in (d.get('trans') or {'kind': 'zoom'}).items() if k in ('kind', 'dur', 'params')})
    T = T[:-1]
    for i, t in enumerate(T): t.setdefault('params', {}); t['from'] = i; t['to'] = i + 1
    F = jload(f'{V}/fotos.json', {})
    for k, f in foto_docs.items():
        new = k not in F; F.setdefault(k, {})
        F[k].update({x: f[x] for x in ('cap', 'credit', 'license', 'source', 'asset', 'origin', 'modo', 'tipo', 'foco', 'enquadrar', 'recorte')
                     if x in f and not (x == 'origin' and not new and 'origin' not in F[k] and f[x] == 'commons')})   # 'commons' is only the Studio's default
        for x in ('modo', 'foco', 'enquadrar', 'recorte'):   # empty value = back to the default
            if x in F[k] and F[k][x] in ('', None, []): del F[k][x]
    old = {n: jload(f'{V}/{n}') for n in ('scenes.json', 'transitions.json', 'fotos.json', 'video.json') if os.path.exists(f'{V}/{n}')}
    new_cfg = dict(cfg)
    for k in VIDEO_EDIT:
        if k in vdoc: new_cfg[k] = vdoc[k]
    if not new_cfg.get('musicas'): new_cfg.pop('musicas', None)
    if not new_cfg.get('ambiente'): new_cfg.pop('ambiente', None)
    if abs(float(new_cfg.get('ritmo_voz') or 1) - 1) < 0.005: new_cfg.pop('ritmo_voz', None)   # empty list = one track for the whole video
    oS = old.get('scenes.json') or []; oT = old.get('transitions.json') or []
    S = [next((o for o in oS if o == x), None) or keep_order(x, oS[i] if i < len(oS) else None) for i, x in enumerate(S)]   # same key order as on disk
    T = [keep_order(t, oT[i] if i < len(oT) else {'from': 0, 'to': 0}) for i, t in enumerate(T)]
    new = {'scenes.json': S, 'transitions.json': T, 'fotos.json': F, 'video.json': new_cfg}
    changed = [n for n in new if old.get(n) != new[n]]
    if not changed: return []
    stamp = time.strftime('%Y%m%d-%H%M%S'); os.makedirs(f'{V}/historico/{stamp}', exist_ok=True)
    for n in old: shutil.copy(f'{V}/{n}', f'{V}/historico/{stamp}/{n}')
    for d in sorted(os.listdir(f'{V}/historico'))[:-30]: shutil.rmtree(f'{V}/historico/{d}', ignore_errors=True)  # keep the last 30
    for n in changed: jsave(new[n], f'{V}/{n}')   # only the files that really changed
    ch = []
    if len(oS) != len(S): ch.append(f'número de cenas {len(oS)} -> {len(S)}')
    for i, s in enumerate(S):
        if i < len(oS) and s != oS[i]:
            ch.append(f'cena {i+1}: ' + ', '.join(sorted(k for k in set(s) | set(oS[i]) if s.get(k) != oS[i].get(k))))
    for i, t in enumerate(T):
        if i < len(oT) and {k: t.get(k) for k in ('kind', 'dur', 'params')} != {k: oT[i].get(k) for k in ('kind', 'dur', 'params')}:
            ch.append(f'transição {i+1}->{i+2}: {oT[i].get("kind")} -> {t.get("kind")}')
    if old.get('video.json') and any(old['video.json'].get(k) != new_cfg.get(k) for k in VIDEO_EDIT): ch.append('configurações do vídeo')
    return ch

def export(V, out, assets_path=None):
    A = jload(assets_path, {}) if assets_path else {}
    def thumb_of(kind, key):
        return A.get('thumb', '') if kind == 'thumb' else A.get(f'scene:{key:02d}' if kind == 'scene' else f'foto:{key}', '')
    vdoc, scenes, fotos = files_to_docs(V, thumb_of); slug = vdoc['slug']
    writes = [{'op': 'set', 'collection': 'videos', 'doc_id': slug, 'data': vdoc}]
    writes += [{'op': 'set', 'collection': f'videos/{slug}/scenes', 'doc_id': i, 'data': d} for i, d in scenes]
    writes += [{'op': 'set', 'collection': f'videos/{slug}/fotos', 'doc_id': k, 'data': d} for k, d in fotos.items()]
    os.makedirs(out, exist_ok=True)
    for n in range(0, len(writes), 45): jsave(writes[n:n + 45], f'{out}/batch_{n // 45}.json')
    print(len(writes), 'writes in', (len(writes) + 44) // 45, 'batches')

def load_dump(D, rel):
    out = {}
    for p in glob.glob(f'{D}/{rel}/*.json'):
        d = jload(p)
        if isinstance(d, dict) and isinstance(d.get('data'), dict): d = d['data']
        out[os.path.basename(p)[:-5]] = d
    return out

def imp(V, D):
    slug = jload(f'{V}/video.json')['slug']
    ch = docs_to_files(V, load_dump(D, 'videos').get(slug, {}), load_dump(D, f'videos/{slug}/scenes'), load_dump(D, f'videos/{slug}/fotos'))
    F = jload(f'{V}/fotos.json', {})
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from clips import find_bg
    up = {k: {'asset': f.get('asset'), 'salvar_como': f'img/{k}.' + ('mp4' if f.get('tipo') == 'video' else 'jpg')} for k, f in F.items() if f.get('origin') == 'upload' and not find_bg(f'{V}/img', k)}
    print(json.dumps({'changes': ch, 'uploads_to_fetch': up}, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    if sys.argv[1] == 'export': export(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif sys.argv[1] == 'import': imp(sys.argv[2], sys.argv[3])
