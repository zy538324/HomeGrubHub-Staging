import os
import stripe
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from ..models.models import User
from datetime import datetime, timedelta

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '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')  # Replace with your Stripe secret key

billing_bp = Blueprint('billing', __name__)

# Stripe Price IDs - Replace these with your actual Stripe Price IDs
STRIPE_PRICES = {
    'Home': 'price_1RsN9kAJtC1Fz22fRpymQGcw',      # £4.99/month
    'Family': 'price_family_placeholder',           # £7.99/month - TODO: Replace with actual Stripe price ID
    'Pro': 'price_pro_placeholder',                 # £12.99/month - TODO: Replace with actual Stripe price ID
}


def _get_pricing_tiers():
    """Return pricing tiers as a list of dicts (shared by HTML + JSON endpoints)."""
    return [
        {
            'name': 'Free',
            'price': '£0',
            'period': 'forever',
            'description': 'Perfect for getting started',
            'features': [
                '10 recipes (all public)',
                'Basic search',
                'Recipe organization',
                'Mobile responsive',
            ],
            'stripe_price_id': 'price_1RsO2sAJtC1Fz22fcUVxbAkx',
            'popular': False,
        },
        {
            'name': 'Home',
            'price': '£4.99',
            'period': 'month',
            'description': 'For home cooks and families',
            'features': [
                'Unlimited recipes',
                'Advanced search',
                'Meal planning',
                'Favorites & tags',
                'Private recipes',
                'Pantry management',
                'Recipe import/export',
                'Priority support',
            ],
            'stripe_price_id': STRIPE_PRICES.get('Home'),
            'popular': False,
        },
        {
            'name': 'Family',
            'price': '£7.99',
            'period': 'month',
            'description': 'Up to 5 users',
            'features': [
                'All Home features',
                'Up to 5 users',
                'Family syncing & pantry management',
                'Dynamic budget alerts',
                'Themed offline packs',
                'Priority email support',
            ],
            'stripe_price_id': STRIPE_PRICES.get('Family'),
            'popular': True,
        },
        {
            'name': 'Pro',
            'price': '£12.99',
            'period': 'month',
            'description': 'For Power Users',
            'features': [
                'All Family features',
                'AI predictive pantry',
                'Smart consumption forecasting',
                'Multi-store price comparison',
                'Barcode scanning',
                'Priority chat support',
            ],
            'stripe_price_id': STRIPE_PRICES.get('Pro'),
            'popular': False,
        },
    ]


def _format_price(currency: str, unit_amount: int | None) -> str:
    try:
        amount = (unit_amount or 0) / 100.0
        symbol = '£' if (currency or '').lower() == 'gbp' else '€' if (currency or '').lower() == 'eur' else '$' if (currency or '').lower() == 'usd' else (currency.upper() + ' ')
        return f"{symbol}{amount:.2f}"
    except Exception:
        return ''


def _augment_tiers_with_stripe(tiers: list[dict]) -> list[dict]:
    """Augment tiers with live Stripe price, currency and interval when possible."""
    for tier in tiers:
        price_id = tier.get('stripe_price_id')
        # Skip if no price id or placeholder
        if not price_id or 'placeholder' in str(price_id):
            continue
        try:
            price = stripe.Price.retrieve(price_id)
            currency = getattr(price, 'currency', None)
            unit_amount = getattr(price, 'unit_amount', None)
            recurring = getattr(price, 'recurring', None)
            interval = getattr(recurring, 'interval', None) if recurring else None
            interval_count = getattr(recurring, 'interval_count', 1) if recurring else 1

            # Update human-readable price and period
            if currency and unit_amount is not None:
                tier['price'] = _format_price(currency, unit_amount)
            if interval:
                tier['period'] = 'month' if (interval == 'month' and interval_count == 1) else f"{interval_count} {interval}"

            # Expose extra fields for clients that want precision
            tier['currency'] = currency
            tier['unit_amount'] = unit_amount
            tier['interval'] = interval
            tier['interval_count'] = interval_count
        except Exception as e:
            current_app.logger.warning(f"Could not fetch Stripe price for %s: %s", price_id, e)
            continue
    return tiers


