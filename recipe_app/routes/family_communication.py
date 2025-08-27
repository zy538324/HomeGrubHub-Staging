"""
Family Communication Hub Routes - Phase 3
Handles internal messaging, notifications, and family member communication
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
import json

from recipe_app.db import db
from recipe_app.models.family_models import (
    FamilyAccount, FamilyMember, FamilyMessage, FamilyNotification, 
    MealPlanComment, ParentalControl, ApprovalRequest
)
from recipe_app.utils.family_decorators import family_required, family_admin_required

# Create Blueprint
family_communication = Blueprint('family_communication', __name__, url_prefix='/family/communication')

# ============================================================================
# FAMILY MESSAGING ROUTES
# ============================================================================

@family_communication.route('/')
@login_required
@family_required
def communication_hub():
    """Main family communication hub dashboard"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Get recent messages
    recent_messages = FamilyMessage.query.filter_by(
        family_id=family.id
    ).filter(
        or_(FamilyMessage.recipient_id == current_member.id, FamilyMessage.recipient_id.is_(None))
    ).order_by(desc(FamilyMessage.created_at)).limit(10).all()
    
    # Get unread notifications
    unread_notifications = FamilyNotification.query.filter_by(
        recipient_id=current_member.id,
        is_read=False
    ).order_by(desc(FamilyNotification.created_at)).limit(5).all()
    
    # Get pending approvals (if parent)
    pending_approvals = []
    if current_member.role in ['admin', 'parent']:
        pending_approvals = ApprovalRequest.query.filter_by(
            family_id=family.id,
            status='pending'
        ).order_by(desc(ApprovalRequest.created_at)).limit(5).all()
    
    # Get statistics
    stats = {
        'total_messages': FamilyMessage.query.filter_by(family_id=family.id).count(),
        'unread_messages': FamilyMessage.query.filter_by(
            family_id=family.id, 
            is_read=False
        ).filter(
            or_(FamilyMessage.recipient_id == current_member.id, FamilyMessage.recipient_id.is_(None))
        ).count(),
        'unread_notifications': len(unread_notifications),
        'pending_approvals': len(pending_approvals)
    }
    
    return render_template('family/communication/hub.html',
                         family=family,
                         current_member=current_member,
                         recent_messages=recent_messages,
                         unread_notifications=unread_notifications,
                         pending_approvals=pending_approvals,
                         stats=stats)

