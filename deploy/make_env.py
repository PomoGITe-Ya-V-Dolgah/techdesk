"""Создает файл .env для работы techdesk в локальной сети.

    python deploy/make_env.py                 # IP определится автоматически
    python deploy/make_env.py 192.168.1.10    # указать IP сервера вручную
    python deploy/make_env.py 192.168.1.10 --postgres   # для Docker/PostgreSQL
    python deploy/make_env.py 192.168.1.10 --domain techdesk.example.ru
                                              # доступ из интернета по HTTPS (Caddy)

Существующий .env не перезаписывается (удалите его вручную, если нужно).
"""

import secrets
import socket
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


def lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main():
    if ENV_PATH.exists():
        print(f"{ENV_PATH} уже существует — не трогаю. Проверьте IP и адреса в нем вручную.")
        return

    argv = sys.argv[1:]
    domain = ""
    if "--domain" in argv:
        index = argv.index("--domain")
        if index + 1 >= len(argv):
            sys.exit("После --domain укажите домен, например techdesk.example.ru")
        domain = argv.pop(index + 1).strip().lower()
        argv.pop(index)
    args = [a for a in argv if not a.startswith("--")]
    use_postgres = "--postgres" in argv
    ip = args[0] if args else lan_ip()
    port = "8000"
    hostname = socket.gethostname().split(".")[0].lower()
    hosts = ["127.0.0.1", "localhost", ip, hostname]
    origins = [f"http://{h}:{port}" for h in hosts]
    public_url = f"http://{ip}:{port}"
    if domain:
        hosts.append(domain)
        origins.append(f"https://{domain}")
        public_url = f"https://{domain}"

    lines = [
        "# Создано deploy/make_env.py. Секретный ключ никому не передавайте.",
        f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}",
        "DJANGO_DEBUG=0",
        f"DJANGO_ALLOWED_HOSTS={','.join(hosts)}",
        f"DJANGO_CSRF_TRUSTED_ORIGINS={','.join(origins)}",
        f"PUBLIC_BASE_URL={public_url}",
        "# 1 — показывать демо-логины на странице входа (только для демонстрации)",
        "SHOW_DEMO_LOGINS=0",
        "DJANGO_TIME_ZONE=Europe/Moscow",
        # Windows + Caddy на том же ПК: приложение слушает только 127.0.0.1, снаружи — только HTTPS.
        # В Docker контейнер должен слушать 0.0.0.0 (порт наружу не публикуется).
        f"TECHDESK_HOST={'127.0.0.1' if domain and not use_postgres else '0.0.0.0'}",
        f"TECHDESK_PORT={port}",
        "",
        "# Почта для уведомлений (пусто — не отправлять)",
        "EMAIL_HOST=",
        "EMAIL_PORT=587",
        "EMAIL_HOST_USER=",
        "EMAIL_HOST_PASSWORD=",
        "EMAIL_USE_TLS=1",
        "DEFAULT_FROM_EMAIL=",
        "",
    ]
    if domain:
        lines += [
            "# Доступ из интернета через Caddy (HTTPS)",
            f"TECHDESK_DOMAIN={domain}",
            "DJANGO_HTTPS=1",
            "BEHIND_PROXY=1",
            f"DJANGO_ADMIN_URL=admin-{secrets.token_hex(4)}/",
            "",
        ]
    if use_postgres:
        lines += [
            "POSTGRES_DB=servicedesk",
            "POSTGRES_USER=servicedesk",
            f"POSTGRES_PASSWORD={secrets.token_urlsafe(24)}",
            "POSTGRES_HOST=db",
            "POSTGRES_PORT=5432",
        ]
    else:
        lines += ["# Пусто = SQLite (файл db.sqlite3 в папке проекта)", "POSTGRES_DB="]

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Создан {ENV_PATH}")
    print(f"Адрес для сотрудников: {public_url}")
    if domain:
        print("Адрес админки записан в .env (DJANGO_ADMIN_URL) — сохраните его.")
    print("Если у сервера другой IP — исправьте его в .env.")


if __name__ == "__main__":
    main()
