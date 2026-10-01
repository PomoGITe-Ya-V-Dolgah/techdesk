# VPS: tech.letii.ru

Эта инструкция относится к VPS `87.106.94.6`. Для офиса и отдельного сервера с собственным Caddy используйте [LAN.md](LAN.md) и [INTERNET.md](INTERNET.md). Здесь порты 80/443 уже обслуживает Caddy проекта Narratio, поэтому запускайте `compose.vps.yml`, а не `docker-compose.internet.yml`.

## Схема и файлы

- SSH: `ssh -A deploy@87.106.94.6`.
- Приложение: `/home/deploy/techdesk`, Compose-проект `techdesk`.
- PostgreSQL: отдельный volume `techdesk_pgdata`, порт наружу не публикуется.
- Контейнер приложения доступен существующему Caddy как `techdesk-app:8000` через сеть `narratio_default`.
- Маршрут домена: `/home/deploy/narratio/Caddyfile`, образец — [Caddyfile.techdesk](../../deploy/vps/Caddyfile.techdesk).
- Секреты: `/home/deploy/techdesk/.env` (права `600`). Действующие логины и пароли: `/home/deploy/techdesk/admin-credentials.txt` (права `600`). Эти файлы не входят в Git.

## Первый запуск

DNS-запись `tech.letii.ru` должна указывать на VPS. Нужны Docker Compose и существующая сеть `narratio_default`. В `/home/deploy/techdesk/.env` задайте уникальные `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD`, а также:

```dotenv
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=tech.letii.ru
DJANGO_CSRF_TRUSTED_ORIGINS=https://tech.letii.ru
PUBLIC_BASE_URL=https://tech.letii.ru
SHOW_DEMO_LOGINS=0
DJANGO_HTTPS=1
DJANGO_SSL_REDIRECT=1
BEHIND_PROXY=1
TECHDESK_HOST=0.0.0.0
TECHDESK_PORT=8000
POSTGRES_DB=servicedesk
POSTGRES_USER=servicedesk
POSTGRES_HOST=techdesk-db
POSTGRES_PORT=5432
```

При желании задайте непредсказуемый `DJANGO_ADMIN_URL`. Не меняйте пароль БД в `.env` после инициализации volume без отдельной процедуры смены пароля PostgreSQL.

```bash
cd /home/deploy/techdesk
docker compose -f compose.vps.yml -p techdesk config --quiet
docker compose -f compose.vps.yml -p techdesk up -d --build
docker compose -f compose.vps.yml -p techdesk ps
```

При запуске контейнер применяет миграции. Если нужны демонстрационные данные, выполните `docker compose -f compose.vps.yml -p techdesk exec -T app python manage.py seed_demo` и **до публикации** замените известные пароли всех пяти пользователей. На текущем VPS они заменены случайными и хранятся в закрытом файле выше.

После проверки приложения замените блок `tech.letii.ru` в Caddyfile на содержимое `deploy/vps/Caddyfile.techdesk`, проверьте конфигурацию и обновите только `web`:

```bash
docker run --rm --entrypoint caddy -v /home/deploy/narratio/Caddyfile:/etc/caddy/Caddyfile:ro narratio-web validate --config /etc/caddy/Caddyfile
cd /home/deploy/narratio
docker compose build web
docker compose up -d --no-deps web
```

Сертификаты Caddy находятся в существующем volume `narratio_caddy_data`. Другие проекты Docker не нужно перезапускать.
Перед переключением сохранён `/home/deploy/narratio/Caddyfile.pre-techdesk-20260929`. После переключения предыдущий проект `tech` остаётся на месте: контейнеры `tech-app-1` и `tech-db-1`, volume `tech_pgdata`, каталог `/home/deploy/tech` и его запись в crontab. Владелец VPS удалит их отдельно после проверки нового сайта.

## Проверки и обновление

С локального корня репозитория передайте отслеживаемые файлы без удаления серверных секретов и архивов:

```bash
git ls-files -z | rsync -az --from0 --files-from=- ./ deploy@87.106.94.6:/home/deploy/techdesk/
ssh -A deploy@87.106.94.6 'cd /home/deploy/techdesk && docker compose -f compose.vps.yml -p techdesk up -d --build app'
```

Перед миграциями делайте внеплановый бекап. После обновления проверьте:

