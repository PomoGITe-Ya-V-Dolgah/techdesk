@echo off
chcp 65001 >nul
rem Первичная установка techdesk на Windows-ПК (запускать двойным щелчком).
cd /d "%~dp0..\.."

where py >nul 2>nul
if errorlevel 1 (
  echo Не найден Python. Установите Python 3.12 или новее с https://www.python.org/downloads/
  echo При установке отметьте "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist .venv (
  echo [1/6] Создаю виртуальное окружение...
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
  echo Нужен Python 3.12 или новее. Удалите папку .venv, установите новый Python и запустите снова.
  pause
  exit /b 1
)

echo [2/6] Устанавливаю зависимости...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || (pause & exit /b 1)

echo [3/6] Создаю файл настроек .env...
python deploy\make_env.py

echo [4/6] Создаю базу данных...
python manage.py migrate || (pause & exit /b 1)

echo [5/6] Собираю оформление сайта...
python manage.py collectstatic --noinput >nul || (pause & exit /b 1)

echo [6/6] Создайте учетную запись администратора:
python manage.py createsuperuser

echo.
echo Готово. Дальше:
echo   - open_firewall.bat  (правой кнопкой - "Запуск от имени администратора")
echo   - start.bat          (запуск сервера)
pause
