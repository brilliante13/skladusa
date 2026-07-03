# warehouse-sync

Костыль самовивозу для usaautoparts.com.ua.

Тягне каталог із Хорошоп API, вилучає наявність на складі
(`vNajavnostNaSklad`) і будує `docs/warehouses.json` виду:

```json
{"41008494446-bmw-3-series-...": ["vyshneve"], "...": ["kyiv","vyshneve"]}
```

Ключ = slug товару (збігається зі slug у href кошика на сайті).
Значення = склади, де товар реально в наявності.

GitHub Pages віддає `docs/warehouses.json`, сайт читає його у чекауті
й лишає в самовивозі лише ті точки, де товар фактично є.

## Склади (id з API/довідника Хорошоп)

    1 = Львів
    2 = Київ
    3 = Вишневе

Мапа в `exporter.py` -> `WAREHOUSE_ID_MAP`.

## Структура

```
warehouse-sync/
├── main.py              # entry-point
├── client.py            # клієнт Хорошоп API
├── exporter.py          # склади + JSON (+ опційно R2)
├── check_warehouses.py  # діагностика: усі склади з назвами
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   └── warehouses.json  # <- це віддає GitHub Pages (комітиться автоматично)
└── .github/workflows/sync.yml
```

## Локальний запуск

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env         # і вписати пароль Хорошоп
python main.py                 # запише docs/warehouses.json
```

## Публікація через GitHub Pages (без картки)

1. Створити ПУБЛІЧНИЙ репозиторій на GitHub, залити ці файли.
2. Додати Secrets: Settings -> Secrets and variables -> Actions:
   - USAAUTOPARTS_API_URL   = https://usaautoparts.com.ua
   - USAAUTOPARTS_LOGIN     = API
   - USAAUTOPARTS_PASSWORD  = <новий пароль>
3. Увімкнути Pages: Settings -> Pages ->
   Source: "Deploy from a branch", Branch: main, Folder: /docs -> Save.
4. Через хвилину файл буде доступний за адресою:
   https://<нік>.github.io/<repo>/warehouses.json
5. Workflow (sync.yml) запускається кожні 30 хв, оновлює docs/warehouses.json
   і комітить його назад. Pages підхоплює автоматично.
   Перший запуск можна зробити вручну: вкладка Actions -> warehouse-sync -> Run workflow.

`.env` у репозиторій НЕ потрапляє (він у .gitignore). Секрети — лише в GitHub Secrets.

## Примітка про кеш

GitHub Pages кешує файли (оновлення підхоплюється за хвилини).
Фронтовий скрипт додає до URL версійний параметр (?v=timestamp),
щоб браузер брав свіжу версію.
