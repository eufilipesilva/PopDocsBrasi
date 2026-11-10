"""Timing plan: scene durations (narration + pauses), reveal steps at sentence pauses, subtitle chunks."""
import re, numpy as np, soundfile as sf
def sents(t): return [x.strip() for x in re.split(r'(?<=[.?!:])\s+', t) if x.strip()]
def chunks(s, maxc=80):
    out = []; cur = ''
    for x in s.split():
        if len(cur) + len(x) + 1 > maxc and cur: out.append(cur); cur = x
        else: cur = (cur + ' ' + x).strip()
    out.append(cur); return out
def wrap2(c, lim=44):
    if len(c) <= lim: return c
    w = c.split(); best = None
    for k in range(1, len(w)):
        a, b = ' '.join(w[:k]), ' '.join(w[k:]); m = max(len(a), len(b))
        if best is None or m < best[0]: best = (m, a + '\n' + b)
    return best[1]
def pads(s):
    pre, post = (0.9, 1.0) if s['t'] in ('chapter', 'title', 'end') else (0.4, 0.6)
    if s['t'] == 'end': post = 4.0
    if s['t'] == 'clip': pre, post = 0.2, 0.2
    return s.get('pre', pre), s.get('post', post)
def build_plan(S, auddir, SR=24000):
    plan = []; t0 = 0; audio = []
    for i, s in enumerate(S):
        pre, post = pads(s)
        if s.get('n'):
            a = sf.read(f'{auddir}/{i:02d}.wav')[0]; nd = len(a) / SR
        else: a = None; nd = float(s.get('dur', 5))
        dur = round(pre + nd + post, 2); e = {"i": i, "start": t0, "dur": dur, "steps": [0.0], "subs": []}
        seg = np.concatenate([np.zeros(int(pre * SR)), a if a is not None else np.zeros(int(nd * SR)), np.zeros(int(post * SR))])
        audio.append(np.pad(seg, (0, max(0, int(round(dur * SR)) - len(seg))))[:int(round(dur * SR))])
        if a is not None:
            ss = sents(s['n']); fl = int(0.02 * SR); n = len(a) // fl
            rms = np.sqrt(np.mean(a[:n * fl].reshape(n, fl) ** 2, axis=1) + 1e-12); db = 20 * np.log10(rms / (rms.max() + 1e-9))
            sil = db < -35; runs = []; k = 0
            while k < n:
                if sil[k]:
                    j = k
                    while j < n and sil[j]: j += 1
                    if (j - k) * 0.02 >= 0.16 and k > 0 and j < n: runs.append(((k + j) / 2 * 0.02, (j - k) * 0.02))
                    k = j
                else: k += 1
            L = [len(x) for x in ss]; cum = np.cumsum(L) / sum(L); bounds = []; last = 0
            for c in cum[:-1]:
                est = c * nd; cand = [r for r in runs if r[0] > last + 0.3]
                b = min(cand, key=lambda r: abs(r[0] - est) - 0.3 * r[1])[0] if cand else est
                bounds.append(b); last = b
            edges = [0] + bounds + [nd]
            for k, x in enumerate(ss):
                a0, a1 = edges[k], edges[k + 1]
                if k > 0: e["steps"].append(pre + a0)
                cs = chunks(x); cl = np.cumsum([0] + [len(c) for c in cs]); tot = cl[-1]
                for m, c in enumerate(cs):
                    e["subs"].append([round(pre + a0 + (a1 - a0) * cl[m] / tot, 2), round(pre + a0 + (a1 - a0) * cl[m + 1] / tot, 2), wrap2(c)])
        plan.append(e); t0 += dur
    return plan, np.concatenate(audio)
