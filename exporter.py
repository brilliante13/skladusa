"""
Вилучення складів, побудова warehouses.json, заливка в Cloudflare R2.

warehouses.json — плаский словник для костыля самовивозу на сайті:
    { "<slug>": ["vyshneve"], "<slug2>": ["kyiv", "vyshneve"], ... }

Ключ  = slug товару (збігається зі slug у href кошика на сайті).
Значення = склади, де товар РЕАЛЬНО в наявності (vNajavnostNaSklad
заповнюється лише за фактичного залишку).
"""

import json
import os


# ============================================================
# МАПА СКЛАДІВ: id з API (vNajavnostNaSklad[].id) -> код для фронта.
#   id 3 = Вишневе — ПІДТВЕРДЖЕНО.
#   Київ і Львів — id підтвердьте з логів першого прогону
#   (рядок "НЕВІДОМІ id складів").
# ============================================================
WAREHOUSE_ID_MAP = {
    1: "lviv",       # підтверджено (API + довідник Хорошоп)
    2: "kyiv",       # підтверджено
    3: "vyshneve",   # підтверджено
}


def extract_warehouses(item: dict) -> list[str]:
    chars = item.get("characteristics") or {}
    raw = chars.get("vNajavnostNaSklad") or []
    if not isinstance(raw, list):
        return []
    codes = []
    for w in raw:
        if isinstance(w, dict):
            code = WAREHOUSE_ID_MAP.get(w.get("id"))
            if code:
                codes.append(code)
    return sorted(set(codes))


def build_map(raw_items: list[dict]) -> dict:
    out: dict[str, list[str]] = {}
    no_slug = no_wh = 0
    unknown_ids: set = set()

    for it in raw_items:
        wh = extract_warehouses(it)
        slug = (it.get("slug") or "").strip()

        raw = (it.get("characteristics") or {}).get("vNajavnostNaSklad") or []
        if isinstance(raw, list):
            for w in raw:
                if isinstance(w, dict) and w.get("id") is not None \
                        and w.get("id") not in WAREHOUSE_ID_MAP:
                    unknown_ids.add(w.get("id"))

        if not wh:
            no_wh += 1
            continue
        if not slug:
            no_slug += 1
            continue

        out[slug] = sorted(set(out.get(slug, [])) | set(wh))

    print(f"warehouses.json: {len(out)} товарів зі складами "
          f"(без складу={no_wh}, без slug={no_slug})")
    if unknown_ids:
        print(f"  [!] НЕВІДОМІ id складів: {sorted(unknown_ids)} — впишіть у WAREHOUSE_ID_MAP")

    dist: dict[str, int] = {}
    for warehouses in out.values():
        for w in warehouses:
            dist[w] = dist.get(w, 0) + 1
    if dist:
        print("  розподіл по складах:")
        for w, n in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    {w}: {n}")

    return out


def write_local(mapping: dict, path: str = "warehouses.json") -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, separators=(",", ":"))
    print(f"warehouses.json записано локально: {os.path.abspath(path)}")
    return path


def upload_r2(mapping: dict, env: dict | None = None) -> bool:
    env = env or os.environ
    endpoint = env.get("CLOUDFLARE_R2_ENDPOINT")
    access_key = env.get("CLOUDFLARE_R2_ACCESS_KEY")
    secret_key = env.get("CLOUDFLARE_R2_SECRET_KEY")
    bucket = env.get("CLOUDFLARE_R2_BUCKET")
    object_key = env.get("R2_OBJECT_KEY", "warehouses.json")

    if not all([endpoint, access_key, secret_key, bucket]):
        print("R2 не налаштований (нема CLOUDFLARE_R2_* у .env) — заливку пропущено.")
        return False

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("[!] нема boto3. Встановіть: pip install boto3")
        return False

    body = json.dumps(mapping, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    ).put_object(
        Bucket=bucket,
        Key=object_key,
        Body=body,
        ContentType="application/json; charset=utf-8",
        CacheControl="public, max-age=300",
    )
    print(f"warehouses.json залито в R2: {bucket}/{object_key} ({len(body)} байт)")
    return True


def export(raw_items: list[dict], env: dict | None = None,
           local_path: str | None = None) -> dict:
    """build -> файл для GitHub Pages (docs/warehouses.json) -> R2 (якщо є).

    За замовчуванням пише у docs/warehouses.json — саме цю папку віддає
    GitHub Pages. Шлях можна перевизначити через OUTPUT_PATH у оточенні
    або аргументом local_path.
    """
    env = env or os.environ
    if local_path is None:
        local_path = env.get("OUTPUT_PATH", "docs/warehouses.json")

    mapping = build_map(raw_items)

    # переконатись, що папка існує (docs/ може ще не бути)
    parent = os.path.dirname(local_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    write_local(mapping, local_path)
    upload_r2(mapping, env)   # тихо пропускається, якщо R2 не налаштований
    return mapping
