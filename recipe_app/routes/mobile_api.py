from flask import Blueprint, jsonify, request, current_app, g, url_for
from flask_login import current_user, login_required, login_user
from datetime import date, datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from recipe_app.db import db
from recipe_app.models import (
    User,
    Recipe,
    MealPlan,
    MealPlanEntry,
    WeeklyShoppingList,
    WeeklyShoppingItem,
    NutritionEntry,
    DailyNutritionSummary,
    NutritionGoal,
    # Added for parity
    RecipeReview,
    RecipeRating,
    RecipeCollection,
)
from recipe_app.models.fitness_models import WeightLog, WorkoutLog, ExerciseLog
from recipe_app.models.advanced_models import NutritionProfile
from recipe_app.models.pantry_models import PantryItem, PantryCategory
from recipe_app.models.user_price_models import UserContributedPrice, PriceDataSanitizer, ShopLocation
from functools import wraps
import time
import re

mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api/mobile/v1')

# Accept Bearer tokens for all mobile API requests
@mobile_api.before_request
def _load_user_from_bearer():
    try:
        if current_user.is_authenticated:
            return
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            user = verify_mobile_token(token)
            if user:
                # Log in the user for this request context
                login_user(user, remember=False, force=True, fresh=False)
                g.mobile_token_user = user
    except Exception:
        # Do not block request; protected endpoints still enforce auth
        pass

# Simple, in-process rate limiter (per-IP, per-endpoint)
_RATE_STATE = {}

def rate_limit(limit: int = 60, window_sec: int = 60):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or 'unknown').split(',')[0].strip()
            key = (ip, request.endpoint or fn.__name__)
            now = time.time()
            window = window_sec
            bucket = _RATE_STATE.get(key, [])
            bucket = [t for t in bucket if now - t < window]
            if len(bucket) >= limit:
                return _err('too_many_requests', 429, 'rate_limited')
            bucket.append(now)
            _RATE_STATE[key] = bucket
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Auth utilities/decorators
_DEF_EXP_SECS = 60 * 60 * 24  # 24h

def _signer():
    return URLSafeTimedSerializer(current_app.config.get('SECRET_KEY', 'dev'), salt='mobile-api')

def issue_mobile_token(user_id: int, expires_in: int | None = None) -> str:
    s = _signer()
    payload = {'uid': user_id, 'aud': 'mobile', 'iat': int(datetime.utcnow().timestamp())}
    return s.dumps(payload)

def verify_mobile_token(token: str, max_age: int | None = None):
    s = _signer()
    try:
        data = s.loads(token, max_age=max_age or _DEF_EXP_SECS)
        if data.get('aud') != 'mobile':
            return None
        from recipe_app.models import User
        return User.query.get(int(data['uid']))
    except (BadSignature, SignatureExpired):
        return None

def mobile_auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated:
            return fn(*args, **kwargs)
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            user = verify_mobile_token(auth.split(' ', 1)[1].strip())
            if user:
                login_user(user, remember=False, force=True, fresh=False)
                g.mobile_token_user = user
                return fn(*args, **kwargs)
        return _err('authentication_required', 401, 'auth_required')
    return wrapped

# Helpers

def _ok(data=None, status=200):
    payload = {'success': True}
    if data is not None:
        payload.update(data)
    return jsonify(payload), status


def _err(message, status=400, code=None):
    payload = {'success': False, 'error': message}
    if code:
        payload['code'] = code
    return jsonify(payload), status


