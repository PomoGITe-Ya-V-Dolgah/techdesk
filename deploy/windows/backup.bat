@echo off
chcp 65001 >nul
rem Резервная копия базы techdesk в папку backups (хранятся последние 30 копий).
rem Удобно добавить в Планировщик заданий Windows ежедневно.
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat
python deploy\backup.py
