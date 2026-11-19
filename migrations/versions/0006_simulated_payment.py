"""Record the simulated approval amount for prototype checkout."""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('simulated_approved_amount', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('orders') as table:
        table.drop_column('simulated_approved_amount')
