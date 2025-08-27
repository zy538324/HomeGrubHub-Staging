"""
Nutrition Calculator Service
Handles calorie and macro-nutrient calculations for recipes and servings
"""

from decimal import Decimal
from typing import Dict, Any, Optional
import json


class NutritionCalculator:
    """Service for calculating nutrition information per serving"""
    
    def __init__(self):
        # Default daily values for percentage calculations (based on 2000 calorie diet)
        self.daily_values = {
            'calories': 2000,
            'protein_g': 50,
            'carbs_g': 300,
            'fat_g': 65,
            'fiber_g': 25,
            'sodium_mg': 2300,
            'sugar_g': 50
        }
    
    def calculate_per_serving(self, nutrition_data: Dict[str, Any], total_servings: int, portion_size: float = 1.0) -> Dict[str, Any]:
        """
        Calculate nutrition information per serving
        
        Args:
            nutrition_data: Raw nutrition data (typically per 100g)
            total_servings: Number of servings this portion will be divided into
            portion_size: Size of the portion in grams (default 100g)
            
        Returns:
            Dictionary with per-serving nutrition info
        """
        if not nutrition_data or total_servings <= 0:
            return {}
        
        per_serving = {}
        
        # Calculate per serving for each nutrient
        for key, value in nutrition_data.items():
            if isinstance(value, (int, float, Decimal)) and value > 0:
                # First calculate for the portion size, then divide by servings
                portion_value = float(value) * (portion_size / 100.0)  # Assuming nutrition data is per 100g
                per_serving_value = portion_value / total_servings
                per_serving[key] = round(per_serving_value, 2)
            elif isinstance(value, dict) and 'value' in value:
                # Handle structured nutrition data
                original_value = value.get('value', 0)
                if isinstance(original_value, (int, float, Decimal)) and original_value > 0:
                    portion_value = float(original_value) * (portion_size / 100.0)
                    per_serving_value = portion_value / total_servings
                    per_serving[key] = {
                        'value': round(per_serving_value, 2),
                        'label': value.get('label', key),
                        'unit': value.get('unit', '')
                    }
        
        return per_serving
    
    def calculate_macros_percentages(self, nutrition_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate macronutrient percentages (protein, carbs, fat)
        
        Args:
            nutrition_data: Nutrition data per serving
            
        Returns:
            Dictionary with macro percentages
        """
        try:
            # Extract calorie values
            calories = self._extract_value(nutrition_data, 'energy_kcal', 'calories')
            protein_g = self._extract_value(nutrition_data, 'proteins', 'protein_g')
            carbs_g = self._extract_value(nutrition_data, 'carbohydrates', 'carbs_g')
            fat_g = self._extract_value(nutrition_data, 'fat', 'fat_g')
            
            if not calories or calories <= 0:
                return {}
            
            # Calculate calories from each macro
            protein_calories = protein_g * 4  # 4 calories per gram
            carbs_calories = carbs_g * 4      # 4 calories per gram
            fat_calories = fat_g * 9          # 9 calories per gram
            
            total_macro_calories = protein_calories + carbs_calories + fat_calories
            
            if total_macro_calories <= 0:
                return {}
            
            # Calculate percentages
            return {
                'protein_percent': round((protein_calories / total_macro_calories) * 100, 1),
                'carbs_percent': round((carbs_calories / total_macro_calories) * 100, 1),
                'fat_percent': round((fat_calories / total_macro_calories) * 100, 1)
            }
            
        except (ValueError, TypeError, ZeroDivisionError):
            return {}
    
    def calculate_daily_values_percentages(self, nutrition_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate percentage of daily values
        
        Args:
            nutrition_data: Nutrition data per serving
            
        Returns:
            Dictionary with daily value percentages
        """
        daily_percentages = {}
        
        try:
            # Map nutrition keys to daily value keys
            nutrient_mapping = {
                'energy_kcal': 'calories',
                'calories': 'calories',
                'proteins': 'protein_g',
                'protein_g': 'protein_g',
                'carbohydrates': 'carbs_g',
                'carbs_g': 'carbs_g',
                'fat': 'fat_g',
                'fat_g': 'fat_g',
                'fiber': 'fiber_g',
                'fiber_g': 'fiber_g',
                'sodium': 'sodium_mg',
                'sodium_mg': 'sodium_mg',
                'sugars': 'sugar_g',
                'sugar_g': 'sugar_g'
            }
            
            for nutrition_key, daily_key in nutrient_mapping.items():
                if daily_key in self.daily_values:
                    value = self._extract_value(nutrition_data, nutrition_key)
                    if value and value > 0:
                        percentage = (value / self.daily_values[daily_key]) * 100
                        daily_percentages[f"{daily_key}_dv"] = round(percentage, 1)
            
        except (ValueError, TypeError):
            pass
        
        return daily_percentages
    
    def create_total_nutrition_label(self, nutrition_data: Dict[str, Any], servings: int = 1, portion_size: float = 100.0) -> Dict[str, Any]:
        """
        Create a complete nutrition label with total nutrition for multiple servings
        
        Args:
            nutrition_data: Raw nutrition data (per 100g)
            servings: Number of servings to calculate total for
            portion_size: Size of each serving in grams
            
        Returns:
            Complete nutrition label data for total servings
        """
        # Calculate total nutrition for all servings
        total_nutrition = self.calculate_total_nutrition_for_servings(nutrition_data, servings, portion_size)
        
        if not total_nutrition:
            return {
                'per_serving': {},
                'macros': {},
                'daily_values': {},
                'servings': servings,
                'portion_size': portion_size,
                'error': 'No nutrition data available'
            }
        
        # Calculate macro percentages based on total nutrition
        macros = self.calculate_macros_percentages(total_nutrition)
        
        # Calculate daily value percentages based on total nutrition
        daily_values = self.calculate_daily_values_percentages(total_nutrition)
        
        return {
            'per_serving': total_nutrition,  # This is now total for all servings
            'macros': macros,
            'daily_values': daily_values,
            'servings': servings,
            'portion_size': portion_size,
            'total_portion_size': portion_size * servings
        }

    def create_nutrition_label(self, nutrition_data: Dict[str, Any], servings: int = 1, portion_size: float = 100.0) -> Dict[str, Any]:
        """
        Create a complete nutrition label with per-serving data
        
        Args:
            nutrition_data: Raw nutrition data (per 100g)
            servings: Number of servings to divide the portion into
            portion_size: Size of the total portion in grams
            
        Returns:
            Complete nutrition label data
        """
        # Calculate per serving
        per_serving = self.calculate_per_serving(nutrition_data, servings, portion_size)
        
        if not per_serving:
            return {
                'per_serving': {},
                'macros': {},
                'daily_values': {},
                'servings': servings,
                'portion_size': portion_size,
                'error': 'No nutrition data available'
            }
        
        # Calculate macro percentages
        macros = self.calculate_macros_percentages(per_serving)
        
        # Calculate daily value percentages
        daily_values = self.calculate_daily_values_percentages(per_serving)
        
        return {
            'per_serving': per_serving,
            'macros': macros,
            'daily_values': daily_values,
            'servings': servings,
            'portion_size': portion_size,
            'total_recipe': nutrition_data
        }
    
    def format_nutrition_for_display(self, nutrition_label: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format nutrition data for frontend display
        
        Args:
            nutrition_label: Complete nutrition label data
            
        Returns:
            Formatted data ready for display
        """
        per_serving = nutrition_label.get('per_serving', {})
        macros = nutrition_label.get('macros', {})
        daily_values = nutrition_label.get('daily_values', {})
        servings = nutrition_label.get('servings', 1)
        
        # Format main nutrients for display
        display_nutrients = []
        
        # Calories
        calories = self._extract_value(per_serving, 'energy_kcal', 'calories')
        if calories:
            display_nutrients.append({
                'name': 'Calories',
                'value': f"{calories:.0f}",
                'unit': 'kcal',
                'daily_value': daily_values.get('calories_dv')
            })
        
        # Macronutrients
        protein = self._extract_value(per_serving, 'proteins', 'protein_g')
        if protein:
            display_nutrients.append({
                'name': 'Protein',
                'value': f"{protein:.1f}",
                'unit': 'g',
                'daily_value': daily_values.get('protein_g_dv'),
                'macro_percent': macros.get('protein_percent')
            })
        
        carbs = self._extract_value(per_serving, 'carbohydrates', 'carbs_g')
        if carbs:
            display_nutrients.append({
                'name': 'Carbohydrates',
                'value': f"{carbs:.1f}",
                'unit': 'g',
                'daily_value': daily_values.get('carbs_g_dv'),
                'macro_percent': macros.get('carbs_percent')
            })
        
        fat = self._extract_value(per_serving, 'fat', 'fat_g')
        if fat:
            display_nutrients.append({
                'name': 'Fat',
                'value': f"{fat:.1f}",
                'unit': 'g',
                'daily_value': daily_values.get('fat_g_dv'),
                'macro_percent': macros.get('fat_percent')
            })
        
        # Other nutrients
        fiber = self._extract_value(per_serving, 'fiber', 'fiber_g')
        if fiber:
            display_nutrients.append({
                'name': 'Fiber',
                'value': f"{fiber:.1f}",
                'unit': 'g',
                'daily_value': daily_values.get('fiber_g_dv')
            })
        
        sodium = self._extract_value(per_serving, 'sodium', 'sodium_mg')
        if sodium:
            display_nutrients.append({
                'name': 'Sodium',
                'value': f"{sodium:.0f}",
                'unit': 'mg',
                'daily_value': daily_values.get('sodium_mg_dv')
            })
        
        return {
            'nutrients': display_nutrients,
            'servings': servings,
            'macros_summary': macros
        }
    
    def _extract_value(self, data: Dict[str, Any], *keys) -> Optional[float]:
        """
        Extract numeric value from nutrition data, trying multiple keys
        
        Args:
            data: Nutrition data dictionary
            *keys: Keys to try in order
            
        Returns:
            Numeric value or None
        """
        for key in keys:
            if key in data:
                value = data[key]
                
                # Handle structured data
                if isinstance(value, dict) and 'value' in value:
                    value = value['value']
                
                # Convert to float
                if isinstance(value, (int, float, Decimal)):
                    return float(value)
                elif isinstance(value, str):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        
        return None

    def calculate_total_nutrition_for_servings(self, nutrition_data: Dict[str, Any], servings: int, portion_size: float = 100.0) -> Dict[str, Any]:
        """
        Calculate total nutrition information for multiple servings
        
        Args:
            nutrition_data: Raw nutrition data (typically per 100g)
            servings: Number of servings to calculate total for
            portion_size: Size of each serving in grams (default 100g)
            
        Returns:
            Dictionary with total nutrition info for all servings
        """
        if not nutrition_data or servings <= 0:
            return {}
        
        total_nutrition = {}
        
        # Calculate total nutrition for all servings
        for key, value in nutrition_data.items():
            if isinstance(value, (int, float, Decimal)) and value > 0:
                # Calculate for one serving, then multiply by number of servings
                serving_value = float(value) * (portion_size / 100.0)  # Assuming nutrition data is per 100g
                total_value = serving_value * servings
                total_nutrition[key] = round(total_value, 2)
            elif isinstance(value, dict) and 'value' in value:
                # Handle nested structure like {'value': 123, 'unit': 'g'}
                if isinstance(value['value'], (int, float, Decimal)) and value['value'] > 0:
                    serving_value = float(value['value']) * (portion_size / 100.0)
                    total_value = serving_value * servings
                    total_nutrition[key] = {
                        'value': round(total_value, 2),
                        'unit': value.get('unit', '')
                    }
            else:
                # Copy non-numeric values as-is
                total_nutrition[key] = value
        
        return total_nutrition

    def get_product_nutrition_per_serving(self, barcode: str, servings: int, portion_size: float = 100.0) -> Dict[str, Any]:
        """
        Get nutrition information for a product per serving
        
        Args:
            barcode: Product barcode
            servings: Number of servings
            portion_size: Portion size in grams
            
        Returns:
            Dictionary with success status and nutrition data
        """
        try:
            from .barcode_scanner import BarcodeScanner
            
            # Get product data from barcode
            scanner = BarcodeScanner()
            product_data = scanner.get_product_by_barcode(barcode)
            
            if not product_data:
                return {
                    'success': False,
                    'error': 'Product not found'
                }
            
            nutrition_data = product_data.get('nutrition', {})
            if not nutrition_data:
                return {
                    'success': False,
                    'error': 'No nutrition data available for this product'
                }
            
            # Create nutrition label for total servings (what user actually wants)
            nutrition_label = self.create_total_nutrition_label(nutrition_data, servings, portion_size)
            
            return {
                'success': True,
                'product': product_data,
                'nutrition_label': nutrition_label,
                'nutrition': nutrition_label.get('per_serving', {}),
                'servings': servings,
                'portion_size': portion_size
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
