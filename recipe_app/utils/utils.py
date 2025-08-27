"""
Utility functions for recipe conversions and adjustments
"""
import re
from fractions import Fraction
from typing import Dict, List, Tuple, Optional

# US to Metric conversion factors
VOLUME_CONVERSIONS = {
    # Liquid measurements
    'cup': 236.588,  # ml
    'cups': 236.588,
    'pint': 473.176,  # ml
    'pints': 473.176,
    'quart': 946.353,  # ml
    'quarts': 946.353,
    'gallon': 3785.41,  # ml
    'gallons': 3785.41,
    'fluid ounce': 29.5735,  # ml
    'fluid ounces': 29.5735,
    'fl oz': 29.5735,
    'fl. oz': 29.5735,
    'tablespoon': 14.7868,  # ml
    'tablespoons': 14.7868,
    'tbsp': 14.7868,
    'tbs': 14.7868,
    'teaspoon': 4.92892,  # ml
    'teaspoons': 4.92892,
    'tsp': 4.92892,
    't': 4.92892,
}

WEIGHT_CONVERSIONS = {
    # Weight measurements
    'pound': 453.592,  # grams
    'pounds': 453.592,
    'lb': 453.592,
    'lbs': 453.592,
    'ounce': 28.3495,  # grams
    'ounces': 28.3495,
    'oz': 28.3495,
}

TEMPERATURE_CONVERSIONS = {
    # Temperature conversions (Fahrenheit to Celsius)
    'fahrenheit': lambda f: (f - 32) * 5/9,
    'f': lambda f: (f - 32) * 5/9,
}

def parse_ingredient_amount(ingredient_text: str) -> Tuple[Optional[float], str, str]:
    """
    Parse ingredient text to extract amount, unit, and ingredient name
    Returns: (amount, unit, ingredient_name)
    """
    # Remove bullet points, dashes, and other list markers at the beginning
    cleaned_text = re.sub(r'^[•\-\*\+]\s*', '', ingredient_text.strip())
    
    # Common patterns for amounts (including fractions)
    amount_patterns = [
        r'(\d+(?:\.\d+)?)\s+(\d+/\d+)\s*',  # e.g., "1 1/2"
        r'(\d+/\d+)\s*',  # e.g., "1/2", "3/4"
        r'(\d+(?:\.\d+)?)\s*',  # e.g., "2", "1.5"
    ]
    
    # Try to match amount at the beginning
    for pattern in amount_patterns:
        match = re.match(pattern, cleaned_text)
        if match:
            groups = match.groups()
            amount = 0
            
            # Handle whole number + fraction (e.g., "1 1/2")
            if len(groups) >= 2 and groups[0] and groups[1]:
                amount += float(groups[0])
                fraction = Fraction(groups[1])
                amount += float(fraction)
            # Handle just fraction (e.g., "1/2")
            elif groups[0] and '/' in groups[0]:
                fraction = Fraction(groups[0])
                amount = float(fraction)
            # Handle decimal/whole number
            elif groups[0]:
                amount = float(groups[0])
            
            remaining_text = cleaned_text[match.end():].strip()
            
            # Extract unit (next word after amount)
            unit_match = re.match(r'(\w+(?:\s+\w+)*?)\s+(.+)', remaining_text)
            if unit_match:
                unit = unit_match.group(1).lower()
                ingredient_name = unit_match.group(2)
            else:
                unit = ''
                ingredient_name = remaining_text
            
            return amount, unit, ingredient_name
    
    # No amount found
    return None, '', ingredient_text

def convert_to_metric(amount: float, unit: str) -> Tuple[float, str]:
    """
    Convert US measurements to metric
    Returns: (converted_amount, metric_unit)
    """
    unit_lower = unit.lower().strip()
    
    # Volume conversions
    if unit_lower in VOLUME_CONVERSIONS:
        ml_amount = amount * VOLUME_CONVERSIONS[unit_lower]
        
        # Convert to appropriate metric unit
        if ml_amount >= 1000:
            return round(ml_amount / 1000, 2), 'L'
        else:
            return round(ml_amount, 1), 'ml'
    
    # Weight conversions
    elif unit_lower in WEIGHT_CONVERSIONS:
        gram_amount = amount * WEIGHT_CONVERSIONS[unit_lower]
        
        # Convert to appropriate metric unit
        if gram_amount >= 1000:
            return round(gram_amount / 1000, 2), 'kg'
        else:
            return round(gram_amount, 0), 'g'
    
    # Temperature conversion
    elif unit_lower in ['fahrenheit', 'f', '°f', 'degrees f']:
        celsius = TEMPERATURE_CONVERSIONS['fahrenheit'](amount)
        return round(celsius, 0), '°C'
    
    # No conversion needed or unknown unit
    return amount, unit

