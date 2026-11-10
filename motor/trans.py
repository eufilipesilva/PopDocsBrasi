"""Applies dossier-style transitions between clips_v4 scenes and overlays subtitles.
Timing is preserved: each transition is centred on the scene boundary, using the
neighbouring scene's edge frame (frozen) for the short overlap.
usage: python3 trans.py [indices]   -> clips_v5/NN.mp4 + list.txt"""
import json, subprocess, numpy as np, cv2, sys, os
from multiprocessing import Pool
FPS=30; W,H=1920,1080; IN='clips'; OUT='trans'
S=json.load(open('scenes.json')); P=json.load(open('plan.json'))
cum=np.array([p['start'] for p in P]+[P[-1]['start']+P[-1]['dur']]); fr=np.round(cum*FPS).astype(int)
os.makedirs(OUT,exist_ok=True); os.makedirs('edges',exist_ok=True)
HALF={'zoom':.2,'scan':.35,'paper':.3,'flash':.2,'whip':.25,'glitch':.25,'dissolve':.5,'cut':0,
      'redact':.4,'stamp':.5,'terminal':.85,'decrypt':.4,'cctv':.6,'folder':.7,
      'shred':.45,'pixel':.3,'static':.3,'enhance':.5,'vhs':.4,'radar':.6,'map':.8,'fingerprint':.65,'access':.8,'search':.8,'wiretap':.6}
OVK={'redact':.5,'stamp':.55,'terminal':.5,'decrypt':.5,'cctv':.5,'folder':.45,  # overlay kinds -> base switch point
     'static':.5,'enhance':.55,'vhs':.5,'radar':.5,'map':.5,'fingerprint':.5,'access':.5,'search':.5,'wiretap':.5}
def _hex(h,d):
    h=(h or d).lstrip('#'); h=h if len(h)==6 else d.lstrip('#'); return np.array([int(h[4:6],16),int(h[2:4],16),int(h[0:2],16)],np.float32)
