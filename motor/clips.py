"""Renders one MP4 per scene (Ken Burns on photos, smooth zoom on text, state reveals). Run inside the work dir."""
import json, subprocess, numpy as np, cv2, sys, os
from multiprocessing import Pool
PREVIA=bool(os.environ.get('POPDOCS_PREVIA')); STEP=2 if PREVIA else 1   # quick scene preview: half the frames, small and fast encode
FPS=30; W,H=1920,1080; OUT='clips'; IMG=os.environ.get('POPDOCS_IMG','img')
def _bgr(h): h=h.lstrip('#'); return np.array([int(h[4:6],16),int(h[2:4],16),int(h[0:2],16)],np.float32)
BOX=(260,140,1400,788)  # x,y,w,h of the window of a 'clip' scene (must match templates/frame.html)
IMG_EXT=('.jpg','.jpeg','.png','.webp'); VID_EXT=('.mp4','.webm','.mov','.m4v')
def find_bg(imgdir,key):
    """Path of the photo or video clip saved as img/<key>.<ext>, or None."""
    for e in IMG_EXT+VID_EXT:
        p=os.path.join(imgdir,key+e)
        if os.path.exists(p): return p
    return None
def is_video(p): return bool(p) and p.lower().endswith(VID_EXT)
def still(p,t=1.0):
    """A still image from a photo, or the frame at t seconds of a clip."""
    if not is_video(p): return cv2.imread(p)
    cap=cv2.VideoCapture(p); n=cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0; fps=cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_FRAMES,min(int(t*fps),max(0,int(n)-1))); ok,f=cap.read()
    if not ok: cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,f=cap.read()
    cap.release(); return f if ok else None
class Clip:
    """Reads a background clip frame by frame at the video's frame rate, starting at `start` seconds, looping at the end."""
    def __init__(self,p,start=0.0):
        self.p=p; self.cap=cv2.VideoCapture(p); self.fps=self.cap.get(cv2.CAP_PROP_FPS) or 30; self.n=-1; self.f=None
        self.start=max(0.0,float(start or 0)); self.len=(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)/self.fps
        if self.len and self.start>=self.len: self.start=0.0
    def at(self,t):
        want=int((self.start+t)*self.fps)
        if self.len: want%=max(1,int(self.len*self.fps))
        if want<self.n: self.cap.release(); self.cap=cv2.VideoCapture(self.p); self.n=-1
        while self.n<want:
            ok,f=self.cap.read()
            if not ok:
                if self.f is None: return None
                break
            self.f=f; self.n+=1
        return self.f
def treat(im,C,clahe=1.5,modo=None):
    """Photo look from the video colors: 'pb' black and white, 'cor' original colors, 'tom' two-tone (background -> highlight color).
    `modo` (from the photo library) overrides the video's choice for one photo."""
    mode=modo if modo in ('pb','cor','tom') else (C or {}).get('fotos','pb')
    if mode=='cor':
        lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB); lab[:,:,0]=cv2.createCLAHE(clipLimit=clahe,tileGridSize=(8,8)).apply(lab[:,:,0]); return cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
    g=cv2.createCLAHE(clipLimit=clahe,tileGridSize=(8,8)).apply(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY))
    if mode=='tom':
        lo=_bgr(C.get('fundo','#0B0B0B')); hi=(_bgr(C.get('texto','#F2F2F2'))+_bgr(C.get('destaque') or C.get('texto','#F2F2F2')))/2
        t=(g.astype(np.float32)/255)[:,:,None]; return np.clip(lo*(1-t)+hi*t,0,255).astype(np.uint8)
    return cv2.cvtColor(g,cv2.COLOR_GRAY2BGR)
CORES=json.load(open('cores.json')) if os.path.exists('cores.json') else {}
if __name__ in ('__main__','__mp_main__'):  # also in worker processes (spawn on Windows and Mac)
    S=json.load(open('scenes.json')); P=json.load(open('plan.json'))
    cum=np.array([p['start'] for p in P]+[P[-1]['start']+P[-1]['dur']]); fr=np.round(cum*FPS).astype(int)
    os.makedirs(OUT,exist_ok=True)
