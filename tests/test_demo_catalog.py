import json
from collections import Counter
from pathlib import Path

from app.logic import build_order_lines
from scripts.create_kiosk import issue_kiosk_key
from scripts.seed import load_store


def test_seeded_catalog_is_searchable_and_prices_its_own_options(env):
    records = json.loads(Path("seed/development-stores.json").read_text(encoding="utf-8"))
    with env.db() as db:
        for record in records:
            load_store(db, record)
        key = issue_kiosk_key(db, "OR01")
    summaries = env.client.get("/stores").json()
    demos = [s for s in summaries if s["storeId"] in {r["storeId"] for r in records}]
    assert len({s["imageUrl"] for s in demos}) == 3
    assert all(s["addressEn"] and s["hoursEn"] and "distanceM" not in s for s in demos)
    matches = env.client.get("/places/search", params={"q": "Seongsu"}).json()["places"]
    assert any(s["storeId"] == "ongi-roastery" for s in matches)
    menu = env.client.get("/kiosk/state", headers={"Authorization": f"Bearer {key}"}).json()["store"]["menu"]
    assert Counter(m["category"] for m in menu) == {"커피": 3, "차·논커피": 2, "빵": 2}
    assert all(m["descriptionEn"] for m in menu)
    _, total = build_order_lines(menu, [{"itemId": "cafe-latte", "qty": 1,
                                         "options": {"temp": "ice", "extras": ["oat", "decaf"]}}])
    assert total == 6500
