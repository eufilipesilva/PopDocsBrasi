"""Baixa as imagens livres de videos/<slug>/fotos-candidatas.json para videos/<slug>/img/ e cria fotos.json (com credito e licenca).
Uso: python motor/baixar_imagens.py diesel eastman kellogg
Pode ser interrompido e rodado de novo: pula o que ja foi baixado. Precisa de: pip install -r motor/requirements.txt"""
import json, os, sys, time, urllib.request, urllib.parse, io
import cv2, numpy as np
UA = "PopDocsBrasil/1.0 (documentario sem fins de assedio; imagens livres com credito)"
import os as _os
BASE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "videos")
SRC = BASE
PAUSA = 2.0
def get(url, tries=6):
    for t in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(r, timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 403): return None
            if e.code in (429, 503):
                espera = int(e.headers.get("Retry-After", "0") or 0) or 60 * (t + 1)
                print(f"   {e.code}, esperando {espera}s", flush=True); time.sleep(espera)
            elif e.code == 404: return None
            else: raise
        except Exception as e:
            print("   erro", e, flush=True); time.sleep(10)
    return None
def candidatos(url):
    """URLs a tentar, sem usar a API: miniatura de 1920 px em upload.wikimedia.org, depois o original."""
    u = url.split("?")[0]
    pre, _, nome = u.rpartition("/")
    ext = nome.rsplit(".", 1)[-1].lower()
    out = []
    if "/commons/thumb/" not in u and "/wikipedia/commons/" in u:
        base = pre.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/")
        suf = {"svg": ".png", "tif": ".jpg", "tiff": ".jpg", "webp": ".jpg", "gif": ".jpg"}.get(ext, "")
        if ext in ("jpg", "jpeg", "png", "svg", "tif", "tiff", "webp", "gif"):
            out.append(f"{base}/{nome}/1920px-{nome}{suf}")
    if ext in ("jpg", "jpeg", "png"): out.append(u)
    return out
def tojpg(data, dest):
    im = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if im is None: return False
    h, w = im.shape[:2]
    if max(h, w) > 2000:
        k = 2000 / max(h, w); im = cv2.resize(im, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    for q in (90, 80, 70, 60):
        ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) < 1_600_000: break
    open(dest, "wb").write(buf.tobytes()); return True
for slug in sys.argv[1:]:
    cand = json.load(open(f"{SRC}/{slug}/fotos-candidatas.json"))
    os.makedirs(f"{BASE}/{slug}/img", exist_ok=True)
    fp = f"{BASE}/{slug}/fotos.json"
    fotos = json.load(open(fp)) if os.path.exists(fp) else {}
    print(f"{slug}: {len(cand)} candidatas", flush=True)
    for k, c in cand.items():
        dest = f"{BASE}/{slug}/img/{k}.jpg"
        if os.path.exists(dest) and k in fotos: continue
        data = None
        for url in candidatos(c["url"]):
            data = get(url)
            time.sleep(PAUSA)
            if data and tojpg(data, dest): break
            data = None
        if not data: print("  FALHOU:", k, c["url"][-60:], flush=True); continue
        fotos[k] = {"cap": c.get("cap", ""), "credit": c["credit"], "license": c["license"], "source": c["source"], "file": c["file"]}
        json.dump(fotos, open(fp, "w"), ensure_ascii=False, indent=1)
        print("  ok", k, flush=True)
print("FIM", flush=True)