def cover(img,scale=1.12,fx=0.5,fy=0.5):
    """Fill the frame, cropping around the focus point (fx, fy from 0 to 1; 0.5, 0.5 is the center)."""
    h,w=img.shape[:2]; tw,th=int(W*scale),int(H*scale); r=max(tw/w,th/h)
    img=cv2.resize(img,(int(w*r+1),int(h*r+1)),interpolation=cv2.INTER_AREA)
    h,w=img.shape[:2]; y=int(round((h-th)*min(max(fy,0),1))); x=int(round((w-tw)*min(max(fx,0),1))); return img[y:y+th,x:x+tw]
def whole(img,scale=1.12,fx=0.5):
    """The whole photo, fitted to the frame height, over a blurred and darkened copy of itself (for portraits and documents)."""
    tw,th=int(W*scale),int(H*scale); back=cover(img,scale)
    back=(cv2.GaussianBlur(back,(0,0),40)*0.45).astype(np.uint8)
    h,w=img.shape[:2]; r=min(th*0.94/h,tw*0.94/w); fw,fh=int(w*r),int(h*r)
    fg=cv2.resize(img,(fw,fh),interpolation=cv2.INTER_AREA if r<1 else cv2.INTER_CUBIC)
    x=int(round((tw-fw)*min(max(fx,0),1))); y=(th-fh)//2; back[y:y+fh,x:x+fw]=fg; return back
def framed(img,s,scale=1.12):
    """Photo framing from the library: 'fotoRecorte' [x0,y0,x1,y1] crops first, 'fotoEnq' 'inteira' shows it whole, 'fotoFoco' [x,y] moves the crop."""
    rc=s.get('fotoRecorte')
    if rc:
        h,w=img.shape[:2]; img=img[int(h*rc[1]):int(h*rc[3]),int(w*rc[0]):int(w*rc[2])]
    fx,fy=(s.get('fotoFoco') or [0.5,0.5])[:2]; h,w=img.shape[:2]
    auto=s.get('auto') and not s.get('fotoEnq') and not s.get('fotoFoco') and h>w*1.15   # extra photo, upright, never framed by hand: show it whole
    return whole(img,scale,fx) if s.get('fotoEnq')=='inteira' or auto else cover(img,scale,fx,fy)
def ambient(frame,f,seed,kind):
    """Life over a photo so that it never looks frozen: the light breathes like an old projector.
    No film grain (it doubles the final file) and no dust (it looked artificial)."""
    if not kind: return frame
    return frame*(1+0.018*np.sin(f*0.83+seed)+0.012*np.sin(f*0.21+seed*1.7))
