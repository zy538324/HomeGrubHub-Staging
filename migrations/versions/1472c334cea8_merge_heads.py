"""merge heads

Revision ID: 1472c334cea8
Revises: advanced_features_v1, community_features
Create Date: 2025-07-29 13:21:55.469937

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1472c334cea8'
down_revision = ('advanced_features_v1', 'community_features')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
