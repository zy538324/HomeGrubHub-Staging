"""Add moderation and community features

Revision ID: community_features
Revises: 
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'community_features'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add moderation fields to Recipe table
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=True, default=True))
        batch_op.add_column(sa.Column('is_featured', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('featured_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('moderation_notes', sa.Text(), nullable=True))

    # Add moderation field to RecipeReview table
    with op.batch_alter_table('recipe_review', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=True, default=True))

    # Create new community tables
    op.create_table('recipe_photo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=256), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('recipe_collection',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('collection_recipe',
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['collection_id'], ['recipe_collection.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.PrimaryKeyConstraint('collection_id', 'recipe_id')
    )

    op.create_table('follow',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('followed_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['followed_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['follower_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'followed_id', name='unique_follow')
    )

    op.create_table('challenge',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('challenge_type', sa.String(length=50), nullable=True, default='weekly'),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('challenge_participation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=True),
        sa.Column('submission_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenge.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('challenge_id', 'user_id', name='unique_participation')
    )

    # Update existing recipes to have default values
    op.execute("UPDATE recipe SET is_approved = 1 WHERE is_approved IS NULL")
    op.execute("UPDATE recipe SET is_featured = 0 WHERE is_featured IS NULL")
    op.execute("UPDATE recipe_review SET is_approved = 1 WHERE is_approved IS NULL")

def downgrade():
    # Remove new tables
    op.drop_table('challenge_participation')
    op.drop_table('challenge')
    op.drop_table('follow')
    op.drop_table('collection_recipe')
    op.drop_table('recipe_collection')
    op.drop_table('recipe_photo')

    # Remove moderation fields from existing tables
    with op.batch_alter_table('recipe_review', schema=None) as batch_op:
        batch_op.drop_column('is_approved')

    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_column('moderation_notes')
        batch_op.drop_column('featured_at')
        batch_op.drop_column('is_featured')
        batch_op.drop_column('is_approved')
