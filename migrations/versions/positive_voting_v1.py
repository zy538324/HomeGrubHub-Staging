"""Add positive voting system and enhanced follow model

Revision ID: positive_voting_v1
Revises: 
Create Date: 2024-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'positive_voting_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create RecipeVote table
    op.create_table('recipe_vote',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('vote_type', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'recipe_id', name='unique_user_recipe_vote')
    )
    
    # Check if Follow table exists, if not create it
    try:
        # Add columns to existing Follow table if it exists
        op.add_column('follow', sa.Column('created_at', sa.DateTime(), nullable=True))
        
        # Add constraints
        op.create_unique_constraint('unique_follow', 'follow', ['follower_id', 'followed_id'])
        op.create_check_constraint('no_self_follow', 'follow', 'follower_id != followed_id')
        
    except Exception:
        # Create Follow table if it doesn't exist
        op.create_table('follow',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('followed_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('follower_id != followed_id', name='no_self_follow'),
        sa.ForeignKeyConstraint(['followed_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['follower_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'followed_id', name='unique_follow')
        )


def downgrade():
    # Drop RecipeVote table
    op.drop_table('recipe_vote')
    
    # Note: We don't drop the Follow table as it might have been created elsewhere
    # Instead, we just remove the columns we added
    try:
        op.drop_constraint('unique_follow', 'follow', type_='unique')
        op.drop_constraint('no_self_follow', 'follow', type_='check')
        op.drop_column('follow', 'created_at')
    except Exception:
        pass
