"""Short-resumo: junta frases da narração de um episódio já renderizado (cenas do work dir do motor, sem legenda embutida)
na ordem do roteiro, com música contínua. Depois rode vertical.py.  Não gera voz nova: só corta o que já existe.
uso: python -X utf8 shorts/resumo.py <nome>"""
import json, os, sys, subprocess, tempfile, shutil
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# trechos: (cena como no Estúdio, primeira legenda, última legenda) — legendas numeradas a partir de 0 dentro da cena (plan.json)
RESUMOS = {
    'diesel-resumo': dict(ep='diesel', titulo='RUDOLF DIESEL', nota='Se você precisa de ajuda, ligue 188 (CVV) ou acesse cvv.org.br',
        trechos=[(1, 0, 2), (2, 2, 2), (3, 0, 2), (4, 0, 0), (45, 1, 2), (47, 1, 1), (48, 0, 1), (50, 0, 1), (52, 0, 1), (60, 2, 2)]),
    'eastman-resumo': dict(ep='eastman', titulo='GEORGE EASTMAN', nota='',
        trechos=[(4, 0, 3), (29, 0, 1), (53, 0, 1), (55, 0, 2), (56, 0, 2), (57, 0, 0), (59, 0, 1), (65, 0, 2)]),
}
nome = sys.argv[1]; c = RESUMOS[nome]; ep = c['ep']
WD = os.path.join(tempfile.gettempdir(), 'popdocs-work', ep); V = os.path.join(R, 'videos', ep)
P = json.load(open(f'{WD}/plan.json', encoding='utf8')); cfg = json.load(open(f'{V}/video.json', encoding='utf8'))
D = os.path.join(R, 'shorts', nome); T = os.path.join(D, 'tmp'); os.makedirs(T, exist_ok=True); os.makedirs(f'{D}/saidas', exist_ok=True)
segs = []; subs = []; t = 0.0
for k, (cena, a, b) in enumerate(c['trechos']):
    p = P[cena - 1]; s = p['subs']
    t0 = max(0, s[a][0] - 0.15); t1 = min(p['dur'], s[b][1] + 0.35)
    seg = f'{T}/{k:02d}.mp4'; d = t1 - t0
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', f'{t0:.3f}', '-t', f'{d:.3f}', '-i', f'{WD}/clips/{cena - 1:02d}.mp4',
                    '-ss', f'{p["start"] + t0:.3f}', '-t', f'{d:.3f}', '-i', f'{WD}/narr.wav',
                    '-map', '0:v', '-map', '1:a', '-vf', 'fade=in:d=0.2,fade=out:st=%.3f:d=0.2' % (d - 0.2), '-af', 'afade=in:d=0.05,afade=out:st=%.3f:d=0.1' % (d - 0.1),
                    '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '1', seg.replace('.mp4', '.mkv')], check=True)
    for m in range(a, b + 1): subs.append((t + s[m][0] - t0, t + min(s[m][1], t1) - t0, s[m][2]))
    segs.append(seg.replace('.mp4', '.mkv')); t += d
open(f'{T}/list.txt', 'w').write(''.join(f"file '{x}'\n" for x in segs))
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{T}/list.txt', '-c', 'copy', f'{T}/junto.mkv'], check=True)
mus = (cfg.get('musicas') or [cfg['music']])[0]['file']; vol = cfg.get('music_volume', 0.2)
out = f'{D}/saidas/{nome}.mp4'
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f'{T}/junto.mkv', '-stream_loop', '-1', '-i', f'{V}/{mus}', '-filter_complex',
    f"[0:a]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11,aformat=channel_layouts=stereo,asplit=2[n][sc];"
    f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{t:.2f},afade=t=in:d=1.5,afade=t=out:st={t - 3:.2f}:d=3,volume={vol}[mu];"
    "[mu][sc]sidechaincompress=threshold=0.02:ratio=5:attack=40:release=700:makeup=1[duck];[n][duck]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]",
    '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-t', f'{t:.2f}', '-movflags', '+faststart', out], check=True)
def ts(x): ms = int(round(x * 1000)); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
open(f'{D}/saidas/{nome}-legendas.srt', 'w', encoding='utf8').write('\n'.join(f'{k+1}\n{ts(a)} --> {ts(b)}\n{x}\n' for k, (a, b, x) in enumerate(subs)))
json.dump(dict(cfg, slug=nome), open(f'{D}/video.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(dict(episodio=ep, kicker='POPDOCSBRASIL · DOSSIÊ', titulo=c['titulo'], nota=c['nota']), open(f'{D}/short.json', 'w', encoding='utf8'), ensure_ascii=False)
shutil.rmtree(T); print(nome, f'{t:.1f}s de narração,', len(subs), 'legendas ->', out)
