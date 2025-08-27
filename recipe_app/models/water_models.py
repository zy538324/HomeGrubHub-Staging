from datetime import datetime
from recipe_app.db import db

class WaterLog(db.Model):
    __tablename__ = 'water_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    amount_ml = db.Column(db.Float, nullable=False)
    log_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount_ml': self.amount_ml,
            'log_time': self.log_time.isoformat() if self.log_time else None,
        }