def kenburns(bg,u,dirn,s=None):
    """One photo in motion. Default: slow push-in with a sideways drift. With s['zoom']=='detalhe', the camera
    travels to the point s['zp'] = [x, y] of the frame (0 to 1), e.g. a signature or one line of a newspaper."""
    bh,bw=bg.shape[:2]
    if s and s.get('zoom')=='detalhe':
        px,py=(s.get('zp') or [0.5,0.5])[:2]; e=u*u*(3-2*u) if u<1 else 1.0; z=1+0.55*e; dx=(bw-W)/2; dy=(bh-H)/2
        M=np.array([[z,0,-dx*z+px*W*(1-z)],[0,z,-dy*z+py*H*(1-z)]],np.float32)
    else:
        z=1+0.09*u; dx=(bw-W)/2+(bw-W)*0.25*(u-0.5)*dirn; dy=(bh-H)/2
        M=np.array([[z,0,-(dx+W/2)*z+W/2],[0,z,-(dy+H/2)*z+H/2]],np.float32)
    return cv2.warpAffine(bg,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
def ld(p):
    o=cv2.imread(p,cv2.IMREAD_UNCHANGED).astype(np.float32)
    if o.shape[2]==3: o=np.dstack([o,np.full(o.shape[:2],255,np.float32)])
    return np.ascontiguousarray(o[:,:,:3]),np.ascontiguousarray(o[:,:,3]/255.0)
def job(i):
    s=S[i]; p=P[i]; N=fr[i+1]-fr[i]; fade=int(0.35*FPS); xf=0.3
    states=[ld(f'png/{i:02d}_{k}.png') for k in range(len(p['steps']))]; allst=[states]
    bg=None; clip=None; dark=(0.55 if s['t']=='title' else 0.85); src=find_bg(IMG,s['bg']) if s.get('bg') else None
    if is_video(src): clip=Clip(src,s.get('vin',0))
    elif src:
        bg=framed(treat(cv2.imread(src),CORES,modo=s.get('fotoModo')),s).astype(np.float32)*dark
        bgs=[bg]   # extra photos of the same scene ('fundos'): the image changes every few seconds while the narration goes on
        for x in s.get('fundos') or []:
            p2=find_bg(IMG,x['key'])
            if p2 and not is_video(p2):
                q=f'png/{i:02d}_f{len(allst)}_0.png'   # text states drawn with this photo's own caption and credit
                allst.append([ld(f'png/{i:02d}_f{len(allst)}_{k}.png') for k in range(len(p['steps']))] if os.path.exists(q) else states)
                bgs.append(framed(treat(cv2.imread(p2),CORES,modo=x.get('fotoModo')),x).astype(np.float32)*dark)
        segN=N/len(bgs); XF=int(0.6*FPS)
    pr=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS/STEP),'-i','-',
        *(['-vf','scale=960:540','-c:v','libx264','-preset','ultrafast','-crf','26'] if PREVIA else ['-c:v','libx264','-preset','veryfast','-crf','16']),'-pix_fmt','yuv420p',f'{OUT}/{i:02d}.mp4'],stdin=subprocess.PIPE)
    zin = (i%2==0)
    for f in range(0,N,STEP):
        t=f/FPS; u=f/max(N-1,1)
        k=max(j for j,st in enumerate(p['steps']) if st<=t+1e-6)
        def comp(rgb,al,M):
            if M is None: return rgb,al[:,:,None]
            return cv2.warpAffine(rgb,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE), cv2.warpAffine(al,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)[:,:,None]
        if clip is not None and s['t']=='clip':
            vf=clip.at(t); bx,by,bw2,bh2=BOX; frame=np.zeros((H,W,3),np.float32); Mo=None
            if vf is not None:
                im=treat(vf,CORES,clahe=1.0,modo=s.get('fotoModo') or 'cor'); h0,w0=im.shape[:2]; r=max(bw2/w0,bh2/h0)
                im=cv2.resize(im,(int(w0*r+1),int(h0*r+1)),interpolation=cv2.INTER_AREA); y0=(im.shape[0]-bh2)//2; x0=(im.shape[1]-bw2)//2
                frame[by:by+bh2,bx:bx+bw2]=im[y0:y0+bh2,x0:x0+bw2]
        elif clip is not None:
            vf=clip.at(t)
            bgv=cover(treat(vf,CORES,modo=s.get('fotoModo')),1.0).astype(np.float32)*dark if vf is not None else np.zeros((H,W,3),np.float32)
            z=1+0.03*u; frame=cv2.warpAffine(bgv,np.array([[z,0,W/2*(1-z)],[0,z,H/2*(1-z)]],np.float32),(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE); Mo=None
            frame=ambient(frame,f,i,s.get('amb'))
        elif bg is not None:
            j=min(int(f/segN),len(bgs)-1); lf=f-j*segN; dj=1 if (i+j)%2 else -1
            frame=kenburns(bgs[j],lf/max(segN-1,1),dj,s if j==0 else None)
            if j>0 and lf<XF:   # cross-fade from the previous photo, which keeps moving
                w=1-lf/XF; frame=frame*(1-w)+kenburns(bgs[j-1],1+lf/max(segN-1,1),-dj,s if j==1 else None)*w
            frame=ambient(frame,f,i,s.get('amb')); Mo=None; states=allst[j]
        else:
            z=1+0.04*(u if zin else 1-u); Mo=np.array([[z,0,W/2*(1-z)],[0,z,H/2*(1-z)]],np.float32); frame=np.zeros((H,W,3),np.float32)
        r,a=comp(*states[k],Mo); frame=frame*(1-a)+r*a
        if k>0 and t-p['steps'][k]<xf:
            w=1-(t-p['steps'][k])/xf; r0,a0=comp(*states[k-1],Mo); frame=frame*(1-w*a0)+r0*(w*a0)  # blend previous on top fading out
        pr.stdin.write(np.clip(frame,0,255).astype(np.uint8).tobytes())
    pr.stdin.close(); pr.wait(); return i
if __name__=='__main__':
    only=[int(x) for x in sys.argv[1:]]
    with Pool(4) as pl:
        for i in pl.imap_unordered(job,only or range(len(S))): print(i,end=' ',flush=True)
    pass #.write(''.join(f"file '{i:02d}.mp4'\n" for i in range(len(S))))
    print('\ntotal',cum[-1])
