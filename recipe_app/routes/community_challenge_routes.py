from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from recipe_app.models.advanced_models import Challenge, ChallengeParticipation
from recipe_app.db import db
from datetime import datetime

community_challenges_bp = Blueprint('community_challenges', __name__)

@community_challenges_bp.route('/challenges')
@login_required
def challenges():
    # Show all current challenges
    now = datetime.utcnow()
    challenges = Challenge.query.filter(Challenge.end_date >= now).all()
    return render_template('community/challenges.html', challenges=challenges)

@community_challenges_bp.route('/challenges/join/<int:challenge_id>', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    # Check if already joined
    existing = ChallengeParticipation.query.filter_by(challenge_id=challenge_id, user_id=current_user.id).first()
    if existing:
        flash('You have already joined this challenge.', 'info')
        return redirect(url_for('community.challenges'))
    # Only allow upload/share/download for non-free members
    if getattr(current_user, 'role', 'free') == 'free':
        flash('Free members can view challenges, but cannot join/upload/share/download.', 'warning')
        return redirect(url_for('community.challenges'))
    participant = ChallengeParticipation(challenge_id=challenge_id, user_id=current_user.id)
    db.session.add(participant)
    db.session.commit()
    flash('You have joined the challenge!', 'success')
    return redirect(url_for('community.challenges')
)
