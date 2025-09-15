TIERS = {
    'free': {
        'basic_recipes', 'search', 'public_recipes', 'basic_filtering',
        'recipe_reviews_read', 'upload_recipes', 'community_features',
        'recipe_reviews', 'recipe_collections', 'cooking_challenges',
        'social_features'
    },
    'home': {
        'unlimited_recipes', 'private_recipes', 'basic_tools', 'import_recipes',
        'advanced_filtering', 'nutrition_analysis', 'equipment_filtering',
        'smart_substitutions', 'price_comparison_trends',
        'budget_suggestions_dynamic', 'meal_planning_advanced', 'batch_cooking',
        'voice_assistant', 'offline_recipes_themed', 'community_photos',
        'seasonal_suggestions', 'priority_support', 'pantry_tracker',
        'url_import', 'meal_planning', 'shopping_list_generation',
        'meal_planning_basic'
    },
    'family': {
        'multi_user', 'family_sharing', 'price_comparison_multi',
        'budget_suggestions', 'pantry_tracker_family', 'dynamic_budget_alerts'
    },
    'pro': {
        'pantry_tracker_predictive', 'barcode_scanning',
        'priority_chat_support', 'smart_consumption_forecasting',
        'multi_store_price_comparison', 'advanced_analytics',
        'premium_content'
    }
}

TIER_ORDER = ['free', 'home', 'family', 'pro']

def get_available_features(user_tier: str):
    """Return cumulative feature set for the given tier."""
    tier = (user_tier or 'free').lower()
    features = set()
    for t in TIER_ORDER:
        features |= TIERS.get(t, set())
        if t == tier:
            break
    return features
