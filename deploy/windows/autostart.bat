@echo off
chcp 65001 >nul
rem Добавляет techdesk в автозапуск при включении компьютера (без входа пользователя).
rem Запускать от имени администратора.
cd /d "%~dp0..\.."
schtasks /Create /F /TN "techdesk" /SC ONSTART /RU SYSTEM /TR "\"%CD%\.venv\Scripts\python.exe\" \"%CD%\serve.py\""
if errorlevel 1 (
  echo Не получилось. Запустите файл от имени администратора.
) else (
  echo Задача "techdesk" создана. Сервер будет запускаться при включении ПК.
  echo Запустить сейчас: schtasks /Run /TN techdesk
)
pause
