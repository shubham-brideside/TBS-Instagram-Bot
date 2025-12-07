"""add_contacted_to_to_instagram_users

Revision ID: add_contacted_to_to_instagram_users
Revises: add_unique_constraint_deal_name_contacted_to
Create Date: 2024-12-19 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_contacted_to_to_instagram_users'
down_revision = '75b7a4b42c57'
branch_labels = None
depends_on = None


def upgrade():
    # Add contacted_to column to instagram_users table
    op.add_column('instagram_users', sa.Column('contacted_to', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_instagram_users_contacted_to', 'instagram_users', 'brideside_users', ['contacted_to'], ['id'])


def downgrade():
    # Remove the foreign key and column
    op.drop_constraint('fk_instagram_users_contacted_to', 'instagram_users', type_='foreignkey')
    op.drop_column('instagram_users', 'contacted_to')