C=json.load(open('cores.json')) if os.path.exists('cores.json') else {}
BG=_hex(C.get('fundo'),'#0B0B0B'); FG=_hex(C.get('texto'),'#F2F2F2'); AC=_hex(C.get('destaque') or C.get('texto'),'#F2F2F2')
BGT=tuple(float(x) for x in BG)
def params(i): return (TR[i].get('params') or {}) if TR else {}
def pixelate(img,b):
    b=int(b)
    if b<=1: return img
    sm=cv2.resize(img,(max(1,W//b),max(1,H//b)),interpolation=cv2.INTER_AREA)
    return cv2.resize(sm,(W,H),interpolation=cv2.INTER_NEAREST)
def pct(v,d):
    try: return float(v)/100
    except (TypeError,ValueError): return d
TR=json.load(open('transitions.json')) if os.path.exists('transitions.json') else None
def kind(i):
    if TR: return TR[i]['kind']
    return kind_rules(i)
def half(i):
    t=TR[i] if TR else {}
    h=int(round(float(t.get('dur',2*HALF[kind(i)]))/2*FPS))
    return min(h,(fr[i+1]-fr[i])//2,(fr[i+2]-fr[i+1])//2)
def kind_rules(i): return 'zoom'
ease=lambda p:p*p*(3-2*p)
def zoom(img,z,cx=W/2,cy=H/2):
    M=np.array([[z,0,cx*(1-z)],[0,z,cy*(1-z)]],np.float32)
    return cv2.warpAffine(img,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
def grade(img,w,g):
    if w<=0: return img
    gr=cv2.cvtColor(np.clip(img,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
    gr=np.clip((gr-128)*1.25+118,0,255); gr=cv2.GaussianBlur(gr,(0,0),1.1)
    gr=gr+np.random.default_rng(g).normal(0,14,gr.shape).astype(np.float32)
    return img*(1-w)+np.dstack([gr]*3)*w
def T(k,A,B,p,g,ov=None,P=None):
    e=ease(p); P=P or {}
    if k in OVK:
        sw=OVK[k]; base=A if p<sw else B
        amp=np.sin(np.pi*p)
        if k=='static':
            rng=np.random.default_rng(g); a=min(1,amp**0.6*1.15)
            nz=rng.uniform(0,255,(H//3+1,W//3+1)).astype(np.float32); nz=cv2.resize(nz,(W,H),interpolation=cv2.INTER_NEAREST)
            nz=np.dstack([nz]*3); nz=nz+np.roll(np.linspace(0,60,H,dtype=np.float32),int(p*H*3))[:,None,None]
            base=base*(1-a*.92)+nz*(a*.92)
        if k=='enhance':
            cx=W*pct(P.get('x'),.5); cy=H*pct(P.get('y'),.5)
            if p<sw: q=ease(min(1,max(0,(p-.15)/.4))); base=pixelate(zoom(A,1+3*q,cx,cy),1+18*q)
            else: q=ease(min(1,(p-sw)/.3)); base=pixelate(zoom(B,1+.12*(1-q)),1+24*(1-q))
        if k=='vhs':
            rng=np.random.default_rng(g); a=amp; o=base.copy()
            y0=int((p*1.6%1)*H); hb=int(60+120*a)
            for y in range(max(0,y0-hb),min(H,y0+hb),6): o[y:y+6]=np.roll(o[y:y+6],int(rng.normal(0,60*a)),axis=1)
            sh=int(10*a)+1; o[:,:,2]=np.roll(o[:,:,2],sh,axis=1); o[:,:,0]=np.roll(o[:,:,0],-sh,axis=1)
            gray=cv2.cvtColor(np.clip(o,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
            o=o*(1-.35*a)+np.dstack([gray]*3)*(.35*a)
            o=np.roll(o,int(rng.integers(-3,4)*a),axis=0)
            o=o+(rng.random(H)<0.05*a)[:,None,None]*rng.uniform(30,90)
            base=o
        if k in ('radar','fingerprint','wiretap'):
            base=zoom(base,1+0.03*amp)
        if k=='stamp' and .27<p<.4:
            r=np.random.default_rng(g); base=cv2.warpAffine(base,np.float32([[1,0,r.integers(-9,10)],[0,1,r.integers(-9,10)]]),(W,H),borderMode=cv2.BORDER_REPLICATE)
        if k=='cctv':
            w=min(1,p/0.1,(1-p)/0.25); base=grade(zoom(base,1+0.04*(p if p<sw else 1-p)),w,g)
        if ov is not None:
            rgb,a=ov; base=base*(1-a)+rgb*a
        return base
    if k=='cut': return A if p<.5 else B
    if k=='zoom':  # push in and dip: A pushes in and darkens, B settles from a slight zoom; no text ghosting
        if p<.5: q=ease(p*2); w=(1-q)**1.3; return zoom(A,1+0.06*q)*w+BG*(1-w)
        q=ease((p-.5)*2); w=q**0.8; return zoom(B,1.05-0.05*q)*w+BG*(1-w)
    if k=='dissolve':
        return zoom(A,1+0.02*e)*(1-e)+B*e
    if k=='scan':
        y=int(round(e*H)); o=A.copy(); o[:y]=B[:y]
        d=np.abs(np.arange(H,dtype=np.float32)-y)
        glow=(0.75*np.exp(-(d/5)**2)+0.18*np.exp(-(d/60)**2))*np.sin(np.pi*p)**0.5
        o=o+(AC-o)*glow[:,None,None]
        return o
    if k=='paper':
        x=W*(1-e); ang=-2.5*(1-e)
        M=cv2.getRotationMatrix2D((W/2,H/2),ang,1.0); M[0,2]+=x
        Bw=cv2.warpAffine(B,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=BGT)
        m=cv2.warpAffine(np.ones((H,W),np.float32),M,(W,H),flags=cv2.INTER_LINEAR,borderValue=0)
        sh=cv2.GaussianBlur(cv2.warpAffine(m,np.float32([[1,0,-40],[0,1,20]]),(W,H)),(0,0),25)*0.7
        bgA=zoom(A,1-0.03*e)*(1-0.45*e)+BG*(0.45*e)
        bgA=bgA*(1-sh[:,:,None])
        return bgA*(1-m[:,:,None])+Bw*m[:,:,None]
    if k=='flash':
        w=(1-abs(2*p-1))**1.6*0.92; base=A if p<.5 else B
        return base+(np.maximum(FG,AC)-base)*w
    if k=='whip':
        x=-W*e; o=np.zeros_like(A)
        Ma=np.float32([[1,0,x],[0,1,0]]); Mb=np.float32([[1,0,x+W],[0,1,0]])
        o=cv2.warpAffine(A,Ma,(W,H),borderValue=(0,0,0))+cv2.warpAffine(B,Mb,(W,H),borderValue=(0,0,0))
        sp=np.sin(np.pi*p); kx=int(1+160*sp)
        return cv2.blur(o,(kx,1)) if kx>2 else o
    if k=='glitch':
        rng=np.random.default_rng(g); base=(A if p<.5 else B).copy(); oth=B if p<.5 else A
        amp=np.sin(np.pi*p)
        y=0
        while y<H:
            hh=int(rng.integers(8,90)); sl=slice(y,min(H,y+hh))
            if rng.random()<0.55*amp:
                src=oth if rng.random()<0.5 else base
                base[sl]=np.roll(src[sl],int(rng.normal(0,140*amp)),axis=1)
            y+=hh
        g2=base.copy(); g2[:,:,2]=np.roll(base[:,:,2],int(14*amp),axis=1); g2[:,:,0]=np.roll(base[:,:,0],-int(14*amp),axis=1)
        gray=cv2.cvtColor(np.clip(g2,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
        out=np.dstack([gray]*3)*0.6+g2*0.4  # keep the channel monochrome-ish
        lines=(rng.random(H)<0.04*amp)[:,None,None]*rng.uniform(40,120)
        return out+lines
    if k=='pixel':
        if p<.5: q=ease(p*2); return pixelate(A,1+70*q)
        q=ease((1-p)*2); return pixelate(B,1+70*q)
    if k=='shred':
        n=int(P.get('n',24) or 24); sw_=W/n; o=B.copy(); rng=np.random.default_rng(12345)
        dl=rng.uniform(0,.35,n); dr=rng.uniform(-1,1,n)
        for j in range(n):
            x0=int(round(j*sw_)); x1=int(round((j+1)*sw_)); q=min(1,max(0,(p-dl[j])/.6)); q=q*q
            dy=int(q*H*1.1)
            if dy>=H: continue
            g0=2 if q>0 else 0
            o[dy:,x0+g0:x1-g0]=A[:H-dy,x0+g0:x1-g0]
            if q>0: o[:dy,x0+g0:x1-g0]=B[:dy,x0+g0:x1-g0]
        return o
    raise ValueError(k)
def edges(i):
    cap=cv2.VideoCapture(f'{IN}/{i:02d}.mp4'); ok,first=cap.read(); last=first
    while True:
        ok,f=cap.read()
        if not ok: break
        last=f
    cv2.imwrite(f'edges/{i:02d}_first.png',first); cv2.imwrite(f'edges/{i:02d}_last.png',last); return i
def ld(p):
    o=cv2.imread(p,cv2.IMREAD_UNCHANGED).astype(np.float32)
    return np.ascontiguousarray(o[:,:,:3]),np.ascontiguousarray(o[:,:,3:4]/255.0)
def job(i):
    p=P[i]; N=fr[i+1]-fr[i]
    hp=half(i-1) if i>0 else 0; hn=half(i) if i<len(S)-1 else 0
    def ovf(j,idx):
        fn=f'ov/{j:02d}/{idx:03d}.png'
        if kind(j) not in OVK or not os.path.exists(fn): return None
        o=cv2.imread(fn,cv2.IMREAD_UNCHANGED).astype(np.float32)
        return (o[:,:,:3],o[:,:,3:4]/255.0) if o.shape[2]==4 else (o,np.ones((H,W,1),np.float32))
    Al=cv2.imread(f'edges/{i-1:02d}_last.png').astype(np.float32) if i>0 else None
    Bf=cv2.imread(f'edges/{i+1:02d}_first.png').astype(np.float32) if i<len(S)-1 else None
    subs=[(a,b,ld(f'subs/{i:02d}_{m}.png')) for m,(a,b,_) in enumerate(p['subs'])]
    cap=cv2.VideoCapture(f'{IN}/{i:02d}.mp4')
    pr=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
        '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p',f'{OUT}/{i:02d}.mp4'],stdin=subprocess.PIPE)
    last=None
    for l in range(N):
        ok,f=cap.read()
        if not ok: f=last
        last=f; fr_=f.astype(np.float32); g=fr[i]+l
        if l<hp: fr_=T(kind(i-1),Al,fr_,(hp+l+0.5)/(2*hp),g,ovf(i-1,hp+l),params(i-1))
        elif l>=N-hn: fr_=T(kind(i),fr_,Bf,(l-(N-hn)+0.5)/(2*hn),g,ovf(i,l-(N-hn)),params(i))
        t=l/FPS
        for a_,b_,(sr,sa) in subs:
            if a_-0.1<=t<=b_+0.1:
                w=min(1,(t-(a_-0.1))/0.12,((b_+0.1)-t)/0.12)
                fr_[780:]=fr_[780:]*(1-sa*w)+sr*(sa*w)
        if i==0: fr_*=min(1,(l+1)/(0.5*FPS))
        if i==len(S)-1: fr_*=min(1,(N-l)/(1.5*FPS))
        pr.stdin.write(np.clip(fr_,0,255).astype(np.uint8).tobytes())
    pr.stdin.close(); pr.wait(); return i
if __name__=='__main__':
    only=[int(x) for x in sys.argv[1:] if x!='--edges']
    with Pool(4) as pl:
        need=sorted({j for i in (only or range(len(S))) for j in (i-1,i,i+1) if 0<=j<len(S)}) if '--edges' in sys.argv else []
        list(pl.imap_unordered(edges,need))
        for i in pl.imap_unordered(job,only or range(len(S))): print(i,end=' ',flush=True)
    open(f'{OUT}/list.txt','w').write(''.join(f"file '{i:02d}.mp4'\n" for i in range(len(S))))
    print()
