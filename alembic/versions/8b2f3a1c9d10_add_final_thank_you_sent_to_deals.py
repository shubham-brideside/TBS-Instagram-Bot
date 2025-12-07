"""Add final_thank_you_sent to deals

Revision ID: 8b2f3a1c9d10
Revises: 11565c162c66
Create Date: 2025-08-11 03:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b2f3a1c9d10'
down_revision: Union[str, None] = '11565c162c66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add persistent flag to avoid duplicate final messages per deal
    op.add_column('deals', sa.Column('final_thank_you_sent', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    # Drop server default to rely on application default behavior going forward
    op.alter_column('deals', 'final_thank_you_sent', server_default=None)


def downgrade() -> None:
    op.drop_column('deals', 'final_thank_you_sent')

