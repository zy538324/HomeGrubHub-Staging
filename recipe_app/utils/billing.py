import stripe
from flask import Blueprint, request, jsonify
from recipe_app.models.models import db, User

stripe.api_key = 'your_stripe_secret_key_here'

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': data['price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=data['success_url'],
            cancel_url=data['cancel_url'],
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = 'your_webhook_secret_here'

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session['customer_email']
        user = User.query.filter_by(email=customer_email).first()
        if user:
            user.current_plan = 'Home'  # Example plan
            user.is_active = True
            db.session.commit()
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice['customer']
        # Update subscription status if needed
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.is_active = False
            db.session.commit()

    return '', 200
