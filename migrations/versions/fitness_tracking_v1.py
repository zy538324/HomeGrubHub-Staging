"""Add fitness tracking models

Revision ID: fitness_tracking_v1
Revises: 1472c334cea8
Create Date: 2025-08-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'fitness_tracking_v1'
down_revision = '1472c334cea8'  # Use the merge heads migration
branch_labels = None
depends_on = None


def upgrade():
    """Create fitness tracking tables"""
    
    # Create weight_logs table
    op.create_table('weight_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('log_date', sa.Date(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('body_fat_percentage', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'log_date', name='unique_user_weight_date')
    )
    op.create_index('ix_weight_logs_user_id', 'weight_logs', ['user_id'])
    op.create_index('ix_weight_logs_log_date', 'weight_logs', ['log_date'])

    # Create workout_logs table
    op.create_table('workout_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('workout_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('workout_type', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workout_logs_user_id', 'workout_logs', ['user_id'])
    op.create_index('ix_workout_logs_workout_date', 'workout_logs', ['workout_date'])

    # Create exercise_logs table
    op.create_table('exercise_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('exercise_name', sa.String(length=100), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('calories_burned', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workout_id'], ['workout_logs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_exercise_logs_workout_id', 'exercise_logs', ['workout_id'])


def downgrade():
    """Drop fitness tracking tables"""
    
    op.drop_index('ix_exercise_logs_workout_id', table_name='exercise_logs')
    op.drop_table('exercise_logs')
    
    op.drop_index('ix_workout_logs_workout_date', table_name='workout_logs')
    op.drop_index('ix_workout_logs_user_id', table_name='workout_logs')
    op.drop_table('workout_logs')
    
    op.drop_index('ix_weight_logs_log_date', table_name='weight_logs')
    op.drop_index('ix_weight_logs_user_id', table_name='weight_logs')
    op.drop_table('weight_logs')
