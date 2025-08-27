from flask import Blueprint, make_response, url_for, render_template_string
from datetime import datetime
from recipe_app.models.models import Recipe, User, db
from sqlalchemy import func

seo_bp = Blueprint('seo', __name__)

@seo_bp.route('/sitemap.xml')
def sitemap():
    """Generate XML sitemap for search engines"""
    
    # Get current date for lastmod
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Start building sitemap
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    
    # Static pages with high priority
    static_pages = [
        {'url': url_for('main.index', _external=True), 'priority': '1.0', 'changefreq': 'daily'},
        {'url': url_for('main.register', _external=True), 'priority': '0.9', 'changefreq': 'monthly'},
        {'url': url_for('main.login', _external=True), 'priority': '0.8', 'changefreq': 'monthly'},
        {'url': url_for('main.recipe_categories', _external=True), 'priority': '0.9', 'changefreq': 'weekly'},
        {'url': url_for('main.search', _external=True), 'priority': '0.8', 'changefreq': 'daily'},
        {'url': url_for('main.about', _external=True), 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': url_for('support.contact_form', _external=True), 'priority': '0.6', 'changefreq': 'monthly'},
        {'url': url_for('main.privacy_policy', _external=True), 'priority': '0.5', 'changefreq': 'yearly'},
        {'url': url_for('main.terms_of_service', _external=True), 'priority': '0.5', 'changefreq': 'yearly'},
        {'url': url_for('main.refund_policy', _external=True), 'priority': '0.4', 'changefreq': 'yearly'},
        {'url': url_for('main.blog', _external=True), 'priority': '0.8', 'changefreq': 'weekly'},
        {'url': url_for('support.faq', _external=True), 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': url_for('support.getting_started', _external=True), 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': url_for('main.tags', _external=True), 'priority': '0.6', 'changefreq': 'weekly'},
    ]
    
    # Add static pages
    for page in static_pages:
        sitemap_xml += f"""  <url>
    <loc>{page['url']}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
"""
    
    # Add blog/content pages
    blog_pages = [
        {'url': url_for('main.blog_post', slug='meal-planning-guide', _external=True), 
         'priority': '0.8', 'changefreq': 'monthly'},
        {'url': url_for('main.blog_post', slug='budget-meal-planning', _external=True), 
         'priority': '0.7', 'changefreq': 'monthly'},
        {'url': url_for('main.blog_post', slug='healthy-family-meals', _external=True), 
         'priority': '0.7', 'changefreq': 'monthly'},
    ]
    
    for page in blog_pages:
        sitemap_xml += f"""  <url>
    <loc>{page['url']}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
"""
    
    # Add individual recipe pages
    try:
        recipes = Recipe.query.filter_by(is_public=True).limit(1000).all()
        for recipe in recipes:
            # Use the correct endpoint name - function is called 'recipe'
            recipe_url = url_for('main.recipe', recipe_id=recipe.id, _external=True)
            # Use recipe's updated date if available, otherwise use today
            lastmod = recipe.updated_at.strftime('%Y-%m-%d') if hasattr(recipe, 'updated_at') and recipe.updated_at else today
            
            sitemap_xml += f"""  <url>
    <loc>{recipe_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
"""
    except Exception as e:
        # If database query fails, continue without recipes
        pass
    
    # Add category/search pages with proper query parameters
    categories = ['quick', 'healthy', 'budget', 'vegetarian', 'gluten-free', 'high-protein', 'low-carb']
    for category in categories:
        # Generate proper search URLs with query parameters
        category_url = url_for('main.search', _external=True) + f'?q={category}'
        sitemap_xml += f"""  <url>
    <loc>{category_url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
"""
    
    # Add cuisine pages with proper query parameters
    cuisines = ['british', 'italian', 'indian', 'chinese', 'mexican', 'thai', 'french', 'greek']
    for cuisine in cuisines:
        # Generate proper search URLs with cuisine parameter
        cuisine_url = url_for('main.search', _external=True) + f'?cuisine={cuisine}'
        sitemap_xml += f"""  <url>
    <loc>{cuisine_url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>
"""
    
    # Close sitemap
    sitemap_xml += "</urlset>"
    
    # Return XML response
    response = make_response(sitemap_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

@seo_bp.route('/robots.txt')
def robots():
    """Generate robots.txt file"""
    robots_txt = f"""User-agent: *
Allow: /

# Sitemap location
Sitemap: {url_for('seo.sitemap', _external=True)}

# Disallow admin/private areas
Disallow: /admin/
Disallow: /user/settings
Disallow: /api/
Disallow: /*.pdf$
Disallow: /login
Disallow: /register

# Allow search engines to crawl important pages
Allow: /
Allow: /recipes/
Allow: /search
Allow: /categories
Allow: /blog/

# Crawl delay (be nice to our server)
Crawl-delay: 1
"""
    
    response = make_response(robots_txt)
    response.headers['Content-Type'] = 'text/plain'
    return response
