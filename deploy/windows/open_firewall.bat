@echo off
chcp 65001 >nul
rem Разрешает входящие подключения к techdesk (порт 8000) из локальной сети.
rem Запускать от имени администратора.
netsh advfirewall firewall delete rule name="techdesk" >nul 2>nul
netsh advfirewall firewall add rule name="techdesk" dir=in action=allow protocol=TCP localport=8000 profile=private,domain
if errorlevel 1 (
  echo Не получилось. Запустите файл правой кнопкой - "Запуск от имени администратора".
) else (
  echo Порт 8000 открыт для частной и доменной сети.
  echo Проверьте, что сеть в Windows помечена как "Частная", а не "Общедоступная".
)
pause