@family_communication.route('/messages')
@login_required
@family_required
def messages():
    """Family messages page with filtering and search"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Get filter parameters
    message_type = request.args.get('type', 'all')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    query = FamilyMessage.query.filter_by(family_id=family.id)
    
    # Filter by recipient (current user or family-wide)
    query = query.filter(
        or_(FamilyMessage.recipient_id == current_member.id, FamilyMessage.recipient_id.is_(None))
    )
    
    # Filter by type
    if message_type != 'all':
        query = query.filter_by(message_type=message_type)
    
    # Search filter
    if search_query:
        query = query.filter(FamilyMessage.message.contains(search_query))
    
    # Pagination
    messages_pagination = query.order_by(desc(FamilyMessage.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('family/communication/messages.html',
                         family=family,
                         current_member=current_member,
                         messages=messages_pagination.items,
                         pagination=messages_pagination,
                         message_type=message_type,
                         search_query=search_query)

@family_communication.route('/send_message', methods=['POST'])
@login_required
@family_required
def send_message():
    """Send a message to family members"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('message'):
        return jsonify({'success': False, 'error': 'Message is required'}), 400
    
    # Create message
    message = FamilyMessage(
        family_id=family.id,
        sender_id=current_member.id,
        recipient_id=data.get('recipient_id'),  # None for family-wide
        message=data['message'],
        message_type=data.get('message_type', 'general'),
        priority=data.get('priority', 'normal'),
        meal_plan_id=data.get('meal_plan_id'),
        challenge_id=data.get('challenge_id'),
        shopping_item_id=data.get('shopping_item_id'),
        is_pinned=data.get('is_pinned', False)
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        
        # Create notifications for recipients
        if message.recipient_id:
            # Direct message - notify specific recipient
            notification = FamilyNotification(
                family_id=family.id,
                recipient_id=message.recipient_id,
                notification_type='new_message',
                title=f'New message from {current_member.display_name}',
                content=message.message[:100] + '...' if len(message.message) > 100 else message.message,
                action_url=f'/family/communication/messages#{message.id}'
            )
            db.session.add(notification)
        else:
            # Family-wide message - notify all members except sender
            for member in family.members:
                if member.id != current_member.id:
                    notification = FamilyNotification(
                        family_id=family.id,
                        recipient_id=member.id,
                        notification_type='new_message',
                        title=f'New family message from {current_member.display_name}',
                        content=message.message[:100] + '...' if len(message.message) > 100 else message.message,
                        action_url=f'/family/communication/messages#{message.id}'
                    )
                    db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'sender_name': current_member.display_name,
                'message': message.message,
                'message_type': message.message_type,
                'priority': message.priority,
                'created_at': message.created_at.isoformat(),
                'is_family_wide': message.is_family_wide()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@family_communication.route('/mark_message_read/<int:message_id>', methods=['POST'])
@login_required
@family_required
def mark_message_read(message_id):
    """Mark a message as read"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    message = FamilyMessage.query.filter_by(id=message_id, family_id=family.id).first_or_404()
    
    # Check if user can read this message
    if not (message.recipient_id == current_member.id or message.recipient_id is None):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    message.mark_as_read()
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# NOTIFICATIONS ROUTES
# ============================================================================

@family_communication.route('/notifications')
@login_required
@family_required
def notifications():
    """View all notifications for current user"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications_pagination = FamilyNotification.query.filter_by(
        recipient_id=current_member.id
    ).order_by(desc(FamilyNotification.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('family/communication/notifications.html',
                         family=family,
                         current_member=current_member,
                         notifications=notifications_pagination.items,
                         pagination=notifications_pagination)

@family_communication.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
@family_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    notification = FamilyNotification.query.filter_by(
        id=notification_id, 
        recipient_id=current_member.id
    ).first_or_404()
    
    notification.mark_as_read()
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@family_communication.route('/mark_all_notifications_read', methods=['POST'])
@login_required
@family_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    FamilyNotification.query.filter_by(
        recipient_id=current_member.id,
        is_read=False
    ).update({
        'is_read': True,
        'read_at': datetime.utcnow()
    })
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# MEAL PLAN COMMENTS ROUTES
# ============================================================================

@family_communication.route('/meal_comments/<int:meal_plan_id>')
@login_required
@family_required
def meal_comments(meal_plan_id):
    """Get comments for a specific meal plan"""
    family = current_user.get_family_account()
    
    comments = MealPlanComment.query.filter_by(
        meal_plan_id=meal_plan_id
    ).order_by(MealPlanComment.created_at).all()
    
    return jsonify({
        'success': True,
        'comments': [{
            'id': comment.id,
            'member_name': comment.member.display_name,
            'comment': comment.comment,
            'comment_type': comment.comment_type,
            'likes_count': comment.likes_count,
            'is_helpful': comment.is_helpful,
            'created_at': comment.created_at.isoformat(),
            'replies': [
                {
                    'id': reply.id,
                    'member_name': reply.member.display_name,
                    'comment': reply.comment,
                    'created_at': reply.created_at.isoformat()
                } for reply in comment.get_replies()
            ]
        } for comment in comments if comment.parent_comment_id is None]
    })

@family_communication.route('/add_meal_comment', methods=['POST'])
@login_required
@family_required
def add_meal_comment():
    """Add a comment to a meal plan"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    data = request.get_json()
    
    if not data.get('comment') or not data.get('meal_plan_id'):
        return jsonify({'success': False, 'error': 'Comment and meal plan ID are required'}), 400
    
    comment = MealPlanComment(
        meal_plan_id=data['meal_plan_id'],
        member_id=current_member.id,
        comment=data['comment'],
        comment_type=data.get('comment_type', 'general'),
        parent_comment_id=data.get('parent_comment_id')
    )
    
    try:
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'member_name': current_member.display_name,
                'comment': comment.comment,
                'comment_type': comment.comment_type,
                'created_at': comment.created_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# APPROVAL REQUESTS ROUTES
# ============================================================================

@family_communication.route('/approvals')
@login_required
@family_required
def approval_requests():
    """View approval requests (parent view)"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Only parents/admins can view approval requests
    if current_member.role not in ['admin', 'parent']:
        flash('Access denied. Only parents can view approval requests.', 'error')
        return redirect(url_for('family_communication.communication_hub'))
    
    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = ApprovalRequest.query.filter_by(family_id=family.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    requests_pagination = query.order_by(desc(ApprovalRequest.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('family/communication/approvals.html',
                         family=family,
                         current_member=current_member,
                         requests=requests_pagination.items,
                         pagination=requests_pagination,
                         status_filter=status_filter)

@family_communication.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
@family_required
def approve_request(request_id):
    """Approve an approval request"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Only parents/admins can approve requests
    if current_member.role not in ['admin', 'parent']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    approval_request = ApprovalRequest.query.filter_by(
        id=request_id, 
        family_id=family.id
    ).first_or_404()
    
    data = request.get_json()
    response_text = data.get('response', '')
    
    approval_request.approve(current_member.id, response_text)
    
    try:
        db.session.commit()
        
        # Create notification for child
        notification = FamilyNotification(
            family_id=family.id,
            recipient_id=approval_request.child_id,
            notification_type='approval_granted',
            title=f'Request Approved: {approval_request.request_title}',
            content=f'Your request has been approved by {current_member.display_name}',
            action_url=f'/family/communication/approvals'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@family_communication.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
@family_required
def reject_request(request_id):
    """Reject an approval request"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Only parents/admins can reject requests
    if current_member.role not in ['admin', 'parent']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    approval_request = ApprovalRequest.query.filter_by(
        id=request_id, 
        family_id=family.id
    ).first_or_404()
    
    data = request.get_json()
    response_text = data.get('response', '')
    
    approval_request.reject(current_member.id, response_text)
    
    try:
        db.session.commit()
        
        # Create notification for child
        notification = FamilyNotification(
            family_id=family.id,
            recipient_id=approval_request.child_id,
            notification_type='approval_denied',
            title=f'Request Declined: {approval_request.request_title}',
            content=f'Your request has been declined by {current_member.display_name}',
            action_url=f'/family/communication/approvals'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# API ENDPOINTS FOR MOBILE/AJAX
# ============================================================================

@family_communication.route('/api/unread_counts')
@login_required
@family_required
def api_unread_counts():
    """Get unread message and notification counts"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    unread_messages = FamilyMessage.query.filter_by(
        family_id=family.id, 
        is_read=False
    ).filter(
        or_(FamilyMessage.recipient_id == current_member.id, FamilyMessage.recipient_id.is_(None))
    ).count()
    
    unread_notifications = FamilyNotification.query.filter_by(
        recipient_id=current_member.id,
        is_read=False
    ).count()
    
    pending_approvals = 0
    if current_member.role in ['admin', 'parent']:
        pending_approvals = ApprovalRequest.query.filter_by(
            family_id=family.id,
            status='pending'
        ).count()
    
    return jsonify({
        'success': True,
        'counts': {
            'messages': unread_messages,
            'notifications': unread_notifications,
            'approvals': pending_approvals,
            'total': unread_messages + unread_notifications + pending_approvals
        }
    })

@family_communication.route('/api/recent_activity')
@login_required
@family_required
def api_recent_activity():
    """Get recent family communication activity"""
    family = current_user.get_family_account()
    current_member = next((m for m in family.members if m.user_id == current_user.id), None)
    
    # Get recent messages
    recent_messages = FamilyMessage.query.filter_by(
        family_id=family.id
    ).filter(
        or_(FamilyMessage.recipient_id == current_member.id, FamilyMessage.recipient_id.is_(None))
    ).order_by(desc(FamilyMessage.created_at)).limit(5).all()
    
    # Get recent notifications
    recent_notifications = FamilyNotification.query.filter_by(
        recipient_id=current_member.id
    ).order_by(desc(FamilyNotification.created_at)).limit(5).all()
    
    return jsonify({
        'success': True,
        'recent_messages': [{
            'id': msg.id,
            'sender_name': msg.sender.display_name,
            'message': msg.message[:100] + '...' if len(msg.message) > 100 else msg.message,
            'message_type': msg.message_type,
            'priority': msg.priority,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat()
        } for msg in recent_messages],
        'recent_notifications': [{
            'id': notif.id,
            'title': notif.title,
            'content': notif.content,
            'notification_type': notif.notification_type,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat()
        } for notif in recent_notifications]
    })