@billing_bp.route('/pricing')
def pricing():
    """Display pricing page"""
    pricing_tiers = _get_pricing_tiers()
    return render_template('billing/pricing.html', pricing_tiers=pricing_tiers, stripe_publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY'])


@billing_bp.route('/pricing.json')
def pricing_json():
    """Return pricing tiers as JSON for mobile/clients."""
    tiers = _augment_tiers_with_stripe(_get_pricing_tiers())
    # Do not expose any secret keys
    return jsonify({'pricing_tiers': tiers})


@billing_bp.route('/subscribe/<plan>')
@login_required
def subscribe(plan):
    """Create Stripe checkout session for subscription"""
    if plan not in STRIPE_PRICES:
        flash('Invalid subscription plan.', 'error')
        return redirect(url_for('billing.pricing'))
    
    try:
        from recipe_app.db import db
        
        # Debug: Check the price details
        try:
            price = stripe.Price.retrieve(STRIPE_PRICES[plan])
            current_app.logger.info(f"Price details for {plan}: amount={price.unit_amount}, currency={price.currency}, trial_period_days={price.recurring.trial_period_days if hasattr(price.recurring, 'trial_period_days') else 'None'}")
        except Exception as e:
            current_app.logger.warning(f"Could not retrieve price details: {e}")
        
        # Create or retrieve Stripe customer
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    'user_id': str(current_user.id),
                    'username': current_user.username
                }
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
            customer_id = customer.id
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICES[plan],
                'quantity': 1,
            }],
            mode='subscription',
            customer=customer_id,
            client_reference_id=str(current_user.id),
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.pricing', _external=True),
            subscription_data={
                'trial_period_days': 14,  # 14-day free trial
                'metadata': {
                    'user_id': str(current_user.id),
                    'plan_name': plan
                }
            },
            payment_method_collection='always'  # Always collect payment method
        )
        
        current_app.logger.info(f"Created checkout session {checkout_session.id} for user {current_user.id} ({current_user.email})")
        current_app.logger.info(f"Checkout session URL: {checkout_session.url}")
        
        # Return JSON with redirect URL for JavaScript handling
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('json'):
            return jsonify({'redirect_url': checkout_session.url})
        
        # Use 302 redirect instead of 303
        return redirect(checkout_session.url, code=302)
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error creating checkout session: {str(e)}")
        flash('Error processing subscription with Stripe. Please try again.', 'error')
        return redirect(url_for('billing.pricing'))
    except Exception as e:
        current_app.logger.error(f"Error creating checkout session: {str(e)}")
        flash('Error processing subscription. Please try again.', 'error')
        return redirect(url_for('billing.pricing'))

@billing_bp.route('/success')
@login_required
def success():
    """Handle successful subscription"""
    from recipe_app.db import db
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Retrieve the session
            session = stripe.checkout.Session.retrieve(session_id)
            current_app.logger.info(f"Processing successful checkout session {session_id} for user {current_user.id}")
            current_app.logger.info(f"Session data: subscription={session.subscription}, payment_status={session.payment_status}, status={session.status}")
            
            # Update user's subscription status
            if session.client_reference_id == str(current_user.id):
                # Check if subscription ID exists
                if session.subscription and session.subscription != 'None':
                    # Get the subscription
                    subscription = stripe.Subscription.retrieve(session.subscription)
                    current_app.logger.info(f"Retrieved subscription {subscription.id} with status {subscription.status}")
                    
                    # Update user's plan and subscription data in PostgreSQL
                    plan_mapping = {v: k for k, v in STRIPE_PRICES.items()}
                    new_plan = plan_mapping.get(subscription.items.data[0].price.id, 'Free')
                    
                    current_user.current_plan = new_plan
                    current_user.stripe_subscription_id = subscription.id
                    current_user.subscription_status = subscription.status
                    current_user.is_active = True
                    
                    # Set trial end date if in trial
                    if subscription.trial_end:
                        current_user.trial_end = datetime.fromtimestamp(subscription.trial_end)
                    elif subscription.status == 'trialing':
                        # Fallback: set trial end to 14 days from now
                        current_user.trial_end = datetime.utcnow() + timedelta(days=14)
                    
                    # Save customer ID if not already saved
                    if not current_user.stripe_customer_id and subscription.customer:
                        current_user.stripe_customer_id = subscription.customer
                    
                    db.session.commit()
                    
                    current_app.logger.info(f"User {current_user.email} subscribed to {new_plan} plan with subscription {subscription.id}")
                    flash(f'Successfully subscribed to {new_plan} plan! Your 14-day free trial has started.', 'success')
                else:
                    # Handle case where subscription is not yet available
                    current_app.logger.warning(f"Checkout session {session_id} completed but no subscription ID found")
                    
                    # Check if there's a customer ID we can use to check for pending subscriptions
                    if session.customer:
                        current_app.logger.info(f"Customer ID found: {session.customer}")
                        # Update customer ID even if subscription isn't ready yet
                        if not current_user.stripe_customer_id:
                            current_user.stripe_customer_id = session.customer
                            db.session.commit()
                    
                    flash('Payment processed successfully! Your subscription is being set up. Please check back in a few minutes.', 'info')
            else:
                current_app.logger.warning(f"Client reference ID mismatch: session={session.client_reference_id}, user={current_user.id}")
                flash('There was an issue verifying your payment. Please contact support if your subscription is not activated.', 'warning')
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error handling successful subscription: {str(e)}")
            flash('Payment processed, but there was an error updating your account. Please contact support.', 'warning')
        except Exception as e:
            current_app.logger.error(f"Error handling successful subscription: {str(e)}")
            flash('Subscription processed, but there was an error updating your account. Please contact support.', 'warning')
    else:
        flash('No session ID provided. Please contact support if your payment was processed.', 'warning')
    
    return redirect(url_for('billing.account'))

