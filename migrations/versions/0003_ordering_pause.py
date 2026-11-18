"""Let staff pause phone ordering per store."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stores', sa.Column('ordering_paused', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    with op.batch_alter_table('stores') as table:
        table.drop_column('ordering_paused')
