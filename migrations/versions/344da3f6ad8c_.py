"""empty message

Revision ID: 344da3f6ad8c
Revises: add_email_verification, pantry_system_v1, positive_voting_v1, support_tickets_v1
Create Date: 2025-08-01 16:50:54.598768

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '344da3f6ad8c'
down_revision = ('add_email_verification', 'pantry_system_v1', 'positive_voting_v1', 'support_tickets_v1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
