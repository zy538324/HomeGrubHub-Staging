"""
Support ticket models for customer support system
"""
from datetime import datetime
from recipe_app import db


class SupportTicket(db.Model):
    """Support tickets submitted by users"""
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for anonymous users
    user_email = db.Column(db.String(120), nullable=False)  # Store email even for registered users
    user_name = db.Column(db.String(100), nullable=False)
    
    # Ticket details
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'bug', 'feature_request', 'account', 'billing', 'general'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    
    # Status tracking
    status = db.Column(db.String(20), default='open')  # 'open', 'in_progress', 'waiting_user', 'resolved', 'closed'
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin user assigned
    
    # Additional information
    browser_info = db.Column(db.Text)  # User agent, browser details
    url_when_reported = db.Column(db.String(500))  # URL where issue occurred
    attachment_path = db.Column(db.String(500))  # Path to uploaded file
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('support_tickets', lazy=True))
    assigned_admin = db.relationship('User', foreign_keys=[assigned_to], backref=db.backref('assigned_tickets', lazy=True))
    
    def __repr__(self):
        return f'<SupportTicket {self.ticket_number}: {self.subject}>'
    
    def generate_ticket_number(self):
        """Generate a unique ticket number"""
        import random
        import string
        
        # Format: ST-YYYYMMDD-XXXX (ST = Support Ticket, date, random 4 chars)
        date_str = datetime.utcnow().strftime('%Y%m%d')
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"ST-{date_str}-{random_part}"
    
    def get_status_color(self):
        """Get Bootstrap color class for status"""
        colors = {
            'open': 'primary',
            'in_progress': 'warning',
            'waiting_user': 'info',
            'resolved': 'success',
            'closed': 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def get_priority_color(self):
        """Get Bootstrap color class for priority"""
        colors = {
            'low': 'secondary',
            'normal': 'primary',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'primary')
    
    def can_be_viewed_by(self, user):
        """Check if a user can view this ticket"""
        if not user:
            return False
        
        # Admins can view all tickets
        if user.is_admin:
            return True
        
        # Users can view their own tickets
        if self.user_id and user.id == self.user_id:
            return True
        
        # For anonymous tickets, check email match (you'd need additional auth)
        return False
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'subject': self.subject,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class SupportTicketReply(db.Model):
    """Replies/comments on support tickets"""
    __tablename__ = 'support_ticket_replies'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    
    # Reply details
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Internal admin notes vs customer-visible replies
    is_from_admin = db.Column(db.Boolean, default=False)
    
    # Author information
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    author_name = db.Column(db.String(100), nullable=False)  # For anonymous replies
    author_email = db.Column(db.String(120), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ticket = db.relationship('SupportTicket', backref=db.backref('replies', lazy=True, order_by='SupportTicketReply.created_at'))
    author = db.relationship('User', backref=db.backref('support_replies', lazy=True))
    
    def __repr__(self):
        return f'<SupportTicketReply {self.id} for Ticket {self.ticket_id}>'


class SupportCategory(db.Model):
    """Support ticket categories for organization"""
    __tablename__ = 'support_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='fas fa-question-circle')  # FontAwesome icon class
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SupportCategory {self.name}>'


class SupportKnowledgeBase(db.Model):
    """Knowledge base articles for self-service support"""
    __tablename__ = 'support_knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('support_categories.id'), nullable=False)
    
    # SEO and search
    slug = db.Column(db.String(200), unique=True, nullable=False)
    meta_description = db.Column(db.String(160))
    tags = db.Column(db.String(500))  # Comma-separated tags for search
    
    # Visibility and organization
    is_published = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    helpful_votes = db.Column(db.Integer, default=0)
    unhelpful_votes = db.Column(db.Integer, default=0)
    
    # Author and timestamps
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('SupportCategory', backref=db.backref('articles', lazy=True))
    author = db.relationship('User', backref=db.backref('knowledge_articles', lazy=True))
    
    def __repr__(self):
        return f'<SupportKnowledgeBase {self.title}>'
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        db.session.commit()
    
    def get_helpfulness_percentage(self):
        """Calculate helpfulness percentage"""
        total_votes = self.helpful_votes + self.unhelpful_votes
        if total_votes == 0:
            return 0
        return int((self.helpful_votes / total_votes) * 100)
