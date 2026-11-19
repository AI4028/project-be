"""Persist the order submission result for safe retries."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sessions', sa.Column('submission', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('sessions') as table:
        table.drop_column('submission')
