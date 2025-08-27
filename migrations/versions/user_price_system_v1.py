"""Add user-contributed price system

Revision ID: user_price_system_v1
Revises: 
Create Date: 2025-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'user_price_system_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user_contributed_prices table
    op.create_table('user_contributed_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shop_name', sa.String(length=100), nullable=False),
        sa.Column('brand_name', sa.String(length=100), nullable=True),
        sa.Column('item_name', sa.String(length=200), nullable=False),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('price_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('shop_location', sa.String(length=200), nullable=False),
        sa.Column('postcode', sa.String(length=10), nullable=True),
        sa.Column('postcode_area', sa.String(length=4), nullable=True),
        sa.Column('submitted_by', sa.Integer(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verification_count', sa.Integer(), nullable=True),
        sa.Column('is_flagged', sa.Boolean(), nullable=True),
        sa.Column('flag_reason', sa.String(length=100), nullable=True),
        sa.Column('normalized_item_name', sa.String(length=200), nullable=False),
        sa.Column('normalized_shop_name', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['submitted_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_item_shop_location', 'user_contributed_prices', ['normalized_item_name', 'normalized_shop_name', 'postcode_area'])
    op.create_index('idx_recent_verified', 'user_contributed_prices', ['submitted_at', 'is_verified'])
    op.create_index('idx_location_item', 'user_contributed_prices', ['postcode_area', 'normalized_item_name'])
    op.create_index(op.f('ix_user_contributed_prices_item_name'), 'user_contributed_prices', ['item_name'])
    op.create_index(op.f('ix_user_contributed_prices_normalized_item_name'), 'user_contributed_prices', ['normalized_item_name'])
    op.create_index(op.f('ix_user_contributed_prices_normalized_shop_name'), 'user_contributed_prices', ['normalized_shop_name'])
    op.create_index(op.f('ix_user_contributed_prices_postcode'), 'user_contributed_prices', ['postcode'])
    op.create_index(op.f('ix_user_contributed_prices_postcode_area'), 'user_contributed_prices', ['postcode_area'])
    op.create_index(op.f('ix_user_contributed_prices_shop_name'), 'user_contributed_prices', ['shop_name'])
    op.create_index(op.f('ix_user_contributed_prices_submitted_at'), 'user_contributed_prices', ['submitted_at'])
    op.create_index(op.f('ix_user_contributed_prices_is_verified'), 'user_contributed_prices', ['is_verified'])
    
    # Create price_verifications table
    op.create_table('price_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('price_id', sa.Integer(), nullable=False),
        sa.Column('verified_by', sa.Integer(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.Column('is_accurate', sa.Boolean(), nullable=False),
        sa.Column('comment', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['price_id'], ['user_contributed_prices.id'], ),
        sa.ForeignKeyConstraint(['verified_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('price_id', 'verified_by', name='unique_user_verification')
    )
    
    # Create shop_locations table
    op.create_table('shop_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shop_name', sa.String(length=100), nullable=False),
        sa.Column('normalized_shop_name', sa.String(length=100), nullable=False),
        sa.Column('address_line', sa.String(length=200), nullable=False),
        sa.Column('postcode', sa.String(length=10), nullable=False),
        sa.Column('postcode_area', sa.String(length=4), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('town', sa.String(length=100), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=True),
        sa.Column('chain_name', sa.String(length=100), nullable=True),
        sa.Column('store_type', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for shop_locations
    op.create_index(op.f('ix_shop_locations_normalized_shop_name'), 'shop_locations', ['normalized_shop_name'])
    op.create_index(op.f('ix_shop_locations_postcode'), 'shop_locations', ['postcode'])
    op.create_index(op.f('ix_shop_locations_postcode_area'), 'shop_locations', ['postcode_area'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('shop_locations')
    op.drop_table('price_verifications') 
    op.drop_table('user_contributed_prices')
