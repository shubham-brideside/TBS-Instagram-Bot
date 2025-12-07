"""add_default_to_persons_is_deleted

Revision ID: add_default_is_deleted_001
Revises: fix_bit_flags_001
Create Date: 2025-12-04 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_default_is_deleted_001'
down_revision: Union[str, None] = 'fix_bit_flags_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add default value to is_deleted column in persons table.
    The column already exists but doesn't have a default value, causing insert errors.
    """
    # First, update any existing NULL values to 0 (shouldn't be any, but just in case)
    op.execute("UPDATE persons SET is_deleted = 0 WHERE is_deleted IS NULL")
    
    # Add default value to the column
    op.execute("""
        ALTER TABLE `persons` 
        MODIFY COLUMN `is_deleted` bit(1) NOT NULL DEFAULT 0
    """)


def downgrade() -> None:
    """
    Remove default value from is_deleted column (revert to NOT NULL without default).
    """
    op.execute("""
        ALTER TABLE `persons` 
        MODIFY COLUMN `is_deleted` bit(1) NOT NULL
    """)

