"""
Barcode Scanner Integration with OpenFoodFacts API
Handles barcode scanning for ingredient and nutrition data
"""

import requests
import json
from typing import Dict, Optional, List
from urllib.parse import quote

class BarcodeScanner:
    """Service for barcode scanning and OpenFoodFacts integration"""
    
    def __init__(self):
        self.openfoodfacts_api = "https://world.openfoodfacts.org/api/v0/product"
        self.headers = {
            'User-Agent': 'HomeGrubHub/1.0 (homegrubhub.co.uk)'
        }
    
    def get_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """
        Get product information from OpenFoodFacts using barcode
        
        Args:
            barcode (str): The product barcode (EAN-13, UPC-A, etc.)
            
        Returns:
            dict: Product information or None if not found
        """
        try:
            # Clean barcode (remove spaces, validate)
            cleaned_barcode = self._clean_barcode(barcode)
            if not cleaned_barcode:
                return None
                
            # Make API request
            url = f"{self.openfoodfacts_api}/{cleaned_barcode}.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 1:  # Product found
                    return self._parse_product_data(data.get('product', {}))
                    
            return None
            
        except requests.RequestException as e:
            print(f"Error fetching product data: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in barcode lookup: {e}")
            return None
    
    def _clean_barcode(self, barcode: str) -> Optional[str]:
        """Clean and validate barcode"""
        if not barcode:
            return None
            
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, barcode))
        
        # Validate length (common barcode lengths)
        if len(cleaned) in [8, 12, 13, 14]:
            return cleaned
            
        return None
    
    def _parse_product_data(self, product: Dict) -> Dict:
        """Parse OpenFoodFacts product data into our format"""
        
        # Get nutrition data per 100g
        nutrition_100g = product.get('nutriments', {})
        
        # Create nutrition data with proper formatting
        nutrition = {}
        
        # Helper function to format nutrition values
        def format_nutrition_value(value, label, unit):
            if value is not None and value != '':
                try:
                    # Convert to float and round to 1 decimal place
                    numeric_value = round(float(value), 1)
                    return {
                        'value': numeric_value,
                        'label': label,
                        'unit': unit
                    }
                except (ValueError, TypeError):
                    return None
            return None
        
        # Add nutrition values if they exist
        calories = format_nutrition_value(nutrition_100g.get('energy-kcal_100g'), 'Calories', 'kcal')
        if calories:
            nutrition['calories'] = calories
            
        protein = format_nutrition_value(nutrition_100g.get('proteins_100g'), 'Protein', 'g')
        if protein:
            nutrition['protein'] = protein
            
        carbs = format_nutrition_value(nutrition_100g.get('carbohydrates_100g'), 'Carbohydrates', 'g')
        if carbs:
            nutrition['carbs'] = carbs
            
        fat = format_nutrition_value(nutrition_100g.get('fat_100g'), 'Fat', 'g')
        if fat:
            nutrition['fat'] = fat
            
        fiber = format_nutrition_value(nutrition_100g.get('fiber_100g'), 'Fiber', 'g')
        if fiber:
            nutrition['fiber'] = fiber
            
        sugar = format_nutrition_value(nutrition_100g.get('sugars_100g'), 'Sugar', 'g')
        if sugar:
            nutrition['sugar'] = sugar
            
        sodium = format_nutrition_value(nutrition_100g.get('sodium_100g'), 'Sodium', 'mg')
        if sodium:
            nutrition['sodium'] = sodium
            
        salt = format_nutrition_value(nutrition_100g.get('salt_100g'), 'Salt', 'g')
        if salt:
            nutrition['salt'] = salt
        
        # Parse ingredients
        ingredients_text = product.get('ingredients_text', '')
        ingredients_list = []
        
        if ingredients_text:
            # Simple ingredient parsing (could be enhanced)
            ingredients_list = [
                ing.strip() for ing in ingredients_text.split(',')
                if ing.strip()
            ]
        
        # Get categories/tags
        categories = product.get('categories_tags', [])
        
        # Determine dietary restrictions
        dietary_info = self._determine_dietary_restrictions(product)
        
        return {
            'name': product.get('product_name', ''),
            'brand': product.get('brands', ''),
            'barcode': product.get('code', ''),
            'image_url': product.get('image_front_url', ''),
            
            # Nutrition per 100g - formatted for frontend display
            'nutrition': nutrition,
            
            # Ingredients
            'ingredients_text': ingredients_text,
            'ingredients_list': ingredients_list,
            
            # Categories and dietary info
            'categories': categories,
            'dietary_info': self._get_dietary_info_list(dietary_info),
            
            # Additional info
            'quantity': product.get('quantity', ''),
            'packaging': product.get('packaging_tags', []),
            'nova_group': product.get('nova_group'),  # Food processing level
            'nutriscore': product.get('nutriscore_grade', '').upper(),
            
            # Data quality
            'data_quality': product.get('data_quality_tags', []),
            'completeness': product.get('completeness', 0),
            
            # Source
            'source': 'openfoodfacts',
            'openfoodfacts_url': f"https://world.openfoodfacts.org/product/{product.get('code', '')}"
        }
    
    def _determine_dietary_restrictions(self, product: Dict) -> Dict:
        """Determine dietary restrictions from product data"""
        labels = product.get('labels_tags', [])
        ingredients = product.get('ingredients_text', '').lower()
        
        dietary_info = {
            'vegetarian': False,
            'vegan': False,
            'gluten_free': False,
            'dairy_free': False,
            'organic': False,
            'kosher': False,
            'halal': False
        }
        
        # Check labels
        for label in labels:
            label_lower = label.lower()
            if 'vegetarian' in label_lower:
                dietary_info['vegetarian'] = True
            if 'vegan' in label_lower:
                dietary_info['vegan'] = True
                dietary_info['vegetarian'] = True  # Vegan implies vegetarian
            if 'gluten-free' in label_lower or 'sans-gluten' in label_lower:
                dietary_info['gluten_free'] = True
            if 'dairy-free' in label_lower or 'sans-lait' in label_lower:
                dietary_info['dairy_free'] = True
            if 'organic' in label_lower or 'bio' in label_lower:
                dietary_info['organic'] = True
            if 'kosher' in label_lower:
                dietary_info['kosher'] = True
            if 'halal' in label_lower:
                dietary_info['halal'] = True
        
        # Check ingredients for common non-vegetarian/vegan items
        non_veg_keywords = ['meat', 'chicken', 'beef', 'pork', 'fish', 'gelatin']
        dairy_keywords = ['milk', 'cheese', 'butter', 'cream', 'whey', 'casein']
        gluten_keywords = ['wheat', 'barley', 'rye', 'oats']
        
        for keyword in non_veg_keywords:
            if keyword in ingredients:
                dietary_info['vegetarian'] = False
                dietary_info['vegan'] = False
                break
        
        for keyword in dairy_keywords:
            if keyword in ingredients:
                dietary_info['vegan'] = False
                dietary_info['dairy_free'] = False
        
        for keyword in gluten_keywords:
            if keyword in ingredients:
                dietary_info['gluten_free'] = False
        
        return dietary_info
    
    def _get_dietary_info_list(self, dietary_info: Dict) -> List[str]:
        """Convert dietary info dict to a list of positive attributes"""
        info_list = []
        
        if dietary_info.get('vegan'):
            info_list.append('Vegan')
        elif dietary_info.get('vegetarian'):
            info_list.append('Vegetarian')
            
        if dietary_info.get('gluten_free'):
            info_list.append('Gluten-Free')
            
        if dietary_info.get('dairy_free'):
            info_list.append('Dairy-Free')
            
        if dietary_info.get('organic'):
            info_list.append('Organic')
            
        if dietary_info.get('kosher'):
            info_list.append('Kosher')
            
        if dietary_info.get('halal'):
            info_list.append('Halal')
            
        return info_list
    
    def search_products(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for products by name/brand
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results
            
        Returns:
            list: List of matching products
        """
        try:
            url = f"https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                'search_terms': query,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': limit
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                return [
                    self._parse_product_data(product)
                    for product in products
                    if product.get('product_name')
                ]
                
            return []
            
        except Exception as e:
            print(f"Error searching products: {e}")
            return []
