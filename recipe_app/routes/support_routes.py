from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from recipe_app.db import db
from recipe_app.models.models import User
from recipe_app.models.support_models import SupportTicket, SupportTicketReply, SupportCategory
from recipe_app.utils.email_service import send_support_email, test_email_service
from datetime import datetime
import random
import string

support_bp = Blueprint('support', __name__)

@support_bp.route('/')
@support_bp.route('/help-center')
def help_center():
    """Main support/help center page"""
    return render_template('support/help_center.html')

@support_bp.route('/contact', methods=['GET', 'POST'])
def contact_form():
    """Contact form for customer support"""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        category = request.form.get('category', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validation
        if not all([name, email, subject, message]):
            flash('Please fill in all required fields', 'error')
            return render_template('support/contact_form.html')
        
        # Send email (you'll need to configure SMTP settings)
        try:
            send_support_email(name, email, subject, category, message)
            flash('Thank you for contacting us! We\'ll get back to you within 24 hours.', 'success')
            return redirect(url_for('support.contact_form'))
        except Exception as e:
            flash('There was an error sending your message. Please try again.', 'error')
            return render_template('support/contact_form.html')
    
    return render_template('support/contact_form.html')

@support_bp.route('/faq')
def faq():
    """Frequently Asked Questions page"""
    return render_template('support/faq.html')

@support_bp.route('/getting-started')
@support_bp.route('/getting-started/<int:step>')
def getting_started(step=1):
    """Getting started guide with individual steps"""
    # Ensure step is valid (1-5)
    if step < 1 or step > 5:
        step = 1
    
    # Calculate progress
    progress = (step / 5) * 100
    
    # Define step titles and descriptions
    steps_info = {
        1: {
            'title': '🎉 Welcome to HomeGrubHub!',
            'description': 'Your personal recipe manager and meal planning companion that makes cooking a joy',
            'template': 'support/getting_started/step1_welcome.html'
        },
        2: {
            'title': '🍳 Add Your First Recipe',
            'description': 'Let\'s start your culinary journey by adding a delicious recipe to your collection',
            'template': 'support/getting_started/step2_first_recipe.html'
        },
        3: {
            'title': '🔍 Explore Key Features',
            'description': 'Discover the powerful tools that make HomeGrubHub special',
            'template': 'support/getting_started/step3_features.html'
        },
        4: {
            'title': '📅 Meal Planning Made Easy',
            'description': 'Plan your weekly meals and never wonder "what\'s for dinner?" again',
            'template': 'support/getting_started/step4_meal_planning.html'
        },
        5: {
            'title': '👥 Join the Community',
            'description': 'Connect with other food lovers and discover amazing recipes',
            'template': 'support/getting_started/step5_community.html'
        }
    }
    
    current_step_info = steps_info[step]
    
    return render_template(current_step_info['template'], 
                         current_step=step,
                         total_steps=5,
                         progress=progress,
                         step_title=current_step_info['title'],
                         step_description=current_step_info['description'],
                         steps_info=steps_info)

@support_bp.route('/live-chat')
def live_chat():
    """Live chat placeholder (for future implementation)"""
    return render_template('support/live_chat.html')

# Chat message handling removed - now using Tawk.to for live chat
# Users can access chat via the Tawk.to widget on all pages

@support_bp.route('/ticket/create', methods=['GET', 'POST'])
def create_ticket():
    """Create a support ticket (both authenticated and anonymous users)"""
    if request.method == 'POST':
        # Debug: Log form data and CSRF token
        print(f"Form data: {dict(request.form)}")
        print(f"CSRF token in form: {request.form.get('csrf_token', 'NOT FOUND')}")
        print(f"Request headers: {dict(request.headers)}")
        
        subject = request.form.get('subject', '').strip()
        category = request.form.get('category', '').strip()
        priority = request.form.get('priority', 'normal').strip()
        description = request.form.get('description', '').strip()
        user_email = request.form.get('email', '').strip()
        user_name = request.form.get('name', '').strip()
        
        if not all([subject, category, description, user_email, user_name]):
            flash('Please fill in all required fields including your name and email', 'error')
            return render_template('support/create_ticket.html')
        
        # Create new support ticket
        try:
            ticket = SupportTicket(
                user_id=current_user.id if current_user.is_authenticated else None,
                user_email=user_email,  # Use the email from the form
                user_name=user_name,    # Use the name from the form
                subject=subject,
                description=description,
                category=category,
                priority=priority,
                browser_info=request.headers.get('User-Agent', ''),
                url_when_reported=request.form.get('current_url', '')
            )
            
            # Generate unique ticket number
            while True:
                ticket_number = generate_ticket_number()
                existing = SupportTicket.query.filter_by(ticket_number=ticket_number).first()
                if not existing:
                    ticket.ticket_number = ticket_number
                    break
            
            db.session.add(ticket)
            db.session.commit()
            
            # Send confirmation email TO THE USER (not to support)
            try:
                # Use the new email service for ticket confirmation
                from recipe_app.utils.email_service import email_service
                email_service.send_ticket_confirmation_to_user(
                    user_email,  # Send to user's email
                    user_name, 
                    ticket.ticket_number,
                    subject
                )
            except Exception as e:
                print(f"Failed to send confirmation email: {e}")
            
            flash(f'Support ticket #{ticket.ticket_number} created successfully! You will receive a confirmation email shortly.', 'success')
            return redirect(url_for('support.view_ticket', ticket_number=ticket.ticket_number))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating ticket. Please try again.', 'error')
            print(f"Error creating ticket: {e}")
    
    # Get categories for dropdown
    categories = SupportCategory.query.filter_by(is_active=True).order_by(SupportCategory.sort_order).all()
    return render_template('support/create_ticket.html', categories=categories)

def send_ticket_email(user, subject, category, priority, description):
    """Send ticket confirmation email"""
    # Similar to send_support_email but for logged-in users
    # Implementation would be similar but include user account information
    pass

def generate_ticket_number():
    """Generate a unique ticket number"""
    # Format: ST-YYYYMMDD-XXXX (ST = Support Ticket, date, random 4 chars)
    date_str = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ST-{date_str}-{random_part}"

@support_bp.route('/test-email')
@login_required
def test_email():
    """Test email configuration (admin only)"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Access denied', 'error')
        return redirect(url_for('support.help_center'))
    
    # Test email service
    test_results = test_email_service()
    
    return jsonify({
        'status': 'success',
        'results': test_results,
        'message': 'Email configuration test completed'
    })

@support_bp.route('/email-admin')
@login_required
def email_admin():
    """Email administration page (admin only)"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Access denied', 'error')
        return redirect(url_for('support.help_center'))
    
    return render_template('support/email_test.html')

@support_bp.route('/debug-env')
@login_required
def debug_env():
    """Debug environment variables (admin only)"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Access denied', 'error')
        return redirect(url_for('support.help_center'))
    
    import os
    env_info = {
        'office365_email': os.getenv('OFFICE365_EMAIL', 'NOT SET'),
        'office365_password': 'SET' if os.getenv('OFFICE365_PASSWORD') else 'NOT SET',
        'office365_tenant_id': os.getenv('OFFICE365_TENANT_ID', 'NOT SET'),
        'office365_client_id': os.getenv('OFFICE365_CLIENT_ID', 'NOT SET'),
        'office365_client_secret': 'SET' if os.getenv('OFFICE365_CLIENT_SECRET') else 'NOT SET',
    }
    
    return jsonify({
        'status': 'success',
        'environment_variables': env_info,
        'message': 'Environment variables status'
    })

@support_bp.route('/debug-csrf')
@login_required
def debug_csrf():
    """Debug CSRF token (admin only)"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Access denied', 'error')
        return redirect(url_for('support.help_center'))
    
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()
    
    return jsonify({
        'status': 'success',
        'csrf_token': csrf_token,
        'request_method': request.method,
        'form_data': dict(request.form) if request.form else 'No form data',
        'message': 'CSRF debug information'
    })

@support_bp.route('/ticket/<ticket_number>')
@login_required
def view_ticket(ticket_number):
    """View a specific support ticket"""
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    # Check if user can view this ticket
    if not ticket.can_be_viewed_by(current_user):
        flash('You do not have permission to view this ticket.', 'error')
        return redirect(url_for('support.help_center'))
    
    return render_template('support/view_ticket.html', ticket=ticket)

@support_bp.route('/tickets')
@login_required
def my_tickets():
    """View user's support tickets"""
    if current_user.is_admin:
        # Admins can see all tickets
        tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    else:
        # Users can only see their own tickets
        tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    
    return render_template('support/my_tickets.html', tickets=tickets)

@support_bp.route('/ticket/<ticket_number>/reply', methods=['POST'])
@login_required
def reply_to_ticket(ticket_number):
    """Add a reply to a support ticket"""
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    # Check if user can reply to this ticket
    if not ticket.can_be_viewed_by(current_user):
        flash('You do not have permission to reply to this ticket.', 'error')
        return redirect(url_for('support.help_center'))
    
    message = request.form.get('message', '').strip()
    if not message:
        flash('Please enter a message.', 'error')
        return redirect(url_for('support.view_ticket', ticket_number=ticket_number))
    
    try:
        reply = SupportTicketReply(
            ticket_id=ticket.id,
            message=message,
            is_from_admin=current_user.is_admin,
            author_id=current_user.id,
            author_name=current_user.username,
            author_email=current_user.email
        )
        
        db.session.add(reply)
        
        # Update ticket status if it was resolved/closed and user is replying
        if ticket.status in ['resolved', 'closed'] and not current_user.is_admin:
            ticket.status = 'open'
        
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Reply added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding reply. Please try again.', 'error')
        print(f"Error adding reply: {e}")
    
    return redirect(url_for('support.view_ticket', ticket_number=ticket_number))

@support_bp.route('/api/ticket/<ticket_number>/status', methods=['POST'])
@login_required
def update_ticket_status(ticket_number):
    """Update ticket status (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    new_status = request.json.get('status')
    
    if new_status not in ['open', 'in_progress', 'waiting_user', 'resolved', 'closed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        ticket.status = new_status
        if new_status in ['resolved', 'closed']:
            ticket.resolved_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update status'}), 500

# -------------------------------
# JSON API endpoints for Mobile
# -------------------------------

@support_bp.route('/support/api/categories.json')
def api_categories():
    """Return active support categories"""
    categories = SupportCategory.query.filter_by(is_active=True).order_by(SupportCategory.sort_order).all()
    return jsonify([
        {
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'icon': c.icon,
            'sort_order': c.sort_order,
        } for c in categories
    ])

@support_bp.route('/support/api/tickets.json')
@login_required
def api_list_tickets():
    """Return tickets for current user (admins see all)"""
    if current_user.is_admin:
        tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    else:
        tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tickets])

@support_bp.route('/support/api/tickets', methods=['POST'])
def api_create_ticket():
    """Create a support ticket via JSON"""
    data = request.get_json(silent=True) or {}
    subject = (data.get('subject') or '').strip()
    category = (data.get('category') or '').strip()
    priority = (data.get('priority') or 'normal').strip()
    description = (data.get('description') or '').strip()

    # If logged in, default to user profile; allow override from payload for name/email fallback
    if current_user.is_authenticated:
        user_email = current_user.email
        user_name = getattr(current_user, 'username', None) or data.get('name') or 'User'
        user_id = current_user.id
    else:
        user_email = (data.get('email') or '').strip()
        user_name = (data.get('name') or '').strip()
        user_id = None

    if not all([subject, category, description, user_email, user_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        ticket = SupportTicket(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            browser_info=request.headers.get('User-Agent', ''),
            url_when_reported=data.get('current_url', '')
        )
        # Generate unique ticket number
        while True:
            ticket_number = generate_ticket_number()
            existing = SupportTicket.query.filter_by(ticket_number=ticket_number).first()
            if not existing:
                ticket.ticket_number = ticket_number
                break
        db.session.add(ticket)
        db.session.commit()

        # Send confirmation email (best-effort)
        try:
            from recipe_app.utils.email_service import email_service
            email_service.send_ticket_confirmation_to_user(
                user_email, user_name, ticket.ticket_number, subject
            )
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")

        return jsonify({'success': True, 'ticket': ticket.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating ticket via API: {e}")
        return jsonify({'error': 'Failed to create ticket'}), 500

@support_bp.route('/support/api/tickets/<ticket_number>.json')
@login_required
def api_get_ticket(ticket_number):
    """Get a ticket with replies"""
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    if not ticket.can_be_viewed_by(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    data = ticket.to_dict()
    data['replies'] = [
        {
            'id': r.id,
            'message': r.message,
            'is_internal': r.is_internal,
            'is_from_admin': r.is_from_admin,
            'author_name': r.author_name,
            'author_email': r.author_email,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in ticket.replies
    ]
    return jsonify(data)

@support_bp.route('/support/api/tickets/<ticket_number>/reply', methods=['POST'])
@login_required
def api_reply_ticket(ticket_number):
    """Reply to a ticket via JSON"""
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    if not ticket.can_be_viewed_by(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    try:
        reply = SupportTicketReply(
            ticket_id=ticket.id,
            message=message,
            is_from_admin=current_user.is_admin,
            author_id=current_user.id if current_user.is_authenticated else None,
            author_name=getattr(current_user, 'username', None) or 'User',
            author_email=current_user.email if current_user.is_authenticated else ''
        )
        db.session.add(reply)
        if ticket.status in ['resolved', 'closed'] and not current_user.is_admin:
            ticket.status = 'open'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error replying to ticket via API: {e}")
        return jsonify({'error': 'Failed to add reply'}), 500
