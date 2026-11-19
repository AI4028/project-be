"""Allow a phone session and its order to belong directly to a store."""

from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('sessions', 'orders'):
        with op.batch_alter_table(name) as table:
            table.alter_column('kiosk_id', existing_type=sa.String(4), nullable=True)
    active_store_session = sa.text("kiosk_id IS NULL AND status = 'active'")
    op.create_index(
        'uq_active_store_session', 'sessions', ['device_id', 'store_id'],
        unique=True, sqlite_where=active_store_session, postgresql_where=active_store_session,
    )


def downgrade():
    connection = op.get_bind()
    if any(connection.scalar(sa.text(f'SELECT 1 FROM {name} WHERE kiosk_id IS NULL LIMIT 1'))
           for name in ('sessions', 'orders')):
        raise ValueError('Code-free ordering records exist. Preserve them before downgrading.')
    op.drop_index('uq_active_store_session', table_name='sessions')
    for name in ('orders', 'sessions'):
        with op.batch_alter_table(name) as table:
            table.alter_column('kiosk_id', existing_type=sa.String(4), nullable=False)