```bash
curl -I https://tech.letii.ru/login/
curl -I https://tech.letii.ru/static/css/app.css
ssh -A deploy@87.106.94.6 'cd /home/deploy/techdesk && docker compose -f compose.vps.yml -p techdesk ps'
```

Страница входа и CSS должны возвращать `200`, оба контейнера — `healthy`. Также проверьте вход администратора и страницу реестра.

## Бекапы

`/home/deploy/techdesk/deploy/vps/backup-db.sh` запускается crontab пользователя `deploy` ежедневно в 03:30 UTC:

```cron
30 3 * * * /home/deploy/techdesk/deploy/vps/backup-db.sh >> /home/deploy/techdesk/backups/backup.log 2>&1
```

Скрипт сохраняет атомарный gzip-архив SQL в `/home/deploy/techdesk/backups`, проверяет архив, затем удаляет архивы старше 7 суток. Каталог имеет права `700`, файлы — `600`; `flock` предотвращает одновременный запуск. Проверить расписание и сделать копию вручную:

```bash
ssh -A deploy@87.106.94.6 'crontab -l; /home/deploy/techdesk/deploy/vps/backup-db.sh'
```

Для проверки восстановления создайте отдельную пустую БД:

```bash
cd /home/deploy/techdesk
docker compose -f compose.vps.yml -p techdesk exec -T db sh -c 'createdb -U "$POSTGRES_USER" servicedesk_restore'
gzip -dc backups/techdesk-YYYYMMDDTHHMMSSZ.sql.gz | docker compose -f compose.vps.yml -p techdesk exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d servicedesk_restore'
```

Архивы сейчас хранятся на этом же VPS. Для защиты от потери самого сервера дополнительно копируйте их за его пределы.

## Обновление со сроками и уведомлениями

Перед обновлением запустите `deploy/vps/backup-db.sh` на сервере. Версия добавляет миграцию `service/0003_profile_notification_scope_and_more`: настройки уведомлений в профиле и таблицу событий. Существующие заявки и пользователи сохраняются; звук изначально выключен, старые заявки не вызывают уведомления.

Передайте также новые отслеживаемые файлы миграции, шаблонов и `static/js/ticket-live.js` (при подготовке к коммиту добавьте их в Git, чтобы `git ls-files` включал их). Пересоберите приложение обычной командой выше. Контейнер применит миграцию и соберёт статику.

После обновления проверьте назначение активного администратора и инженера, сохранение даты/времени, цветные статусы, автообновление очереди и настройки звука под двумя разными пользователями. Для проверки уведомления создайте заявку из другой учётной записи, оставив у получателя открытую страницу и включив «Все новые заявки и назначенные мне». Нажмите «Проверить звук» на устройстве получателя. Интервалы: события 5 секунд, очередь 10 секунд. Отдельные Redis, WebSocket и настройки Caddy не требуются.

Подробная инструкция для пользователей: [TICKETS.md](../TICKETS.md).

### Публикация 01.10.2026

Доработки исполнителей, сроков, цветных статусов и уведомлений опубликованы на `https://tech.letii.ru`. Миграция `0003` применена. Проверены страницы очереди, карточки, назначения и статусов под администратором, выдача событий и фрагмента таблицы; вход и новые JS/CSS возвращают `200`. При обновлении сохранены 5 заявок и 7 пользователей.

Бекап перед обновлением: `/home/deploy/techdesk/backups/techdesk-20261001T180935Z.sql.gz`. Исходники предыдущей версии сохранены рядом в `source-before-*.tar.gz`, прежний образ — с тегом `techdesk-app:before-*`. Расписание ежедневного бекапа в 03:30 UTC с хранением SQL-архивов 7 суток сохранено.

## Обновление фильтров и сортировки

Версия добавляет фильтр оборудования по сотруднику, ссылки на его технику и сортировку таблиц. Миграций БД нет. Перед публикацией выполните обычный бекап, передайте отслеживаемые файлы и пересоберите `app`. Новые файлы: `service/sorting.py`, шаблон заголовков и `static/js/table-sort.js`. Проверьте совместную работу фильтров с сортировкой реестра, сохранение порядка при автообновлении заявок и независимую сортировку трёх таблиц отчёта. Пользовательская инструкция: [TABLES.md](../TABLES.md).
