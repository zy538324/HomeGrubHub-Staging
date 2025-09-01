from .routes import main_bp
from .auth_routes import auth_bp
from .community_routes import community_bp
from .community_challenge_routes import community_challenges_bp
from .meal_planning_routes import meal_planning_bp
from .fitness_routes import fitness_bp
from .nutrition_tracking_api import nutrition_bp
from .pantry_routes import pantry_bp
from .scanner_routes import scanner_upload_bp
from .smart_shopping_routes import smart_shopping_bp
from .support_routes import support_bp
from .weekly_shopping_routes import weekly_shopping_bp
from .user_price_routes import user_prices_bp
from .shop_management_routes import shop_management_bp

# Family routes
try:
    from .family_api import family_bp
    from .family_communication import family_communication, parental_controls_bp
    from .family_collaboration import family_collab_bp
except ImportError:
    # Family features not available
    family_bp = None
    family_communication = None
    parental_controls_bp = None
    family_collab_bp = None

# Admin routes
try:
    from .admin_routes import admin_bp
    from .admin_moderation_routes import admin_moderation_bp
except ImportError:
    # Create minimal admin blueprints if they don't exist
    from flask import Blueprint
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    admin_moderation_bp = Blueprint('admin_moderation', __name__, url_prefix='/admin/moderation')
