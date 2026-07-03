"""
Клієнт Хорошоп API — авторизація і пагінація каталогу.
"""

import time

import requests

AUTH_ENDPOINT = "/api/auth/"
EXPORT_ENDPOINT = "/api/catalog/export/"
MAX_LIMIT = 500  # стеля Хорошопа за один запит


class HoroshopClient:
    def __init__(self, base_url: str, login: str, password: str):
        self.base = base_url.rstrip("/")
        self.login = login
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "warehouse-sync/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def auth(self):
        resp = self.session.post(
            self.base + AUTH_ENDPOINT,
            json={"login": self.login, "password": self.password},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = (
            (data.get("response") or {}).get("token")
            or data.get("token")
            or data.get("access_token")
        )
        if not token:
            raise RuntimeError(f"Не вдалось отримати токен. Відповідь: {data}")
        self.token = token
        return token

    def _fetch_batch(self, offset: int, limit: int) -> dict:
        url = self.base + EXPORT_ENDPOINT
        body = {"token": self.token, "offset": offset, "limit": limit}
        resp = self.session.post(url, json=body, timeout=60)

        # прострочений токен -> 200 зі status=ERROR -> перелогін
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise

        if data.get("status") == "ERROR":
            msg = (data.get("response") or {}).get("message", "")
            if "token" in msg.lower() or "auth" in msg.lower():
                self.auth()
                body["token"] = self.token
                resp = self.session.post(url, json=body, timeout=60)
                data = resp.json()

        resp.raise_for_status()
        return data

    def fetch_all_raw(self, page_limit: int = MAX_LIMIT) -> list[dict]:
        """Всі сирі товари каталогу."""
        self.auth()
        batch_size = min(page_limit, MAX_LIMIT)
        offset = 0
        items: list[dict] = []

        while True:
            payload = self._fetch_batch(offset, batch_size)
            if payload.get("status") != "OK":
                err = (payload.get("response") or {}).get("message", "")
                raise RuntimeError(f"API повернув помилку: {err or payload}")

            products = (payload.get("response") or {}).get("products") or []
            if not products:
                break

            items.extend(products)
            print(f"  батч offset={offset}: +{len(products)} (разом {len(items)})")

            if len(products) < batch_size:
                break
            offset += batch_size
            time.sleep(0.3)

        return items
