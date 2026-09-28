@echo off
chcp 65001 >nul
rem Запуск techdesk. Окно не закрывайте, пока сервер нужен.
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat
python serve.py
pause
