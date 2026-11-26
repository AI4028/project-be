"""Keep the customer's dining preference on the order."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("dining_option", sa.String(16), nullable=True))


def downgrade():
    op.drop_column("orders", "dining_option")
