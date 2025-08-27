import requests
import re
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me
from urllib.parse import urlparse, urljoin
import json
from typing import Dict, List, Optional

class RecipeImporter:
    """Service class to import recipes from various sources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def import_from_url(self, url: str) -> Dict:
        """Import a recipe from a single URL"""
        try:
            # First try using recipe-scrapers (supports many popular sites)
            soup = None
            try:
                scraper = scrape_me(url)
                instructions = scraper.instructions()
                print(f"DEBUG: Recipe-scrapers found {len(instructions)} instructions")
                
                # Get the soup for additional extraction
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check if instructions are actually individual characters (common bug)
                if len(instructions) > 100 and all(len(instr.strip()) <= 2 for instr in instructions[:10]):
                    print("DEBUG: Instructions appear to be individual characters, joining them")
                    # Join all characters back into a single string and try to split properly
                    full_text = ''.join(instructions)
                    print(f"DEBUG: Full text length: {len(full_text)}")
                    print(f"DEBUG: First 200 chars: {full_text[:200]}...")
                    
                    # Try multiple splitting strategies for Food.com and similar sites
                    instructions = []
                    
                    # Strategy 1: Look for numbered steps (1., 2., etc.)
                    numbered_pattern = r'(\d+)\.\s*([^.]*(?:\.[^.]*)*?)(?=\s*\d+\.\s*|$)'
                    numbered_matches = re.findall(numbered_pattern, full_text, re.DOTALL)
                    if numbered_matches and len(numbered_matches) > 2:
                        print(f"DEBUG: Found {len(numbered_matches)} numbered steps")
                        instructions = [match[1].strip() for match in numbered_matches if match[1].strip()]
                    
                    # Strategy 2: Split by periods followed by capital letters (if no numbered steps)
                    if not instructions:
                        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', full_text)
                        instructions = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
                        print(f"DEBUG: Split by sentences, found {len(instructions)} instructions")
                    
                    # Strategy 3: If still nothing good, treat as one instruction
                    if not instructions or len(instructions) == 1:
                        instructions = [full_text.strip()] if full_text.strip() else []
                        print("DEBUG: Using full text as single instruction")
                
                for i, instr in enumerate(instructions[:3]):  # Print first 3 for debugging
                    print(f"DEBUG: Instruction {i+1}: {instr[:100]}...")
                
                # Extract enhanced timing and serving information
                prep_time = self._extract_time(getattr(scraper, 'prep_time', lambda: None)()) or self._extract_prep_time(soup)
                cook_time = self._extract_time(getattr(scraper, 'cook_time', lambda: None)()) or self._extract_cook_time(soup)
                servings = self._extract_servings(soup)
                if not servings:
                    servings = getattr(scraper, 'yields', lambda: None)()
                    if isinstance(servings, str):
                        servings = self._extract_number(servings)
                
                return {
                    'success': True,
                    'recipe': {
                        'title': scraper.title(),
                        'description': getattr(scraper, 'description', lambda: '')() or '',
                        'ingredients': self._format_ingredients(scraper.ingredients()),
                        'method': self._format_instructions(instructions),
                        'prep_time': prep_time,
                        'cook_time': cook_time,
                        'servings': servings,
                        'image_url': getattr(scraper, 'image', lambda: '')() or '',
                        'source_url': url,
                        'difficulty': 'Medium'  # Default
                    },
                    'source': 'recipe-scrapers'
                }
            except Exception as e:
                print(f"Recipe-scrapers failed: {e}")
                # Fall back to custom parsing
                return self._parse_with_custom_logic(url)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to import recipe: {str(e)}"
            }
    
    def _parse_with_custom_logic(self, url: str) -> Dict:
        """Custom recipe parsing logic for sites not supported by recipe-scrapers"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find JSON-LD structured data first
            json_ld = self._extract_json_ld(soup)
            if json_ld:
                return {
                    'success': True,
                    'recipe': json_ld,
                    'source': 'json-ld'
                }
            
            # Fall back to heuristic parsing
            recipe = self._extract_with_heuristics(soup, url)
            return {
                'success': True,
                'recipe': recipe,
                'source': 'heuristic'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Custom parsing failed: {str(e)}"
            }
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract recipe data from JSON-LD structured data"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    # Look for Recipe type
                    if data.get('@type') == 'Recipe' or 'Recipe' in str(data.get('@type', '')):
                        return self._parse_json_ld_recipe(data)
                    
                    # Sometimes it's nested in @graph
                    if '@graph' in data:
                        for item in data['@graph']:
                            if item.get('@type') == 'Recipe':
                                return self._parse_json_ld_recipe(item)
                                
                except json.JSONDecodeError:
                    continue
                    
        except Exception:
            pass
        return None
    
    def _parse_json_ld_recipe(self, data: Dict) -> Dict:
        """Parse a JSON-LD recipe object"""
        recipe = {
            'title': data.get('name', ''),
            'description': data.get('description', ''),
            'ingredients': [],
            'method': '',
            'prep_time': None,
            'cook_time': None,
            'servings': None,
            'image_url': '',
            'difficulty': 'Medium'
        }
        
        # Extract ingredients
        ingredients = data.get('recipeIngredient', [])
        recipe['ingredients'] = self._format_ingredients(ingredients)
        
        # Extract instructions
        instructions = data.get('recipeInstructions', [])
        recipe['method'] = self._format_json_ld_instructions(instructions)
        
        # Extract times with multiple fallback options
        prep_time = data.get('prepTime')
        cook_time = data.get('cookTime') or data.get('cookingTime')
        total_time = data.get('totalTime')
        
        # Parse preparation time
        if prep_time:
            recipe['prep_time'] = self._parse_iso_duration(prep_time) or self._extract_time(prep_time)
        
        # Parse cooking time
        if cook_time:
            recipe['cook_time'] = self._parse_iso_duration(cook_time) or self._extract_time(cook_time)
        elif total_time and not prep_time:
            # If we only have total time and no prep time, use it as cook time
            recipe['cook_time'] = self._parse_iso_duration(total_time) or self._extract_time(total_time)
        elif total_time and prep_time:
            # If we have both, calculate cook time as total - prep
            total_minutes = self._parse_iso_duration(total_time) or self._extract_time(total_time)
            prep_minutes = recipe['prep_time']
            if total_minutes and prep_minutes and total_minutes > prep_minutes:
                recipe['cook_time'] = total_minutes - prep_minutes
        
        # Extract servings with multiple key options
        yield_keys = ['recipeYield', 'yield', 'serves', 'servings', 'portions']
        for key in yield_keys:
            yield_data = data.get(key)
            if yield_data:
                if isinstance(yield_data, (int, float)):
                    recipe['servings'] = int(yield_data)
                    break
                elif isinstance(yield_data, str):
                    servings = self._extract_number(yield_data)
                    if servings:
                        recipe['servings'] = servings
                        break
                elif isinstance(yield_data, list) and yield_data:
                    # Sometimes it's an array, take the first value
                    first_item = yield_data[0]
                    if isinstance(first_item, (int, float)):
                        recipe['servings'] = int(first_item)
                        break
                    elif isinstance(first_item, str):
                        servings = self._extract_number(first_item)
                        if servings:
                            recipe['servings'] = servings
                            break
            if isinstance(yield_data, list):
                yield_data = yield_data[0]
            recipe['servings'] = self._extract_number(str(yield_data))
        
        # Extract image
        image = data.get('image')
        if image:
            if isinstance(image, list):
                image = image[0]
            if isinstance(image, dict):
                image = image.get('url', '')
            recipe['image_url'] = str(image)
        
        # Extract nutrition information
        nutrition = self._extract_nutrition_from_json_ld(data)
        
        # Also try to extract nutrition from description if available
        if recipe.get('description'):
            desc_nutrition = self._extract_nutrition_from_description(recipe['description'])
            print(f"DEBUG: Description nutrition extracted: {desc_nutrition}")
            # Merge description nutrition with JSON-LD nutrition (JSON-LD takes priority)
            for key, value in desc_nutrition.items():
                if key not in nutrition:
                    nutrition[key] = value
        
        print(f"DEBUG: Final nutrition data: {nutrition}")
        recipe.update(nutrition)
        
        return recipe
    
    def _extract_with_heuristics(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract recipe using heuristic parsing"""
        recipe = {
            'title': '',
            'description': '',
            'ingredients': '',
            'method': '',
            'prep_time': None,
            'cook_time': None,
            'servings': None,
            'image_url': '',
            'source_url': url,
            'difficulty': 'Medium'
        }
        
        # Extract title
        title_selectors = [
            'h1.recipe-title', 'h1.entry-title', 'h1', 
            '.recipe-header h1', '.recipe-title', 'title'
        ]
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                recipe['title'] = title_elem.get_text().strip()
                break
        
        # Extract ingredients
        ingredient_selectors = [
            '.recipe-ingredients li', '.ingredients li', '.recipe-ingredient',
            '.ingredient', '[class*="ingredient"] li', '.recipe-ingredients p'
        ]
        ingredients = []
        for selector in ingredient_selectors:
            elements = soup.select(selector)
            if elements:
                ingredients = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                break
        
        recipe['ingredients'] = '\n'.join(ingredients) if ingredients else ''
        
        # Extract method/instructions
        method_selectors = [
            '.recipe-instructions li', '.instructions li', '.recipe-method li',
            '.method li', '.recipe-directions li', '.directions li',
            '.recipe-instructions p', '.instructions p', '.recipe-instructions ol li',
            '.instructions ol li', '.recipe-method ol li'
        ]
        instructions = []
        for selector in method_selectors:
            elements = soup.select(selector)
            if elements:
                # Get all non-empty text, reduce length filter to be less restrictive
                instructions = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                # Filter out very short instructions (like single words)
                instructions = [instr for instr in instructions if len(instr) > 3]
                if instructions:  # Only break if we found meaningful instructions
                    break
        
        # Enhanced time and serving extraction
        recipe['prep_time'] = self._extract_prep_time(soup)
        recipe['cook_time'] = self._extract_cook_time(soup)
        recipe['servings'] = self._extract_servings(soup)
        
        # Extract recipe image
        recipe['image_url'] = self._extract_recipe_image(soup)
        
        # Extract method/instructions if not found
        if not instructions:
            instruction_block_selectors = [
                '.recipe-instructions', '.instructions', '.recipe-method', 
                '.method', '.recipe-directions', '.directions'
            ]
            for selector in instruction_block_selectors:
                block = soup.select_one(selector)
                if block:
                    # Try to split by sentences or periods
                    text = block.get_text().strip()
                    if text and len(text) > 20:  # Make sure we have substantial content
                        # Split by periods followed by space and capital letter, or numbered steps
                        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=\d\.)\s+', text)
                        instructions = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
                        if instructions:
                            break
        
        # If still no instructions, try broader selectors
        if not instructions:
            broad_selectors = [
                'ol li', 'ul li', '.steps li', '.directions p', '.instructions div'
            ]
            for selector in broad_selectors:
                elements = soup.select(selector)
                if elements:
                    potential_instructions = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                    # Check if these look like recipe instructions (contain cooking words)
                    cooking_words = ['heat', 'cook', 'bake', 'mix', 'add', 'stir', 'place', 'remove', 'serve', 'season', 'preheat']
                    cooking_instructions = []
                    for instr in potential_instructions:
                        if any(word in instr.lower() for word in cooking_words) and len(instr) > 10:
                            cooking_instructions.append(instr)
                    if cooking_instructions:
                        instructions = cooking_instructions
                        break
        
        # Format instructions with proper numbering and spacing
        if instructions:
            formatted_instructions = []
            for i, instr in enumerate(instructions, 1):
                # Clean up the instruction text
                clean_instr = ' '.join(instr.strip().split())
                if clean_instr:
                    # Remove existing numbering if present
                    clean_instr = re.sub(r'^\d+\.\s*', '', clean_instr)
                    formatted_instructions.append(f"{i}. {clean_instr}")
            recipe['method'] = '\n\n'.join(formatted_instructions)
        else:
            # Last resort - try to get any text that might be instructions
            all_text = soup.get_text()
            if 'cook' in all_text.lower() or 'bake' in all_text.lower():
                recipe['method'] = "Method not automatically parsed. Please edit to add cooking instructions."
            else:
                recipe['method'] = ''
        
        # Extract nutrition information from the page text
        nutrition = self._extract_nutrition_from_text(soup)
        
        # Also try to extract nutrition from description if available
        if recipe.get('description'):
            desc_nutrition = self._extract_nutrition_from_description(recipe['description'])
            print(f"DEBUG: Description nutrition extracted: {desc_nutrition}")
            # Merge description nutrition with page nutrition (page nutrition takes priority)
            for key, value in desc_nutrition.items():
                if key not in nutrition:
                    nutrition[key] = value
        
        print(f"DEBUG: Final nutrition data: {nutrition}")
        recipe.update(nutrition)
        
        return recipe
    
    def _format_ingredients(self, ingredients: List[str]) -> str:
        """Format ingredients list into a string"""
        if not ingredients:
            return ''
        return '\n'.join(f"• {ingredient.strip()}" for ingredient in ingredients if ingredient.strip())
    
    def _format_instructions(self, instructions: List[str]) -> str:
        """Format instructions list into a string"""
        if not instructions:
            return ''
        
        # Check if we got individual characters instead of proper instructions
        if len(instructions) > 100 and all(len(instr.strip()) <= 2 for instr in instructions[:20]):
            print("DEBUG: _format_instructions detected character-level splitting, fixing...")
            # Join all characters and try to split properly
            full_text = ''.join(instructions).strip()
            if full_text:
                # Try to find numbered steps first
                numbered_pattern = r'(\d+)\.\s*([^.]*(?:\.[^.]*)*?)(?=\s*\d+\.\s*|$)'
                numbered_matches = re.findall(numbered_pattern, full_text, re.DOTALL)
                if numbered_matches and len(numbered_matches) > 2:
                    instructions = [match[1].strip() for match in numbered_matches if match[1].strip()]
                # Try to split by common instruction separators
                elif '. ' in full_text:
                    instructions = [s.strip() for s in full_text.split('. ') if s.strip() and len(s.strip()) > 15]
                elif '\n' in full_text:
                    instructions = [s.strip() for s in full_text.split('\n') if s.strip() and len(s.strip()) > 15]
                else:
                    # Last resort - treat as one long instruction
                    instructions = [full_text]
        
        # Clean and filter instructions
        cleaned_instructions = []
        for instruction in instructions:
            if instruction and instruction.strip():
                # Remove extra whitespace and normalize
                clean_instruction = ' '.join(instruction.strip().split())
                # Be less restrictive with length - allow shorter instructions
                if len(clean_instruction) > 5:  # Increased from 3 to 5 for better quality
                    # Remove existing numbering if present at the start
                    clean_instruction = re.sub(r'^\d+\.\s*', '', clean_instruction)
                    # Ensure instruction ends with a period
                    if not clean_instruction.endswith('.'):
                        clean_instruction += '.'
                    cleaned_instructions.append(clean_instruction)
        
        if not cleaned_instructions:
            return ''
        
        # Format with step numbers and double line breaks for better display
        formatted = []
        for i, instruction in enumerate(cleaned_instructions, 1):
            formatted.append(f"{i}. {instruction}")
        
        return '\n\n'.join(formatted)
    
    def _format_json_ld_instructions(self, instructions: List) -> str:
        """Format JSON-LD instructions into a string"""
        if not instructions:
            return ''
            
        formatted = []
        for i, instruction in enumerate(instructions, 1):
            if isinstance(instruction, dict):
                text = instruction.get('text', '')
            else:
                text = str(instruction)
            
            # Clean and normalize text
            clean_text = ' '.join(text.strip().split()) if text else ''
            if clean_text and len(clean_text) > 5:
                formatted.append(f"{i}. {clean_text}")
        
        return '\n\n'.join(formatted)
    
    def _extract_time(self, time_value) -> Optional[int]:
        """Extract time in minutes from various formats"""
        if not time_value:
            return None
        
        time_str = str(time_value).lower().strip()
        
        # Handle ISO 8601 duration format first
        if time_str.startswith('pt'):
            return self._parse_iso_duration(time_str.upper())
        
        # Look for number followed by time unit
        patterns = [
            (r'(\d+)\s*h(?:ours?)?(?:\s*(\d+)\s*m(?:in|inutes?)?)?', lambda h, m: int(h) * 60 + (int(m) if m else 0)),  # "2h 30min" or "2h"
            (r'(\d+)\s*m(?:in|inutes?)?', lambda m: int(m)),  # minutes only
            (r'(\d+)\s*hours?', lambda h: int(h) * 60),  # hours only
            (r'(\d+)\s*minutes?', lambda m: int(m)),  # written out minutes
            (r'(\d+)[:.](\d+)', lambda h, m: int(h) * 60 + int(m)),  # "2:30" or "2.30" format
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, time_str)
            if match:
                try:
                    if len(match.groups()) == 2:
                        return converter(match.group(1), match.group(2))
                    else:
                        return converter(match.group(1))
                except (ValueError, TypeError):
                    continue
        
        # Last resort: extract any number and assume it's minutes
        number_match = re.search(r'(\d+)', time_str)
        if number_match:
            minutes = int(number_match.group(1))
            # If the number is very large, it might be in seconds
            if minutes > 300:  # More than 5 hours, probably seconds
                return minutes // 60
            return minutes
        
        return None
    
    def _extract_prep_time(self, soup: BeautifulSoup, data: dict = None) -> Optional[int]:
        """Extract preparation time from various sources"""
        if data and 'prepTime' in data:
            return self._extract_time(data['prepTime'])
        
        # Look for common prep time selectors and text patterns
        selectors = [
            '[class*="prep"], [class*="preparation"]',
            '[data-recipe-prep], [data-prep-time]',
            '.recipe-prep-time, .prep-time',
            '.time-prep, .preparation-time'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                time_value = self._extract_time(text)
                if time_value:
                    return time_value
        
        # Text-based search for prep time
        text_patterns = [
            r'prep(?:aration)?\s*time[:\s]*([^,\n]+)',
            r'preparation[:\s]*([^,\n]+)',
            r'prep[:\s]*([^,\n]+)',
        ]
        
        page_text = soup.get_text()
        for pattern in text_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                time_value = self._extract_time(match.group(1))
                if time_value:
                    return time_value
        
        return None
    
    def _extract_cook_time(self, soup: BeautifulSoup, data: dict = None) -> Optional[int]:
        """Extract cooking time from various sources"""
        if data and 'cookTime' in data:
            return self._extract_time(data['cookTime'])
        
        # Look for common cook time selectors
        selectors = [
            '[class*="cook"], [class*="cooking"]',
            '[data-recipe-cook], [data-cook-time]',
            '.recipe-cook-time, .cook-time',
            '.time-cook, .cooking-time'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                time_value = self._extract_time(text)
                if time_value:
                    return time_value
        
        # Text-based search for cook time
        text_patterns = [
            r'cook(?:ing)?\s*time[:\s]*([^,\n]+)',
            r'cooking[:\s]*([^,\n]+)',
            r'cook[:\s]*([^,\n]+)',
            r'bake\s*time[:\s]*([^,\n]+)',
            r'baking[:\s]*([^,\n]+)',
        ]
        
        page_text = soup.get_text()
        for pattern in text_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                time_value = self._extract_time(match.group(1))
                if time_value:
                    return time_value
        
        return None
    
    def _extract_servings(self, soup: BeautifulSoup, data: dict = None) -> Optional[int]:
        """Extract serving information from various sources"""
        if data:
            # Check multiple possible keys for servings
            serving_keys = ['recipeYield', 'yield', 'serves', 'servings', 'portions']
            for key in serving_keys:
                if key in data:
                    value = data[key]
                    if isinstance(value, (int, float)):
                        return int(value)
                    elif isinstance(value, str):
                        number = self._extract_number(value)
                        if number:
                            return number
        
        # Look for common serving selectors
        selectors = [
            '[class*="serv"], [class*="yield"], [class*="portion"]',
            '[data-recipe-yield], [data-servings], [data-serves]',
            '.recipe-yield, .recipe-servings, .servings',
            '.serves, .portions, .yield'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                number = self._extract_number(text)
                if number and 1 <= number <= 50:  # Reasonable serving range
                    return number
        
        # Text-based search for servings
        text_patterns = [
            r'serves?\s*:?\s*(\d+)',
            r'servings?\s*:?\s*(\d+)', 
            r'portions?\s*:?\s*(\d+)',
            r'yield\s*:?\s*(\d+)',
            r'makes?\s*:?\s*(\d+)',
            r'recipe\s*yields?\s*:?\s*(\d+)',
        ]
        
        page_text = soup.get_text()
        for pattern in text_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                number = int(match.group(1))
                if 1 <= number <= 50:  # Reasonable serving range
                    return number
        
        return None
    
    def _parse_iso_duration(self, duration: str) -> Optional[int]:
        """Parse ISO 8601 duration (e.g., PT30M) to minutes"""
        if not duration:
            return None
        
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration)
        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            return hours * 60 + minutes
        
        return None
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract the first number from a string"""
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None
    
    def _extract_recipe_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the best recipe image from the page"""
        # Strategy 1: Look for recipe-specific image selectors
        recipe_image_selectors = [
            '.recipe-image img', '.recipe-photo img', '.recipe-header img',
            '[class*="recipe"] img', '.entry-content img:first-of-type',
            '.post-content img:first-of-type', '.recipe img:first-of-type'
        ]
        
        for selector in recipe_image_selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and self._is_valid_image_url(src):
                    return self._resolve_image_url(src, soup)
        
        # Strategy 2: Look for Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = og_image['content']
            if self._is_valid_image_url(url):
                return url
        
        # Strategy 3: Look for the largest image on the page
        all_images = soup.find_all('img')
        best_image = None
        best_score = 0
        
        for img in all_images:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src or not self._is_valid_image_url(src):
                continue
            
            score = 0
            
            # Prefer images with recipe-related attributes
            img_classes = ' '.join(img.get('class', [])).lower()
            img_alt = (img.get('alt') or '').lower()
            
            if any(word in img_classes for word in ['recipe', 'food', 'dish', 'cooking']):
                score += 50
            if any(word in img_alt for word in ['recipe', 'food', 'dish', 'cooking']):
                score += 30
            
            # Prefer larger images (if dimensions are available)
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    w, h = int(width), int(height)
                    if w >= 300 and h >= 200:  # Reasonable recipe image size
                        score += w * h // 1000  # Bigger is better
                except ValueError:
                    pass
            
            # Penalize obviously non-recipe images
            if any(word in img_classes for word in ['ad', 'banner', 'logo', 'social', 'avatar']):
                score -= 100
            if any(word in img_alt for word in ['ad', 'advertisement', 'logo', 'social', 'avatar']):
                score -= 50
            
            # Penalize very small images
            if width and height:
                try:
                    w, h = int(width), int(height)
                    if w < 150 or h < 100:
                        score -= 50
                except ValueError:
                    pass
            
            if score > best_score:
                best_score = score
                best_image = self._resolve_image_url(src, soup)
        
        return best_image
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL looks like a valid image"""
        if not url:
            return False
        
        # Skip data URLs, tracking pixels, and very small images
        if url.startswith('data:') or '1x1' in url or 'pixel' in url.lower():
            return False
        
        # Check for image file extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        url_lower = url.lower()
        
        # Direct extension check
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Check for image in URL path or query params
        if any(ext in url_lower for ext in image_extensions):
            return True
        
        # Check for common image hosting patterns
        image_hosts = ['cloudinary', 'imgix', 'unsplash', 'images', 'photos', 'media']
        if any(host in url_lower for host in image_hosts):
            return True
        
        return False
    
    def _resolve_image_url(self, src: str, soup: BeautifulSoup) -> str:
        """Resolve relative URLs to absolute URLs"""
        if src.startswith(('http://', 'https://')):
            return src
        
        # Get base URL from the page
        base_url = ''
        base_tag = soup.find('base')
        if base_tag and base_tag.get('href'):
            base_url = base_tag['href']
        else:
            # Extract from canonical URL or current page
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                base_url = canonical['href']
        
        if base_url:
            from urllib.parse import urljoin
            return urljoin(base_url, src)
        
        return src

    def import_from_kaggle_dataset(self, dataset_path: str, file_path: str = "", max_recipes: int = 100) -> Dict:
        """Import recipes from a Kaggle dataset"""
        try:
            # Install kagglehub if not already installed
            try:
                import kagglehub
                from kagglehub import KaggleDatasetAdapter
            except ImportError:
                return {
                    'success': False,
                    'error': 'kagglehub package not installed. Please run: pip install kagglehub[pandas-datasets]'
                }
            
            # Load the dataset
            try:
                df = kagglehub.load_dataset(
                    KaggleDatasetAdapter.PANDAS,
                    dataset_path,
                    file_path
                )
                print(f"Loaded Kaggle dataset with {len(df)} records")
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to load Kaggle dataset: {str(e)}'
                }
            
            # Limit the number of recipes
            if len(df) > max_recipes:
                df = df.head(max_recipes)
            
            return self._process_dataframe_recipes(df)
            
        except Exception as e:
            print(f"Error importing from Kaggle dataset: {e}")
            return {
                'success': False,
                'error': f'Failed to import from Kaggle dataset: {str(e)}'
            }

    def import_from_csv_file(self, file, max_recipes: int = 100) -> Dict:
        """Import recipes from an uploaded CSV file"""
        try:
            import pandas as pd
            import io
            
            # Read CSV file - first get total row count
            file_content = file.read()
            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8')
            
            # Create DataFrame from CSV
            df = pd.read_csv(io.StringIO(file_content))
            total_rows = len(df)
            print(f"Loaded CSV with {total_rows} records")
            
            # Limit the number of recipes for processing
            if len(df) > max_recipes:
                df = df.head(max_recipes)
                print(f"Limited to {max_recipes} recipes for this import batch")
            
            result = self._process_dataframe_recipes(df)
            
            # Add total row count to result
            if result and result.get('success'):
                result['total_rows'] = total_rows
                result['processed_rows'] = len(df)
            
            return result
            
        except Exception as e:
            print(f"Error importing from CSV file: {e}")
            return {
                'success': False,
                'error': f'Failed to import from CSV file: {str(e)}'
            }

    def _process_dataframe_recipes(self, df) -> Dict:
        """Process a pandas DataFrame and extract recipe data"""
        try:
            recipes = []
            
            # Map common column names to our recipe fields
            column_mappings = {
                # Title mappings
                'title': ['title', 'name', 'recipe_title', 'recipe_name', 'recipe'],
                'description': ['description', 'desc', 'summary', 'recipe_description'],
                'ingredients': ['ingredients', 'ingredient_list', 'ingredients_list', 'recipe_ingredients', 'ingredients_raw_str'],
                'method': ['method', 'instructions', 'directions', 'steps', 'procedure', 'recipe_instructions'],
                'prep_time': ['prep_time', 'preparation_time', 'prep_time_minutes', 'prep_minutes'],
                'cook_time': ['cook_time', 'cooking_time', 'cook_time_minutes', 'cook_minutes'],
                'total_time': ['total_time', 'total_time_minutes', 'total_minutes'],
                'servings': ['servings', 'serves', 'portions', 'yield'],
                'difficulty': ['difficulty', 'skill_level', 'level'],
                'cuisine': ['cuisine', 'cuisine_type', 'category'],
                'tags': ['tags', 'categories', 'keywords', 'search_terms'],
                'calories': ['calories', 'nutrition_calories', 'kcal'],
                'rating': ['rating', 'average_rating', 'stars'],
                'url': ['url', 'source_url', 'recipe_url', 'id'],  # Food.com uses 'id' for recipe ID
                'image_url': ['image_url', 'image', 'photo_url', 'picture_url']
            }
            
            # Find the best matching columns
            mapped_columns = {}
            for field, possible_names in column_mappings.items():
                for col_name in possible_names:
                    if col_name.lower() in [col.lower() for col in df.columns]:
                        # Find exact case match
                        actual_col = next(col for col in df.columns if col.lower() == col_name.lower())
                        mapped_columns[field] = actual_col
                        break
            
            print(f"Mapped columns: {mapped_columns}")
            
            # Process each row in the dataframe
            for index, row in df.iterrows():
                try:
                    # Check if this is a Food.com dataset
                    if 'ingredients_raw_str' in df.columns and 'steps' in df.columns:
                        recipe_data = self._process_foodcom_recipe(row, mapped_columns)
                    else:
                        # Standard processing for other datasets
                        recipe_data = {}
                        
                        # Extract basic recipe information
                        recipe_data['title'] = str(row.get(mapped_columns.get('title', ''), f'Recipe {index + 1}')).strip()
                        recipe_data['description'] = str(row.get(mapped_columns.get('description', ''), '')).strip()
                        recipe_data['ingredients'] = str(row.get(mapped_columns.get('ingredients', ''), '')).strip()
                        recipe_data['method'] = str(row.get(mapped_columns.get('method', ''), '')).strip()
                        
                        # Handle time fields (convert to integers)
                        try:
                            prep_time = row.get(mapped_columns.get('prep_time', ''))
                            recipe_data['prep_time'] = int(float(prep_time)) if prep_time and str(prep_time).replace('.', '').isdigit() else None
                        except (ValueError, TypeError):
                            recipe_data['prep_time'] = None
                        
                        try:
                            cook_time = row.get(mapped_columns.get('cook_time', ''))
                            recipe_data['cook_time'] = int(float(cook_time)) if cook_time and str(cook_time).replace('.', '').isdigit() else None
                        except (ValueError, TypeError):
                            recipe_data['cook_time'] = None
                        
                        # Handle servings
                        try:
                            servings = row.get(mapped_columns.get('servings', ''))
                            recipe_data['servings'] = int(float(servings)) if servings and str(servings).replace('.', '').isdigit() else 4
                        except (ValueError, TypeError):
                            recipe_data['servings'] = 4
                        
                        # Handle difficulty
                        difficulty = str(row.get(mapped_columns.get('difficulty', ''), 'Medium')).strip().title()
                        if difficulty.lower() in ['easy', 'medium', 'hard', 'beginner', 'intermediate', 'advanced']:
                            recipe_data['difficulty'] = difficulty.title()
                        else:
                            recipe_data['difficulty'] = 'Medium'
                    
                    # Handle cuisine
                    recipe_data['cuisine_type'] = str(row.get(mapped_columns.get('cuisine', ''), '')).strip()
                    
                    # Handle tags (convert lists or comma-separated strings)
                    tags_raw = row.get(mapped_columns.get('tags', ''), '')
                    if tags_raw:
                        if isinstance(tags_raw, list):
                            recipe_data['tags'] = ', '.join(str(tag) for tag in tags_raw[:10])
                        else:
                            # Clean up tags string
                            tags_str = str(tags_raw).replace('[', '').replace(']', '').replace("'", '').replace('"', '')
                            recipe_data['tags'] = tags_str[:200]  # Limit length
                    else:
                        recipe_data['tags'] = ''
                    
                    # Handle source URL
                    recipe_data['source_url'] = str(row.get(mapped_columns.get('url', ''), '')).strip()
                    
                    # Handle image URL
                    recipe_data['image_url'] = str(row.get(mapped_columns.get('image_url', ''), '')).strip()
                    
                    # Skip recipes with insufficient data
                    if not recipe_data['title'] or len(recipe_data['title']) < 3:
                        continue
                    if not recipe_data['ingredients'] or len(recipe_data['ingredients']) < 10:
                        continue
                    if not recipe_data['method'] or len(recipe_data['method']) < 20:
                        continue
                    
                    # Clean up the data
                    recipe_data = self._clean_recipe_data(recipe_data)
                    
                    recipes.append(recipe_data)
                    
                    if len(recipes) >= 1000:  # Safety limit
                        break
                        
                except Exception as e:
                    print(f"Error processing recipe {index}: {e}")
                    continue
            
            print(f"Successfully processed {len(recipes)} recipes from dataset")
            
            return {
                'success': True,
                'recipes': recipes,
                'total_processed': len(recipes),
                'source': 'dataset'
            }
            
        except Exception as e:
            print(f"Error processing dataframe: {e}")
            return {
                'success': False,
                'error': f'Failed to process dataset: {str(e)}'
            }

    def _clean_recipe_data(self, recipe_data: dict) -> dict:
        """Clean and standardize recipe data"""
        try:
            # Clean ingredients - handle common formats
            if recipe_data.get('ingredients'):
                ingredients = recipe_data['ingredients']
                
                # If ingredients are in a list format like "['item1', 'item2']"
                if ingredients.startswith('[') and ingredients.endswith(']'):
                    try:
                        import ast
                        ingredients_list = ast.literal_eval(ingredients)
                        if isinstance(ingredients_list, list):
                            ingredients = '\n'.join(str(item).strip() for item in ingredients_list)
                    except:
                        # If literal_eval fails, try simple string processing
                        ingredients = ingredients.replace('[', '').replace(']', '').replace("'", '').replace('"', '')
                        ingredients = ingredients.replace(',', '\n')
                
                recipe_data['ingredients'] = ingredients.strip()
            
            # Clean method/instructions
            if recipe_data.get('method'):
                method = recipe_data['method']
                
                # If method is in a list format
                if method.startswith('[') and method.endswith(']'):
                    try:
                        import ast
                        method_list = ast.literal_eval(method)
                        if isinstance(method_list, list):
                            method = '\n'.join(f"{i+1}. {step.strip()}" for i, step in enumerate(method_list))
                    except:
                        method = method.replace('[', '').replace(']', '').replace("'", '').replace('"', '')
                        # Split by common delimiters and number the steps
                        steps = [step.strip() for step in method.split(',') if step.strip()]
                        method = '\n'.join(f"{i+1}. {step}" for i, step in enumerate(steps))
                
                recipe_data['method'] = method.strip()
            
            # Ensure title is not too long
            if recipe_data.get('title') and len(recipe_data['title']) > 140:
                recipe_data['title'] = recipe_data['title'][:137] + '...'
            
            # Ensure description is not too long
            if recipe_data.get('description') and len(recipe_data['description']) > 500:
                recipe_data['description'] = recipe_data['description'][:497] + '...'
            
            return recipe_data
            
        except Exception as e:
            print(f"Error cleaning recipe data: {e}")
            return recipe_data

    def _process_foodcom_recipe(self, row, mapped_columns) -> dict:
        """Special processing for Food.com dataset format"""
        import ast
        
        recipe_data = {}
        
        try:
            # Basic info
            recipe_data['title'] = str(row.get('name', '')).strip()
            recipe_data['description'] = str(row.get('description', '')).strip()
            
            # Handle ingredients - prefer raw ingredients with quantities
            ingredients_raw = row.get('ingredients_raw_str', '')
            ingredients_norm = row.get('ingredients', '')
            
            if ingredients_raw and str(ingredients_raw) != 'nan':
                try:
                    if isinstance(ingredients_raw, str) and ingredients_raw.startswith('['):
                        ingredients_list = ast.literal_eval(ingredients_raw)
                    elif isinstance(ingredients_raw, list):
                        ingredients_list = ingredients_raw
                    else:
                        ingredients_list = [str(ingredients_raw)]
                    
                    recipe_data['ingredients'] = '\n'.join([f"• {ingredient.strip()}" for ingredient in ingredients_list if ingredient and str(ingredient).strip()])
                except:
                    # Fallback to normalized ingredients
                    if ingredients_norm and str(ingredients_norm) != 'nan':
                        try:
                            if isinstance(ingredients_norm, str) and ingredients_norm.startswith('['):
                                ingredients_list = ast.literal_eval(ingredients_norm)
                            elif isinstance(ingredients_norm, list):
                                ingredients_list = ingredients_norm
                            else:
                                ingredients_list = [str(ingredients_norm)]
                            
                            recipe_data['ingredients'] = '\n'.join([f"• {ingredient.strip()}" for ingredient in ingredients_list if ingredient and str(ingredient).strip()])
                        except:
                            recipe_data['ingredients'] = str(ingredients_norm).replace('[', '').replace(']', '').replace("'", "")
            
            # Handle cooking steps/method
            steps = row.get('steps', '')
            if steps and str(steps) != 'nan':
                try:
                    if isinstance(steps, str) and steps.startswith('['):
                        steps_list = ast.literal_eval(steps)
                    elif isinstance(steps, list):
                        steps_list = steps
                    else:
                        steps_list = [str(steps)]
                    
                    recipe_data['method'] = '\n'.join([f"{i+1}. {step.strip()}" for i, step in enumerate(steps_list) if step and str(step).strip()])
                except:
                    recipe_data['method'] = str(steps).replace('[', '').replace(']', '').replace("'", "")
            
            # Handle servings
            servings = row.get('servings', '')
            if servings and str(servings) != 'nan':
                try:
                    recipe_data['servings'] = int(float(servings))
                except:
                    recipe_data['servings'] = 4
            else:
                recipe_data['servings'] = 4
            
            # Handle tags and search terms
            tags = row.get('tags', '')
            search_terms = row.get('search_terms', '')
            
            all_tags = []
            
            # Process tags
            if tags and str(tags) != 'nan':
                try:
                    if isinstance(tags, str) and tags.startswith('['):
                        tags_list = ast.literal_eval(tags)
                    elif isinstance(tags, list):
                        tags_list = tags
                    else:
                        tags_list = [str(tags)]
                    
                    for tag in tags_list:
                        if tag and str(tag).strip():
                            clean_tag = str(tag).strip().lower()
                            if len(clean_tag) <= 30 and clean_tag not in all_tags:
                                all_tags.append(clean_tag)
                except:
                    pass
            
            # Process search terms
            if search_terms and str(search_terms) != 'nan':
                try:
                    if isinstance(search_terms, str) and search_terms.startswith('['):
                        search_list = ast.literal_eval(search_terms)
                    elif isinstance(search_terms, list):
                        search_list = search_terms
                    else:
                        search_list = [str(search_terms)]
                    
                    for term in search_list:
                        if term and str(term).strip():
                            clean_term = str(term).strip().lower()
                            if len(clean_term) <= 30 and clean_term not in all_tags:
                                all_tags.append(clean_term)
                except:
                    pass
            
            # Limit tags
            recipe_data['tags'] = ', '.join(all_tags[:15])
            
            # Set defaults for Food.com
            recipe_data['difficulty'] = 'Medium'
            recipe_data['cuisine_type'] = 'American'
            recipe_data['country'] = 'United States'
            recipe_data['prep_time'] = None
            recipe_data['cook_time'] = None
            
            # Add source URL
            original_id = row.get('id', '')
            if original_id:
                recipe_data['source_url'] = f"https://www.food.com/recipe/{original_id}"
            
            return recipe_data
            
        except Exception as e:
            print(f"Error processing Food.com recipe: {e}")
            return {
                'title': f'Recipe {row.name}',
                'description': '',
                'ingredients': '',
                'method': '',
                'servings': 4,
                'difficulty': 'Medium',
                'tags': ''
            }
    
    def _extract_nutrition_from_json_ld(self, data: Dict) -> Dict:
        """Extract nutrition information from JSON-LD structured data"""
        nutrition = {}
        
        # Look for nutrition information in the JSON-LD data
        nutrition_data = data.get('nutrition', {})
        
        if nutrition_data:
            # Extract calories
            calories = nutrition_data.get('calories')
            if calories:
                nutrition['calories'] = self._parse_nutrition_value(calories)
            
            # Extract macronutrients
            protein = nutrition_data.get('proteinContent') or nutrition_data.get('protein')
            if protein:
                nutrition['protein_g'] = self._parse_nutrition_value(protein, 'g')
            
            carbs = nutrition_data.get('carbohydrateContent') or nutrition_data.get('carbs') or nutrition_data.get('carbohydrates')
            if carbs:
                nutrition['carbs_g'] = self._parse_nutrition_value(carbs, 'g')
            
            fat = nutrition_data.get('fatContent') or nutrition_data.get('fat')
            if fat:
                nutrition['fat_g'] = self._parse_nutrition_value(fat, 'g')
            
            # Extract fiber and sugar
            fiber = nutrition_data.get('fiberContent') or nutrition_data.get('fiber')
            if fiber:
                nutrition['fiber_g'] = self._parse_nutrition_value(fiber, 'g')
            
            sugar = nutrition_data.get('sugarContent') or nutrition_data.get('sugar')
            if sugar:
                nutrition['sugar_g'] = self._parse_nutrition_value(sugar, 'g')
            
            # Extract sodium
            sodium = nutrition_data.get('sodiumContent') or nutrition_data.get('sodium')
            if sodium:
                nutrition['sodium_mg'] = self._parse_nutrition_value(sodium, 'mg')
        
        return nutrition
    
    def _extract_nutrition_from_text(self, soup: BeautifulSoup) -> Dict:
        """Extract nutrition information from webpage text using pattern matching"""
        nutrition = {}
        
        # Get all text content
        text = soup.get_text().lower()
        
        # Define patterns for common nutrition indicators
        nutrition_patterns = {
            'calories': [
                r'calories?\s*[:=]?\s*(\d+(?:\.\d+)?)',
                r'(\d+(?:\.\d+)?)\s*cal(?:ories?)?',
                r'(\d+(?:\.\d+)?)\s*kcal',
                r'provides\s+(\d+(?:\.\d+)?)\s*kcal',  # "provides 487 kcal"
                r'(\d+(?:\.\d+)?)\s*calories?\s+per',
                r'serving\s+provides\s+(\d+(?:\.\d+)?)\s*kcal'
            ],
            'protein_g': [
                r'protein\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g',
                r'(\d+(?:\.\d+)?)\s*g\s*protein',
                r'(\d+(?:\.\d+)?)g\s+protein',  # "37g protein"
                r'protein\s*[:=]?\s*(\d+(?:\.\d+)?)g'
            ],
            'carbs_g': [
                r'carb(?:ohydrate)?s?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g',
                r'(\d+(?:\.\d+)?)\s*g\s*carb(?:ohydrate)?s?',
                r'(\d+(?:\.\d+)?)g\s+carbohydrates?',  # "66g carbohydrates"
                r'carbohydrates?\s*[:=]?\s*(\d+(?:\.\d+)?)g'
            ],
            'fat_g': [
                r'fat\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g',
                r'(\d+(?:\.\d+)?)\s*g\s*fat',
                r'(\d+(?:\.\d+)?)g\s+fat',  # "7g fat"
                r'fat\s*[:=]?\s*(\d+(?:\.\d+)?)g'
            ],
            'fiber_g': [
                r'fiber\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g',
                r'(\d+(?:\.\d+)?)\s*g\s*fiber',
                r'(\d+(?:\.\d+)?)g\s+fibre?',  # "4.5g fibre"
                r'fibre?\s*[:=]?\s*(\d+(?:\.\d+)?)g'
            ],
            'sugar_g': [
                r'sugar\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g',
                r'(\d+(?:\.\d+)?)\s*g\s*sugar',
                r'(\d+(?:\.\d+)?)g\s+sugars?',  # "10.5g sugars"
                r'sugars?\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'of\s+which\s+(\d+(?:\.\d+)?)g\s+sugars?'  # "of which 10.5g sugars"
            ],
            'sodium_mg': [
                r'sodium\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mg',
                r'(\d+(?:\.\d+)?)\s*mg\s*sodium',
                r'(\d+(?:\.\d+)?)g\s+salt',  # "2g salt" - convert to sodium
                r'salt\s*[:=]?\s*(\d+(?:\.\d+)?)g'
            ]
        }
        
        # Look for nutrition facts table or section
        nutrition_sections = soup.find_all(['div', 'section', 'table'], 
                                         class_=re.compile(r'nutrition|nutritional', re.I))
        
        # If we found nutrition sections, focus on those
        search_text = text
        if nutrition_sections:
            search_text = ' '.join(section.get_text().lower() for section in nutrition_sections)
        
        # Extract nutrition values using patterns
        for key, patterns in nutrition_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, search_text)
                if match:
                    try:
                        value = float(match.group(1))
                        
                        # Handle salt to sodium conversion (1g salt ≈ 400mg sodium)
                        if key == 'sodium_mg' and ('salt' in pattern):
                            value = value * 400  # Convert grams of salt to mg of sodium
                        
                        # Reasonable bounds checking
                        if key == 'calories' and 10 <= value <= 5000:
                            nutrition[key] = value
                            break
                        elif key.endswith('_g') and 0 <= value <= 500:
                            nutrition[key] = value
                            break
                        elif key.endswith('_mg') and 0 <= value <= 10000:  # Increased for sodium
                            nutrition[key] = value
                            break
                    except (ValueError, IndexError):
                        continue
        
        return nutrition
    
    def _extract_nutrition_from_description(self, description: str) -> Dict:
        """Extract nutrition information specifically from recipe description text"""
        nutrition = {}
        
        if not description:
            return nutrition
        
        # Convert to lowercase for pattern matching
        text = description.lower()
        
        # Enhanced patterns specifically for description format like:
        # "Each serving provides 487 kcal, 37g protein, 66g carbohydrates (of which 10.5g sugars), 7g fat (of which 1.5g saturates), 4.5g fibre and 2g salt."
        description_patterns = {
            'calories': [
                r'provides\s+(\d+(?:\.\d+)?)\s*kcal',
                r'provides\s+(\d+(?:\.\d+)?)\s*calories?',
                r'(\d+(?:\.\d+)?)\s*kcal\s*per\s+serving',
                r'(\d+(?:\.\d+)?)\s*calories?\s*per\s+serving',
                r'serving\s+provides\s+(\d+(?:\.\d+)?)\s*kcal'
            ],
            'protein_g': [
                r'(\d+(?:\.\d+)?)g\s+protein',
                r'protein\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'(\d+(?:\.\d+)?)\s*g\s*protein'
            ],
            'carbs_g': [
                r'(\d+(?:\.\d+)?)g\s+carbohydrates?',
                r'carbohydrates?\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'(\d+(?:\.\d+)?)\s*g\s*carbohydrates?'
            ],
            'fat_g': [
                r'(\d+(?:\.\d+)?)g\s+fat',
                r'fat\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'(\d+(?:\.\d+)?)\s*g\s*fat'
            ],
            'fiber_g': [
                r'(\d+(?:\.\d+)?)g\s+fibre?',
                r'fibre?\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'(\d+(?:\.\d+)?)\s*g\s*fibre?'
            ],
            'sugar_g': [
                r'(\d+(?:\.\d+)?)g\s+sugars?',
                r'sugars?\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'of\s+which\s+(\d+(?:\.\d+)?)g\s+sugars?',
                r'\(\s*of\s+which\s+(\d+(?:\.\d+)?)g\s+sugars?\s*\)'
            ],
            'sodium_mg': [
                r'(\d+(?:\.\d+)?)g\s+salt',  # Convert salt to sodium
                r'salt\s*[:=]?\s*(\d+(?:\.\d+)?)g',
                r'(\d+(?:\.\d+)?)\s*mg\s*sodium',
                r'sodium\s*[:=]?\s*(\d+(?:\.\d+)?)mg'
            ]
        }
        
        # Extract nutrition values using patterns
        for key, patterns in description_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        value = float(match.group(1))
                        
                        # Handle salt to sodium conversion (1g salt ≈ 400mg sodium)
                        if key == 'sodium_mg' and ('salt' in pattern):
                            value = value * 400  # Convert grams of salt to mg of sodium
                        
                        # Reasonable bounds checking
                        if key == 'calories' and 10 <= value <= 5000:
                            nutrition[key] = value
                            break
                        elif key.endswith('_g') and 0 <= value <= 500:
                            nutrition[key] = value
                            break
                        elif key.endswith('_mg') and 0 <= value <= 10000:
                            nutrition[key] = value
                            break
                    except (ValueError, IndexError):
                        continue
        
        return nutrition
    
    def _parse_nutrition_value(self, value, unit: str = None) -> Optional[float]:
        """Parse a nutrition value that might be a string with units"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove common units and extract number
            clean_value = re.sub(r'[^\d.]', '', value.strip())
            try:
                return float(clean_value)
            except ValueError:
                return None
        
        return None
