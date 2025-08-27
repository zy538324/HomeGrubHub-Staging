"""
Smart ingredient mapping and shopping list integration
Converts recipe ingredients to purchasable products with price checking
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from recipe_app.db import db
from recipe_app.models.advanced_models import ShoppingListItem
# Removed scraping_models import - replaced with safe price estimation
from recipe_app.utils.safe_price_service import safe_price_service

@dataclass
class IngredientMapping:
    """Maps recipe ingredients to purchasable products"""
    original_ingredient: str
    quantity: float
    unit: str
    product_name: str
    purchasable_unit: str
    conversion_factor: float  # How many recipe units per purchasable unit
    category: str
    notes: str = ""

class IngredientParser:
    """Parse and convert recipe ingredients to purchasable products using dynamic intelligence"""
    
    # Basic unit conversions and packaging knowledge
    LIQUID_UNITS = ['ml', 'cl', 'l', 'litre', 'liter', 'fl oz', 'fluid oz', 'cup', 'cups', 'pint', 'pints']
    WEIGHT_UNITS = ['g', 'gram', 'grams', 'kg', 'kilogram', 'kilograms', 'oz', 'ounce', 'ounces', 'lb', 'lbs', 'pound', 'pounds']
    VOLUME_UNITS = ['tsp', 'teaspoon', 'teaspoons', 'tbsp', 'tablespoon', 'tablespoons', 'cup', 'cups']
    COUNT_UNITS = ['item', 'items', 'piece', 'pieces', 'slice', 'slices', 'clove', 'cloves', 'bulb', 'bulbs']
    
    # Common packaging for different ingredient types
    PACKAGING_RULES = {
        'oils': {'package': 'bottle', 'typical_size': '500ml', 'buy_whole': True},
        'vinegars': {'package': 'bottle', 'typical_size': '500ml', 'buy_whole': True},
        'sauces': {'package': 'bottle', 'typical_size': '250ml', 'buy_whole': True},
        'pastes': {'package': 'jar', 'typical_size': '200g', 'buy_whole': True},
        'spices': {'package': 'jar', 'typical_size': '50g', 'buy_whole': True},
        'herbs': {'package': 'packet', 'typical_size': '20g', 'buy_whole': True},
        'extracts': {'package': 'bottle', 'typical_size': '50ml', 'buy_whole': True},
        'dairy_liquid': {'package': 'carton', 'typical_size': '1L', 'scalable': True},
        'dairy_solid': {'package': 'pack', 'typical_size': '250g', 'scalable': True},
        'meat': {'package': 'pack', 'typical_size': '500g', 'scalable': True},
        'vegetables': {'package': 'bag', 'typical_size': '1kg', 'scalable': True},
        'fruits': {'package': 'bag', 'typical_size': '1kg', 'scalable': True},
        'grains': {'package': 'bag', 'typical_size': '1kg', 'scalable': True},
        'canned': {'package': 'can', 'typical_size': '400g', 'scalable': True},
        'frozen': {'package': 'bag', 'typical_size': '500g', 'scalable': True}
    }
    
    @classmethod
    def parse_ingredient(cls, ingredient_line: str) -> IngredientMapping:
        """Parse a recipe ingredient line into a purchasable product mapping"""
        original_line = ingredient_line.strip()
        ingredient_line = ingredient_line.strip().lower()
        
        # Extract quantity, unit, and ingredient name using flexible parsing
        parsed = cls._extract_quantity_unit_ingredient(ingredient_line)
        quantity = parsed['quantity']
        unit = parsed['unit']
        ingredient = parsed['ingredient']
        
        # Determine ingredient category and appropriate packaging
        category = cls._determine_category(ingredient)
        packaging_info = cls._determine_packaging(ingredient, category, quantity, unit)
        
        # Calculate final purchase quantity and unit
        purchase_quantity, purchase_unit = cls._calculate_purchase_amount(
            quantity, unit, packaging_info
        )
        
        return IngredientMapping(
            original_ingredient=original_line,
            quantity=quantity,
            unit=unit,
            product_name=packaging_info['product_name'],
            purchasable_unit=purchase_unit,
            conversion_factor=purchase_quantity,
            category=category,
            notes=packaging_info['reasoning']
        )
    
    @classmethod
    def _extract_quantity_unit_ingredient(cls, ingredient_line: str) -> dict:
        """Extract quantity, unit, and ingredient name from ingredient line"""
        import re
        
        # Clean up the line
        ingredient_line = re.sub(r'\s+', ' ', ingredient_line.strip())
        
        # Patterns to match quantity + unit + ingredient
        patterns = [
            # "2 tbsp olive oil" or "1.5 cups flour"
            r'^(\d+(?:\.\d+)?)\s+(tsp|teaspoons?|tbsp|tablespoons?|cup|cups|ml|cl|l|litres?|liters?|fl\s*oz|fluid\s*ounces?|pint|pints|g|grams?|kg|kilograms?|oz|ounces?|lbs?|pounds?)\s+(.+)$',
            
            # "2 large onions" or "3 medium carrots"
            r'^(\d+(?:\.\d+)?)\s+(large|medium|small|whole|thick|thin)\s+(.+)$',
            
            # "12 chicken thighs" or "6 eggs"
            r'^(\d+(?:\.\d+)?)\s+(.+)$',
            
            # "a pinch of salt" or "handful of herbs"
            r'^(?:a|an)\s+(pinch|handful|dash|splash)\s+(?:of\s+)?(.+)$',
            
            # Just ingredient name "olive oil"
            r'^(.+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, ingredient_line, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 3 and groups[0].replace('.','').isdigit():
                    # Has quantity, unit, ingredient
                    return {
                        'quantity': float(groups[0]),
                        'unit': groups[1].lower(),
                        'ingredient': groups[2].strip()
                    }
                elif len(groups) == 2:
                    if groups[0].replace('.','').isdigit():
                        # Has quantity, ingredient (no unit)
                        return {
                            'quantity': float(groups[0]),
                            'unit': 'item',
                            'ingredient': groups[1].strip()
                        }
                    elif groups[0] in ['pinch', 'handful', 'dash', 'splash']:
                        # Special quantities
                        return {
                            'quantity': 1.0,
                            'unit': groups[0],
                            'ingredient': groups[1].strip()
                        }
                else:
                    # Just ingredient name
                    return {
                        'quantity': 1.0,
                        'unit': 'item',
                        'ingredient': groups[0].strip()
                    }
        
        # Fallback
        return {
            'quantity': 1.0,
            'unit': 'item',
            'ingredient': ingredient_line
        }
    
    @classmethod
    def _determine_category(cls, ingredient: str) -> str:
        """Determine ingredient category based on keywords"""
        ingredient = ingredient.lower()
        
        # Keyword-based categorization
        categories = {
            'oils': ['oil', 'olive oil', 'vegetable oil', 'coconut oil', 'sesame oil', 'sunflower oil'],
            'sauces': ['sauce', 'soy sauce', 'tomato sauce', 'worcestershire', 'hot sauce', 'ketchup'],
            'pastes': ['paste', 'tomato paste', 'chili paste', 'gochujang', 'tahini', 'pesto'],
            'spices': ['salt', 'pepper', 'paprika', 'cumin', 'coriander', 'turmeric', 'cinnamon', 'nutmeg'],
            'herbs': ['basil', 'oregano', 'thyme', 'rosemary', 'parsley', 'cilantro', 'mint', 'sage'],
            'dairy_liquid': ['milk', 'cream', 'buttermilk', 'yogurt'],
            'dairy_solid': ['cheese', 'butter', 'cream cheese', 'cottage cheese'],
            'meat': ['chicken', 'beef', 'pork', 'lamb', 'turkey', 'bacon', 'sausage', 'thigh', 'breast'],
            'vegetables': ['onion', 'carrot', 'potato', 'tomato', 'bell pepper', 'garlic', 'ginger'],
            'fruits': ['apple', 'banana', 'lemon', 'lime', 'orange', 'berries'],
            'grains': ['rice', 'flour', 'pasta', 'quinoa', 'oats', 'bread'],
            'canned': ['canned', 'tinned', 'tin of', 'can of'],
            'frozen': ['frozen']
        }
        
        for category, keywords in categories.items():
            if any(keyword in ingredient for keyword in keywords):
                return category
        
        return 'other'
    
    @classmethod
    def _determine_packaging(cls, ingredient: str, category: str, quantity: float, unit: str) -> dict:
        """Determine appropriate packaging for the ingredient"""
        
        # Get packaging rules for this category
        packaging_rule = cls.PACKAGING_RULES.get(category, {
            'package': 'item',
            'typical_size': '1 unit',
            'scalable': True
        })
        
        # Clean up ingredient name for product naming
        product_name = cls._clean_product_name(ingredient)
        
        # Determine if we should buy whole package or scale
        if packaging_rule.get('buy_whole', False):
            # For items like spices, oils, sauces - always buy the whole package
            reasoning = f"Typically sold as complete {packaging_rule['package']}"
            return {
                'product_name': product_name,
                'package_type': packaging_rule['package'],
                'reasoning': reasoning
            }
        else:
            # For scalable items, calculate based on quantity needed
            reasoning = f"Calculated based on recipe quantity of {quantity} {unit}"
            return {
                'product_name': product_name,
                'package_type': packaging_rule['package'],
                'reasoning': reasoning
            }
    
    @classmethod
    def _calculate_purchase_amount(cls, recipe_quantity: float, recipe_unit: str, packaging_info: dict) -> tuple:
        """Calculate how much to actually purchase"""
        
        package_type = packaging_info['package_type']
        
        # For items typically bought as complete packages (regardless of recipe quantity)
        if package_type in ['bottle', 'jar', 'packet']:
            return (1, package_type)
        
        # For scalable items, calculate reasonable purchase amount
        if package_type in ['bag', 'pack', 'kg', 'carton']:
            if recipe_unit in cls.WEIGHT_UNITS:
                # Convert to kg if needed
                if recipe_unit in ['g', 'gram', 'grams']:
                    kg_needed = recipe_quantity / 1000
                    purchase_kg = max(0.5, round(kg_needed * 2, 1))  # Buy a bit extra
                    return (purchase_kg, 'kg')
                else:
                    return (max(1, round(recipe_quantity)), 'pack')
            elif recipe_unit in cls.LIQUID_UNITS:
                # For liquids, round up to reasonable container size
                return (1, 'carton')
            elif recipe_unit in ['item', 'items', 'piece', 'pieces'] or recipe_unit.isdigit():
                # For count items like "12 chicken thighs", calculate pack size
                if 'chicken' in packaging_info['product_name'].lower():
                    # Chicken usually sold in packs, round up to reasonable pack size
                    packs_needed = max(1, round(recipe_quantity / 6))  # Assume 6 pieces per pack
                    return (packs_needed, 'pack')
                else:
                    return (max(1, int(recipe_quantity)), package_type)
            else:
                # Default for other units
                return (max(1, int(recipe_quantity)), package_type)
        
        # Default fallback
        return (max(1, int(recipe_quantity)), package_type)
    
    @classmethod
    def _clean_product_name(cls, ingredient: str) -> str:
        """Clean up ingredient name to make it more suitable for shopping"""
        import re
        
        # Handle complex ingredients with alternatives (like "gochujang or ketchup and sriracha")
        # Take the first main ingredient before "or"
        if ' or ' in ingredient:
            ingredient = ingredient.split(' or ')[0].strip()
        
        # Remove parenthetical explanations
        ingredient = re.sub(r'\([^)]*\)', '', ingredient)
        
        # Remove common recipe-specific words
        ingredient = re.sub(r'\b(fresh|dried|ground|chopped|sliced|diced|minced|crushed|grated)\b', '', ingredient)
        ingredient = re.sub(r'\b(large|medium|small|thick|thin)\b', '', ingredient)
        ingredient = re.sub(r'\b(boneless|skinless|and)\b', '', ingredient)
        
        # Clean up multiple spaces
        ingredient = re.sub(r'\s+', ' ', ingredient).strip()
        
        # Capitalize first letter
        if ingredient:
            ingredient = ingredient[0].upper() + ingredient[1:]
        
        return ingredient or "Unknown ingredient"


class ShoppingListPriceService:
    """Service for integrating price checking with shopping lists"""
    
    @staticmethod
    def convert_recipe_to_shopping_items(recipe_ingredients: str, recipe_id: int) -> List[IngredientMapping]:
        """Convert recipe ingredients to shopping list items with smart mapping"""
        if not recipe_ingredients:
            return []
        
        shopping_items = []
        ingredient_lines = recipe_ingredients.strip().split('\n')
        
        for line in ingredient_lines:
            line = line.strip()
            if line and len(line) > 2:  # Skip empty or very short lines
                mapping = IngredientParser.parse_ingredient(line)
                shopping_items.append(mapping)
        
        return shopping_items
    
    @staticmethod
    def add_prices_to_shopping_list(user_id: int, shopping_list_id: int = None) -> Dict:
        """Add price information to shopping list items"""
        # Get user's shopping list items
        query = ShoppingListItem.query.filter_by(user_id=user_id, is_purchased=False)
        if shopping_list_id:
            query = query.filter_by(shopping_list_id=shopping_list_id)
        
        items = query.all()
        
        results = {
            'items_checked': 0,
            'items_with_prices': 0,
            'total_estimated_cost': 0.0,
            'cheapest_stores': {},
            'price_details': []
        }
        
        for item in items:
            try:
                # Get price estimate using safe service
                estimate = safe_price_service.estimate_price(item.name)
                
                results['items_checked'] += 1
                
                if estimate:
                    results['items_with_prices'] += 1
                    
                    # Update item with estimated price
                    item.estimated_price = estimate.estimated_price
                    
                    # Get store comparisons for this item
                    store_comparisons = safe_price_service.get_store_comparison(item.name)
                    cheapest_store = min(store_comparisons, key=lambda x: x['estimated_price'])
                    
                    # Track cheapest stores
                    store = cheapest_store['store']
                    if store not in results['cheapest_stores']:
                        results['cheapest_stores'][store] = {'count': 0, 'total_savings': 0.0}
                    results['cheapest_stores'][store]['count'] += 1
                    
                    # Calculate total cost
                    results['total_estimated_cost'] += estimate.estimated_price
                    
                    # Store price details
                    results['price_details'].append({
                        'item_id': item.id,
                        'item_name': item.name,
                        'cheapest_price': estimate.estimated_price,
                        'cheapest_store': store,
                        'confidence': estimate.confidence,
                        'is_estimate': True,
                        'all_prices': [
                            {
                                'store': comp['store'],
                                'price': comp['estimated_price'],
                                'name': item.name,
                                'confidence': comp['confidence']
                            } for comp in store_comparisons
                        ]
                    })
                
                db.session.commit()
                
            except Exception as e:
                print(f"Error estimating prices for {item.name}: {e}")
                continue
        
        return results
    
    @staticmethod
    def optimize_shopping_list_by_store(user_id: int, shopping_list_id: int = None) -> Dict:
        """Optimize shopping list to minimize cost and visits using safe price estimates"""
        # Get items with prices
        query = ShoppingListItem.query.filter_by(user_id=user_id, is_purchased=False)
        if shopping_list_id:
            query = query.filter_by(shopping_list_id=shopping_list_id)
        
        items = query.filter(ShoppingListItem.estimated_price.isnot(None)).all()
        
        if not items:
            return {'error': 'No items with price data found'}
        
        # Get store comparisons for all items
        store_totals = {}
        item_store_prices = {}
        
        for item in items:
            # Get store price estimates for this item
            store_comparisons = safe_price_service.get_store_comparison(item.name)
            
            item_store_prices[item.id] = {}
            
            for comparison in store_comparisons:
                store = comparison['store']
                price_val = comparison['estimated_price']
                
                # Track price per store for this item
                item_store_prices[item.id][store] = price_val
                
                # Track store totals
                if store not in store_totals:
                    store_totals[store] = 0.0
                
        # Calculate optimized shopping strategy
        strategies = []
        
        # Strategy 1: Single store (minimize trips)
        for store in store_totals.keys():
            total_cost = 0.0
            available_items = 0
            
            for item in items:
                if item.id in item_store_prices and store in item_store_prices[item.id]:
                    total_cost += item_store_prices[item.id][store]
                    available_items += 1
            
            if available_items > 0:
                strategies.append({
                    'type': 'single_store',
                    'stores': [store],
                    'total_cost': total_cost,
                    'items_available': available_items,
                    'items_missing': len(items) - available_items,
                    'cost_per_item': total_cost / available_items if available_items > 0 else 0
                })
        
        # Strategy 2: Multi-store (minimize cost)
        min_cost_total = 0.0
        min_cost_stores = {}
        items_covered = 0
        
        for item in items:
            if item.id in item_store_prices:
                # Find cheapest store for this item
                cheapest_store = min(item_store_prices[item.id].items(), key=lambda x: x[1])
                min_cost_total += cheapest_store[1]
                items_covered += 1
                
                if cheapest_store[0] not in min_cost_stores:
                    min_cost_stores[cheapest_store[0]] = {'items': 0, 'cost': 0.0}
                min_cost_stores[cheapest_store[0]]['items'] += 1
                min_cost_stores[cheapest_store[0]]['cost'] += cheapest_store[1]
        
        if items_covered > 0:
            strategies.append({
                'type': 'multi_store_cheapest',
                'stores': list(min_cost_stores.keys()),
                'total_cost': min_cost_total,
                'items_available': items_covered,
                'items_missing': len(items) - items_covered,
                'store_breakdown': min_cost_stores,
                'num_trips': len(min_cost_stores)
            })
        
        # Sort strategies by preference (single store with good coverage first)
        strategies.sort(key=lambda x: (x['items_missing'], x['total_cost']))
        
        return {
            'total_items': len(items),
            'strategies': strategies[:3],  # Top 3 strategies
            'item_details': item_store_prices
        }


def update_shopping_list_with_smart_mapping(recipe_id: int, user_id: int) -> Dict:
    """Update shopping list with smart ingredient mapping and price checking"""
    from recipe_app.models.models import Recipe
    
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return {'error': 'Recipe not found'}
    
    # Convert recipe ingredients to smart shopping items
    mappings = ShoppingListPriceService.convert_recipe_to_shopping_items(
        recipe.ingredients, recipe_id
    )
    
    items_added = 0
    items_updated = 0
    
    for mapping in mappings:
        # Check if item already exists
        existing_item = ShoppingListItem.query.filter_by(
            name=mapping.product_name,
            is_purchased=False
        ).filter(
            ShoppingListItem.shopping_list.has(user_id=user_id)
        ).first()
        
        if existing_item:
            # Update existing item
            existing_item.notes = f"{existing_item.notes or ''}\nFrom recipe: {recipe.title}"
            existing_item.source_recipe_id = recipe_id
            items_updated += 1
        else:
            # Create new shopping list item
            # Get or create default shopping list
            from recipe_app.models.advanced_models import ShoppingList
            shopping_list = ShoppingList.query.filter_by(
                user_id=user_id,
                is_active=True
            ).first()
            
            if not shopping_list:
                shopping_list = ShoppingList(
                    user_id=user_id,
                    name="My Shopping List",
                    is_active=True
                )
                db.session.add(shopping_list)
                db.session.flush()
            
            new_item = ShoppingListItem(
                shopping_list_id=shopping_list.id,
                name=mapping.product_name,
                quantity=mapping.conversion_factor,
                unit=mapping.purchasable_unit,
                category=mapping.category,
                source='recipe',
                source_recipe_id=recipe_id,
                notes=f"From recipe: {recipe.title}. Original: {mapping.original_ingredient}"
            )
            db.session.add(new_item)
            items_added += 1
    
    db.session.commit()
    
    # Now add prices
    price_results = ShoppingListPriceService.add_prices_to_shopping_list(user_id)
    
    return {
        'success': True,
        'items_added': items_added,
        'items_updated': items_updated,
        'price_results': price_results,
        'mappings_created': len(mappings)
    }
