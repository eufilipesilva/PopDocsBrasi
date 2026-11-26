"""Transforma um Short renderizado pelo motor (16:9) em vídeo vertical 9:16 (1080x1920) com legenda, cabeçalho e cartão final.
uso: python -X utf8 shorts/vertical.py shorts/<pasta>"""
import json, os, re, subprocess, sys, html
D = os.path.abspath(sys.argv[1]); HERE = os.path.dirname(os.path.abspath(__file__)); MOTOR = os.path.join(os.path.dirname(HERE), 'motor')
cfg = json.load(open(f'{D}/video.json')); slug = cfg['slug']; ep = json.load(open(f'{D}/short.json'))
SUF = sys.argv[2] if len(sys.argv) > 2 else ''   # '-TESTE' para o rascunho com voz grátis
src = f'{D}/saidas/{slug}{SUF}.mp4'; WD = f'{D}/vert'; os.makedirs(WD, exist_ok=True)
END = 3.5   # segundos do cartão final
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
def t(s): h, m, rest = s.split(':'); sec, ms = rest.split(','); return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
subs = []
for blk in open(f'{D}/saidas/{slug}-legendas.srt', encoding='utf8').read().strip().split('\n\n'):
    ln = blk.split('\n'); a, b = ln[1].split(' --> '); subs.append((t(a), t(b), ' '.join(ln[2:])))
NOTA = ('<div style="font-family:IBM Plex Mono,monospace;font-size:26px;line-height:1.4;margin-top:60px;opacity:.85">' + html.escape(ep['nota']) + '</div>') if ep.get('nota') else ''
FONT = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=IBM+Plex+Mono:wght@500&display=swap">'
BASE = FONT + '<style>*{box-sizing:border-box;margin:0}body{background:transparent;color:#F2F2F2;font-family:Oswald,sans-serif}</style>'
items = [dict(w=1080, h=700, out=f"{WD}/head.png", html=BASE + f'''
<div style="position:absolute;left:0;right:0;top:330px;text-align:center">
 <div style="font-family:'IBM Plex Mono',monospace;font-size:30px;letter-spacing:6px;opacity:.85">{html.escape(ep['kicker'])}</div>
 <div style="font-weight:700;font-size:104px;line-height:1.05;letter-spacing:2px;margin-top:14px">{html.escape(ep['titulo'])}</div>
 <div style="width:120px;height:4px;background:#F2F2F2;margin:22px auto 0"></div></div>'''),
 dict(w=1080, h=1920, out=f'{WD}/fim.png', html=BASE + f'''
<div style="position:absolute;inset:0;background:rgba(11,11,11,.86)"></div>
<div style="position:absolute;left:80px;right:80px;top:640px;text-align:center">
 <div style="font-family:'IBM Plex Mono',monospace;font-size:32px;letter-spacing:6px;opacity:.85">O DOSSIÊ COMPLETO</div>
 <div style="font-weight:700;font-size:130px;line-height:1.18;margin-top:26px">{html.escape(cfg['title'])}</div>
 <div style="font-weight:500;font-size:46px;line-height:1.2;margin-top:24px">{html.escape(cfg['subtitle'])}</div>
 <div style="width:120px;height:4px;background:#F2F2F2;margin:40px auto"></div>
 <div style="font-weight:500;font-size:44px">no canal <b>PopDocsBrasil</b></div>
 {NOTA}</div>''')]
for k, (a, b, s) in enumerate(subs):
    items.append(dict(w=1080, h=300, out=f'{WD}/sub{k:02d}.png', html=BASE + f'''
<div style="position:absolute;left:70px;right:70px;top:0;height:300px;display:flex;align-items:flex-start;justify-content:center;text-align:center">
<span style="font-weight:500;font-size:60px;line-height:1.22;text-shadow:0 3px 12px #000,0 0 4px #000">{html.escape(s)}</span></div>'''))
json.dump(items, open(f'{WD}/lista.json', 'w', encoding='utf8'), ensure_ascii=False)
subprocess.run(['node', os.path.join(HERE, 'png.js'), f'{WD}/lista.json'], check=True, env=dict(os.environ, NODE_PATH=os.path.join(MOTOR, 'node_modules')))
VY = 700   # topo do quadro 16:9
fc = (f"[0:v]tpad=stop_mode=clone:stop_duration={END},split[a][b];"
      "[a]scale=-2:1920,crop=1080:1920,boxblur=40:2,eq=brightness=-0.25[bg];"
      f"[b]scale=1080:-2[fg];[bg][fg]overlay=0:{VY}[v0];[v0][1:v]overlay=0:0[v1]")
ins = ['-i', src, '-loop', '1', '-i', f'{WD}/head.png']; cur = 'v1'; n = 2
for k, (a, b, s) in enumerate(subs):
    ins += ['-loop', '1', '-i', f'{WD}/sub{k:02d}.png']
    fc += f";[{cur}][{n}:v]overlay=0:{VY + 608 + 60}:enable='between(t,{a:.3f},{min(b, dur):.3f})'[s{k}]"; cur = f's{k}'; n += 1
ins += ['-loop', '1', '-i', f'{WD}/fim.png']
fc += f";[{cur}][{n}:v]overlay=0:0:enable='gte(t,{dur:.3f})',format=yuv420p[v]"
fc += f";[0:a]apad=pad_dur={END}[au]"
os.makedirs(f'{D}/saidas', exist_ok=True); out = os.path.join(os.path.dirname(HERE), 'videos', ep['episodio'], 'saidas', 'shorts', f'{slug}{SUF}-vertical.mp4')
os.makedirs(os.path.dirname(out), exist_ok=True)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *ins, '-filter_complex', fc, '-map', '[v]', '-map', '[au]', '-t', f'{dur + END:.2f}',
                '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out], check=True)
print(out, f'{dur + END:.1f}s')
