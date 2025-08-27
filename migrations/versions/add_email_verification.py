"""Add email verification and password reset fields

Revision ID: add_email_verification
Revises: 
Create Date: 2025-08-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_email_verification'
down_revision = '4515bebd0311'
branch_labels = None
depends_on = None


def upgrade():
    # Add email verification fields to user table
    op.add_column('user', sa.Column('email_verified', sa.Boolean(), nullable=True, default=False))
    op.add_column('user', sa.Column('email_verification_token', sa.String(length=128), nullable=True))
    op.add_column('user', sa.Column('email_verification_sent_at', sa.DateTime(), nullable=True))
    
    # Add password reset fields to user table
    op.add_column('user', sa.Column('password_reset_token', sa.String(length=128), nullable=True))
    op.add_column('user', sa.Column('password_reset_sent_at', sa.DateTime(), nullable=True))
    
    # Create unique indexes for tokens
    op.create_index('ix_user_email_verification_token', 'user', ['email_verification_token'], unique=True)
    op.create_index('ix_user_password_reset_token', 'user', ['password_reset_token'], unique=True)
    
    # Set existing users as email verified (since they were created before this system)
    op.execute("UPDATE user SET email_verified = true WHERE email_verified IS NULL")
    
    # Make email_verified not nullable after setting default values
    op.alter_column('user', 'email_verified', nullable=False)


def downgrade():
    # Remove indexes
    op.drop_index('ix_user_password_reset_token', table_name='user')
    op.drop_index('ix_user_email_verification_token', table_name='user')
    
    # Remove columns
    op.drop_column('user', 'password_reset_sent_at')
    op.drop_column('user', 'password_reset_token')
    op.drop_column('user', 'email_verification_sent_at')
    op.drop_column('user', 'email_verification_token')
    op.drop_column('user', 'email_verified')
