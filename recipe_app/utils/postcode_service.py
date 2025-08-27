"""
Postcode Lookup Service
Uses UK Government API to get location data from postcodes
"""
import requests
import logging
from typing import Dict, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class PostcodeLookupService:
    """
    Service to lookup postcode information using free UK APIs
    """
    
    def __init__(self):
        # UK Government postcode API (free and legal)
        self.api_base_url = "https://api.postcodes.io"
        
    def validate_postcode(self, postcode: str) -> bool:
        """Validate UK postcode format"""
        if not postcode:
            return False
        
        # UK postcode regex pattern
        pattern = r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$'
        return bool(re.match(pattern, postcode.upper().replace(' ', '')))
    
    def normalize_postcode(self, postcode: str) -> str:
        """Normalize postcode format"""
        if not postcode:
            return ""
        
        # Remove spaces and convert to uppercase
        clean = postcode.replace(' ', '').upper()
        
        # Add space in correct position (before last 3 characters)
        if len(clean) >= 5:
            return f"{clean[:-3]} {clean[-3:]}"
        
        return clean
    
    def lookup_postcode(self, postcode: str) -> Optional[Dict]:
        """
        Look up postcode information using postcodes.io API
        Returns location data or None if not found
        """
        if not self.validate_postcode(postcode):
            logger.warning(f"Invalid postcode format: {postcode}")
            return None
        
        normalized_postcode = self.normalize_postcode(postcode)
        
        try:
            # Use the free postcodes.io API
            url = f"{self.api_base_url}/postcodes/{normalized_postcode.replace(' ', '')}"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 200 and data.get('result'):
                    result = data['result']
                    
                    return {
                        'postcode': result.get('postcode'),
                        'latitude': result.get('latitude'),
                        'longitude': result.get('longitude'),
                        'town': result.get('admin_ward'),
                        'district': result.get('admin_district'),
                        'county': result.get('admin_county'),
                        'region': result.get('region'),
                        'country': result.get('country'),
                        'postcode_area': result.get('postcode').split()[0] if result.get('postcode') else None,
                    }
            else:
                logger.warning(f"Postcode lookup failed for {postcode}: HTTP {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Error looking up postcode {postcode}: {e}")
        
        return None
    
    def get_nearby_postcodes(self, postcode: str, radius_km: int = 5) -> list:
        """
        Get nearby postcodes within specified radius
        """
        postcode_data = self.lookup_postcode(postcode)
        if not postcode_data:
            return []
        
        lat = postcode_data['latitude']
        lon = postcode_data['longitude']
        
        try:
            # Convert km to miles for the API (postcodes.io uses miles)
            radius_miles = radius_km * 0.621371
            
            url = f"{self.api_base_url}/postcodes"
            params = {
                'lon': lon,
                'lat': lat,
                'radius': int(radius_miles * 1000),  # API expects meters
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 200 and data.get('result'):
                    nearby = []
                    for result in data['result']:
                        nearby.append({
                            'postcode': result.get('postcode'),
                            'distance': result.get('distance'),
                            'latitude': result.get('latitude'),
                            'longitude': result.get('longitude'),
                        })
                    return nearby
                    
        except requests.RequestException as e:
            logger.error(f"Error finding nearby postcodes for {postcode}: {e}")
        
        return []
    
    def extract_postcode_area(self, postcode: str) -> str:
        """Extract postcode area (first part) for regional grouping"""
        if not postcode:
            return ""
        
        # Remove spaces and get first 1-2 letters
        clean_postcode = postcode.replace(' ', '').upper()
        area_match = re.match(r'^([A-Z]{1,2})', clean_postcode)
        
        if area_match:
            return area_match.group(1)
        
        return ""

# Create global instance
postcode_service = PostcodeLookupService()
