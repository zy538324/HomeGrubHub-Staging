"""
Models for tracking weight and fitness activities.
"""
from datetime import datetime, date
from recipe_app.db import db

class WeightLog(db.Model):
    """Log for daily weight entries."""
    __tablename__ = 'weight_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    body_fat_percentage = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('weight_logs', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'log_date', name='unique_user_weight_date'),)

    def __repr__(self):
        return f'<WeightLog {self.user.username} - {self.log_date}: {self.weight_kg}kg>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'log_date': self.log_date.isoformat(),
            'weight_kg': self.weight_kg,
            'body_fat_percentage': self.body_fat_percentage,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class WorkoutLog(db.Model):
    """Log for a workout session, which can contain multiple exercises."""
    __tablename__ = 'workout_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    workout_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True) # Calculated or manual entry
    workout_type = db.Column(db.String(50), nullable=True) # e.g., 'Strength Training', 'Cardio', 'Yoga'

    notes = db.Column(db.Text, nullable=True)
    calories_burned = db.Column(db.Float, nullable=True)  # Estimated calories burned

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('workout_logs', lazy='dynamic'))
    exercises = db.relationship('ExerciseLog', backref='workout_log', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<WorkoutLog {self.user.username} - {self.workout_date}>'
    
    def calculate_duration(self):
        if self.start_time and self.end_time:
            self.duration_minutes = (self.end_time - self.start_time).total_seconds() / 60
        return self.duration_minutes

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'workout_date': self.workout_date.isoformat(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'workout_type': self.workout_type,
            'notes': self.notes,
            'exercises': [ex.to_dict() for ex in self.exercises],
            'created_at': self.created_at.isoformat()
        }

class ExerciseLog(db.Model):
    """Log for a specific exercise within a workout session."""
    __tablename__ = 'exercise_logs'

    id = db.Column(db.Integer, primary_key=True)
    workout_log_id = db.Column(db.Integer, db.ForeignKey('workout_logs.id'), nullable=False, index=True)
    
    exercise_name = db.Column(db.String(100), nullable=False)
    exercise_type = db.Column(db.String(50), nullable=True) # 'strength', 'cardio', 'flexibility'
    
    # For strength exercises
    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    
    # For cardio exercises
    distance_km = db.Column(db.Float, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    
    # For all types
    calories_burned = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ExerciseLog {self.exercise_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'workout_log_id': self.workout_log_id,
            'exercise_name': self.exercise_name,
            'exercise_type': self.exercise_type,
            'sets': self.sets,
            'reps': self.reps,
            'weight_kg': self.weight_kg,
            'distance_km': self.distance_km,
            'duration_minutes': self.duration_minutes,
            'calories_burned': self.calories_burned,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
