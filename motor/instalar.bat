@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Instalando o que o motor precisa (pode levar alguns minutos)...
python -m pip install -r requirements.txt
call npm install
call npx playwright install chromium
echo.
echo Pronto. Agora rode iniciar-estudio.bat
pause
