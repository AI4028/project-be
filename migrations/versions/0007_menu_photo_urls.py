"""Move the former bundled menu thumbnails into existing menu records."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

# This is the set of item IDs that previously displayed a bundled photo.
PHOTO_IDS = {'americano', 'cafe-latte', 'vanilla-latte', 'grapefruit-ade'}


def upgrade():
    stores = sa.table('stores', sa.column('id', sa.String()), sa.column('menu', sa.JSON()))
    connection = op.get_bind()
    for store_id, menu in connection.execute(sa.select(stores.c.id, stores.c.menu).with_for_update()):
        changed = False
        for item in menu or []:
            if item.get('id') in PHOTO_IDS and not item.get('imageUrl'):
                item['imageUrl'] = f"/media/menu/{item['id']}.jpg"
                changed = True
        if changed:
            connection.execute(stores.update().where(stores.c.id == store_id).values(menu=menu))


def downgrade():
    # Older versions already support imageUrl. Keep any merchant edits.
    pass
