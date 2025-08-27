"""Add recipe conversions table

Revision ID: recipe_conversions_v1
Revises: 1472c334cea8
Create Date: 2025-08-06 07:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'recipe_conversions_v1'
down_revision = '1472c334cea8'
branch_labels = None
depends_on = None


def upgrade():
    # Create recipe_conversion table
    op.create_table('recipe_conversion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_recipe_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversion_type', sa.String(length=20), nullable=False),
        sa.Column('original_servings', sa.Integer(), nullable=True),
        sa.Column('target_servings', sa.Integer(), nullable=True),
        sa.Column('is_metric_converted', sa.Boolean(), nullable=True),
        sa.Column('converted_ingredients', sa.Text(), nullable=False),
        sa.Column('converted_title', sa.String(length=200), nullable=False),
        sa.Column('conversion_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_saved', sa.Boolean(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['original_recipe_id'], ['recipe.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Set default values for boolean and integer columns
    with op.batch_alter_table('recipe_conversion', schema=None) as batch_op:
        batch_op.alter_column('is_metric_converted', server_default='0')
        batch_op.alter_column('is_saved', server_default='0')
        batch_op.alter_column('access_count', server_default='0')
        batch_op.alter_column('created_at', server_default=sa.text('CURRENT_TIMESTAMP'))


def downgrade():
    # Drop recipe_conversion table
    op.drop_table('recipe_conversion')