def adjust_serving_size(ingredient_text: str, original_servings: int, target_servings: int) -> str:
    """
    Adjust ingredient amounts based on serving size
    """
    print(f"=== ADJUSTING LINE: '{ingredient_text}' ===")
    
    if original_servings <= 0 or target_servings <= 0:
        print("Invalid serving sizes, returning original")
        return ingredient_text
    
    multiplier = target_servings / original_servings
    print(f"Multiplier: {multiplier}")
    
    # Check if the line starts with a bullet point or list marker
    bullet_match = re.match(r'^([•\-\*\+]\s*)', ingredient_text.strip())
    bullet_prefix = bullet_match.group(1) if bullet_match else ''
    
    amount, unit, ingredient_name = parse_ingredient_amount(ingredient_text)
    print(f"Parsed - Amount: {amount}, Unit: '{unit}', Name: '{ingredient_name}'")
    
    if amount is None:
        print("No amount found, returning original")
        return ingredient_text
    
    new_amount = amount * multiplier
    print(f"New amount: {new_amount}")
    
    # Format the new amount nicely
    if new_amount == int(new_amount):
        formatted_amount = str(int(new_amount))
    elif new_amount < 1:
        # Try to convert to fraction for small amounts
        fraction = Fraction(new_amount).limit_denominator(16)
        if abs(float(fraction) - new_amount) < 0.01:
            formatted_amount = str(fraction)
        else:
            formatted_amount = f"{new_amount:.2f}".rstrip('0').rstrip('.')
    else:
        formatted_amount = f"{new_amount:.2f}".rstrip('0').rstrip('.')
    
    if unit:
        result = f"{bullet_prefix}{formatted_amount} {unit} {ingredient_name}"
    else:
        result = f"{bullet_prefix}{formatted_amount} {ingredient_name}"
    
    print(f"Final result: '{result}'")
    return result

def convert_recipe_to_metric(recipe_text: str) -> str:
    """
    Convert all US measurements in a recipe text to metric
    """
    lines = recipe_text.split('\n')
    converted_lines = []
    
    for line in lines:
        amount, unit, ingredient_name = parse_ingredient_amount(line)
        
        if amount is not None and unit:
            metric_amount, metric_unit = convert_to_metric(amount, unit)
            
            # Format the converted amount
            if metric_amount == int(metric_amount):
                formatted_amount = str(int(metric_amount))
            else:
                formatted_amount = f"{metric_amount:.2f}".rstrip('0').rstrip('.')
            
            converted_line = f"{formatted_amount} {metric_unit} {ingredient_name}"
            converted_lines.append(converted_line)
        else:
            converted_lines.append(line)
    
    return '\n'.join(converted_lines)

def adjust_recipe_servings(recipe_text: str, original_servings: int, target_servings: int) -> str:
    """
    Adjust all ingredient amounts in a recipe for different serving size
    """
    lines = recipe_text.split('\n')
    adjusted_lines = []
    
    for line in lines:
        adjusted_line = adjust_serving_size(line.strip(), original_servings, target_servings)
        adjusted_lines.append(adjusted_line)
    
    return '\n'.join(adjusted_lines)

def get_conversion_suggestions(ingredient_text: str) -> Dict[str, str]:
    """
    Get both metric conversion and serving adjustment suggestions for an ingredient
    """
    amount, unit, ingredient_name = parse_ingredient_amount(ingredient_text)
    suggestions = {}
    
    if amount is not None and unit:
        # Metric conversion
        metric_amount, metric_unit = convert_to_metric(amount, unit)
        if metric_unit != unit:
            if metric_amount == int(metric_amount):
                formatted_amount = str(int(metric_amount))
            else:
                formatted_amount = f"{metric_amount:.2f}".rstrip('0').rstrip('.')
            suggestions['metric'] = f"{formatted_amount} {metric_unit} {ingredient_name}"
        
        # Serving adjustments (common multipliers)
        for servings in [1, 2, 4, 6, 8]:
            adjusted = adjust_serving_size(ingredient_text, 4, servings)  # Assume original recipe serves 4
            suggestions[f'serves_{servings}'] = adjusted
    
    return suggestions


# Database utility functions for handling connection issues and retries
import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError, DisconnectionError

logger = logging.getLogger(__name__)

def retry_db_operation(max_retries=3, delay=1):
    """
    Decorator for retrying database operations that might fail due to connection issues.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        delay (float): Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a connection-related error
                    if any(phrase in error_msg for phrase in [
                        'server closed the connection',
                        'connection was killed',
                        'lost connection',
                        'connection timeout',
                        'connection refused'
                    ]):
                        if attempt < max_retries:
                            logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                            time.sleep(delay * (attempt + 1))  # Exponential backoff
                            
                            # Try to refresh the database session
                            try:
                                from recipe_app.db import db
                                db.session.rollback()
                                db.session.close()
                            except Exception as session_error:
                                logger.warning(f"Error closing session: {session_error}")
                            
                            continue
                    
                    # If it's not a connection error, don't retry
                    raise e
                except Exception as e:
                    # For non-database errors, don't retry
                    raise e
            
            # If we've exhausted all retries, raise the last exception
            logger.error(f"Database operation failed after {max_retries + 1} attempts: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator

def safe_db_query(query_func, default_value=None):
    """
    Safely execute a database query with error handling.
    
    Args:
        query_func: Function that performs the database query
        default_value: Value to return if query fails
    
    Returns:
        Query result or default_value if query fails
    """
    try:
        return retry_db_operation()(query_func)()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return default_value

def check_db_connection():
    """
    Check if the database connection is alive.
    
    Returns:
        bool: True if connection is alive, False otherwise
    """
    try:
        from recipe_app.db import db
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def refresh_db_session():
    """
    Refresh the database session to handle stale connections.
    """
    try:
        from recipe_app.db import db
        db.session.rollback()
        db.session.close()
        db.session.remove()
    except Exception as e:
        logger.warning(f"Error refreshing database session: {e}")
