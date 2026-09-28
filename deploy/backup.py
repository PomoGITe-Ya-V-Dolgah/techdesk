"""Резервная копия базы techdesk (SQLite) в папку backups/.

    python deploy/backup.py

Копия делается средствами SQLite, поэтому ее можно запускать при работающем
сервере. Хранятся последние KEEP копий. Для PostgreSQL используйте
deploy/linux/backup.sh (pg_dump).
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
KEEP = 30


def main():
    if os.getenv("POSTGRES_DB"):
        sys.exit("Используется PostgreSQL — делайте копию через pg_dump (deploy/linux/backup.sh).")
    db_path = Path(os.getenv("SQLITE_PATH") or BASE_DIR / "db.sqlite3")
    if not db_path.exists():
        sys.exit(f"База не найдена: {db_path}")

    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    target = backup_dir / f"techdesk-{datetime.now():%Y%m%d-%H%M}.sqlite3"

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(target)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    print(f"Копия сохранена: {target}")

    for old in sorted(backup_dir.glob("techdesk-*.sqlite3"))[:-KEEP]:
        old.unlink()


if __name__ == "__main__":
    main()
