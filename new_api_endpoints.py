@main_bp.route('/api/recipes/<int:recipe_id>')
def api_get_recipe(recipe_id):
    """Get a single recipe by ID."""
    from recipe_app.db import db as _db

    if current_user.is_authenticated and hasattr(current_user, 'can_view_private_recipes') and current_user.can_view_private_recipes():
        recipe = Recipe.query.get_or_404(recipe_id)
    else:
        recipe = Recipe.query.filter(
            _db.and_(
                Recipe.id == recipe_id,
                _db.or_(
                    Recipe.is_private == False,  # public
                    Recipe.user_id == (current_user.id if current_user.is_authenticated else -1)
                )
            )
        ).first_or_404()

    return jsonify(_recipe_to_dict(recipe))

@main_bp.route('/api/favourites')
def api_get_favourites():
    """Get user's favourite recipes."""
    if not current_user.is_authenticated:
        return jsonify({'favourites': [], 'message': 'Authentication required'}), 401

    # For now, return empty list as favourites functionality may not be fully implemented
    # In a full implementation, you would query a favourites table or relationship
    return jsonify({'favourites': []})
