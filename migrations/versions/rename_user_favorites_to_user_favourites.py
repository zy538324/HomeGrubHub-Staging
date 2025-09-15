"""Rename user_favorites to user_favourites"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_user_favorites_to_user_favourites'
down_revision = 'add_stripe_subscription_fields'
branch_labels = None
depends_on = None

def upgrade():
    op.rename_table('user_favorites', 'user_favourites')


def downgrade():
    op.rename_table('user_favourites', 'user_favorites')
