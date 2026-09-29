# Service Desk ТО

Web-приложение для учета и обработки заявок отдела технического обслуживания предприятия.

## Новизна ВКР

Система объединяет учет заявок с историей обслуживания конкретного оборудования. QR-паспорт оборудования ускоряет регистрацию обращения, а рекомендации похожих решений помогают новым сотрудникам быстрее найти проверенный способ устранения неисправности.

## Быстрый запуск на новом устройстве

Нужен Python 3.12 или новее (требование Django 6).

```bash
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate.bat   
#source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
## Запуск повторный
```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate.bat   
python manage.py runserver
```

Открыть: http://127.0.0.1:8000

Демо-пользователи:

- `admin` / `admin123`
- `operator` / `operator123`
- `engineer` / `engineer123`
- `manager` / `manager123`
- `employee` / `employee123` — роль «Сотрудник»

## Работа в локальной сети офиса

`runserver` подходит только для разработки. Для доступа с других компьютеров:

```bash
python deploy/make_env.py          # .env с IP этого ПК, DEBUG=0, новым секретным ключом
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python serve.py                    # сервер waitress на 0.0.0.0:8000
```

Для Windows есть готовые скрипты в `deploy/windows/`, для Linux — `docker-compose.lan.yml`.
Подробная инструкция: [docs/deploy/LAN.md](docs/deploy/LAN.md).
Доступ из интернета (VPN или HTTPS через Caddy): [docs/deploy/INTERNET.md](docs/deploy/INTERNET.md).
Развёртывание на VPS `tech.letii.ru` через существующий Caddy: [docs/deploy/VPS.md](docs/deploy/VPS.md).

## PostgreSQL

Для запуска PostgreSQL:

```bash
docker compose up -d db
cp .env.example .env
# затем укажите POSTGRES_DB=servicedesk в .env
python manage.py migrate
python manage.py seed_demo
```

Если переменная `POSTGRES_DB` не задана, приложение использует SQLite для быстрого локального тестирования.

## Основные возможности

- авторизация и роли;
- учет оборудования;
- QR-код оборудования;
- создание и обработка заявок;
- история заявок по оборудованию;
- база типовых решений;
- рекомендации похожих решений;
- отчеты и CSV-экспорт;
- реестр: сотрудник за устройством, имя ПК/IP, ОС, установленное ПО, статус, связи «подключено к»;
- страница «Что где стоит» по кабинетам;
- импорт реестра из Excel/CSV, печать QR-наклеек;
- роль «Сотрудник»: свои заявки и своя техника;
- уведомления на e-mail, защита входа от подбора пароля.

## Проверка

```bash
python manage.py test
```
