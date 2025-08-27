"""
Nutrition Analysis Service
Integrates with external APIs (Edamam, Spoonacular) to provide nutrition data for recipes
"""

import requests
import os
import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from recipe_app.db import db

logger = logging.getLogger(__name__)

@dataclass
class NutritionData:
    """Data class for nutrition information"""
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    calcium_mg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None
    vitamin_d_ug: Optional[float] = None
    confidence_score: float = 0.0
    data_source: str = "unknown"

class NutritionAnalysisService:
    """Service for analyzing recipe nutrition using external APIs"""
    
    def __init__(self):
        # API Keys - these should be set in environment variables
        self.edamam_app_id = os.environ.get('EDAMAM_APP_ID')
        self.edamam_app_key = os.environ.get('EDAMAM_APP_KEY')
        self.spoonacular_api_key = os.environ.get('SPOONACULAR_API_KEY')
        
        # API Endpoints
        self.edamam_nutrition_url = "https://api.edamam.com/api/nutrition-details"
        self.edamam_food_db_url = "https://api.edamam.com/api/food-database/v2/parser"
        self.spoonacular_nutrition_url = "https://api.spoonacular.com/recipes/parseIngredients"
        
    def analyze_recipe_nutrition(self, recipe, api_source='edamam') -> Optional[NutritionData]:
        """
        Analyze nutrition for a complete recipe
        
        Args:
            recipe: Recipe object
            api_source: 'edamam' or 'spoonacular'
        
        Returns:
            NutritionData object or None if analysis fails
        """
        try:
            if api_source == 'edamam' and self._has_edamam_credentials():
                return self._analyze_with_edamam(recipe)
            elif api_source == 'spoonacular' and self._has_spoonacular_credentials():
                return self._analyze_with_spoonacular(recipe)
            else:
                logger.warning(f"API credentials not available for {api_source}")
                return self._estimate_nutrition_basic(recipe)
                
        except Exception as e:
            logger.error(f"Nutrition analysis failed: {str(e)}")
            return None
    
    def _has_edamam_credentials(self) -> bool:
        """Check if Edamam API credentials are available"""
        return bool(self.edamam_app_id and self.edamam_app_key)
    
    def _has_spoonacular_credentials(self) -> bool:
        """Check if Spoonacular API credentials are available"""
        return bool(self.spoonacular_api_key)
    
    def _analyze_with_edamam(self, recipe) -> Optional[NutritionData]:
        """Analyze nutrition using Edamam API"""
        
        # Parse ingredients for Edamam format
        ingredients_list = self._parse_ingredients_for_api(recipe.ingredients)
        
        if not ingredients_list:
            logger.warning("No valid ingredients found for Edamam analysis")
            return None
        
        # Prepare request data
        request_data = {
            "title": recipe.title,
            "ingr": ingredients_list,
            "summary": recipe.description or "",
            "prep": recipe.method
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "app_id": self.edamam_app_id,
            "app_key": self.edamam_app_key
        }
        
        try:
            response = requests.post(
                self.edamam_nutrition_url,
                json=request_data,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_edamam_response(data, recipe.servings or 4)
            else:
                logger.warning(f"Edamam API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Edamam API request failed: {str(e)}")
            return None
    
    def _analyze_with_spoonacular(self, recipe) -> Optional[NutritionData]:
        """Analyze nutrition using Spoonacular API"""
        
        # Parse ingredients for Spoonacular format
        ingredients_list = self._parse_ingredients_for_api(recipe.ingredients)
        
        if not ingredients_list:
            logger.warning("No valid ingredients found for Spoonacular analysis")
            return None
        
        params = {
            "apiKey": self.spoonacular_api_key,
            "ingredientList": "\n".join(ingredients_list),
            "servings": recipe.servings or 4,
            "includeNutrition": True
        }
        
        try:
            response = requests.post(
                self.spoonacular_nutrition_url,
                data=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_spoonacular_response(data, recipe.servings or 4)
            else:
                logger.warning(f"Spoonacular API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Spoonacular API request failed: {str(e)}")
            return None
    
    def _parse_ingredients_for_api(self, ingredients_text: str) -> List[str]:
        """Parse recipe ingredients text into API-friendly format"""
        if not ingredients_text:
            return []
        
        lines = ingredients_text.strip().split('\n')
        cleaned_ingredients = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove bullet points, numbers, and other formatting
                cleaned_line = re.sub(r'^[\d\-\*\•\·\‣\⁃]+\.?\s*', '', line)
                cleaned_line = cleaned_line.strip()
                
                if cleaned_line and len(cleaned_line) > 2:
                    cleaned_ingredients.append(cleaned_line)
        
        return cleaned_ingredients
    
    def _parse_edamam_response(self, data: dict, servings: int) -> NutritionData:
        """Parse Edamam API response into NutritionData"""
        
        total_nutrients = data.get('totalNutrients', {})
        
        # Extract nutrition data and convert to per-serving
        nutrition = NutritionData(
            data_source='edamam',
            confidence_score=0.8  # Edamam is generally reliable
        )
        
        # Macronutrients
        if 'ENERC_KCAL' in total_nutrients:
            nutrition.calories = total_nutrients['ENERC_KCAL']['quantity'] / servings
        
        if 'PROCNT' in total_nutrients:
            nutrition.protein_g = total_nutrients['PROCNT']['quantity'] / servings
        
        if 'CHOCDF' in total_nutrients:
            nutrition.carbs_g = total_nutrients['CHOCDF']['quantity'] / servings
        
        if 'FAT' in total_nutrients:
            nutrition.fat_g = total_nutrients['FAT']['quantity'] / servings
        
        if 'FIBTG' in total_nutrients:
            nutrition.fiber_g = total_nutrients['FIBTG']['quantity'] / servings
        
        if 'SUGAR' in total_nutrients:
            nutrition.sugar_g = total_nutrients['SUGAR']['quantity'] / servings
        
        # Micronutrients
        if 'NA' in total_nutrients:
            nutrition.sodium_mg = total_nutrients['NA']['quantity'] / servings
        
        if 'K' in total_nutrients:
            nutrition.potassium_mg = total_nutrients['K']['quantity'] / servings
        
        if 'FE' in total_nutrients:
            nutrition.iron_mg = total_nutrients['FE']['quantity'] / servings
        
        if 'CA' in total_nutrients:
            nutrition.calcium_mg = total_nutrients['CA']['quantity'] / servings
        
        if 'VITC' in total_nutrients:
            nutrition.vitamin_c_mg = total_nutrients['VITC']['quantity'] / servings
        
        if 'VITD' in total_nutrients:
            nutrition.vitamin_d_ug = total_nutrients['VITD']['quantity'] / servings
        
        return nutrition
    
    def _parse_spoonacular_response(self, data: list, servings: int) -> NutritionData:
        """Parse Spoonacular API response into NutritionData"""
        
        nutrition = NutritionData(
            data_source='spoonacular',
            confidence_score=0.7  # Slightly lower confidence than Edamam
        )
        
        # Aggregate nutrition from all ingredients
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        total_sugar = 0
        total_sodium = 0
        
        for ingredient in data:
            if 'nutrition' in ingredient:
                nutrients = ingredient['nutrition']['nutrients']
                
                for nutrient in nutrients:
                    name = nutrient.get('name', '').lower()
                    amount = nutrient.get('amount', 0)
                    
                    if 'calorie' in name:
                        total_calories += amount
                    elif 'protein' in name:
                        total_protein += amount
                    elif 'carbohydrate' in name:
                        total_carbs += amount
                    elif 'fat' in name and 'saturated' not in name:
                        total_fat += amount
                    elif 'fiber' in name:
                        total_fiber += amount
                    elif 'sugar' in name:
                        total_sugar += amount
                    elif 'sodium' in name:
                        total_sodium += amount
        
        # Convert to per-serving
        nutrition.calories = total_calories / servings if total_calories > 0 else None
        nutrition.protein_g = total_protein / servings if total_protein > 0 else None
        nutrition.carbs_g = total_carbs / servings if total_carbs > 0 else None
        nutrition.fat_g = total_fat / servings if total_fat > 0 else None
        nutrition.fiber_g = total_fiber / servings if total_fiber > 0 else None
        nutrition.sugar_g = total_sugar / servings if total_sugar > 0 else None
        nutrition.sodium_mg = total_sodium / servings if total_sodium > 0 else None
        
        return nutrition
    
    def _estimate_nutrition_basic(self, recipe) -> NutritionData:
        """Basic nutrition estimation when APIs are unavailable"""
        
        # Very basic estimation based on ingredient patterns
        # This is a fallback and should not be relied upon for accuracy
        
        ingredients_text = recipe.ingredients.lower()
        servings = recipe.servings or 4
        
        # Rough calorie estimation based on ingredient types
        estimated_calories = 200  # Base calories
        
        # Add calories based on ingredient patterns
        if any(word in ingredients_text for word in ['oil', 'butter', 'cream']):
            estimated_calories += 150
        
        if any(word in ingredients_text for word in ['meat', 'chicken', 'beef', 'pork']):
            estimated_calories += 200
        
        if any(word in ingredients_text for word in ['rice', 'pasta', 'bread', 'flour']):
            estimated_calories += 100
        
        if any(word in ingredients_text for word in ['cheese', 'milk']):
            estimated_calories += 80
        
        return NutritionData(
            calories=estimated_calories,
            protein_g=15.0,  # Very rough estimates
            carbs_g=30.0,
            fat_g=8.0,
            confidence_score=0.2,  # Very low confidence
            data_source='estimated'
        )
    
    def update_recipe_nutrition(self, recipe, nutrition_data: NutritionData):
        """Update recipe with nutrition data"""
        
        # Import here to avoid circular imports
        from recipe_app.advanced_models import NutritionProfile
        
        # Check if nutrition profile already exists
        nutrition_profile = recipe.nutrition_profile
        if not nutrition_profile:
            nutrition_profile = NutritionProfile(recipe_id=recipe.id)
            db.session.add(nutrition_profile)
        
        # Update nutrition data
        nutrition_profile.calories = nutrition_data.calories
        nutrition_profile.protein_g = nutrition_data.protein_g
        nutrition_profile.carbs_g = nutrition_data.carbs_g
        nutrition_profile.fat_g = nutrition_data.fat_g
        nutrition_profile.fiber_g = nutrition_data.fiber_g
        nutrition_profile.sugar_g = nutrition_data.sugar_g
        nutrition_profile.sodium_mg = nutrition_data.sodium_mg
        nutrition_profile.potassium_mg = nutrition_data.potassium_mg
        nutrition_profile.iron_mg = nutrition_data.iron_mg
        nutrition_profile.calcium_mg = nutrition_data.calcium_mg
        nutrition_profile.vitamin_c_mg = nutrition_data.vitamin_c_mg
        nutrition_profile.vitamin_d_ug = nutrition_data.vitamin_d_ug
        
        nutrition_profile.data_source = nutrition_data.data_source
        nutrition_profile.confidence_score = nutrition_data.confidence_score
        nutrition_profile.last_updated = db.func.now()
        
        # Calculate percentages and flags
        nutrition_profile.calculate_percentages()
        nutrition_profile.update_nutritional_flags()
        
        try:
            db.session.commit()
            logger.info(f"Updated nutrition for recipe {recipe.id} from {nutrition_data.data_source}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update nutrition for recipe {recipe.id}: {str(e)}")
            return False


class IngredientSubstitutionService:
    """Service for suggesting ingredient substitutions"""
    
    def __init__(self):
        # Common substitution rules
        self.substitution_rules = self._load_substitution_rules()
    
    def _load_substitution_rules(self) -> Dict:
        """Load common ingredient substitution rules"""
        return {
            # Dairy substitutions
            'milk': [
                {'substitute': 'almond milk', 'ratio': 1.0, 'dietary_reason': 'dairy-free'},
                {'substitute': 'oat milk', 'ratio': 1.0, 'dietary_reason': 'dairy-free'},
                {'substitute': 'soy milk', 'ratio': 1.0, 'dietary_reason': 'dairy-free'}
            ],
            'butter': [
                {'substitute': 'coconut oil', 'ratio': 0.75, 'dietary_reason': 'dairy-free'},
                {'substitute': 'olive oil', 'ratio': 0.75, 'dietary_reason': 'dairy-free'},
                {'substitute': 'vegan butter', 'ratio': 1.0, 'dietary_reason': 'vegan'}
            ],
            'cream': [
                {'substitute': 'coconut cream', 'ratio': 1.0, 'dietary_reason': 'dairy-free'},
                {'substitute': 'cashew cream', 'ratio': 1.0, 'dietary_reason': 'vegan'}
            ],
            
            # Egg substitutions
            'eggs': [
                {'substitute': 'flax eggs', 'ratio': 1.0, 'dietary_reason': 'vegan'},
                {'substitute': 'chia eggs', 'ratio': 1.0, 'dietary_reason': 'vegan'},
                {'substitute': 'applesauce', 'ratio': 0.25, 'dietary_reason': 'vegan', 'cooking_method': 'baking'}
            ],
            
            # Flour substitutions
            'wheat flour': [
                {'substitute': 'almond flour', 'ratio': 0.75, 'dietary_reason': 'gluten-free'},
                {'substitute': 'rice flour', 'ratio': 1.0, 'dietary_reason': 'gluten-free'},
                {'substitute': 'oat flour', 'ratio': 1.0, 'dietary_reason': 'gluten-free'}
            ],
            
            # Protein substitutions
            'chicken': [
                {'substitute': 'tofu', 'ratio': 1.0, 'dietary_reason': 'vegetarian'},
                {'substitute': 'tempeh', 'ratio': 1.0, 'dietary_reason': 'vegetarian'},
                {'substitute': 'seitan', 'ratio': 1.0, 'dietary_reason': 'vegetarian'}
            ],
            'beef': [
                {'substitute': 'mushrooms', 'ratio': 1.0, 'dietary_reason': 'vegetarian'},
                {'substitute': 'lentils', 'ratio': 0.75, 'dietary_reason': 'vegetarian'},
                {'substitute': 'black beans', 'ratio': 0.75, 'dietary_reason': 'vegetarian'}
            ],
            
            # Sugar substitutions
            'sugar': [
                {'substitute': 'maple syrup', 'ratio': 0.75, 'dietary_reason': 'natural'},
                {'substitute': 'honey', 'ratio': 0.75, 'dietary_reason': 'natural'},
                {'substitute': 'stevia', 'ratio': 0.1, 'dietary_reason': 'low-calorie'}
            ]
        }
    
    def get_substitutions(self, ingredient: str, dietary_restrictions: List[str] = None, 
                         cooking_method: str = None) -> List[Dict]:
        """
        Get substitution suggestions for an ingredient
        
        Args:
            ingredient: Original ingredient name
            dietary_restrictions: List of dietary restrictions to consider
            cooking_method: Cooking method (e.g., 'baking', 'frying')
        
        Returns:
            List of substitution dictionaries
        """
        ingredient_lower = ingredient.lower().strip()
        substitutions = []
        
        # Look for exact or partial matches in substitution rules
        for rule_ingredient, subs in self.substitution_rules.items():
            if rule_ingredient in ingredient_lower or ingredient_lower in rule_ingredient:
                for sub in subs:
                    # Filter by dietary restrictions if specified
                    if dietary_restrictions:
                        if sub.get('dietary_reason') in dietary_restrictions:
                            substitutions.append({
                                'original': ingredient,
                                'substitute': sub['substitute'],
                                'ratio': sub['ratio'],
                                'ratio_notes': f"Use {sub['ratio']} cups substitute for 1 cup {ingredient}",
                                'dietary_reason': sub.get('dietary_reason'),
                                'cooking_method': sub.get('cooking_method'),
                                'confidence_score': 0.8
                            })
                    else:
                        substitutions.append({
                            'original': ingredient,
                            'substitute': sub['substitute'],
                            'ratio': sub['ratio'],
                            'ratio_notes': f"Use {sub['ratio']} cups substitute for 1 cup {ingredient}",
                            'dietary_reason': sub.get('dietary_reason'),
                            'cooking_method': sub.get('cooking_method'),
                            'confidence_score': 0.8
                        })
        
        return substitutions
    
    def analyze_substitution_impact(self, original_nutrition: NutritionData, 
                                   substitute_nutrition: NutritionData) -> Dict:
        """Analyze the nutritional impact of a substitution"""
        
        impact = {
            'calorie_change': 0,
            'protein_change': 0,
            'carb_change': 0,
            'fat_change': 0,
            'overall_impact': 'minimal'
        }
        
        if original_nutrition.calories and substitute_nutrition.calories:
            impact['calorie_change'] = substitute_nutrition.calories - original_nutrition.calories
        
        if original_nutrition.protein_g and substitute_nutrition.protein_g:
            impact['protein_change'] = substitute_nutrition.protein_g - original_nutrition.protein_g
        
        if original_nutrition.carbs_g and substitute_nutrition.carbs_g:
            impact['carb_change'] = substitute_nutrition.carbs_g - original_nutrition.carbs_g
        
        if original_nutrition.fat_g and substitute_nutrition.fat_g:
            impact['fat_change'] = substitute_nutrition.fat_g - original_nutrition.fat_g
        
        # Determine overall impact level
        total_change = abs(impact['calorie_change']) + abs(impact['protein_change']) * 4 + \
                      abs(impact['carb_change']) * 4 + abs(impact['fat_change']) * 9
        
        if total_change < 50:
            impact['overall_impact'] = 'minimal'
        elif total_change < 100:
            impact['overall_impact'] = 'moderate'
        else:
            impact['overall_impact'] = 'significant'
        
        return impact
