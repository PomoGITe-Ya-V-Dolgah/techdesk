#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/deploy/techdesk
backup_dir="$project_dir/backups"
umask 077
mkdir -p -m 700 "$backup_dir"

exec 9>"$backup_dir/.backup.lock"
flock -n 9 || exit 0

cd "$project_dir"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$backup_dir/techdesk-$stamp.sql.gz"
temporary=$(mktemp "$backup_dir/.techdesk-$stamp.XXXXXX")
trap 'rm -f "$temporary"' EXIT

docker compose -f compose.vps.yml -p techdesk exec -T db \
  sh -c 'exec pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip -9 > "$temporary"
test -s "$temporary"
gzip -t "$temporary"
mv "$temporary" "$target"

find "$backup_dir" -maxdepth 1 -type f -name 'techdesk-*.sql.gz' -mmin +10080 -delete
echo "$(date -u +%FT%TZ) Backup saved: $target"
