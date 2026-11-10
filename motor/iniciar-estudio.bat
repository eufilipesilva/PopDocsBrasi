@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Abrindo o Estudio PopDocs...
python estudio_local\servidor.py
pause
