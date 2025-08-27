#!/usr/bin/env python3
"""
Clean up the family_collaboration.py file by removing @require_tier decorators
"""

import re

# Read the file
with open('recipe_app/routes/family_collaboration.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all @require_tier lines
cleaned_content = re.sub(r'@require_tier\[.*\]\n', '', content)

# Write back the cleaned content
with open('recipe_app/routes/family_collaboration.py', 'w', encoding='utf-8') as f:
    f.write(cleaned_content)

print("Removed all @require_tier decorators from family_collaboration.py")
