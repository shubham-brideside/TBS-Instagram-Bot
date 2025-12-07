"""fix_bit_to_tinyint_for_deal_flags

Revision ID: fix_bit_flags_001
Revises: 75b7a4b42c57
Create Date: 2025-12-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_bit_flags_001'
down_revision: Union[str, None] = '75b7a4b42c57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix MySQL bit(1) type conversion issue by changing to tinyint(1).
    This ensures proper boolean conversion in SQLAlchemy/PyMySQL.
    """
    # Convert bit(1) columns to tinyint(1) for proper boolean handling
    # Using raw SQL to ensure proper type conversion
    op.execute("""
        ALTER TABLE `deals` 
        MODIFY COLUMN `contact_number_asked` tinyint(1) DEFAULT NULL,
        MODIFY COLUMN `event_date_asked` tinyint(1) DEFAULT NULL,
        MODIFY COLUMN `venue_asked` tinyint(1) DEFAULT NULL,
        MODIFY COLUMN `final_thank_you_sent` tinyint(1) DEFAULT NULL
    """)


def downgrade() -> None:
    """
    Revert back to bit(1) type (though this shouldn't be necessary).
    """
    op.execute("""
        ALTER TABLE `deals` 
        MODIFY COLUMN `contact_number_asked` bit(1) DEFAULT NULL,
        MODIFY COLUMN `event_date_asked` bit(1) DEFAULT NULL,
        MODIFY COLUMN `venue_asked` bit(1) DEFAULT NULL,
        MODIFY COLUMN `final_thank_you_sent` bit(1) DEFAULT NULL
    """)

