"""Add advanced features models

Revision ID: advanced_features_v1
Revises: [previous_revision]
Create Date: 2025-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = 'advanced_features_v1'
down_revision = None  # Update this with the actual last revision
branch_labels = None
depends_on = None


def upgrade():
    # Create nutrition_profile table
    op.create_table('nutrition_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('calories', sa.Float(), nullable=True),
        sa.Column('protein_g', sa.Float(), nullable=True),
        sa.Column('carbs_g', sa.Float(), nullable=True),
        sa.Column('fat_g', sa.Float(), nullable=True),
        sa.Column('fiber_g', sa.Float(), nullable=True),
        sa.Column('sugar_g', sa.Float(), nullable=True),
        sa.Column('sodium_mg', sa.Float(), nullable=True),
        sa.Column('potassium_mg', sa.Float(), nullable=True),
        sa.Column('iron_mg', sa.Float(), nullable=True),
        sa.Column('calcium_mg', sa.Float(), nullable=True),
        sa.Column('vitamin_c_mg', sa.Float(), nullable=True),
        sa.Column('vitamin_d_ug', sa.Float(), nullable=True),
        sa.Column('protein_percentage', sa.Float(), nullable=True),
        sa.Column('carbs_percentage', sa.Float(), nullable=True),
        sa.Column('fat_percentage', sa.Float(), nullable=True),
        sa.Column('is_high_protein', sa.Boolean(), nullable=True),
        sa.Column('is_low_carb', sa.Boolean(), nullable=True),
        sa.Column('is_high_fiber', sa.Boolean(), nullable=True),
        sa.Column('is_low_sodium', sa.Boolean(), nullable=True),
        sa.Column('is_iron_rich', sa.Boolean(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create dietary_restriction table
    op.create_table('dietary_restriction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create equipment table
    op.create_table('equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_common', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create seasonal_tag table
    op.create_table('seasonal_tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('start_month', sa.Integer(), nullable=True),
        sa.Column('end_month', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create ingredient table
    op.create_table('ingredient',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('common_unit', sa.String(length=20), nullable=True),
        sa.Column('calories_per_100g', sa.Float(), nullable=True),
        sa.Column('protein_per_100g', sa.Float(), nullable=True),
        sa.Column('carbs_per_100g', sa.Float(), nullable=True),
        sa.Column('fat_per_100g', sa.Float(), nullable=True),
        sa.Column('typical_shelf_life_days', sa.Integer(), nullable=True),
        sa.Column('storage_location', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create store table
    op.create_table('store',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('chain', sa.String(length=50), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('api_endpoint', sa.String(length=200), nullable=True),
        sa.Column('has_api', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create meal_plan table
    op.create_table('meal_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preferred_meal_types', sa.JSON(), nullable=True),
        sa.Column('max_prep_time', sa.Integer(), nullable=True),
        sa.Column('max_cook_time', sa.Integer(), nullable=True),
        sa.Column('preferred_difficulty', sa.String(length=20), nullable=True),
        sa.Column('max_cost_per_serving', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('preferred_stores', sa.JSON(), nullable=True),
        sa.Column('daily_calorie_target', sa.Integer(), nullable=True),
        sa.Column('protein_percentage_target', sa.Float(), nullable=True),
        sa.Column('carb_percentage_target', sa.Float(), nullable=True),
        sa.Column('fat_percentage_target', sa.Float(), nullable=True),
        sa.Column('allergens', sa.JSON(), nullable=True),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create pantry_item table
    op.create_table('pantry_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('store', sa.String(length=50), nullable=True),
        sa.Column('is_running_low', sa.Boolean(), nullable=True),
        sa.Column('is_expired', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create shopping_list table
    op.create_table('shopping_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('meal_plan_id', sa.Integer(), nullable=True),
        sa.Column('generated_from_pantry', sa.Boolean(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plan.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ingredient_price table
    op.create_table('ingredient_price',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price_per_100g', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=True),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('is_organic', sa.Boolean(), nullable=True),
        sa.Column('is_on_sale', sa.Boolean(), nullable=True),
        sa.Column('date_recorded', sa.Date(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ),
        sa.ForeignKeyConstraint(['store_id'], ['store.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ingredient_substitution table
    op.create_table('ingredient_substitution',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_ingredient_id', sa.Integer(), nullable=False),
        sa.Column('substitute_ingredient_id', sa.Integer(), nullable=False),
        sa.Column('ratio', sa.Float(), nullable=True),
        sa.Column('ratio_notes', sa.String(length=200), nullable=True),
        sa.Column('dietary_reason', sa.String(length=50), nullable=True),
        sa.Column('cooking_method', sa.String(length=50), nullable=True),
        sa.Column('taste_impact', sa.String(length=20), nullable=True),
        sa.Column('texture_impact', sa.String(length=20), nullable=True),
        sa.Column('nutrition_impact', sa.String(length=20), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['original_ingredient_id'], ['ingredient.id'], ),
        sa.ForeignKeyConstraint(['substitute_ingredient_id'], ['ingredient.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create meal_plan_entry table
    op.create_table('meal_plan_entry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meal_plan_id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('planned_date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(length=20), nullable=False),
        sa.Column('planned_servings', sa.Integer(), nullable=True),
        sa.Column('scaling_factor', sa.Float(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plan.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create shopping_list_item table
    op.create_table('shopping_list_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shopping_list_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('is_purchased', sa.Boolean(), nullable=True),
        sa.Column('purchased_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('store', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ),
        sa.ForeignKeyConstraint(['shopping_list_id'], ['shopping_list.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create association tables
    op.create_table('user_dietary_restrictions',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('restriction_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['restriction_id'], ['dietary_restriction.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'restriction_id')
    )

    op.create_table('recipe_dietary_compliance',
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('restriction_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.ForeignKeyConstraint(['restriction_id'], ['dietary_restriction.id'], ),
        sa.PrimaryKeyConstraint('recipe_id', 'restriction_id')
    )

    op.create_table('recipe_equipment',
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('recipe_id', 'equipment_id')
    )

    op.create_table('user_equipment',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'equipment_id')
    )

    op.create_table('recipe_seasonal_tags',
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('seasonal_tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.ForeignKeyConstraint(['seasonal_tag_id'], ['seasonal_tag.id'], ),
        sa.PrimaryKeyConstraint('recipe_id', 'seasonal_tag_id')
    )

    # Add new columns to existing recipe table
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cost_per_serving', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('batch_cooking_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('freezing_instructions', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('skill_level', sa.String(length=20), nullable=True))

    # Create indexes for performance
    op.create_index('idx_nutrition_profile_recipe', 'nutrition_profile', ['recipe_id'])
    op.create_index('idx_pantry_user_ingredient', 'pantry_item', ['user_id', 'ingredient_id'])
    op.create_index('idx_meal_plan_entry_date', 'meal_plan_entry', ['planned_date'])
    op.create_index('idx_ingredient_price_ingredient', 'ingredient_price', ['ingredient_id'])
    op.create_index('idx_ingredient_price_date', 'ingredient_price', ['date_recorded'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_ingredient_price_date', table_name='ingredient_price')
    op.drop_index('idx_ingredient_price_ingredient', table_name='ingredient_price')
    op.drop_index('idx_meal_plan_entry_date', table_name='meal_plan_entry')
    op.drop_index('idx_pantry_user_ingredient', table_name='pantry_item')
    op.drop_index('idx_nutrition_profile_recipe', table_name='nutrition_profile')

    # Remove columns from recipe table
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_column('skill_level')
        batch_op.drop_column('freezing_instructions')
        batch_op.drop_column('batch_cooking_notes')
        batch_op.drop_column('estimated_cost')
        batch_op.drop_column('cost_per_serving')

    # Drop association tables
    op.drop_table('recipe_seasonal_tags')
    op.drop_table('user_equipment')
    op.drop_table('recipe_equipment')
    op.drop_table('recipe_dietary_compliance')
    op.drop_table('user_dietary_restrictions')

    # Drop main tables
    op.drop_table('shopping_list_item')
    op.drop_table('meal_plan_entry')
    op.drop_table('ingredient_substitution')
    op.drop_table('ingredient_price')
    op.drop_table('shopping_list')
    op.drop_table('pantry_item')
    op.drop_table('user_preferences')
    op.drop_table('meal_plan')
    op.drop_table('store')
    op.drop_table('ingredient')
    op.drop_table('seasonal_tag')
    op.drop_table('equipment')
    op.drop_table('dietary_restriction')
    op.drop_table('nutrition_profile')