@billing_bp.route('/account')
@login_required  
def account():
    """Display user's billing account page"""
    subscription_info = None
    
    # Get subscription info from Stripe if user has a subscription
    if current_user.stripe_subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
            subscription_info = {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'trial_end': datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
            }
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Error retrieving subscription for user {current_user.id}: {str(e)}")
    
    return render_template('billing/account.html', user=current_user, subscription_info=subscription_info)


@billing_bp.route('/account.json')
@login_required
def account_json():
    """Return current user's plan and subscription info as JSON for clients."""
    info = {
        'plan': getattr(current_user, 'current_plan', 'Free') or 'Free',
        'is_active': bool(getattr(current_user, 'is_active', True)),
        'trial_end': None,
        'stripe_customer_id': getattr(current_user, 'stripe_customer_id', None),
        'stripe_subscription_id': getattr(current_user, 'stripe_subscription_id', None),
        'subscription_status': getattr(current_user, 'subscription_status', None),
    }
    # Attempt to enrich with Stripe subscription dates if available
    try:
        sub_id = getattr(current_user, 'stripe_subscription_id', None)
        if sub_id:
            subscription = stripe.Subscription.retrieve(sub_id)
            info.update({
                'subscription': {
                    'id': subscription.id,
                    'status': subscription.status,
                    'current_period_start': datetime.fromtimestamp(subscription.current_period_start).isoformat() if subscription.current_period_start else None,
                    'current_period_end': datetime.fromtimestamp(subscription.current_period_end).isoformat() if subscription.current_period_end else None,
                    'trial_end': datetime.fromtimestamp(subscription.trial_end).isoformat() if getattr(subscription, 'trial_end', None) else None,
                    'cancel_at_period_end': subscription.cancel_at_period_end,
                    'canceled_at': datetime.fromtimestamp(subscription.canceled_at).isoformat() if getattr(subscription, 'canceled_at', None) else None,
                }
            })
    except Exception as e:
        current_app.logger.warning(f"Could not enrich account.json with Stripe data: {e}")
    return jsonify(info)

@billing_bp.route('/cancel')
@login_required
def cancel_subscription():
    """Cancel user's subscription"""
    from recipe_app.db import db
    # This would integrate with Stripe to cancel the subscription
    # For now, just update the user's plan
    current_user.current_plan = 'Free'
    current_user.is_active = True
    db.session.commit()
    
    flash('Your subscription has been cancelled. You will continue to have access until the end of your billing period.', 'info')
    return redirect(url_for('billing.account'))

@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        # Handle new subscription
        handle_subscription_created(subscription)
        
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Handle subscription update
        handle_subscription_updated(subscription)
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Handle subscription cancellation
        handle_subscription_deleted(subscription)
        
    elif event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Handle checkout session completion
        handle_checkout_session_completed(session)
        
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        # Handle successful payment
        handle_payment_succeeded(invoice)
        
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        # Handle failed payment
        handle_payment_failed(invoice)

    return jsonify({'status': 'success'})

