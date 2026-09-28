#!/bin/sh
# Резервная копия PostgreSQL из docker-compose.lan.yml в папку backups/.
# Добавить в cron ежедневно в 20:00:  0 20 * * * /path/to/techdesk/deploy/linux/backup.sh
set -e
cd "$(dirname "$0")/../.."
mkdir -p backups
. ./.env
FILE="backups/techdesk-$(date +%Y%m%d-%H%M).sql.gz"
docker compose -f docker-compose.lan.yml exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"
echo "Копия сохранена: $FILE"
# Храним последние 30 копий
ls -1t backups/techdesk-*.sql.gz | tail -n +31 | xargs -r rm --
