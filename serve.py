"""Запуск techdesk для локальной сети (Windows, Linux, macOS).

Использует waitress — готовый к работе WSGI-сервер на чистом Python.
В отличие от `manage.py runserver`, он предназначен для постоянной работы
и принимает подключения с других компьютеров.

    python serve.py

Адрес и порт задаются в .env: TECHDESK_HOST (по умолчанию 0.0.0.0 — все
сетевые интерфейсы) и TECHDESK_PORT (по умолчанию 8000).
"""

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def lan_ip() -> str:
    """IP этого компьютера в локальной сети (пакеты никуда не отправляются)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main():
    from waitress import serve

    from config.wsgi import application

    host = os.getenv("TECHDESK_HOST", "0.0.0.0")
    port = int(os.getenv("TECHDESK_PORT", "8000"))
    print("techdesk запущен.")
    print(f"  На этом компьютере:  http://127.0.0.1:{port}")
    if host in ("127.0.0.1", "localhost"):
        print(f"  Для сотрудников: {os.getenv('PUBLIC_BASE_URL') or '(только этот компьютер)'}")
    else:
        print(f"  С других компьютеров: http://{lan_ip()}:{port}")
    print("Остановить: Ctrl+C")
    options = {}
    if os.getenv("BEHIND_PROXY", "0") == "1":
        # За Caddy: доверяем его заголовкам X-Forwarded-For/Proto, чтобы Django
        # видел реальный IP клиента и понимал, что соединение шло по HTTPS.
        # Безопасно, потому что в этом режиме порт приложения закрыт снаружи
        # (Windows: слушаем 127.0.0.1, Docker: порт не публикуется).
        options = {
            "trusted_proxy": "*",
            "trusted_proxy_count": 1,
            "trusted_proxy_headers": {"x-forwarded-for", "x-forwarded-proto"},
        }
        print("Режим за обратным прокси (HTTPS через Caddy).")
    serve(application, host=host, port=port, threads=8, **options)


if __name__ == "__main__":
    main()
