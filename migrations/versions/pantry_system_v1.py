"""Add pantry management tables

Revision ID: pantry_system_v1
Revises: 
Create Date: 2025-07-30 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'pantry_system_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create pantry management tables"""
    
    # Create pantry_categories table
    op.create_table('pantry_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True, default='fas fa-box'),
        sa.Column('color', sa.String(length=20), nullable=True, default='#6c757d'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create pantry_items table
    op.create_table('pantry_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('brand', sa.String(length=50), nullable=True),
        sa.Column('barcode', sa.String(length=50), nullable=True),
        sa.Column('current_quantity', sa.Float(), nullable=False, default=0.0),
        sa.Column('unit', sa.String(length=20), nullable=False, default='units'),
        sa.Column('minimum_quantity', sa.Float(), nullable=True, default=1.0),
        sa.Column('ideal_quantity', sa.Float(), nullable=True, default=5.0),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('storage_location', sa.String(length=50), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('days_until_expiry_alert', sa.Integer(), nullable=True, default=7),
        sa.Column('cost_per_unit', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('last_purchased', sa.Date(), nullable=True),
        sa.Column('purchase_frequency_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_running_low', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_expired', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['pantry_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for pantry_items
    op.create_index('ix_pantry_items_user_id', 'pantry_items', ['user_id'])
    op.create_index('ix_pantry_items_is_running_low', 'pantry_items', ['is_running_low'])
    op.create_index('ix_pantry_items_is_expired', 'pantry_items', ['is_expired'])
    
    # Create pantry_usage_logs table
    op.create_table('pantry_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('quantity_change', sa.Float(), nullable=False),
        sa.Column('old_quantity', sa.Float(), nullable=False),
        sa.Column('new_quantity', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=True),
        sa.Column('meal_plan_entry_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['pantry_items.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for pantry_usage_logs
    op.create_index('ix_pantry_usage_logs_user_id', 'pantry_usage_logs', ['user_id'])
    op.create_index('ix_pantry_usage_logs_timestamp', 'pantry_usage_logs', ['timestamp'])
    
    # Create shopping_list_items table
    op.create_table('shopping_list_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('item_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('quantity_needed', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('pantry_item_id', sa.Integer(), nullable=True),
        sa.Column('recipe_id', sa.Integer(), nullable=True),
        sa.Column('meal_plan_id', sa.Integer(), nullable=True),
        sa.Column('is_purchased', sa.Boolean(), nullable=True, default=False),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('actual_cost', sa.Float(), nullable=True),
        sa.Column('store_section', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=3),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('purchased_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pantry_item_id'], ['pantry_items.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for shopping_list_items
    op.create_index('ix_shopping_list_items_user_id', 'shopping_list_items', ['user_id'])
    op.create_index('ix_shopping_list_items_is_purchased', 'shopping_list_items', ['is_purchased'])
    
    # Insert default pantry categories
    connection = op.get_bind()
    default_categories = [
        {'name': 'Dairy & Eggs', 'icon': 'fas fa-cheese', 'color': '#ffc107', 'sort_order': 1},
        {'name': 'Meat & Seafood', 'icon': 'fas fa-fish', 'color': '#dc3545', 'sort_order': 2},
        {'name': 'Fresh Produce', 'icon': 'fas fa-apple-alt', 'color': '#28a745', 'sort_order': 3},
        {'name': 'Pantry Staples', 'icon': 'fas fa-box', 'color': '#6f42c1', 'sort_order': 4},
        {'name': 'Frozen Foods', 'icon': 'fas fa-snowflake', 'color': '#17a2b8', 'sort_order': 5},
        {'name': 'Beverages', 'icon': 'fas fa-glass-whiskey', 'color': '#fd7e14', 'sort_order': 6},
        {'name': 'Snacks', 'icon': 'fas fa-cookie-bite', 'color': '#e83e8c', 'sort_order': 7},
        {'name': 'Spices & Herbs', 'icon': 'fas fa-pepper-hot', 'color': '#20c997', 'sort_order': 8},
        {'name': 'Baking Supplies', 'icon': 'fas fa-birthday-cake', 'color': '#6f42c1', 'sort_order': 9},
        {'name': 'Condiments', 'icon': 'fas fa-wine-bottle', 'color': '#6c757d', 'sort_order': 10}
    ]
    
    for category in default_categories:
        connection.execute(
            text("INSERT INTO pantry_categories (name, icon, color, sort_order) VALUES (:name, :icon, :color, :sort_order)"),
            category
        )


def downgrade():
    """Drop pantry management tables"""
    op.drop_index('ix_shopping_list_items_is_purchased', table_name='shopping_list_items')
    op.drop_index('ix_shopping_list_items_user_id', table_name='shopping_list_items')
    op.drop_table('shopping_list_items')
    
    op.drop_index('ix_pantry_usage_logs_timestamp', table_name='pantry_usage_logs')
    op.drop_index('ix_pantry_usage_logs_user_id', table_name='pantry_usage_logs')
    op.drop_table('pantry_usage_logs')
    
    op.drop_index('ix_pantry_items_is_expired', table_name='pantry_items')
    op.drop_index('ix_pantry_items_is_running_low', table_name='pantry_items')
    op.drop_index('ix_pantry_items_user_id', table_name='pantry_items')
    op.drop_table('pantry_items')
    
    op.drop_table('pantry_categories')
