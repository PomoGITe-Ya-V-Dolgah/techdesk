@echo off
chcp 65001 >nul
rem Запуск Caddy (HTTPS для доступа из интернета) на Windows.
rem 1) Скачайте caddy_windows_amd64.exe с https://caddyserver.com/download,
rem    переименуйте в caddy.exe и положите в папку deploy\windows.
rem 2) .env создайте командой: python deploy\make_env.py <IP> --domain <домен>
rem 3) techdesk должен быть запущен (start.bat), затем запустите этот файл.
cd /d "%~dp0..\.."
if not exist deploy\windows\caddy.exe (
  echo Не найден deploy\windows\caddy.exe — см. инструкцию в начале этого файла.
  pause
  exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  if "%%a"=="TECHDESK_DOMAIN" set TECHDESK_DOMAIN=%%b
)
set TECHDESK_UPSTREAM=127.0.0.1:8000
deploy\windows\caddy.exe run --config deploy\internet\Caddyfile --adapter caddyfile
pause
