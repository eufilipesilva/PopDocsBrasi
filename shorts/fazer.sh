#!/bin/bash
# uso: bash shorts/fazer.sh <nome> ...   (rodar na pasta popdocsbrasi, depois de montar.py)
cd "$(dirname "$0")/../motor"
W="$(python -c 'import tempfile;print(tempfile.gettempdir())')/popdocs-work"
for s in "$@"; do
  python motor.py ../shorts/$s tts plan shots clips srt || exit 1
  # o Short tem legenda grande própria: apaga as legendas pequenas do motor antes de montar as transições
  python -c "
import cv2,glob,numpy as np,sys,json
for f in glob.glob(sys.argv[1]+'/subs/*.png'):
  im=cv2.imread(f,cv2.IMREAD_UNCHANGED); cv2.imwrite(f,np.zeros_like(im))
p=sys.argv[1]+'/hashes.json';h=json.load(open(p));[h.pop(k) for k in list(h) if k.startswith('tr')];json.dump(h,open(p,'w'))" "$W/$s"
  python motor.py ../shorts/$s trans mix || exit 1
  (cd .. && python -X utf8 shorts/vertical.py shorts/$s) || exit 1
done
