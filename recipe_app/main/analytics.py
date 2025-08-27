from recipe_app.db import db
from datetime import datetime

class UserEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    event_type = db.Column(db.String(64), nullable=False)
    event_data = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f'<UserEvent {self.event_type} by {self.user_id} at {self.timestamp}>'

class FaultLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    plan = db.Column(db.String(64), nullable=True)
    fault_id = db.Column(db.String(64), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('fault_logs', lazy=True))

    def __repr__(self):
        return f'<FaultLog {self.fault_id} by {self.user_id} at {self.timestamp}>'

def log_fault(fault_id, details, user=None):
    """Helper function to log faults"""
    fault_log = FaultLog(
        user_id=user.id if user else None,
        plan=user.current_plan if user else None,
        fault_id=fault_id,
        details=details
    )
    db.session.add(fault_log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # If we can't log the fault, at least don't crash the app
        pass
