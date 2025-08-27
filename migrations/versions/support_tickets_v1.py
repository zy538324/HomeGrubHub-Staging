"""Support ticket system tables

Revision ID: support_tickets_v1
Revises: 
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'support_tickets_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create support_categories table
    op.create_table('support_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True, default='fas fa-question-circle'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create support_tickets table
    op.create_table('support_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_number', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=120), nullable=False),
        sa.Column('user_name', sa.String(length=100), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=True, default='normal'),
        sa.Column('status', sa.String(length=20), nullable=True, default='open'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('browser_info', sa.Text(), nullable=True),
        sa.Column('url_when_reported', sa.String(length=500), nullable=True),
        sa.Column('attachment_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )
    
    # Create indexes for support_tickets
    op.create_index('ix_support_tickets_ticket_number', 'support_tickets', ['ticket_number'])
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('ix_support_tickets_category', 'support_tickets', ['category'])
    op.create_index('ix_support_tickets_user_id', 'support_tickets', ['user_id'])
    op.create_index('ix_support_tickets_created_at', 'support_tickets', ['created_at'])
    
    # Create support_ticket_replies table
    op.create_table('support_ticket_replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_from_admin', sa.Boolean(), nullable=True, default=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('author_name', sa.String(length=100), nullable=False),
        sa.Column('author_email', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for support_ticket_replies
    op.create_index('ix_support_ticket_replies_ticket_id', 'support_ticket_replies', ['ticket_id'])
    op.create_index('ix_support_ticket_replies_created_at', 'support_ticket_replies', ['created_at'])
    
    # Create support_knowledge_base table
    op.create_table('support_knowledge_base',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('meta_description', sa.String(length=160), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_featured', sa.Boolean(), nullable=True, default=False),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.Column('helpful_votes', sa.Integer(), nullable=True, default=0),
        sa.Column('unhelpful_votes', sa.Integer(), nullable=True, default=0),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['category_id'], ['support_categories.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    # Create indexes for support_knowledge_base
    op.create_index('ix_support_knowledge_base_category_id', 'support_knowledge_base', ['category_id'])
    op.create_index('ix_support_knowledge_base_is_published', 'support_knowledge_base', ['is_published'])
    op.create_index('ix_support_knowledge_base_is_featured', 'support_knowledge_base', ['is_featured'])
    
    # Insert default support categories
    categories_table = sa.table('support_categories',
        sa.column('name', sa.String),
        sa.column('description', sa.String),
        sa.column('icon', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('is_active', sa.Boolean)
    )
    
    op.bulk_insert(categories_table, [
        {'name': 'bug', 'description': 'Report bugs and technical issues', 'icon': 'fas fa-bug', 'sort_order': 1, 'is_active': True},
        {'name': 'feature_request', 'description': 'Request new features', 'icon': 'fas fa-lightbulb', 'sort_order': 2, 'is_active': True},
        {'name': 'account', 'description': 'Account and login issues', 'icon': 'fas fa-user', 'sort_order': 3, 'is_active': True},
        {'name': 'billing', 'description': 'Billing and subscription questions', 'icon': 'fas fa-credit-card', 'sort_order': 4, 'is_active': True},
        {'name': 'recipes', 'description': 'Recipe-related problems', 'icon': 'fas fa-utensils', 'sort_order': 5, 'is_active': True},
        {'name': 'meal_planning', 'description': 'Meal planning assistance', 'icon': 'fas fa-calendar-alt', 'sort_order': 6, 'is_active': True},
        {'name': 'general', 'description': 'General support questions', 'icon': 'fas fa-question-circle', 'sort_order': 7, 'is_active': True}
    ])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('support_knowledge_base')
    op.drop_table('support_ticket_replies')
    op.drop_table('support_tickets')
    op.drop_table('support_categories')
