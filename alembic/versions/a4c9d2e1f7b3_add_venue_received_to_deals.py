"""add_venue_received_to_deals

Revision ID: a4c9d2e1f7b3
Revises: fix_bit_flags_001
Create Date: 2026-03-15 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4c9d2e1f7b3'
down_revision: Union[str, None] = 'fix_bit_flags_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deals',
        sa.Column('venue_received', sa.Boolean(), nullable=False, server_default=sa.text('0'))
    )
    op.execute("""
        UPDATE deals
        SET venue_received = 1
        WHERE venue IS NOT NULL AND TRIM(venue) <> ''
    """)
    op.alter_column('deals', 'venue_received', server_default=None)


def downgrade() -> None:
    op.drop_column('deals', 'venue_received')
