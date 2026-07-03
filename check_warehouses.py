"""
Показує ВСІ склади (id + назва), що взагалі зустрічаються в каталозі,
незалежно від WAREHOUSE_ID_MAP. Відповідає на питання "де Львів?".

Запуск з папки проєкту:
    py check_warehouses.py
"""

import os
import sys
from collections import Counter

import client


def load_env():
    for d in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        path = os.path.join(d, ".env")
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
            return


def main():
    load_env()
    c = client.HoroshopClient(
        os.environ["USAAUTOPARTS_API_URL"],
        os.environ["USAAUTOPARTS_LOGIN"],
        os.environ["USAAUTOPARTS_PASSWORD"],
    )
    print("Тягну каталог...")
    items = c.fetch_all_raw()
    print(f"Сирих товарів: {len(items)}\n")

    # рахуємо кожен склад як (id, назва)
    seen = Counter()
    for it in items:
        raw = (it.get("characteristics") or {}).get("vNajavnostNaSklad") or []
        if not isinstance(raw, list):
            continue
        for w in raw:
            if isinstance(w, dict):
                wid = w.get("id")
                name = ((w.get("value") or {}).get("ua") or "").strip()
                seen[(wid, name)] += 1

    if not seen:
        print("У жодного товару немає заповненого vNajavnostNaSklad.")
        return

    print("УСІ склади, що зустрічаються в каталозі (id | назва | к-сть товарів):")
    for (wid, name), n in sorted(seen.items(), key=lambda x: -x[1]):
        print(f"  id={wid!r:>5}  {name:<20}  {n} товарів")

    print("\nЯкщо Львова тут немає — на ньому зараз немає товарів у наявності.")
    print("Якщо є, але з новим id — впишіть цей id у WAREHOUSE_ID_MAP (exporter.py).")


if __name__ == "__main__":
    sys.exit(main())
