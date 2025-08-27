"""
Advanced Recipe Filtering Service
Handles complex recipe queries with multiple filters including nutrition, equipment, dietary restrictions, etc.
"""

from sqlalchemy import and_, or_, text, func
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from .models import Recipe, Tag, User, RecipeRating
from recipe_app.db import db
import logging

logger = logging.getLogger(__name__)

class AdvancedRecipeFilter:
    """
    Advanced filtering service for recipes with support for:
    - Nutrition-based filtering
    - Equipment requirements
    - Dietary restrictions
    - Time constraints
    - Cost analysis
    - Seasonal recommendations
    """
    
    def __init__(self, user=None):
        self.user = user
        self.query = Recipe.query
        self.filters = []
        self.joins = set()
        
    def build_query(self, filter_data):
        """Build the main query with all filters applied"""
        self._reset_query()
        
        # Apply privacy filtering first
        self._apply_privacy_filter()
        
        # Apply all filters based on form data
        self._apply_basic_filters(filter_data)
        self._apply_time_filters(filter_data)
        self._apply_nutrition_filters(filter_data)
        self._apply_dietary_filters(filter_data)
        self._apply_equipment_filters(filter_data)
        self._apply_cost_filters(filter_data)
        self._apply_cuisine_filters(filter_data)
        self._apply_seasonal_filters(filter_data)
        self._apply_feature_filters(filter_data)
        
        # Apply sorting
        self._apply_sorting(filter_data.get('sort_by', 'relevance'))
        
        return self.query
    
    def _reset_query(self):
        """Reset query to base state"""
        self.query = Recipe.query
        self.filters = []
        self.joins = set()
        
    def _apply_privacy_filter(self):
        """Apply privacy filtering based on user's subscription"""
        if not self.user or not self.user.is_authenticated:
            # Anonymous users can only see public recipes
            self.query = self.query.filter(Recipe.is_private == False)
        elif not self.user.can_view_private_recipes():
            # Free users can see public recipes and their own recipes
            self.query = self.query.filter(
                or_(
                    Recipe.is_private == False,
                    Recipe.user_id == self.user.id
                )
            )
        # Paid users can see all recipes (no additional filter needed)
    
    def _apply_basic_filters(self, filter_data):
        """Apply basic search and metadata filters"""
        
        # Search query
        search_query = filter_data.get('search_query')
        if search_query:
            search_term = f"%{search_query.strip()}%"
            self.query = self.query.filter(
                or_(
                    Recipe.title.ilike(search_term),
                    Recipe.description.ilike(search_term),
                    Recipe.ingredients.ilike(search_term),
                    Recipe.method.ilike(search_term),
                    Recipe.country.ilike(search_term),
                    Recipe.cuisine_type.ilike(search_term)
                )
            )
        
        # Difficulty filter
        difficulty = filter_data.get('difficulty')
        if difficulty:
            self.query = self.query.filter(Recipe.difficulty.in_(difficulty))
        
        # Skill level filter (if we add this field)
        skill_level = filter_data.get('skill_level')
        if skill_level:
            self.query = self.query.filter(Recipe.skill_level.in_(skill_level))
        
        # Servings filter
        min_servings = filter_data.get('min_servings')
        if min_servings:
            self.query = self.query.filter(Recipe.servings >= min_servings)
            
        max_servings = filter_data.get('max_servings')
        if max_servings:
            self.query = self.query.filter(Recipe.servings <= max_servings)
    
    def _apply_time_filters(self, filter_data):
        """Apply time-based filters"""
        
        max_prep_time = filter_data.get('max_prep_time')
        if max_prep_time:
            self.query = self.query.filter(
                or_(
                    Recipe.prep_time.is_(None),
                    Recipe.prep_time <= max_prep_time
                )
            )
        
        max_cook_time = filter_data.get('max_cook_time')
        if max_cook_time:
            self.query = self.query.filter(
                or_(
                    Recipe.cook_time.is_(None),
                    Recipe.cook_time <= max_cook_time
                )
            )
        
        max_total_time = filter_data.get('max_total_time')
        if max_total_time:
            # Calculate total time: prep_time + cook_time
            self.query = self.query.filter(
                or_(
                    and_(Recipe.prep_time.is_(None), Recipe.cook_time.is_(None)),
                    func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0) <= max_total_time
                )
            )
        
        # Quick prep filter
        if filter_data.get('quick_prep'):
            self.query = self.query.filter(
                or_(
                    Recipe.prep_time.is_(None),
                    Recipe.prep_time <= 15
                )
            )
    
    def _apply_nutrition_filters(self, filter_data):
        """Apply nutrition-based filters"""
        # Add nutrition profile join if needed
        nutrition_filters = [
            'max_calories', 'min_protein', 'max_carbs', 'max_fat', 
            'min_fiber', 'max_sodium', 'nutritional_flags', 'has_nutrition_info'
        ]
        
        if any(filter_data.get(f) for f in nutrition_filters):
            if 'nutrition_profile' not in self.joins:
                self.query = self.query.outerjoin('nutrition_profile')
                self.joins.add('nutrition_profile')
        
        # Calorie filter
        max_calories = filter_data.get('max_calories')
        if max_calories:
            self.query = self.query.filter(
                or_(
                    Recipe.nutrition_profile.has() == False,  # No nutrition data
                    Recipe.nutrition_profile.has(calories <= max_calories)
                )
            )
        
        # Protein filter
        min_protein = filter_data.get('min_protein')
        if min_protein:
            self.query = self.query.filter(
                Recipe.nutrition_profile.has(protein_g >= min_protein)
            )
        
        # Carbs filter
        max_carbs = filter_data.get('max_carbs')
        if max_carbs:
            self.query = self.query.filter(
                or_(
                    Recipe.nutrition_profile.has() == False,
                    Recipe.nutrition_profile.has(carbs_g <= max_carbs)
                )
            )
        
        # Fat filter
        max_fat = filter_data.get('max_fat')
        if max_fat:
            self.query = self.query.filter(
                or_(
                    Recipe.nutrition_profile.has() == False,
                    Recipe.nutrition_profile.has(fat_g <= max_fat)
                )
            )
        
        # Fiber filter
        min_fiber = filter_data.get('min_fiber')
        if min_fiber:
            self.query = self.query.filter(
                Recipe.nutrition_profile.has(fiber_g >= min_fiber)
            )
        
        # Sodium filter
        max_sodium = filter_data.get('max_sodium')
        if max_sodium:
            self.query = self.query.filter(
                or_(
                    Recipe.nutrition_profile.has() == False,
                    Recipe.nutrition_profile.has(sodium_mg <= max_sodium)
                )
            )
        
        # Nutritional flags
        nutritional_flags = filter_data.get('nutritional_flags', [])
        for flag in nutritional_flags:
            if flag == 'is_high_protein':
                self.query = self.query.filter(
                    Recipe.nutrition_profile.has(is_high_protein == True)
                )
            elif flag == 'is_low_carb':
                self.query = self.query.filter(
                    Recipe.nutrition_profile.has(is_low_carb == True)
                )
            elif flag == 'is_high_fiber':
                self.query = self.query.filter(
                    Recipe.nutrition_profile.has(is_high_fiber == True)
                )
            elif flag == 'is_low_sodium':
                self.query = self.query.filter(
                    Recipe.nutrition_profile.has(is_low_sodium == True)
                )
            elif flag == 'is_iron_rich':
                self.query = self.query.filter(
                    Recipe.nutrition_profile.has(is_iron_rich == True)
                )
        
        # Has nutrition info filter
        if filter_data.get('has_nutrition_info'):
            self.query = self.query.filter(Recipe.nutrition_profile.has())
    
    def _apply_dietary_filters(self, filter_data):
        """Apply dietary restriction filters"""
        dietary_restrictions = filter_data.get('dietary_restrictions', [])
        
        if dietary_restrictions:
            if 'dietary_compliance' not in self.joins:
                # Join with recipe_dietary_compliance table
                self.query = self.query.join(
                    'dietary_compliance'
                ).join(
                    'dietary_restriction'
                )
                self.joins.add('dietary_compliance')
            
            # Filter recipes that comply with ALL selected dietary restrictions
            for restriction in dietary_restrictions:
                self.query = self.query.filter(
                    Recipe.dietary_compliance.any(name=restriction)
                )
    
    def _apply_equipment_filters(self, filter_data):
        """Apply equipment requirement filters"""
        required_equipment = filter_data.get('required_equipment', [])
        
        if required_equipment:
            if 'no_cook' in required_equipment:
                # Special case: no cooking required
                self.query = self.query.filter(
                    or_(
                        Recipe.cook_time.is_(None),
                        Recipe.cook_time == 0
                    )
                )
                required_equipment.remove('no_cook')
            
            if required_equipment:
                # Filter recipes that can be made with available equipment
                if 'equipment_requirements' not in self.joins:
                    self.query = self.query.outerjoin('equipment_requirements')
                    self.joins.add('equipment_requirements')
                
                # Recipe must not require equipment that user doesn't have
                # This is a complex query - we'll implement a simplified version
                # In a full implementation, you'd want to check equipment requirements
                # against user's available equipment
                pass
    
    def _apply_cost_filters(self, filter_data):
        """Apply cost-based filters"""
        max_cost_per_serving = filter_data.get('max_cost_per_serving')
        
        if max_cost_per_serving:
            self.query = self.query.filter(
                or_(
                    Recipe.cost_per_serving.is_(None),
                    Recipe.cost_per_serving <= max_cost_per_serving
                )
            )
    
    def _apply_cuisine_filters(self, filter_data):
        """Apply cuisine and cultural filters"""
        cuisine_types = filter_data.get('cuisine_type', [])
        
        if cuisine_types:
            # Convert to case-insensitive matching
            cuisine_conditions = []
            for cuisine in cuisine_types:
                cuisine_conditions.append(Recipe.cuisine_type.ilike(f"%{cuisine}%"))
            
            self.query = self.query.filter(or_(*cuisine_conditions))
        
        # Meal type filter (based on tags)
        meal_types = filter_data.get('meal_type', [])
        if meal_types:
            if 'tags' not in self.joins:
                self.query = self.query.join(Recipe.tags)
                self.joins.add('tags')
            
            tag_conditions = []
            for meal_type in meal_types:
                tag_conditions.append(Tag.name.ilike(f"%{meal_type}%"))
            
            self.query = self.query.filter(or_(*tag_conditions))
    
    def _apply_seasonal_filters(self, filter_data):
        """Apply seasonal preference filters"""
        seasonal_preference = filter_data.get('seasonal_preference')
        
        if seasonal_preference == 'current':
            # Determine current season
            current_month = datetime.now().month
            if current_month in [12, 1, 2]:
                seasonal_preference = 'winter'
            elif current_month in [3, 4, 5]:
                seasonal_preference = 'spring'
            elif current_month in [6, 7, 8]:
                seasonal_preference = 'summer'
            else:
                seasonal_preference = 'autumn'
        
        if seasonal_preference and seasonal_preference != 'current':
            if 'seasonal_tags' not in self.joins:
                self.query = self.query.outerjoin('seasonal_tags')
                self.joins.add('seasonal_tags')
            
            # Filter recipes with matching seasonal tags
            self.query = self.query.filter(
                Recipe.seasonal_tags.any(name=seasonal_preference)
            )
    
    def _apply_feature_filters(self, filter_data):
        """Apply recipe feature filters"""
        
        # Has image filter
        if filter_data.get('has_image'):
            self.query = self.query.filter(Recipe.image_file.isnot(None))
        
        # Batch cooking filter
        if filter_data.get('has_batch_cooking'):
            self.query = self.query.filter(Recipe.batch_cooking_notes.isnot(None))
        
        # Freezer friendly filter
        if filter_data.get('freezer_friendly'):
            self.query = self.query.filter(Recipe.freezing_instructions.isnot(None))
        
        # One pot/pan filter (tag-based)
        if filter_data.get('one_pot'):
            if 'tags' not in self.joins:
                self.query = self.query.join(Recipe.tags)
                self.joins.add('tags')
            
            self.query = self.query.filter(
                or_(
                    Tag.name.ilike('%one pot%'),
                    Tag.name.ilike('%one pan%'),
                    Tag.name.ilike('%skillet%')
                )
            )
    
    def _apply_sorting(self, sort_by):
        """Apply sorting to the query"""
        
        if sort_by == 'newest':
            self.query = self.query.order_by(Recipe.created_at.desc())
        elif sort_by == 'oldest':
            self.query = self.query.order_by(Recipe.created_at.asc())
        elif sort_by == 'title_asc':
            self.query = self.query.order_by(Recipe.title.asc())
        elif sort_by == 'title_desc':
            self.query = self.query.order_by(Recipe.title.desc())
        elif sort_by == 'prep_time_asc':
            self.query = self.query.order_by(Recipe.prep_time.asc().nulls_last())
        elif sort_by == 'prep_time_desc':
            self.query = self.query.order_by(Recipe.prep_time.desc().nulls_last())
        elif sort_by == 'total_time_asc':
            self.query = self.query.order_by(
                (func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)).asc()
            )
        elif sort_by == 'total_time_desc':
            self.query = self.query.order_by(
                (func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0)).desc()
            )
        elif sort_by == 'difficulty_asc':
            # Order by difficulty: Easy, Medium, Hard
            self.query = self.query.order_by(
                func.case(
                    (Recipe.difficulty == 'Easy', 1),
                    (Recipe.difficulty == 'Medium', 2),
                    (Recipe.difficulty == 'Hard', 3),
                    else_=2
                )
            )
        elif sort_by == 'difficulty_desc':
            # Order by difficulty: Hard, Medium, Easy
            self.query = self.query.order_by(
                func.case(
                    (Recipe.difficulty == 'Hard', 1),
                    (Recipe.difficulty == 'Medium', 2),
                    (Recipe.difficulty == 'Easy', 3),
                    else_=2
                )
            )
        elif sort_by == 'rating_desc':
            # Order by average rating (requires subquery)
            self.query = self.query.outerjoin(RecipeRating).group_by(Recipe.id).order_by(
                func.avg(RecipeRating.rating).desc().nulls_last()
            )
        # Add nutrition-based sorting
        elif sort_by == 'calories_asc':
            if 'nutrition_profile' not in self.joins:
                self.query = self.query.outerjoin('nutrition_profile')
            self.query = self.query.order_by(Recipe.nutrition_profile.calories.asc().nulls_last())
        elif sort_by == 'calories_desc':
            if 'nutrition_profile' not in self.joins:
                self.query = self.query.outerjoin('nutrition_profile')
            self.query = self.query.order_by(Recipe.nutrition_profile.calories.desc().nulls_last())
        # Add cost-based sorting
        elif sort_by == 'cost_asc':
            self.query = self.query.order_by(Recipe.cost_per_serving.asc().nulls_last())
        elif sort_by == 'cost_desc':
            self.query = self.query.order_by(Recipe.cost_per_serving.desc().nulls_last())
        else:
            # Default relevance sorting
            self.query = self.query.order_by(Recipe.created_at.desc())
    
    def get_filter_counts(self, base_filter_data):
        """Get counts for filter options to show users what's available"""
        counts = {}
        
        # Build base query without specific filters
        base_query = self._build_base_query(base_filter_data)
        
        # Count by difficulty
        counts['difficulty'] = {}
        for diff in ['Easy', 'Medium', 'Hard']:
            count = base_query.filter(Recipe.difficulty == diff).count()
            counts['difficulty'][diff] = count
        
        # Count by cuisine type
        counts['cuisine_type'] = {}
        cuisine_counts = base_query.group_by(Recipe.cuisine_type).with_entities(
            Recipe.cuisine_type, func.count(Recipe.id)
        ).all()
        for cuisine, count in cuisine_counts:
            if cuisine:
                counts['cuisine_type'][cuisine.lower()] = count
        
        return counts
    
    def _build_base_query(self, filter_data):
        """Build base query without specific filters for counting"""
        base_query = Recipe.query
        
        # Apply privacy filter
        if not self.user or not self.user.is_authenticated:
            base_query = base_query.filter(Recipe.is_private == False)
        elif not self.user.can_view_private_recipes():
            base_query = base_query.filter(
                or_(
                    Recipe.is_private == False,
                    Recipe.user_id == self.user.id
                )
            )
        
        # Apply basic search filter
        search_query = filter_data.get('search_query')
        if search_query:
            search_term = f"%{search_query.strip()}%"
            base_query = base_query.filter(
                or_(
                    Recipe.title.ilike(search_term),
                    Recipe.description.ilike(search_term),
                    Recipe.ingredients.ilike(search_term),
                    Recipe.method.ilike(search_term),
                    Recipe.country.ilike(search_term),
                    Recipe.cuisine_type.ilike(search_term)
                )
            )
        
        return base_query


