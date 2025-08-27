"""Application blueprint registration utilities."""
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
    family_collab_bp,
)
from recipe_app.routes.email_routes import email_bp
from recipe_app.routes.seo_routes import seo_bp
from recipe_app.routes.predictive_routes import predictive_bp
from recipe_app.routes.mobile_api import mobile_api
from recipe_app.main.billing import billing_bp
from recipe_app.extensions import csrf

def register_blueprints(app):
    """Register Flask blueprints on the provided application."""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(email_bp)

    # Admin blueprints
    if admin_bp:
        app.register_blueprint(admin_bp)
    if admin_moderation_bp:
        app.register_blueprint(admin_moderation_bp)

    # Family feature blueprints
    if family_bp:
        app.register_blueprint(family_bp)
    if family_communication:
        app.register_blueprint(family_communication)
    if family_collab_bp:
        app.register_blueprint(family_collab_bp)

    # Mobile API blueprint with CSRF exemption
    app.register_blueprint(mobile_api)
    try:
        csrf.exempt(mobile_api)
    except Exception:
        pass

    # Domain-specific blueprints
    app.register_blueprint(community_bp, url_prefix="/community")
    app.register_blueprint(community_challenges_bp, url_prefix="/community/challenges")
    app.register_blueprint(meal_planning_bp)
    app.register_blueprint(fitness_bp, url_prefix="/fitness")
    app.register_blueprint(nutrition_bp, url_prefix="/nutrition")
    app.register_blueprint(pantry_bp)
    app.register_blueprint(predictive_bp, url_prefix="/predictive")
    app.register_blueprint(scanner_upload_bp)
    app.register_blueprint(smart_shopping_bp)
    app.register_blueprint(weekly_shopping_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(user_prices_bp)
    app.register_blueprint(shop_management_bp)
    app.register_blueprint(seo_bp)
    app.register_blueprint(billing_bp, url_prefix="/billing")

__all__ = ["register_blueprints"]