def handle_subscription_created(subscription):
    """Handle new subscription creation"""
    from recipe_app.db import db
    try:
        customer_id = subscription['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        # Find user by email or customer metadata
        user = User.query.filter_by(email=customer.email).first()
        if not user and customer.metadata.get('user_id'):
            user = User.query.get(int(customer.metadata['user_id']))
        
        if user:
            # Map Stripe price to plan name
            plan_mapping = {v: k for k, v in STRIPE_PRICES.items()}
            new_plan = plan_mapping.get(subscription['items']['data'][0]['price']['id'], 'Free')
            
            # Update user subscription data in PostgreSQL
            user.current_plan = new_plan
            user.stripe_subscription_id = subscription['id']
            user.subscription_status = subscription['status']
            user.is_active = True
            user.stripe_customer_id = customer_id
            
            if subscription.get('trial_end'):
                user.trial_end = datetime.fromtimestamp(subscription['trial_end'])
            
            db.session.commit()
            current_app.logger.info(f"Subscription created for user {user.email}: {new_plan} plan (subscription: {subscription['id']})")
        else:
            current_app.logger.warning(f"User not found for customer {customer_id} in subscription creation webhook")
    except Exception as e:
        current_app.logger.error(f"Error handling subscription creation: {str(e)}")

def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    from recipe_app.db import db
    try:
        customer_id = subscription['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        # Find user by email, customer metadata, or subscription ID
        user = User.query.filter_by(email=customer.email).first()
        if not user and customer.metadata.get('user_id'):
            user = User.query.get(int(customer.metadata['user_id']))
        if not user:
            user = User.query.filter_by(stripe_subscription_id=subscription['id']).first()
        
        if user:
            # Map Stripe price to plan name
            plan_mapping = {v: k for k, v in STRIPE_PRICES.items()}
            new_plan = plan_mapping.get(subscription['items']['data'][0]['price']['id'], 'Free')
            
            # Update user subscription data in PostgreSQL
            user.current_plan = new_plan
            user.stripe_subscription_id = subscription['id']
            user.subscription_status = subscription['status']
            user.is_active = subscription['status'] in ['active', 'trialing']
            user.stripe_customer_id = customer_id
            
            if subscription.get('trial_end'):
                user.trial_end = datetime.fromtimestamp(subscription['trial_end'])
            
            db.session.commit()
            current_app.logger.info(f"Subscription updated for user {user.email}: {new_plan} plan, status: {subscription['status']}")
        else:
            current_app.logger.warning(f"User not found for customer {customer_id} in subscription update webhook")
    except Exception as e:
        current_app.logger.error(f"Error handling subscription update: {str(e)}")

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    from recipe_app.db import db
    try:
        customer_id = subscription['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        # Find user by email, customer metadata, or subscription ID
        user = User.query.filter_by(email=customer.email).first()
        if not user and customer.metadata.get('user_id'):
            user = User.query.get(int(customer.metadata['user_id']))
        if not user:
            user = User.query.filter_by(stripe_subscription_id=subscription['id']).first()
        
        if user:
            # Update user to free plan in PostgreSQL
            user.current_plan = 'Free'
            user.subscription_status = 'canceled'
            user.trial_end = None
            user.is_active = True
            # Keep stripe_subscription_id for reference
            
            db.session.commit()
            current_app.logger.info(f"Subscription cancelled for user {user.email}")
        else:
            current_app.logger.warning(f"User not found for customer {customer_id} in subscription deletion webhook")
    except Exception as e:
        current_app.logger.error(f"Error handling subscription deletion: {str(e)}")

def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    from recipe_app.db import db
    try:
        customer_id = invoice['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if user:
            user.is_active = True
            db.session.commit()
            current_app.logger.info(f"Payment succeeded for user {user.email}")
        else:
            current_app.logger.warning(f"User not found for email {customer.email} in payment success webhook")
    except Exception as e:
        current_app.logger.error(f"Error handling payment success: {str(e)}")

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if user:
            # You might want to send an email notification here
            # For now, just log it
            current_app.logger.warning(f"Payment failed for user {user.email}")
        else:
            current_app.logger.warning(f"User not found for email {customer.email} in payment failure webhook")
    except Exception as e:
        current_app.logger.error(f"Error handling payment failure: {str(e)}")

def handle_checkout_session_completed(session):
    """Handle checkout session completion"""
    from recipe_app.db import db
    try:
        # This is a backup handler in case the success route doesn't work
        client_reference_id = session.get('client_reference_id')
        if client_reference_id:
            user = User.query.get(int(client_reference_id))
            if user and session.get('subscription'):
                subscription = stripe.Subscription.retrieve(session['subscription'])
                
                # Map Stripe price to plan name
                plan_mapping = {v: k for k, v in STRIPE_PRICES.items()}
                new_plan = plan_mapping.get(subscription.items.data[0].price.id, 'Free')
                
                # Update user subscription data in PostgreSQL
                user.current_plan = new_plan
                user.stripe_subscription_id = subscription.id
                user.subscription_status = subscription.status
                user.is_active = True
                
                if subscription.trial_end:
                    user.trial_end = datetime.fromtimestamp(subscription.trial_end)
                
                # Save customer ID if not already saved
                if not user.stripe_customer_id and subscription.customer:
                    user.stripe_customer_id = subscription.customer
                
                db.session.commit()
                current_app.logger.info(f"Checkout session completed for user {user.email}: {new_plan} plan (subscription: {subscription.id})")
            else:
                current_app.logger.warning(f"User not found or no subscription in checkout session {session['id']}")
        else:
            current_app.logger.warning(f"No client reference ID in checkout session {session['id']}")
    except Exception as e:
        current_app.logger.error(f"Error handling checkout session completion: {str(e)}")

@billing_bp.before_app_request
def setup_stripe():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

@billing_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': request.form['price_id'],
                'quantity': 1,
            }],
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.pricing', _external=True),
            subscription_data={
                'trial_period_days': 14,  # 14-day free trial
            }
        )
        return redirect(session.url, code=303)
    except Exception as e:
        current_app.logger.error(f"Error creating checkout session: {str(e)}")
        flash(f'Error creating Stripe session: {e}', 'error')
        return redirect(url_for('billing.pricing'))