def _get_week_start(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def _get_or_create_weekly_list(uid, start=None):
    start = start or _get_week_start()
    end = start + timedelta(days=6)
    lst = WeeklyShoppingList.query.filter_by(user_id=uid, week_start_date=start).first()
    if not lst:
        lst = WeeklyShoppingList(
            user_id=uid,
            week_start_date=start,
            week_end_date=end,
            week_label=f"Week of {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
        )
        db.session.add(lst)
        db.session.commit()
    return lst


# Common pagination/validation helpers

def _get_pagination():
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        size = int(request.args.get('page_size', 20))
    except Exception:
        size = 20
    page = max(page, 1)
    size = min(max(size, 1), 100)
    return page, size

# Health/auth
@mobile_api.get('/health')
def health():
    return jsonify(status='ok', service='mobile_api', version='v1'), 200

@mobile_api.get('/auth/status')
def auth_status():
    if current_user.is_authenticated:
        return _ok({'authenticated': True, 'user': {'id': current_user.id, 'email': current_user.email}})
    return _ok({'authenticated': False})

# Auth exchange: exchange current session for a bearer token
@mobile_api.post('/auth/exchange')
@mobile_auth_required
def auth_exchange():
    token = issue_mobile_token(current_user.id)
    return _ok({'token': token, 'token_type': 'Bearer', 'expires_in': _DEF_EXP_SECS})

# JSON username/password login issuing a mobile bearer token
@mobile_api.post('/auth/login')
@rate_limit(limit=5, window_sec=60)
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return _err('username and password required', 400, 'bad_request')
    # Lookup by email or username
    user = User.query.filter((User.email == username) | (User.username == username)).first()
    if not user or not user.check_password(password):
        return _err('invalid_credentials', 401, 'invalid_credentials')
    login_user(user, remember=True, fresh=True)
    token = issue_mobile_token(user.id)
    return _ok({'token': token, 'token_type': 'Bearer', 'user': {'id': user.id, 'email': user.email, 'username': user.username}})

# User
@mobile_api.get('/me')
@mobile_auth_required
def me():
    u = current_user
    sub = {
        'plan': u.current_plan,
        'status': u.subscription_status,
        'trial_end': u.trial_end.isoformat() if u.trial_end else None,
    }
    return _ok({'id': u.id, 'email': u.email, 'username': u.username, 'display_name': u.display_name, 'subscription': sub})

@mobile_api.get('/me/subscription')
@mobile_auth_required
def me_subscription():
    u = current_user
    pricing_tiers = [
        {
            'name': 'Free',
            'price': '£0',
            'period': 'forever',
            'description': 'Basic access to public recipes and community features',
            'features': [
                'Public recipes', 'Basic search', 'Community feed'
            ],
            'stripe_price_id': None,
            'popular': False,
        },
        {
            'name': 'Home',
            'price': '£4.99',
            'period': 'month',
            'description': 'Unlock meal planning, shopping list and pantry tracker',
            'features': [
                'Unlimited recipes', 'Meal planning', 'Shopping list generation', 'Pantry tracker'
            ],
            'stripe_price_id': 'price_home_monthly',
            'popular': True,
        },
        {
            'name': 'Pro',
            'price': '£9.99',
            'period': 'month',
            'description': 'All features plus advanced nutrition and barcode scanner',
            'features': [
                'Everything in Home', 'Advanced nutrition', 'Barcode scanning', 'Priority support'
            ],
            'stripe_price_id': 'price_pro_monthly',
            'popular': False,
        },
    ]
    return _ok({
        'plan': u.current_plan,
        'status': u.subscription_status,
        'trial_end': u.trial_end.isoformat() if u.trial_end else None,
        'entitlements': [],  # TODO: derive from plan
        'pricing_tiers': pricing_tiers,
    })

@mobile_api.get('/me/settings')
@mobile_auth_required
def me_settings_get():
    # Placeholder user settings
    return _ok({'notifications': True, 'units': 'metric'})

@mobile_api.put('/me/settings')
@mobile_auth_required
def me_settings_put():
    # Accept and store settings later
    return _ok({'updated': True})

# Recipes
# Remove delegators and handle flags inline in recipes_list

@mobile_api.get('/recipes')
@rate_limit(limit=120, window_sec=60)
def recipes_list():
    page, size = _get_pagination()
    q = request.args.get('q')
    mine = request.args.get('mine')
    favourite = request.args.get('favourite')

    # Base query per privacy
    if current_user.is_authenticated:
        base_qs = Recipe.query.filter(
            db.or_(
                Recipe.is_private == False,
                Recipe.user_id == current_user.id
            )
        )
    else:
        base_qs = Recipe.query.filter(Recipe.is_private == False)

    # Favourites filter
    if favourite is not None and current_user.is_authenticated:
        from recipe_app.models import user_favourites
        qs = db.session.query(Recipe).join(user_favourites, (user_favourites.c.recipe_id == Recipe.id)) \
            .filter(user_favourites.c.user_id == current_user.id)
    # Mine filter
    elif mine is not None and current_user.is_authenticated:
        qs = base_qs.filter(Recipe.user_id == current_user.id)
    else:
        qs = base_qs

    if q:
        qs = qs.filter(Recipe.title.ilike(f"%{q}%"))

    total = qs.count()
    items = qs.order_by(Recipe.created_at.desc()).offset((page-1)*size).limit(size).all()
    data = []
    for r in items:
        img_url = None
        try:
            if getattr(r, 'image_file', None):
                img_url = url_for('static', filename=f'uploads/{r.image_file}', _external=True)
        except Exception:
            img_url = None
        # Determine source_type for badges in mobile app
        if r.is_private:
            source_type = 'private'
        else:
            try:
                source_type = 'public' if (current_user.is_authenticated and r.user_id == current_user.id) else 'community'
            except Exception:
                source_type = 'community'
        data.append({
            'id': r.id,
            'title': r.title,
            'description': r.description,
            'image_url': img_url,
            'author_id': r.user_id,
            'rating': round(r.average_rating(), 2) if hasattr(r, 'average_rating') else 0,
            'reviews': r.rating_count() if hasattr(r, 'rating_count') else 0,
            'source_type': source_type,
        })
    return _ok({'page': page, 'page_size': size, 'total': total, 'items': data})

@mobile_api.get('/recipes/<int:rid>')
@rate_limit(limit=240, window_sec=60)
def recipes_get(rid):
    r = Recipe.query.get_or_404(rid)
    # Enforce privacy rules
    if current_user.is_authenticated:
        if not r.can_be_viewed_by(current_user):
            return _err('forbidden', 403, 'forbidden')
    else:
        if r.is_private:
            return _err('not_found', 404, 'not_found')
    # Build absolute image URL if available
    img_url = None
    try:
        if getattr(r, 'image_file', None):
            # For mobile API, use the current request host to build image URLs
            # This ensures consistency between API calls and image URLs
            if request.is_secure:
                scheme = 'https'
            else:
                scheme = 'http'
            host = request.headers.get('Host', 'staging.homegrubhub.co.uk')
            img_url = f"{scheme}://{host}/static/uploads/{r.image_file}"
    except Exception:
        img_url = None
    # Build nutrition data from nutrition_profile
    nutrition_data = None
    calories = protein = carbs = fat = None
    
    if hasattr(r, 'nutrition_profile') and r.nutrition_profile:
        np = r.nutrition_profile
        # Extract values with proper null handling
        calories = getattr(np, 'calories', None)
        protein = getattr(np, 'protein_g', None)
        carbs = getattr(np, 'carbs_g', None)
        fat = getattr(np, 'fat_g', None)
        
        nutrition_data = {
            'calories': calories,
            'protein': protein,
            'protein_g': protein,  # Both formats for compatibility
            'carbs': carbs,
            'carbs_g': carbs,
            'carbohydrates': carbs,  # Alternative naming
            'fat': fat,
            'fat_g': fat,
            'total_fat': fat,  # Alternative naming
            'fiber': getattr(np, 'fiber_g', None),
            'fiber_g': getattr(np, 'fiber_g', None),
            'sugar_g': getattr(np, 'sugar_g', None),
            'sodium_mg': getattr(np, 'sodium_mg', None),
            'potassium_mg': getattr(np, 'potassium_mg', None),
            'iron_mg': getattr(np, 'iron_mg', None),
            'calcium_mg': getattr(np, 'calcium_mg', None),
            'vitamin_c_mg': getattr(np, 'vitamin_c_mg', None),
            'vitamin_d_ug': getattr(np, 'vitamin_d_ug', None),
        }
    
    return _ok({
        'id': r.id,
        'title': r.title,
        'description': r.description,
        'ingredients': r.ingredients,
        # Site model uses `method`; expose it as `instructions` for app compatibility
        'instructions': getattr(r, 'method', None),
        'servings': getattr(r, 'servings', None),
        'image_url': img_url,
        'rating': round(r.average_rating(), 2) if hasattr(r, 'average_rating') else 0,
        'reviews': r.rating_count() if hasattr(r, 'rating_count') else 0,
        'nutrition': nutrition_data,
        # Also include direct fields for backwards compatibility  
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'source_type': ('private' if r.is_private else ('public' if (current_user.is_authenticated and r.user_id == current_user.id) else 'community'))
    })

@mobile_api.post('/recipes/<int:rid>/shopping-list')
@mobile_auth_required
def recipes_add_ingredients_to_weekly_list(rid: int):
    """Add all recipe ingredients to the current user's weekly shopping list.
    Request JSON: { servings: int (optional), include_optional: bool (optional, default true) }
    Response: { added: int, list_id: int }
    """
    r = Recipe.query.get_or_404(rid)
    data = request.get_json(silent=True) or {}
    req_servings = None
    try:
        if data.get('servings') is not None:
            req_servings = int(data.get('servings'))
    except Exception:
        req_servings = None
    include_optional = bool(data.get('include_optional', True))

    # Compute scaling factor based on requested servings vs recipe.servings
    base_servings = getattr(r, 'servings', None) or 1
    factor = (req_servings / base_servings) if (req_servings and base_servings) else 1.0

    # Prepare or get this week's list
    week_start = _get_week_start()
    lst = _get_or_create_weekly_list(current_user.id, week_start)

    # Parse ingredients text into lines; very lightweight parser
    text = (r.ingredients or '').strip()
    lines = [ln.strip('-• ').strip() for ln in text.splitlines() if ln.strip()]

    # Simple quantity/unit parser: "1 cup sugar" -> qty=1, unit=cup, name=rest
    qty_unit_re = re.compile(r"^(?P<qty>[\d/\.]+)\s*(?P<unit>[a-zA-Z]+)?\s*(?P<name>.*)$")

    added = 0
    for ln in lines:
        # Optionally skip lines that look like optional items, e.g., '(optional)'
        if not include_optional and ('optional' in ln.lower()):
            continue
        qty = 1.0
        unit = 'units'
        name = ln
        m = qty_unit_re.match(ln)
        if m:
            try:
                raw_qty = m.group('qty') or '1'
                # Handle fractions like 1/2
                if '/' in raw_qty and not raw_qty.strip().endswith('/'):
                    num, den = raw_qty.split('/', 1)
                    qty = float(num) / float(den)
                else:
                    qty = float(raw_qty)
            except Exception:
                qty = 1.0
            parsed_unit = (m.group('unit') or '').strip()
            # Normalize a few common units
            unit_map = {
                'tsp': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
                'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
                'cup': 'cup', 'cups': 'cup',
                'g': 'g', 'gram': 'g', 'grams': 'g',
                'kg': 'kg', 'ml': 'ml', 'l': 'l', 'oz': 'oz', 'lb': 'lb',
                'piece': 'pieces', 'pieces': 'pieces', 'pc': 'pieces'
            }
            unit = unit_map.get(parsed_unit.lower(), parsed_unit.lower() or 'units')
            name_part = (m.group('name') or '').strip()
            if name_part:
                name = name_part
        # Apply scaling factor
        qty = max(0.01, qty * factor)

        # Check for existing item with same name to avoid duplicates
        existing_item = WeeklyShoppingItem.query.filter_by(
            weekly_list_id=lst.id,
            item_name=name
        ).first()
        
        if existing_item and existing_item.unit.lower() == unit.lower():
            # Update existing item quantity
            existing_item.quantity_needed += qty
            if existing_item.source != 'recipe':
                existing_item.source = 'mixed'  # Mark as mixed source
        else:
            # Create new item
            item = WeeklyShoppingItem(
                weekly_list_id=lst.id,
                item_name=name,
                quantity_needed=qty,
                unit=unit,
                category=None,
                notes=None,
                source='recipe',
                recipe_id=r.id,
            )
            db.session.add(item)
        added += 1

    db.session.commit()
    return _ok({'added': added, 'list_id': lst.id}, 201)

# Meal planning
@mobile_api.get('/meal-plan/week')
@mobile_auth_required
def meal_plan_week_get():
    start_str = request.args.get('start')
    start = date.fromisoformat(start_str) if start_str else _get_week_start()
    end = start + timedelta(days=6)
    plan = MealPlan.query.filter_by(user_id=current_user.id, is_active=True).first()
    entries = []
    if plan:
        rows = MealPlanEntry.query.filter(
            MealPlanEntry.meal_plan_id == plan.id,
            MealPlanEntry.planned_date >= start,
            MealPlanEntry.planned_date <= end,
        ).all()
        entries = [{
            'id': e.id,
            'date': e.planned_date.isoformat(),
            'meal_type': e.meal_type,
            'recipe_id': e.recipe_id,
            'servings': e.planned_servings,
        } for e in rows]
    return _ok({'start': start.isoformat(), 'end': end.isoformat(), 'entries': entries})

@mobile_api.post('/meal-plan/entries')
@mobile_auth_required
def meal_plan_entry_create():
    data = request.get_json(silent=True) or {}
    if not data.get('recipe_id') or not data.get('date'):
        return _err('recipe_id and date are required', 400, 'bad_request')
    plan = MealPlan.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not plan:
        today = date.today()
        plan = MealPlan(user_id=current_user.id, name='My Plan', start_date=today, end_date=today + timedelta(days=6))
        db.session.add(plan)
        db.session.commit()
    e = MealPlanEntry(
        meal_plan_id=plan.id,
        recipe_id=int(data.get('recipe_id')),
        planned_date=date.fromisoformat(data.get('date')),
        meal_type=data.get('meal_type') or 'dinner',
        planned_servings=int(data.get('servings') or 1),
    )
    db.session.add(e)
    db.session.commit()
    return _ok({'id': e.id}, 201)

@mobile_api.patch('/meal-plan/entries/<int:eid>')
@mobile_auth_required
def meal_plan_entry_update(eid):
    data = request.get_json(silent=True) or {}
    e = MealPlanEntry.query.get_or_404(eid)
    if 'date' in data:
        e.planned_date = date.fromisoformat(data['date'])
    if 'meal_type' in data:
        e.meal_type = data['meal_type']
    if 'servings' in data:
        e.planned_servings = int(data['servings'])
    db.session.commit()
    return _ok({'updated': True})

@mobile_api.delete('/meal-plan/entries/<int:eid>')
@mobile_auth_required
def meal_plan_entry_delete(eid):
    e = MealPlanEntry.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    return _ok({'deleted': True})

@mobile_api.post('/meal-plan/generate-shopping-list')
@mobile_auth_required
def meal_plan_generate_shopping_list():
    # Generate items from this week's meal plan entries
    start_str = request.args.get('start')
    start = date.fromisoformat(start_str) if start_str else _get_week_start()
    end = start + timedelta(days=6)
    plan = MealPlan.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not plan:
        return _ok({'generated': False, 'reason': 'no_active_plan'})
    entries = MealPlanEntry.query.filter(
        MealPlanEntry.meal_plan_id == plan.id,
        MealPlanEntry.planned_date >= start,
        MealPlanEntry.planned_date <= end,
    ).all()
    if not entries:
        return _ok({'generated': False, 'reason': 'no_entries'})
    lst = _get_or_create_weekly_list(current_user.id, start)
    added = 0
    qty_re = re.compile(r"^(?P<qty>[\d/\.]+)\s*(?P<unit>[a-zA-Z]+)?\s*(?P<name>.*)$")
    for e in entries:
        r = Recipe.query.get(e.recipe_id)
        if not r:
            continue
        base_servings = getattr(r, 'servings', None) or 1
        factor = (e.planned_servings / base_servings) if base_servings else 1.0
        lines = [ln.strip('-• ').strip() for ln in (r.ingredients or '').splitlines() if ln.strip()]
        for ln in lines:
            qty = 1.0
            unit = 'units'
            name = ln
            m = qty_re.match(ln)
            if m:
                try:
                    raw_qty = m.group('qty') or '1'
                    if '/' in raw_qty and not raw_qty.strip().endswith('/'):
                        num, den = raw_qty.split('/', 1)
                        qty = float(num) / float(den)
                    else:
                        qty = float(raw_qty)
                except Exception:
                    qty = 1.0
                unit_map = {
                    'tsp': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
                    'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
                    'cup': 'cup', 'cups': 'cup',
                    'g': 'g', 'gram': 'g', 'grams': 'g',
                    'kg': 'kg', 'ml': 'ml', 'l': 'l', 'oz': 'oz', 'lb': 'lb',
                    'piece': 'pieces', 'pieces': 'pieces', 'pc': 'pieces'
                }
                parsed_unit = (m.group('unit') or '').strip()
                unit = unit_map.get(parsed_unit.lower(), parsed_unit.lower() or 'units')
                name_part = (m.group('name') or '').strip()
                if name_part:
                    name = name_part
            qty = max(0.01, qty * factor)
            db.session.add(WeeklyShoppingItem(
                weekly_list_id=lst.id,
                item_name=name,
                quantity_needed=qty,
                unit=unit,
                category=None,
                notes=None,
                source='plan',
                recipe_id=r.id,
            ))
            added += 1
    db.session.commit()
    return _ok({'generated': True, 'added': added, 'list_id': lst.id})

# Weekly shopping list
@mobile_api.get('/shopping-list/week')
@mobile_auth_required
def shopping_week_get():
    start_str = request.args.get('start')
    start = date.fromisoformat(start_str) if start_str else _get_week_start()
    lst = _get_or_create_weekly_list(current_user.id, start)
    items = lst.items.order_by(WeeklyShoppingItem.id.desc()).all()
    include_pricing = (request.args.get('pricing') in ('1', 'true', 'yes'))
    # Preferred stores bias (names and ids)
    pref_names = set()
    pref_ids = set()
    # Support both comma-separated and repeated query params
    try:
        raw_names = request.args.getlist('preferred_store_names')
        if not raw_names:
            csv = request.args.get('preferred_store_names')
            if csv:
                raw_names = [x.strip() for x in csv.split(',') if x.strip()]
        pref_names = set([x.strip() for x in raw_names if x and x.strip()])
    except Exception:
        pref_names = set()
    try:
        raw_ids = request.args.getlist('preferred_store_ids')
        if not raw_ids:
            csv = request.args.get('preferred_store_ids')
            if csv:
                raw_ids = [x.strip() for x in csv.split(',') if x.strip()]
        pref_ids = set()
        for x in raw_ids:
            try:
                pref_ids.add(int(x))
            except Exception:
                pass
    except Exception:
        pref_ids = set()
    enriched = []
    if include_pricing:
        try:
            # Use lightweight estimator (no scraping)
            from recipe_app.utils.safe_price_service import safe_price_service  # singleton instance
            price_svc = safe_price_service
        except Exception:
            price_svc = None
        for i in items:
            item_dict = {
                'id': i.id,
                'item_name': i.item_name,
                'quantity_needed': i.quantity_needed,
                'unit': i.unit,
                'category': i.category,
                'is_purchased': i.is_purchased,
                'notes': i.notes,
            }
            if price_svc is not None:
                try:
                    comps = price_svc.get_store_comparison(i.item_name)  # returns list of dicts
                    if isinstance(comps, list) and comps:
                        # Filter to preferred stores if provided
                        def _valid(d):
                            return isinstance(d, dict) and 'estimated_price' in d and d.get('store')
                        candidates = [c for c in comps if _valid(c)]
                        pref_candidates = [c for c in candidates if (str(c.get('store')).strip() in pref_names)]
                        pick_from = pref_candidates if pref_candidates else candidates
                        if pick_from:
                            cheapest = min(pick_from, key=lambda c: c.get('estimated_price', 1e9))
                            store = cheapest.get('store')
                            price = cheapest.get('estimated_price')
                            if store:
                                item_dict['recommended_store'] = store
                            if isinstance(price, (int, float)):
                                item_dict['estimated_price'] = float(price)
                except Exception:
                    pass
            # expose store_section as aisle hint
            if getattr(i, 'store_section', None):
                item_dict['store_section'] = i.store_section
            enriched.append(item_dict)
        payload_items = enriched
    else:
        payload_items = [
            {
                'id': i.id,
                'item_name': i.item_name,
                'quantity_needed': i.quantity_needed,
                'unit': i.unit,
                'category': i.category,
                'is_purchased': i.is_purchased,
                'notes': i.notes,
            } for i in items
        ]
    return _ok({'list_id': lst.id, 'week_label': lst.week_label, 'items': payload_items})

@mobile_api.post('/shopping-list/items')
@mobile_auth_required
def shopping_item_add():
    data = request.get_json(silent=True) or {}
    if not (data.get('item_name') or data.get('name')):
        return _err('item_name is required', 400, 'bad_request')
    lst = _get_or_create_weekly_list(current_user.id)
    
    item_name = data.get('item_name') or data.get('name')
    quantity = float(data.get('quantity') or data.get('quantity_needed') or 1)
    unit = data.get('unit') or 'units'
    
    # Check for existing item with same name to avoid duplicates
    existing_item = WeeklyShoppingItem.query.filter_by(
        weekly_list_id=lst.id,
        item_name=item_name
    ).first()
    
    if existing_item and existing_item.unit.lower() == unit.lower():
        # Update existing item quantity
        existing_item.quantity_needed += quantity
        if existing_item.source != 'manual':
            existing_item.source = 'mixed'  # Mark as mixed source
        # Update category if provided and current is None
        if data.get('category') and not existing_item.category:
            existing_item.category = data.get('category')
        db.session.commit()
        return _ok({'id': existing_item.id, 'updated_existing': True}, 200)
    else:
        # Create new item
        i = WeeklyShoppingItem(
            weekly_list_id=lst.id,
            item_name=item_name,
            quantity_needed=quantity,
            unit=unit,
            category=data.get('category'),
            notes=data.get('notes'),
            source='manual'
        )
        db.session.add(i)
        db.session.commit()
        return _ok({'id': i.id, 'updated_existing': False}, 201)

@mobile_api.patch('/shopping-list/items/<int:iid>')
@mobile_auth_required
def shopping_item_update(iid):
    data = request.get_json(silent=True) or {}
    i = WeeklyShoppingItem.query.get_or_404(iid)
    for f in ['item_name', 'category', 'unit', 'notes']:
        if f in data:
            setattr(i, f, data[f])
    if 'quantity_needed' in data or 'quantity' in data:
        i.quantity_needed = float(data.get('quantity_needed') or data.get('quantity'))
    if 'is_purchased' in data:
        i.is_purchased = bool(data['is_purchased'])
        if i.is_purchased:
            i.purchased_at = datetime.utcnow()
    db.session.commit()
    return _ok({'updated': True})

@mobile_api.delete('/shopping-list/items/<int:iid>')
@mobile_auth_required
def shopping_item_delete(iid):
    i = WeeklyShoppingItem.query.get_or_404(iid)
    db.session.delete(i)
    db.session.commit()
    return _ok({'deleted': True})

# Pantry
@mobile_api.get('/pantry/items')
@mobile_auth_required
def pantry_items_list():
    page, size = _get_pagination()
    q = PantryItem.query.filter_by(user_id=current_user.id)
    total = q.count()
    items = q.order_by(PantryItem.updated_at.desc()).offset((page-1)*size).limit(size).all()
    return _ok({'page': page, 'page_size': size, 'total': total, 'items': [x.to_dict() for x in items]})

@mobile_api.post('/pantry/items')
@mobile_auth_required
def pantry_item_create():
    d = request.get_json(silent=True) or {}
    if not d.get('name'):
        return _err('name is required', 400, 'bad_request')
    x = PantryItem(
        user_id=current_user.id,
        name=d.get('name'),
        brand=d.get('brand'),
        current_quantity=float(d.get('current_quantity') or 0),
        unit=d.get('unit') or 'units',
        minimum_quantity=float(d.get('minimum_quantity') or 1),
        ideal_quantity=float(d.get('ideal_quantity') or 5),
        storage_location=d.get('storage_location'),
        notes=d.get('notes')
    )
    db.session.add(x)
    db.session.commit()
    return _ok({'id': x.id}, 201)

@mobile_api.get('/pantry/items/<int:pid>')
@mobile_auth_required
def pantry_item_get(pid):
    x = PantryItem.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    return _ok({'item': x.to_dict()})

@mobile_api.patch('/pantry/items/<int:pid>')
@mobile_auth_required
def pantry_item_update(pid):
    d = request.get_json(silent=True) or {}
    x = PantryItem.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    for f in ['name','brand','unit','minimum_quantity','ideal_quantity','storage_location','notes']:
        if f in d:
            setattr(x, f, d[f])
    if 'current_quantity' in d:
        x.current_quantity = float(d['current_quantity'])
    db.session.commit()
    return _ok({'updated': True})

@mobile_api.delete('/pantry/items/<int:pid>')
@mobile_auth_required
def pantry_item_delete(pid):
    x = PantryItem.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    db.session.delete(x)
    db.session.commit()
    return _ok({'deleted': True})

@mobile_api.post('/pantry/items/<int:pid>/adjust')
@mobile_auth_required
def pantry_item_adjust(pid):
    d = request.get_json(silent=True) or {}
    x = PantryItem.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    amount = float(d.get('amount') or 0)
    op = d.get('operation') or 'subtract'
    x.update_quantity(amount, operation=op)
    db.session.commit()
    return _ok({'new_quantity': x.current_quantity})

@mobile_api.get('/pantry/categories')
@mobile_auth_required
def pantry_categories():
    cats = PantryCategory.query.filter_by(user_id=current_user.id).all()
    return _ok({'items': [{'id': c.id, 'name': c.name} for c in cats]})

# Predictive pantry (low stock)
@mobile_api.get('/pantry/predict-low')
@mobile_auth_required
def pantry_predict_low():
    items = PantryItem.query.filter(
        PantryItem.user_id == current_user.id,
        PantryItem.current_quantity <= PantryItem.minimum_quantity
    ).all()
    return _ok({'items': [x.to_dict() for x in items]})

# Nutrition entries CRUD
@mobile_api.get('/nutrition/entries')
@mobile_auth_required
def nutrition_entries_list():
    from recipe_app.models.nutrition_models import NutritionEntry as NE
    page, size = _get_pagination()
    d_str = request.args.get('date')
    q = NE.query.filter_by(user_id=str(current_user.id))
    if d_str:
        try:
            target = date.fromisoformat(d_str)
            q = q.filter(NE.entry_date == target)
        except ValueError:
            return _err('Invalid date format, expected YYYY-MM-DD', 400, 'bad_request')
    total = q.count()
    items = q.order_by(NE.entry_time.desc()).offset((page-1)*size).limit(size).all()
    return _ok({'page': page, 'page_size': size, 'total': total, 'items': [i.to_dict() for i in items]})

@mobile_api.post('/nutrition/entries')
@mobile_auth_required
def nutrition_entries_create():
    from recipe_app.models.nutrition_models import NutritionEntry as NE
    d = request.get_json(silent=True) or {}
    entry = NE(
        user_id=str(current_user.id),
        entry_date=date.fromisoformat(d.get('entry_date')) if d.get('entry_date') else date.today(),
        barcode=d.get('barcode'),
        product_name=d.get('product_name') or 'Food Item',
        brand=d.get('brand'),
        portion_size=float(d.get('portion_size') or 100.0),
        servings=float(d.get('servings') or 1.0),
        calories=float(d.get('calories') or 0),
        protein=float(d.get('protein') or 0),
        carbs=float(d.get('carbs') or 0),
        fat=float(d.get('fat') or 0),
        fiber=float(d.get('fiber') or 0),
        sugar=float(d.get('sugar') or 0),
        sodium=float(d.get('sodium') or 0),
        saturated_fat=float(d.get('saturated_fat') or 0),
        meal_type=d.get('meal_type') or 'snack',
        notes=d.get('notes')
    )
    db.session.add(entry)
    db.session.commit()
    return _ok({'id': entry.id}, 201)

@mobile_api.delete('/nutrition/entries/<int:nid>')
@mobile_auth_required
def nutrition_entries_delete(nid):
    from recipe_app.models.nutrition_models import NutritionEntry as NE
    e = NE.query.filter_by(id=nid, user_id=str(current_user.id)).first_or_404()
    db.session.delete(e)
    db.session.commit()
    return _ok({'deleted': True})

# Nutrition goals
@mobile_api.get('/nutrition/goals')
@mobile_auth_required
def nutrition_goals_get():
    from recipe_app.models.nutrition_models import NutritionGoal as NG
    g = NG.query.filter_by(user_id=str(current_user.id)).first()
    return _ok({'goals': g.to_dict() if g else None})

@mobile_api.put('/nutrition/goals')
@mobile_auth_required
def nutrition_goals_put():
    from recipe_app.models.nutrition_models import NutritionGoal as NG
    d = request.get_json(silent=True) or {}
    g = NG.query.filter_by(user_id=str(current_user.id)).first()
    if not g:
        g = NG(user_id=str(current_user.id))
        db.session.add(g)
    for f in ['daily_calories','daily_protein','daily_carbs','daily_fat','daily_fiber','daily_sugar','daily_sodium','age','gender','height','weight','activity_level','goal_type']:
        if f in d:
            setattr(g, f, d[f])
    db.session.commit()
    return _ok({'goals': g.to_dict()})

# Support tickets (stubs)
@mobile_api.get('/support/tickets')
@mobile_auth_required
def support_tickets_list():
    return _ok({'tickets': []})

@mobile_api.post('/support/tickets')
@mobile_auth_required
def support_tickets_create():
    d = request.get_json(silent=True) or {}
    # TODO: persist ticket
    return _ok({'created': True, 'ticket': {'id': None, 'subject': d.get('subject'), 'status': 'open'}} , 201)

# Community feed and lightweight content
@mobile_api.get('/community/feed')
@rate_limit(limit=120, window_sec=60)
def community_feed():
    page, size = _get_pagination()
    q = Recipe.query.filter_by(is_private=False, is_approved=True)
    total = q.count()
    rs = q.order_by(Recipe.created_at.desc()).offset((page-1)*size).limit(size).all()
    items = []
    for r in rs:
        img_url = None
        try:
            if getattr(r, 'image_file', None):
                img_url = url_for('static', filename=f'uploads/{r.image_file}', _external=True)
        except Exception:
            pass
        items.append({'id': r.id, 'title': r.title, 'image_url': img_url})
    return _ok({'page': page, 'page_size': size, 'total': total, 'items': items})

@mobile_api.get('/community/posts')
@rate_limit(limit=120, window_sec=60)
def community_posts_list():
    # Stub: no persistence yet
    return _ok({'items': []})

@mobile_api.post('/community/posts')
@mobile_auth_required
def community_posts_create():
    d = request.get_json(silent=True) or {}
    return _ok({'created': True, 'post': {'id': None, 'title': d.get('title'), 'body': d.get('body')}} , 201)

@mobile_api.get('/recipes/<int:rid>/reviews')
@rate_limit(limit=240, window_sec=60)
def recipe_reviews_list(rid):
    Recipe.query.get_or_404(rid)  # ensure recipe exists
    reviews = RecipeReview.query.filter_by(recipe_id=rid, is_approved=True).order_by(RecipeReview.created_at.desc()).all()
    items = [{
        'id': rv.id,
        'recipe_id': rv.recipe_id,
        'user_id': rv.user_id,
        'user_name': getattr(rv.user, 'username', None),
        'rating': rv.rating,
        'text': rv.comment,
        'created_at': rv.created_at.isoformat(),
    } for rv in reviews]
    return _ok({'items': items})

@mobile_api.post('/recipes/<int:rid>/reviews')
@mobile_auth_required
def recipe_reviews_create(rid):
    Recipe.query.get_or_404(rid)  # ensure recipe exists
    d = request.get_json(silent=True) or {}
    try:
        rating_val = int(d.get('rating') or 0)
    except Exception:
        rating_val = 0
    rating_val = max(1, min(5, rating_val))
    comment = (d.get('text') or d.get('comment') or '').strip()
    # Upsert rating
    rr = RecipeRating.query.filter_by(user_id=current_user.id, recipe_id=rid).first()
    if not rr:
        rr = RecipeRating(user_id=current_user.id, recipe_id=rid, rating=rating_val, comment=comment)
        db.session.add(rr)
    else:
        rr.rating = rating_val
        if comment:
            rr.comment = comment
    # Create/update review (one per user for simplicity)
    rv = RecipeReview.query.filter_by(user_id=current_user.id, recipe_id=rid).first()
    if not rv:
        rv = RecipeReview(user_id=current_user.id, recipe_id=rid, rating=rating_val, comment=comment)
        db.session.add(rv)
    else:
        rv.rating = rating_val
        rv.comment = comment
    db.session.commit()
    return _ok({'created': True, 'review': {
        'id': rv.id,
        'recipe_id': rid,
        'rating': rv.rating,
        'text': rv.comment,
    }}, 201)

@mobile_api.get('/collections')
@mobile_auth_required
def collections_list():
    cols = RecipeCollection.query.filter_by(user_id=current_user.id).order_by(RecipeCollection.created_at.desc()).all()
    items = [{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'is_public': c.is_public,
        'recipe_ids': [r.id for r in c.recipes],
    } for c in cols]
    return _ok({'items': items})

@mobile_api.post('/collections')
@mobile_auth_required
def collections_create():
    d = request.get_json(silent=True) or {}
    name = (d.get('name') or '').strip()
    if not name:
        return _err('name is required', 400, 'bad_request')
    desc = d.get('description')
    is_public = bool(d.get('is_public', False))
    c = RecipeCollection(user_id=current_user.id, name=name, description=desc, is_public=is_public)
    db.session.add(c)
    # Attach recipes if provided
    ids = d.get('recipe_ids') or []
    if isinstance(ids, list) and ids:
        rs = Recipe.query.filter(Recipe.id.in_(ids)).all()
        for r in rs:
            c.recipes.append(r)
    db.session.commit()
    return _ok({'id': c.id}, 201)

# Scanner endpoints
@mobile_api.post('/scanner/ocr')
@mobile_auth_required
def scanner_ocr():
    d = request.get_json(silent=True) or {}
    # Expect base64 image or text; return extracted text stub
    return _ok({'text': d.get('text') or '', 'labels': []})

@mobile_api.post('/scanner/barcode/lookup')
@mobile_auth_required
def scanner_barcode_lookup():
    d = request.get_json(silent=True) or {}
    barcode = (d.get('barcode') or '').strip()
    if not barcode:
        return _err('barcode is required', 400, 'bad_request')
    # TODO: integrate external DB; currently not implemented
    return _ok({'found': False})

# New barcode lookup (v1 scope) - GET endpoint for app integration
@mobile_api.get('/barcode/lookup')
@mobile_auth_required
def barcode_lookup():
    """Lookup a barcode and return a normalized product with nutrients.
    Query: ?barcode=EAN
    Response: { found: bool, product: { barcode, product_name, brand, quantity, nutrients: {...} } }
    """
    bc = (request.args.get('barcode') or '').strip()
    if not bc:
        return _err('barcode is required', 400, 'bad_request')
    # Minimal stub; replace with cached external lookup
    product = {
        'barcode': bc,
        'product_name': None,
        'brand': None,
        'quantity': None,
        'nutrients': {
            'calories': None,
            'protein': None,
            'carbs': None,
            'fat': None,
            'fiber': None,
            'sugar': None,
            'sodium': None,
            'saturated_fat': None,
        }
    }
    return _ok({'found': False, 'product': product})


# ================================
# FITNESS TRACKING ENDPOINTS
# ================================

# BMI Calculator and Weight Management
@mobile_api.get('/fitness/bmi/calculate')
@mobile_auth_required
def fitness_bmi_calculate():
    """Calculate BMI from provided height and weight.
    Query: ?weight_kg=70&height_cm=175 OR ?weight_lbs=154&height_feet=5&height_inches=9
    Response: { bmi: number, classification: string, weight_kg: number, height_cm: number }
    """
    try:
        # Get parameters
        weight_kg = request.args.get('weight_kg')
        weight_lbs = request.args.get('weight_lbs')
        height_cm = request.args.get('height_cm')
        height_feet = request.args.get('height_feet')
        height_inches = request.args.get('height_inches')
        
        # Convert weight to kg if provided in lbs
        if weight_lbs:
            weight_kg = float(weight_lbs) * 0.453592
        elif weight_kg:
            weight_kg = float(weight_kg)
        else:
            return _err('Weight is required (weight_kg or weight_lbs)', 400, 'bad_request')
        
        # Convert height to cm if provided in feet/inches
        if height_feet and height_inches:
            height_cm = (float(height_feet) * 12 + float(height_inches)) * 2.54
        elif height_cm:
            height_cm = float(height_cm)
        else:
            return _err('Height is required (height_cm or height_feet+height_inches)', 400, 'bad_request')
        
        # Calculate BMI
        bmi = weight_kg / ((height_cm / 100) ** 2)
        
        # Classify BMI
        if bmi < 18.5:
            classification = 'Underweight'
        elif bmi < 25:
            classification = 'Normal weight'
        elif bmi < 30:
            classification = 'Overweight'
        else:
            classification = 'Obese'
        
        return _ok({
            'bmi': round(bmi, 2),
            'classification': classification,
            'weight_kg': round(weight_kg, 2),
            'height_cm': round(height_cm, 1)
        })
        
    except Exception as e:
        return _err(f'BMI calculation error: {str(e)}', 400, 'calculation_error')

# Weight Logs
@mobile_api.get('/fitness/weight-logs')
@mobile_auth_required
def fitness_weight_logs():
    """Get all weight logs for the current user.
    Query: ?limit=30&start_date=2024-01-01&end_date=2024-12-31
    Response: { logs: [{ id, log_date, weight_kg, body_fat_percentage, notes, created_at }] }
    """
    try:
        limit = min(int(request.args.get('limit', 100)), 500)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.log_date.desc())
        
        if start_date:
            query = query.filter(WeightLog.log_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(WeightLog.log_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
        logs = query.limit(limit).all()
        return _ok({'logs': [log.to_dict() for log in logs]})
        
    except Exception as e:
        return _err(f'Error retrieving weight logs: {str(e)}', 500, 'retrieval_error')

@mobile_api.post('/fitness/weight-logs')
@mobile_auth_required
def fitness_weight_logs_create():
    """Log a weight entry for the current user.
    Body: { weight_kg: number, log_date?: string, body_fat_percentage?: number, notes?: string }
    Response: { log: { id, log_date, weight_kg, body_fat_percentage, notes, created_at } }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data.get('weight_kg'):
            return _err('weight_kg is required', 400, 'bad_request')
        
        log_date_str = data.get('log_date', date.today().isoformat())
        log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
        
        # Check for existing entry for this date
        existing_log = WeightLog.query.filter_by(user_id=current_user.id, log_date=log_date).first()
        
        if existing_log:
            # Update existing
            existing_log.weight_kg = float(data['weight_kg'])
            if data.get('body_fat_percentage'):
                existing_log.body_fat_percentage = float(data['body_fat_percentage'])
            if data.get('notes'):
                existing_log.notes = data['notes']
            db.session.commit()
            return _ok({'log': existing_log.to_dict()})
        else:
            # Create new
            weight_log = WeightLog(
                user_id=current_user.id,
                log_date=log_date,
                weight_kg=float(data['weight_kg']),
                body_fat_percentage=float(data['body_fat_percentage']) if data.get('body_fat_percentage') else None,
                notes=data.get('notes')
            )
            db.session.add(weight_log)
            db.session.commit()
            return _ok({'log': weight_log.to_dict()}, status=201)
            
    except Exception as e:
        db.session.rollback()
        return _err(f'Error creating weight log: {str(e)}', 500, 'creation_error')

@mobile_api.delete('/fitness/weight-logs/<int:log_id>')
@mobile_auth_required
def fitness_weight_logs_delete(log_id):
    """Delete a weight log entry."""
    try:
        weight_log = WeightLog.query.filter_by(id=log_id, user_id=current_user.id).first()
        if not weight_log:
            return _err('Weight log not found', 404, 'not_found')
        
        db.session.delete(weight_log)
        db.session.commit()
        return _ok({'message': 'Weight log deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return _err(f'Error deleting weight log: {str(e)}', 500, 'deletion_error')

# Workout Logs
@mobile_api.get('/fitness/workout-logs')
@mobile_auth_required
def fitness_workout_logs():
    """Get all workout logs for the current user.
    Query: ?limit=50&start_date=2024-01-01&end_date=2024-12-31&include_exercises=true
    Response: { logs: [{ id, workout_date, workout_type, duration_minutes, start_time, end_time, notes, exercises?: [...] }] }
    """
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        include_exercises = request.args.get('include_exercises', 'false').lower() == 'true'
        
        query = WorkoutLog.query.filter_by(user_id=current_user.id).order_by(WorkoutLog.workout_date.desc())
        
        if start_date:
            query = query.filter(WorkoutLog.workout_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(WorkoutLog.workout_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
        logs = query.limit(limit).all()
        
        result_logs = []
        for log in logs:
            log_dict = log.to_dict()
            if include_exercises:
                log_dict['exercises'] = [exercise.to_dict() for exercise in log.exercises]
            result_logs.append(log_dict)
            
        return _ok({'logs': result_logs})
        
    except Exception as e:
        return _err(f'Error retrieving workout logs: {str(e)}', 500, 'retrieval_error')

@mobile_api.post('/fitness/workout-logs')
@mobile_auth_required
def fitness_workout_logs_create():
    """Log a workout entry for the current user.
    Body: { 
        workout_date?: string, 
        workout_type: string, 
        duration_minutes?: number,
        start_time?: string,
        end_time?: string,
        notes?: string,
        exercises?: [{ exercise_name, exercise_type?, sets?, reps?, weight_kg?, distance_km?, duration_minutes?, calories_burned?, notes? }]
    }
    Response: { log: { id, workout_date, workout_type, ... } }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data.get('workout_type'):
            return _err('workout_type is required', 400, 'bad_request')
        
        workout_date_str = data.get('workout_date', date.today().isoformat())
        workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d').date()
        
        # Create workout log
        workout_log = WorkoutLog(
            user_id=current_user.id,
            workout_date=workout_date,
            workout_type=data['workout_type'],
            duration_minutes=data.get('duration_minutes'),
            notes=data.get('notes')
        )
        
        # Handle start and end times
        if data.get('start_time'):
            start_time_str = f"{workout_date_str} {data['start_time']}:00"
            workout_log.start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
            
        if data.get('end_time'):
            end_time_str = f"{workout_date_str} {data['end_time']}:00"
            workout_log.end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        
        db.session.add(workout_log)
        db.session.flush()  # Get the ID
        
        # Add exercises if provided
        exercises_data = data.get('exercises', [])
        for ex_data in exercises_data:
            if ex_data.get('exercise_name'):
                exercise = ExerciseLog(
                    workout_log_id=workout_log.id,
                    exercise_name=ex_data['exercise_name'],
                    exercise_type=ex_data.get('exercise_type'),
                    sets=ex_data.get('sets'),
                    reps=ex_data.get('reps'),
                    weight_kg=ex_data.get('weight_kg'),
                    distance_km=ex_data.get('distance_km'),
                    duration_minutes=ex_data.get('duration_minutes'),
                    calories_burned=ex_data.get('calories_burned'),
                    notes=ex_data.get('notes')
                )
                db.session.add(exercise)
        
        db.session.commit()
        
        # Return with exercises
        result = workout_log.to_dict()
        result['exercises'] = [exercise.to_dict() for exercise in workout_log.exercises]
        return _ok({'log': result}, status=201)
        
    except Exception as e:
        db.session.rollback()
        return _err(f'Error creating workout log: {str(e)}', 500, 'creation_error')

@mobile_api.delete('/fitness/workout-logs/<int:log_id>')
@mobile_auth_required
def fitness_workout_logs_delete(log_id):
    """Delete a workout log entry and all associated exercises."""
    try:
        workout_log = WorkoutLog.query.filter_by(id=log_id, user_id=current_user.id).first()
        if not workout_log:
            return _err('Workout log not found', 404, 'not_found')
        
        # Delete associated exercises first
        ExerciseLog.query.filter_by(workout_log_id=log_id).delete()
        
        # Delete workout
        db.session.delete(workout_log)
        db.session.commit()
        return _ok({'message': 'Workout log and exercises deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return _err(f'Error deleting workout log: {str(e)}', 500, 'deletion_error')

# Exercise Logs (individual exercises within workouts)
@mobile_api.post('/fitness/exercise-logs')
@mobile_auth_required
def fitness_exercise_logs_create():
    """Add an exercise to an existing workout.
    Body: { 
        workout_log_id: number, 
        exercise_name: string, 
        exercise_type?: string,
        sets?: number, 
        reps?: number, 
        weight_kg?: number,
        distance_km?: number,
        duration_minutes?: number,
        calories_burned?: number,
        notes?: string
    }
    Response: { exercise: { id, workout_log_id, exercise_name, ... } }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data.get('workout_log_id') or not data.get('exercise_name'):
            return _err('workout_log_id and exercise_name are required', 400, 'bad_request')
        
        # Verify workout belongs to current user
        workout_log = WorkoutLog.query.filter_by(id=data['workout_log_id'], user_id=current_user.id).first()
        if not workout_log:
            return _err('Workout not found or access denied', 404, 'not_found')
        
        exercise = ExerciseLog(
            workout_log_id=data['workout_log_id'],
            exercise_name=data['exercise_name'],
            exercise_type=data.get('exercise_type'),
            sets=data.get('sets'),
            reps=data.get('reps'),
            weight_kg=data.get('weight_kg'),
            distance_km=data.get('distance_km'),
            duration_minutes=data.get('duration_minutes'),
            calories_burned=data.get('calories_burned'),
            notes=data.get('notes')
        )
        
        db.session.add(exercise)
        db.session.commit()
        
        return _ok({'exercise': exercise.to_dict()}, status=201)
        
    except Exception as e:
        db.session.rollback()
        return _err(f'Error creating exercise log: {str(e)}', 500, 'creation_error')

@mobile_api.delete('/fitness/exercise-logs/<int:exercise_id>')
@mobile_auth_required
def fitness_exercise_logs_delete(exercise_id):
    """Delete an exercise log entry."""
    try:
        # Find exercise and verify it belongs to user via workout
        exercise_log = ExerciseLog.query.join(WorkoutLog).filter(
            ExerciseLog.id == exercise_id,
            WorkoutLog.user_id == current_user.id
        ).first()
        
        if not exercise_log:
            return _err('Exercise log not found or access denied', 404, 'not_found')
        
        db.session.delete(exercise_log)
        db.session.commit()
        return _ok({'message': 'Exercise log deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return _err(f'Error deleting exercise log: {str(e)}', 500, 'deletion_error')

# Fitness Dashboard/Summary
@mobile_api.get('/fitness/dashboard')
@mobile_auth_required
def fitness_dashboard():
    """Get fitness dashboard summary.
    Response: { 
        latest_weight: { log_date, weight_kg, bmi?, classification? },
        recent_workouts: [...],
        this_week_stats: { workouts: number, total_duration: number },
        this_month_stats: { workouts: number, weight_entries: number }
    }
    """
    try:
        # Latest weight
        latest_weight_log = WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.log_date.desc()).first()
        latest_weight = None
        if latest_weight_log:
            latest_weight = latest_weight_log.to_dict()
        
        # Recent workouts (last 5)
        recent_workouts = WorkoutLog.query.filter_by(user_id=current_user.id).order_by(WorkoutLog.workout_date.desc()).limit(5).all()
        
        # This week stats
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_workouts = WorkoutLog.query.filter(
            WorkoutLog.user_id == current_user.id,
            WorkoutLog.workout_date >= week_start
        ).all()
        
        week_total_duration = sum(w.duration_minutes or 0 for w in week_workouts)
        
        # This month stats  
        month_start = date.today().replace(day=1)
        month_workouts = WorkoutLog.query.filter(
            WorkoutLog.user_id == current_user.id,
            WorkoutLog.workout_date >= month_start
        ).count()
        
        month_weight_entries = WeightLog.query.filter(
            WeightLog.user_id == current_user.id,
            WeightLog.log_date >= month_start
        ).count()
        
        return _ok({
            'latest_weight': latest_weight,
            'recent_workouts': [w.to_dict() for w in recent_workouts],
            'this_week_stats': {
                'workouts': len(week_workouts),
                'total_duration': week_total_duration
            },
            'this_month_stats': {
                'workouts': month_workouts,
                'weight_entries': month_weight_entries
            }
        })
        
    except Exception as e:
        return _err(f'Error retrieving fitness dashboard: {str(e)}', 500, 'retrieval_error')


# ================================
# END FITNESS TRACKING ENDPOINTS  
# ================================

# Simple dashboard summary (v1 scope)
@mobile_api.get('/dashboard/summary')
@mobile_auth_required
def dashboard_summary():
    """Return a lightweight dashboard summary for the app."""
    try:
        recipes_total = Recipe.query.filter(
            db.or_(Recipe.is_private == False, Recipe.user_id == current_user.id)
        ).count()
    except Exception:
        recipes_total = 0
    # Shopping stats
    start = _get_week_start()
    lst = _get_or_create_weekly_list(current_user.id, start)
    all_items = lst.items.all() if hasattr(lst.items, 'all') else lst.items
    unpurchased = [i for i in all_items if not getattr(i, 'is_purchased', False)]
    return _ok({
        'recipes_total': recipes_total,
        'shopping_unpurchased_count': len(unpurchased),
        'week_label': lst.week_label,
    })

# Price endpoints
@mobile_api.get('/prices/lookup')
@mobile_auth_required
def prices_lookup():
    item = request.args.get('item')
    return _ok({'item': item, 'prices': []})

@mobile_api.post('/prices/report')
@mobile_auth_required
def prices_report():
    d = request.get_json(silent=True) or {}
    item_name = (d.get('item_name') or d.get('name') or '').strip()
    shop_name = (d.get('shop_name') or d.get('store') or '').strip()
    price = d.get('price')
    location = (d.get('shop_location') or d.get('location') or '').strip()
    size = (d.get('size') or d.get('unit') or '').strip() or None
    if not item_name or not shop_name or price is None or not location:
        return _err('item_name, shop_name, price, shop_location are required', 400, 'bad_request')
    try:
        price_val = float(price)
    except Exception:
        return _err('price must be a number', 400, 'bad_request')
    norm_item = PriceDataSanitizer.normalize_item_name(item_name)
    norm_shop = PriceDataSanitizer.normalize_shop_name(shop_name)
    rec = UserContributedPrice(
        shop_name=shop_name,
        brand_name=d.get('brand_name'),
        item_name=item_name,
        size=size,
        price=price_val,
        price_per_unit=None,
        shop_location=location,
        postcode=d.get('postcode'),
        postcode_area=(d.get('postcode_area') or (d.get('postcode') or '')[:4] or None),
        user_id=current_user.id,
        normalized_item_name=norm_item,
        normalized_shop_name=norm_shop,
    )
    db.session.add(rec)
    db.session.commit()
    return _ok({'created': True, 'id': rec.id}, 201)

@mobile_api.patch('/shops/<int:sid>')
@mobile_auth_required
def shops_update(sid):
    d = request.get_json(silent=True) or {}
    return _ok({'updated': True})

@mobile_api.delete('/shops/<int:sid>')
@mobile_auth_required
def shops_delete(sid):
    return _ok({'deleted': True})

# OpenAPI skeleton (expanded)
@mobile_api.get('/openapi.json')
def openapi_spec():
    base_url = request.host_url.rstrip('/')
    components = {
        'securitySchemes': {
            'bearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
        },
        'schemas': {
            'Error': {
                'type': 'object',
                'required': ['success', 'error'],
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'auth_required'},
                    'code': {'type': 'string', 'example': 'authentication_required'},
                    'message': {'type': 'string'}
                }
            },
            'DashboardSummary': {
                'type': 'object',
                'properties': {
                    'recipes_total': {'type': 'integer'},
                    'shopping_unpurchased_count': {'type': 'integer'},
                    'week_label': {'type': 'string'}
                }
            },
            'WeeklyShoppingItem': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'item_name': {'type': 'string'},
                    'quantity_needed': {'type': 'number'},
                    'unit': {'type': 'string'},
                    'category': {'type': 'string'},
                    'is_purchased': {'type': 'boolean'},
                    'notes': {'type': 'string'},
                    'recommended_store': {'type': 'string'},
                    'estimated_price': {'type': 'number'},
                    'store_section': {'type': 'string'}
                }
            },
            'WeeklyShoppingWeek': {
                'type': 'object',
                'properties': {
                    'list_id': {'type': 'integer'},
                    'week_label': {'type': 'string'},
                    'items': {'type': 'array', 'items': {'$ref': '#/components/schemas/WeeklyShoppingItem'}}
                }
            },
            'RecipeSummary': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'image_url': {'type': 'string'},
                    'source_type': {'type': 'string', 'enum': ['private','public','community']},
                    'rating': {'type': 'number'},
                    'reviews': {'type': 'integer'}
                }
            },
            'RecipeDetail': {
                'allOf': [ {'$ref': '#/components/schemas/RecipeSummary'} ],
                'properties': {
                    'ingredients': {'type': 'string'}, 'instructions': {'type': 'string'}, 'servings': {'type': 'integer'}
                }
            },
            'MealPlanEntry': {
                'type': 'object', 'properties': {
                    'id': {'type':'integer'}, 'date': {'type':'string','format':'date'}, 'meal_type': {'type':'string'}, 'recipe_id': {'type':'integer'}, 'servings': {'type':'integer'}
                }
            },
            'BarcodeProduct': {
                'type': 'object', 'properties': {
                    'barcode': {'type': 'string'},
                    'product_name': {'type': 'string'},
                    'brand': {'type': 'string'},
                    'quantity': {'type': 'string'},
                    'nutrients': {
                        'type': 'object', 'properties': {
                            'calories': {'type': 'number'}, 'protein': {'type': 'number'}, 'carbs': {'type': 'number'},
                            'fat': {'type': 'number'}, 'fiber': {'type': 'number'}, 'sugar': {'type': 'number'}, 'sodium': {'type': 'number'}, 'saturated_fat': {'type': 'number'}
                        }
                    }
                }
            }
        },
        'parameters': {
            'PageParam': {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'default': 1, 'minimum': 1}},
            'PageSizeParam': {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer', 'default': 20, 'minimum': 1, 'maximum': 100}},
            'PreferredStoreNames': {'name': 'preferred_store_names', 'in': 'query', 'schema': {'type':'array','items': {'type':'string'}}, 'style':'form', 'explode': True},
            'PreferredStoreIds': {'name': 'preferred_store_ids', 'in': 'query', 'schema': {'type':'array','items': {'type':'integer'}}, 'style':'form', 'explode': True},
            'PricingParam': {'name': 'pricing', 'in': 'query', 'schema': {'type':'boolean'}}
        },
        'responses': {
            'Unauthorized': {'description': 'Unauthorized', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}},
            'NotFound': {'description': 'Not Found', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}},
            'ValidationError': {'description': 'Validation error', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}
        }
    }
    paths = {
        '/api/mobile/v1/health': {'get': {'summary': 'Health check','responses': {'200': {'description':'OK'}}}},
        '/api/mobile/v1/auth/status': {'get': {'summary': 'Auth status','responses': {'200': {'description':'OK'}}}},
        '/api/mobile/v1/auth/login': {'post': {'summary': 'Login (JSON)','responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/auth/exchange': {'post': {'summary': 'Exchange session for bearer token','responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/me': {'get': {'summary': 'Current user', 'security': [{'bearerAuth': []}],'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/dashboard/summary': {'get': {'summary': 'Dashboard summary', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description': 'OK', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/DashboardSummary'}}}}, '401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/recipes': {'get': {'summary': 'List recipes', 'parameters': [{'$ref': '#/components/parameters/PageParam'},{'$ref': '#/components/parameters/PageSizeParam'}],'responses': {'200': {'description':'OK'}}}},
        '/api/mobile/v1/recipes/{id}': {'get': {'summary': 'Get recipe','responses': {'200': {'description':'OK'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/recipes/{rid}/shopping-list': {'post': {'summary': 'Add recipe ingredients to weekly shopping list', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/meal-plan/week': {'get': {'summary': 'Get week plan', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/meal-plan/entries': {'post': {'summary': 'Create entry', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/meal-plan/entries/{id}': {'patch': {'summary': 'Update entry', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}, 'delete': {'summary': 'Delete entry', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/meal-plan/generate-shopping-list': {'post': {'summary': 'Generate weekly shopping', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/shopping-list/week': {'get': {'summary': 'Get weekly list', 'parameters': [ {'name': 'start','in':'query','schema':{'type':'string','format':'date'}},{'$ref': '#/components/parameters/PricingParam'},{'$ref': '#/components/parameters/PreferredStoreNames'},{'$ref': '#/components/parameters/PreferredStoreIds'}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/shopping-list/items': {'post': {'summary': 'Add item', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/shopping-list/items/{id}': {'patch': {'summary': 'Update item', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}, 'delete': {'summary': 'Delete item', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/nutrition/entries': {'get': {'summary': 'List entries', 'parameters': [{'$ref': '#/components/parameters/PageParam'},{'$ref': '#/components/parameters/PageSizeParam'},{'name':'date','in':'query','schema':{'type':'string','format':'date'}}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}, 'post': {'summary': 'Create entry', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/nutrition/goals': {'get': {'summary': 'Get goals', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}, 'put': {'summary': 'Update goals', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/barcode/lookup': {'get': {'summary': 'Barcode lookup', 'parameters': [{'name':'barcode','in':'query','required': True,'schema': {'type':'string'}}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'OK'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        # Fitness Tracking Endpoints
        '/api/mobile/v1/fitness/bmi/calculate': {'get': {'summary': 'Calculate BMI', 'parameters': [{'name':'weight_kg','in':'query','schema':{'type':'number'}},{'name':'weight_lbs','in':'query','schema':{'type':'number'}},{'name':'height_cm','in':'query','schema':{'type':'number'}},{'name':'height_feet','in':'query','schema':{'type':'number'}},{'name':'height_inches','in':'query','schema':{'type':'number'}}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'BMI calculation result'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/fitness/weight-logs': {'get': {'summary': 'Get weight logs', 'parameters': [{'name':'limit','in':'query','schema':{'type':'integer','default':100}},{'name':'start_date','in':'query','schema':{'type':'string','format':'date'}},{'name':'end_date','in':'query','schema':{'type':'string','format':'date'}}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Weight logs list'},'401': {'$ref':'#/components/responses/Unauthorized'}}}, 'post': {'summary': 'Create weight log', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Weight log created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/fitness/weight-logs/{log_id}': {'delete': {'summary': 'Delete weight log', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Weight log deleted'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/fitness/workout-logs': {'get': {'summary': 'Get workout logs', 'parameters': [{'name':'limit','in':'query','schema':{'type':'integer','default':50}},{'name':'start_date','in':'query','schema':{'type':'string','format':'date'}},{'name':'end_date','in':'query','schema':{'type':'string','format':'date'}},{'name':'include_exercises','in':'query','schema':{'type':'boolean','default':false}}], 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Workout logs list'},'401': {'$ref':'#/components/responses/Unauthorized'}}}, 'post': {'summary': 'Create workout log', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Workout log created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/fitness/workout-logs/{log_id}': {'delete': {'summary': 'Delete workout log', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Workout log deleted'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/fitness/exercise-logs': {'post': {'summary': 'Create exercise log', 'security': [{'bearerAuth': []}], 'responses': {'201': {'description':'Exercise log created'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
        '/api/mobile/v1/fitness/exercise-logs/{exercise_id}': {'delete': {'summary': 'Delete exercise log', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Exercise log deleted'},'401': {'$ref':'#/components/responses/Unauthorized'},'404': {'$ref':'#/components/responses/NotFound'}}}},
        '/api/mobile/v1/fitness/dashboard': {'get': {'summary': 'Get fitness dashboard', 'security': [{'bearerAuth': []}], 'responses': {'200': {'description':'Fitness dashboard data'},'401': {'$ref':'#/components/responses/Unauthorized'}}}},
    }
    spec = {
        'openapi': '3.0.0',
        'info': {'title': 'HomeGrubHub Mobile API', 'version': '1.0.0'},
        'servers': [{'url': base_url}],
        'components': components,
        'paths': paths,
    }
    return jsonify(spec)
