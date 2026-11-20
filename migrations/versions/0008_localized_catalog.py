"""Add English addresses and enrich previously seeded demo catalogs."""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

GIST_ADDRESS = '광주광역시 북구 첨단과기로 123 (GIST)'
GIST_ADDRESS_EN = '123 Cheomdangwagi-ro, Buk-gu, Gwangju (GIST)'
GIST_DESCRIPTIONS = {
    'americano': ('에스프레소에 물을 더한 기본 커피', 'Espresso topped with water.'),
    'cafe-latte': ('에스프레소와 우유', 'Espresso with milk.'),
    'vanilla-latte': ('바닐라 시럽이 들어간 라떼', 'A latte with vanilla syrup.'),
    'grapefruit-ade': ('탄산이 들어간 자몽 음료, 아이스만 가능', 'Sparkling grapefruit, served iced.'),
    'croissant': ('버터 크루아상', 'A butter croissant.'),
    'cheesecake': ('오늘은 품절 (품절 처리 테스트용)', 'Sold out today (demo).'),
}


def updated_menu(menu, original, revised):
    if menu == original:
        return revised
    # Preserve the merchant's selection, order, price, availability, and uploads.
    before = {item["id"]: item for item in original}
    after = {item["id"]: item for item in revised}
    result = []
    for item in menu or []:
        old = before.get(item.get("id"))
        current = dict(item)
        if old and item.get("name") == old["name"]:
            new = after[item["id"]]
            for field in ("category", "options"):
                if item.get(field) == old.get(field):
                    current[field] = new[field]
            if item.get("description") == old["description"] and not item.get("descriptionEn"):
                current.update(description=new["description"], descriptionEn=new["descriptionEn"])
        result.append(current)
    return result


def upgrade():
    op.add_column("stores", sa.Column("address_en", sa.String(300), nullable=True))
    connection = op.get_bind()
    stores = sa.Table("stores", sa.MetaData(), autoload_with=connection)
    fixture = Path(__file__).resolve().parents[1] / "fixtures/0008_demo_catalog.json"
    for store_id, info in json.loads(fixture.read_text(encoding="utf-8")).items():
        target = stores.c.id == store_id
        row = connection.execute(stores.select().where(target).with_for_update()).mappings().first()
        if not row or row["address"] != info["address"] or row["name"] != info["name"]:
            continue
        changes = {"address_en": info["addressEn"]}
        if not row["accessibility"]:
            changes["accessibility"] = info["accessibility"]
        if (row["hours"], row["hours_en"]) == (info["hours"].removeprefix("매일 "), info["hoursEn"].removeprefix("Daily ")):
            changes.update(hours=info["hours"], hours_en=info["hoursEn"])
        changes["menu"] = updated_menu(row["menu"], info["originalMenu"], info["menu"])
        connection.execute(stores.update().where(target).values(**changes))

    target = stores.c.id == "gist-cafe"
    row = connection.execute(stores.select().where(target).with_for_update()).mappings().first()
    if row:
        menu = row["menu"] or []
        for item in menu:
            translation = GIST_DESCRIPTIONS.get(item.get("id"))
            if translation and item.get("description") == translation[0] and not item.get("descriptionEn"):
                item["descriptionEn"] = translation[1]
        changes = {"menu": menu}
        if row["address"] == GIST_ADDRESS:
            changes["address_en"] = GIST_ADDRESS_EN
        connection.execute(stores.update().where(target).values(**changes))


def downgrade():
    op.drop_column("stores", "address_en")
