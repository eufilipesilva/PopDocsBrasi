#!/bin/bash
cd "$(dirname "$0")"
echo "Instalando o que o motor precisa (pode levar alguns minutos)..."
python3 -m pip install -r requirements.txt
npm install
npx playwright install chromium
echo
echo "Pronto. Agora abra iniciar-estudio.command"
