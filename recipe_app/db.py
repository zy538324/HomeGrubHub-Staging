import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from jinja2 import FileSystemLoader, ChoiceLoader
import flask_bootstrap
from configs.config import Config, validate_config
from configs.auth0_config import (
        AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, AUTH0_CALLBACK_URL
    )
from authlib.integrations.flask_client import OAuth

# Adjust sys.path to include the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
bootstrap = Bootstrap()
oauth = OAuth()
csrf = CSRFProtect()

def create_app():
    # Get the path to the project root directory (parent of recipe_app)
    project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recipe_app_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(recipe_app_dir, 'templates')
    static_dir = os.path.join(recipe_app_dir, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)
    validate_config(app.config)

    # Add Flask-Bootstrap templates to the loader
    bootstrap_template_dir = os.path.join(os.path.dirname(flask_bootstrap.__file__), 'templates')
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(template_dir),  # Your custom templates
        FileSystemLoader(bootstrap_template_dir)  # Flask-Bootstrap templates
    ])
    
    # CSRF Configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
    app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow CSRF over HTTP for development
    
    # Don't override the database URI - use the one from Config class
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(project_root_dir, "instance", "recipes.db")}'
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Configure the database engine for better connection handling
    if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
        from sqlalchemy import event
        from sqlalchemy.pool import Pool
        
        @event.listens_for(Pool, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            # This is for PostgreSQL, not SQLite, but we keep the name for consistency
            pass
        
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            # Test the connection is still alive
            try:
                dbapi_connection.cursor().execute("SELECT 1")
            except Exception:
                # Connection is stale, raise an exception to get a new one
                raise Exception("Connection is stale")
    
    login_manager.init_app(app)
    bootstrap.init_app(app)
    oauth.init_app(app)
    csrf.init_app(app)
    
    # Add custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to <br> tags"""
        if text is None:
            return ''
        from markupsafe import Markup
        return Markup(str(text).replace('\n', '<br>\n'))
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Configure Auth0
    app.auth0 = oauth.register(
        'auth0',
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        api_base_url='https://' + AUTH0_DOMAIN,
        access_token_url='https://' + AUTH0_DOMAIN + '/oauth/token',
        authorize_url='https://' + AUTH0_DOMAIN + '/authorize',
        client_kwargs={
            'scope': 'openid profile email',
        },
    )
   

    # Register blueprints using the unified imports from routes.__init__.py
    from recipe_app.routes import (
        main_bp,
        admin_bp,
        admin_moderation_bp,
        community_challenges_bp,
        auth_bp,
        community_bp,
        meal_planning_bp,
        fitness_bp,
        nutrition_bp,
        pantry_bp,
        scanner_upload_bp,
        support_bp,
        smart_shopping_bp,
        weekly_shopping_bp,
        user_prices_bp,
        shop_management_bp,
        family_bp,
        family_communication,
        family_collab_bp
    )
    
    # Import email routes separately
    from recipe_app.routes.email_routes import email_bp
    
    # Import SEO routes
    from recipe_app.routes.seo_routes import seo_bp
    
    # Import Predictive Pantry routes
    from recipe_app.routes.predictive_routes import predictive_bp

    # Register mobile API
    from recipe_app.routes.mobile_api import mobile_api

    # Import nutrition blueprint
    from recipe_app.routes.nutrition_tracking_api import nutrition_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(email_bp)
    
    # Register admin blueprints if available
    if admin_bp:
        app.register_blueprint(admin_bp)
    if admin_moderation_bp:
        app.register_blueprint(admin_moderation_bp)

    # Register family blueprints if available
    if family_bp:
        app.register_blueprint(family_bp)
    if family_communication:
        app.register_blueprint(family_communication)
    if family_collab_bp:
        app.register_blueprint(family_collab_bp)

    # Register mobile API blueprint
    app.register_blueprint(mobile_api)
    
    # Exempt JSON mobile API from CSRF
    from recipe_app.db import csrf as _csrf
    try:
        _csrf.exempt(mobile_api)
    except Exception as _:
        pass
    
    app.register_blueprint(community_bp, url_prefix='/community')
    app.register_blueprint(community_challenges_bp, url_prefix='/community/challenges')
    app.register_blueprint(meal_planning_bp)
    app.register_blueprint(fitness_bp, url_prefix='/fitness')
    app.register_blueprint(nutrition_bp, url_prefix='/nutrition')
    app.register_blueprint(pantry_bp)
    app.register_blueprint(predictive_bp, url_prefix='/predictive')
    app.register_blueprint(scanner_upload_bp)
    app.register_blueprint(smart_shopping_bp)
    app.register_blueprint(weekly_shopping_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(user_prices_bp)  # User-contributed price system
    app.register_blueprint(shop_management_bp)
    app.register_blueprint(seo_bp)  # Register SEO routes

    from .main.billing import billing_bp
    app.register_blueprint(billing_bp, url_prefix='/billing')

    # User loader function
    from .models.models import User
    
    # Import family models to ensure tables are created
    try:
        from .models.family_models import (
            FamilyAccount, FamilyMember, FamilyMealPlan, 
            FamilyShoppingList, FamilyChallenge, FamilyAchievement
        )
        from .models.family_collaboration import (
            FamilyCookingAssignment, FamilyRecipeCollection, 
            FamilyShoppingRequest, FamilyRecipeRating
        )
    except ImportError:
        print("Warning: Family models not available")
    
    # Import nutrition models to ensure tables are created
    try:
        from .models.nutrition_tracking import Food, Meal, NutritionLog
    except ImportError:
        print("Warning: Nutrition tracking models not available")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            # Test database connection
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            print("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")
            app.logger.error(f"Database connection failed: {e}")
            # Don't fail startup, but log the error

    # Configure logging
    import logging
    from logging.handlers import RotatingFileHandler
    
    if not app.debug:
        # Set up file logging for production
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'homegrubhub.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('HomeGrubHub startup')

    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")  # Log the database URI for debugging
    print(f"Resolved Database Path: {os.path.join(project_root_dir, 'instance', 'recipes.db')}")  # Log the resolved database path
    print(f"Current Working Directory: {os.getcwd()}")  # Log the current working directory

    return app