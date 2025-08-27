"""Add missing columns to meal_plan and shopping_list tables

Revision ID: fix_missing_columns
Revises: 1472c334cea8
Create Date: 2025-07-29 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'fix_missing_columns'
down_revision = '1472c334cea8'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to meal_plan table
    with op.batch_alter_table('meal_plan', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, default=True))
        batch_op.add_column(sa.Column('is_template', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Add missing columns to shopping_list table
    with op.batch_alter_table('shopping_list', schema=None) as batch_op:
        batch_op.add_column(sa.Column('meal_plan_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('generated_from_pantry', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('is_completed', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))
        
    # Add foreign key constraint for meal_plan_id
    with op.batch_alter_table('shopping_list', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_shopping_list_meal_plan_id', 'meal_plan', ['meal_plan_id'], ['id'])

    # Update existing records with default values
    op.execute("UPDATE meal_plan SET is_active = 1 WHERE is_active IS NULL")
    op.execute("UPDATE meal_plan SET is_template = 0 WHERE is_template IS NULL")
    op.execute("UPDATE meal_plan SET created_at = datetime('now') WHERE created_at IS NULL")
    op.execute("UPDATE meal_plan SET updated_at = datetime('now') WHERE updated_at IS NULL")
    
    op.execute("UPDATE shopping_list SET generated_from_pantry = 0 WHERE generated_from_pantry IS NULL")
    op.execute("UPDATE shopping_list SET is_completed = 0 WHERE is_completed IS NULL")


def downgrade():
    # Remove foreign key constraint
    with op.batch_alter_table('shopping_list', schema=None) as batch_op:
        batch_op.drop_constraint('fk_shopping_list_meal_plan_id', type_='foreignkey')
    
    # Remove columns from shopping_list table
    with op.batch_alter_table('shopping_list', schema=None) as batch_op:
        batch_op.drop_column('completed_at')
        batch_op.drop_column('is_completed')
        batch_op.drop_column('generated_from_pantry')
        batch_op.drop_column('meal_plan_id')

    # Remove columns from meal_plan table
    with op.batch_alter_table('meal_plan', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('is_template')
        batch_op.drop_column('is_active')
        batch_op.drop_column('description')
