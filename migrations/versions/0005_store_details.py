"""Add a store's pickup location, photo, phone number and opening hours."""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

COLUMNS = (
    ('pickup_location', sa.Text()),
    ('image_url', sa.String(500)),
    ('phone', sa.String(30)),
    ('hours', sa.String(100)),
    ('hours_en', sa.String(100)),
)


def upgrade():
    for name, kind in COLUMNS:
        op.add_column('stores', sa.Column(name, kind, nullable=True))


def downgrade():
    with op.batch_alter_table('stores') as table:
        for name, _ in reversed(COLUMNS):
            table.drop_column(name)
