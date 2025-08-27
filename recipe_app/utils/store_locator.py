"""
UK Store Locator Service
Maps postcodes to nearby supermarkets for price scraping
"""
import re
import requests
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class NearbyStore:
    name: str
    postcode: str
    distance_miles: float
    delivery_available: bool = True

class UKStoreLocator:
    """Find nearby stores based on UK postcode"""
    
    def __init__(self):
        # Major UK supermarket delivery areas by postcode prefix
        self.store_coverage = {
            'tesco': {
                'london': ['E', 'N', 'NW', 'SE', 'SW', 'W', 'WC', 'EC'],
                'manchester': ['M'],
                'birmingham': ['B'],
                'leeds': ['LS'],
                'glasgow': ['G'],
                'edinburgh': ['EH'],
                'bristol': ['BS'],
                'liverpool': ['L'],
                'sheffield': ['S'],
                'newcastle': ['NE'],
                'cardiff': ['CF'],
                'nottingham': ['NG'],
                'leicester': ['LE'],
                'coventry': ['CV'],
                'hull': ['HU'],
                'bradford': ['BD'],
                'wakefield': ['WF'],
                'plymouth': ['PL'],
                'derby': ['DE'],
                'southampton': ['SO'],
                'portsmouth': ['PO'],
                'brighton': ['BN'],
                'blackpool': ['FY'],
                'middlesbrough': ['TS'],
                'bolton': ['BL'],
                'wigan': ['WN'],
                'preston': ['PR'],
                'york': ['YO'],
                'canterbury': ['CT'],
                'exeter': ['EX'],
                'cambridge': ['CB'],
                'oxford': ['OX'],
                'reading': ['RG'],
                'swindon': ['SN'],
                'northampton': ['NN'],
                'peterborough': ['PE'],
                'luton': ['LU'],
                'watford': ['WD'],
                'basildon': ['SS'],
                'southend': ['SS'],
                'chelmsford': ['CM'],
                'colchester': ['CO'],
                'ipswich': ['IP'],
                'norwich': ['NR'],
                'great_yarmouth': ['NR'],
                'kingslynn': ['PE'],
                'stevenage': ['SG'],
                'hemel_hempstead': ['HP'],
                'slough': ['SL'],
                'woking': ['GU'],
                'guildford': ['GU'],
                'crawley': ['RH'],
                'eastbourne': ['BN'],
                'hastings': ['TN'],
                'maidstone': ['ME'],
                'dartford': ['DA'],
                'bromley': ['BR'],
                'croydon': ['CR'],
                'kingston': ['KT'],
                'sutton': ['SM'],
                'wimbledon': ['SW'],
                'richmond': ['TW'],
                'hounslow': ['TW'],
                'ealing': ['W'],
                'harrow': ['HA'],
                'barnet': ['EN'],
                'enfield': ['EN'],
                'waltham_forest': ['E'],
                'redbridge': ['IG'],
                'havering': ['RM'],
                'bexley': ['DA'],
                'greenwich': ['SE'],
                'lewisham': ['SE'],
                'southwark': ['SE'],
                'lambeth': ['SE'],
                'wandsworth': ['SW'],
                'merton': ['SW'],
                'kensington': ['SW'],
                'hammersmith': ['W'],
                'islington': ['N'],
                'camden': ['NW'],
                'brent': ['NW'],
                'westminster': ['SW', 'W', 'WC'],
                'tower_hamlets': ['E'],
                'hackney': ['E'],
                'newham': ['E']
            },
            'sainsburys': {
                'london': ['E', 'N', 'NW', 'SE', 'SW', 'W', 'WC', 'EC'],
                'manchester': ['M'],
                'birmingham': ['B'],
                'leeds': ['LS'],
                'bristol': ['BS'],
                'liverpool': ['L'],
                'sheffield': ['S'],
                'edinburgh': ['EH'],
                'glasgow': ['G'],
                'cardiff': ['CF'],
                'nottingham': ['NG'],
                'leicester': ['LE'],
                'coventry': ['CV'],
                'southampton': ['SO'],
                'portsmouth': ['PO'],
                'brighton': ['BN'],
                'cambridge': ['CB'],
                'oxford': ['OX'],
                'reading': ['RG'],
                'swindon': ['SN'],
                'northampton': ['NN'],
                'peterborough': ['PE'],
                'luton': ['LU'],
                'watford': ['WD'],
                'chelmsford': ['CM'],
                'colchester': ['CO'],
                'ipswich': ['IP'],
                'norwich': ['NR'],
                'stevenage': ['SG'],
                'hemel_hempstead': ['HP'],
                'slough': ['SL'],
                'woking': ['GU'],
                'guildford': ['GU'],
                'crawley': ['RH'],
                'eastbourne': ['BN'],
                'maidstone': ['ME'],
                'dartford': ['DA'],
                'croydon': ['CR'],
                'kingston': ['KT'],
                'sutton': ['SM'],
                'richmond': ['TW'],
                'hounslow': ['TW'],
                'ealing': ['W'],
                'harrow': ['HA'],
                'barnet': ['EN'],
                'enfield': ['EN']
            },
            'asda': {
                'manchester': ['M'],
                'birmingham': ['B'],
                'leeds': ['LS'],
                'glasgow': ['G'],
                'sheffield': ['S'],
                'newcastle': ['NE'],
                'liverpool': ['L'],
                'bradford': ['BD'],
                'wakefield': ['WF'],
                'hull': ['HU'],
                'derby': ['DE'],
                'nottingham': ['NG'],
                'leicester': ['LE'],
                'coventry': ['CV'],
                'bolton': ['BL'],
                'wigan': ['WN'],
                'preston': ['PR'],
                'blackpool': ['FY'],
                'middlesbrough': ['TS'],
                'sunderland': ['SR'],
                'gateshead': ['NE'],
                'south_shields': ['NE'],
                'tynemouth': ['NE'],
                'cramlington': ['NE'],
                'blyth': ['NE'],
                'hexham': ['NE'],
                'consett': ['DH'],
                'durham': ['DH'],
                'darlington': ['DL'],
                'stockton': ['TS'],
                'hartlepool': ['TS'],
                'redcar': ['TS'],
                'whitby': ['YO'],
                'scarborough': ['YO'],
                'york': ['YO'],
                'harrogate': ['HG'],
                'ripon': ['HG'],
                'skipton': ['BD'],
                'keighley': ['BD'],
                'halifax': ['HX'],
                'huddersfield': ['HD'],
                'dewsbury': ['WF'],
                'pontefract': ['WF'],
                'castleford': ['WF'],
                'normanton': ['WF'],
                'ossett': ['WF'],
                'horsforth': ['LS'],
                'otley': ['LS'],
                'ilkley': ['LS'],
                'garforth': ['LS'],
                'morley': ['LS'],
                'pudsey': ['LS'],
                'yeadon': ['LS'],
                'wetherby': ['LS'],
                'tadcaster': ['LS'],
                'selby': ['YO'],
                'goole': ['DN'],
                'scunthorpe': ['DN'],
                'grimsby': ['DN'],
                'cleethorpes': ['DN'],
                'immingham': ['DN'],
                'barton': ['DN'],
                'gainsborough': ['DN'],
                'lincoln': ['LN'],
                'grantham': ['NG'],
                'sleaford': ['NG'],
                'boston': ['PE'],
                'spalding': ['PE'],
                'stamford': ['PE'],
                'corby': ['NN'],
                'kettering': ['NN'],
                'wellingborough': ['NN'],
                'rushden': ['NN'],
                'daventry': ['NN'],
                'towcester': ['NN'],
                'brackley': ['NN']
            }
        }
    
    def normalize_postcode(self, postcode: str) -> str:
        """Normalize UK postcode format"""
        if not postcode:
            return ""
        
        # Remove spaces and convert to uppercase
        clean = re.sub(r'\s+', '', postcode.upper())
        
        # UK postcode pattern: M1 1AA -> M1
        match = re.match(r'^([A-Z]{1,2}\d{1,2}[A-Z]?)', clean)
        if match:
            return match.group(1)
        
        return clean[:2]  # Fallback to first 2 chars
    
    def get_stores_for_postcode(self, postcode: str) -> List[str]:
        """Get list of stores that deliver to this postcode"""
        postcode_prefix = self.normalize_postcode(postcode)
        available_stores = []
        
        for store, regions in self.store_coverage.items():
            for region, prefixes in regions.items():
                if any(postcode_prefix.startswith(prefix) for prefix in prefixes):
                    available_stores.append(store)
                    break
        
        # Default to Tesco if no matches (largest coverage)
        if not available_stores:
            available_stores = ['tesco']
        
        return available_stores
    
    def get_priority_stores(self, postcode: str) -> List[str]:
        """Get stores in priority order for scraping"""
        available = self.get_stores_for_postcode(postcode)
        
        # Priority order: biggest selection first
        priority_order = ['tesco', 'sainsburys', 'asda', 'morrisons']
        
        return sorted(available, key=lambda x: priority_order.index(x) if x in priority_order else 999)

# Global instance
store_locator = UKStoreLocator()
