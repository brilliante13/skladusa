"""
warehouse-sync — окремий проєкт костыля самовивозу для usaautoparts.

Тягне каталог з Хорошоп API, будує warehouses.json { slug: [склади] },
зберігає локально і (якщо налаштований R2) заливає в Cloudflare.

Запуск локально:
    py main.py

Змінні оточення (локально з .env, на GitHub Actions — з Secrets):
    USAAUTOPARTS_API_URL   = https://usaautoparts.com.ua
    USAAUTOPARTS_LOGIN     = ...
    USAAUTOPARTS_PASSWORD  = ...
    (опційно, для заливки)
    CLOUDFLARE_R2_ENDPOINT / _ACCESS_KEY / _SECRET_KEY / _BUCKET
"""

import os
import sys

import client
import exporter


def load_env():
    """Підтягує .env з папки проєкту (локально). На CI нічого не робить."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (here, os.getcwd()):
        path = os.path.join(d, ".env")
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
            print(f"[env] підхоплено {path}")
            return
    print("[env] .env не знайдено — беру змінні з оточення")


def main() -> int:
    load_env()

    base = os.environ.get("USAAUTOPARTS_API_URL")
    login = os.environ.get("USAAUTOPARTS_LOGIN")
    password = os.environ.get("USAAUTOPARTS_PASSWORD")
    if not all([base, login, password]):
        print("[!] нема USAAUTOPARTS_API_URL / LOGIN / PASSWORD")
        return 1

    print("[1/2] Тягну каталог з Хорошоп API...")
    c = client.HoroshopClient(base, login, password)
    raw_items = c.fetch_all_raw()
    print(f"      сирих товарів: {len(raw_items)}")

    print("[2/2] Будую warehouses.json...")
    mapping = exporter.export(raw_items)

    print(f"Готово. Товарів зі складами: {len(mapping)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