class PantryBasedSuggestions:
    """Service for suggesting recipes based on available pantry items"""
    
    def __init__(self, user):
        self.user = user
    
    def get_suggestions(self, available_ingredients, max_missing=2, filters=None):
        """
        Get recipe suggestions based on available ingredients
        
        Args:
            available_ingredients: List of ingredient names
            max_missing: Maximum number of missing ingredients allowed
            filters: Additional filters (meal_type, max_time, difficulty)
        """
        if not available_ingredients:
            return []
        
        # Build base query
        query = Recipe.query
        
        # Apply privacy filters
        if not self.user.can_view_private_recipes():
            query = query.filter(
                or_(
                    Recipe.is_private == False,
                    Recipe.user_id == self.user.id
                )
            )
        
        # Apply additional filters if provided
        if filters:
            if filters.get('meal_type'):
                # Filter by tags containing meal type
                query = query.join(Recipe.tags).filter(
                    Tag.name.ilike(f"%{filters['meal_type']}%")
                )
            
            if filters.get('max_time'):
                max_time = int(filters['max_time'])
                query = query.filter(
                    func.coalesce(Recipe.prep_time, 0) + func.coalesce(Recipe.cook_time, 0) <= max_time
                )
            
            if filters.get('difficulty'):
                query = query.filter(Recipe.difficulty == filters['difficulty'])
        
        # Get all recipes and calculate ingredient matches
        recipes = query.all()
        suggestions = []
        
        for recipe in recipes:
            match_score, missing_ingredients = self._calculate_ingredient_match(
                recipe, available_ingredients
            )
            
            if len(missing_ingredients) <= max_missing:
                suggestions.append({
                    'recipe': recipe,
                    'match_score': match_score,
                    'missing_ingredients': missing_ingredients,
                    'missing_count': len(missing_ingredients)
                })
        
        # Sort by match score (highest first), then by missing count (lowest first)
        suggestions.sort(key=lambda x: (-x['match_score'], x['missing_count']))
        
        return suggestions[:20]  # Return top 20 suggestions
    
    def _calculate_ingredient_match(self, recipe, available_ingredients):
        """Calculate how well available ingredients match a recipe"""
        # Simple implementation - in production, you'd want more sophisticated parsing
        recipe_ingredients = self._parse_recipe_ingredients(recipe.ingredients)
        available_set = set(ingredient.lower().strip() for ingredient in available_ingredients)
        
        matched_ingredients = []
        missing_ingredients = []
        
        for ingredient in recipe_ingredients:
            ingredient_lower = ingredient.lower()
            
            # Check for exact match or partial match
            found = False
            for available in available_set:
                if available in ingredient_lower or ingredient_lower in available:
                    matched_ingredients.append(ingredient)
                    found = True
                    break
            
            if not found:
                missing_ingredients.append(ingredient)
        
        # Calculate match score (percentage of ingredients available)
        total_ingredients = len(recipe_ingredients)
        if total_ingredients == 0:
            match_score = 0
        else:
            match_score = len(matched_ingredients) / total_ingredients * 100
        
        return match_score, missing_ingredients
    
    def _parse_recipe_ingredients(self, ingredients_text):
        """Parse ingredients text into list of individual ingredients"""
        # Simple parsing - split by lines and clean up
        lines = ingredients_text.split('\n')
        ingredients = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove quantities and measurements (basic implementation)
                # In production, you'd want more sophisticated ingredient parsing
                ingredient = self._extract_ingredient_name(line)
                if ingredient:
                    ingredients.append(ingredient)
        
        return ingredients
    
    def _extract_ingredient_name(self, ingredient_line):
        """Extract the main ingredient name from a recipe line"""
        # Remove common measurements and quantities
        import re
        
        # Remove measurements like "2 cups", "1 tbsp", etc.
        line = re.sub(r'^\d+[^\w]*\s*\w*\s*', '', ingredient_line.strip())
        
        # Remove common words
        common_words = ['chopped', 'diced', 'minced', 'sliced', 'fresh', 'dried', 'ground']
        words = line.split()
        filtered_words = [word for word in words if word.lower() not in common_words]
        
        if filtered_words:
            return ' '.join(filtered_words[:2])  # Take first 2 significant words
        
        return None
