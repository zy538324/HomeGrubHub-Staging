"""Remove family connection fields for home-only subscription model

Revision ID: remove_family_connections
Revises: advanced_features_v1
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_family_connections'
down_revision = 'advanced_features_v1'
branch_labels = None
depends_on = None


def upgrade():
    """Remove family connection fields since we only support Home users now"""
    
    # Remove family_connection_id column from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('family_connection_id')


def downgrade():
    """Add back family connection fields"""
    
    # Add back family_connection_id column
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('family_connection_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_user_family_connection', 'user', ['family_connection_id'], ['id'])
