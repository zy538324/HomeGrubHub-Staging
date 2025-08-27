"""Add cholesterol fields for nutrition tracking

Revision ID: cholesterol_tracking_v1
Revises:
Create Date: 2025-09-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'cholesterol_tracking_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('nutrition_entries', sa.Column('cholesterol', sa.Float(), nullable=True))
    op.add_column('daily_nutrition_summaries', sa.Column('total_cholesterol', sa.Float(), nullable=True))
    op.add_column('nutrition_goals', sa.Column('daily_cholesterol', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('nutrition_entries', 'cholesterol')
    op.drop_column('daily_nutrition_summaries', 'total_cholesterol')
    op.drop_column('nutrition_goals', 'daily_cholesterol')
