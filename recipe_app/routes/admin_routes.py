from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from .. import db
from recipe_app.forms.admin_forms import AdminSettingsForm
from recipe_app.models.models import RecipeReview


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Admin site configuration"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))

    form = AdminSettingsForm()
    if form.validate_on_submit():
        # Settings persistence would occur here
        flash('Settings updated.', 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', form=form)


@admin_bp.route('/moderation')
@login_required
def moderation():
    """List flagged content awaiting review"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))

    flagged_reviews = (
        RecipeReview.query.filter_by(is_flagged=True).all()
        if hasattr(RecipeReview, 'is_flagged')
        else []
    )

    return render_template(
        'admin/moderation.html', flagged_reviews=flagged_reviews
    )


@admin_bp.route('/review/<int:review_id>/<action>', methods=['POST'])
@login_required
def review_moderation(review_id, action):
    """Approve or deny a flagged review"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))

    review = RecipeReview.query.get_or_404(review_id)

    if action == 'approve':
        if hasattr(review, 'is_flagged'):
            review.is_flagged = False
        review.is_approved = True
        message = 'Review approved.'
    elif action == 'deny':
        if hasattr(review, 'is_flagged'):
            review.is_flagged = False
        review.is_approved = False
        message = 'Review denied.'
    else:
        flash('Invalid action.', 'error')
        return redirect(url_for('admin.moderation'))

    db.session.commit()
    flash(message, 'success')
    return redirect(url_for('admin.moderation'))

