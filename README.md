# Service Desk ТО

Web-приложение для учета и обработки заявок отдела технического обслуживания предприятия.

## Новизна ВКР

Система объединяет учет заявок с историей обслуживания конкретного оборудования. QR-паспорт оборудования ускоряет регистрацию обращения, а рекомендации похожих решений помогают новым сотрудникам быстрее найти проверенный способ устранения неисправности.

## Быстрый запуск на новом устройстве

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
- отчеты и CSV-экспорт.

## Проверка

```bash
python manage.py test
```
