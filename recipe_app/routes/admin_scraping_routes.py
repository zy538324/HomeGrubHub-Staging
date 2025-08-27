"""
Admin routes for managing the scraping system
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import uuid

from recipe_app.db import db
from recipe_app.models.scraping_models import (
    ScrapedProduct, ScrapedPrice, ScrapingLog, PriceAlert,
    save_scraped_price, find_or_create_product
)
from recipe_app.utils.supermarket_scraper import supermarket_scraper

admin_scraping = Blueprint('admin_scraping', __name__)

def admin_redirect():
    """Redirect admin requests to user dashboard with notice"""
    flash('Admin features have been moved to a separate admin portal.', 'info')
    return redirect(url_for('main.dashboard'))

@admin_scraping.route('/admin/scraping')
@login_required
def scraping_dashboard():
    """Admin dashboard moved to separate admin application"""
    return admin_redirect()
    
    # Get statistics
    total_products = ScrapedProduct.query.count()
    total_prices = ScrapedPrice.query.count()
    
    # Recent activity
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_prices = ScrapedPrice.query.filter(
        ScrapedPrice.scraped_at >= last_24h
    ).count()
    
    # Store breakdown
    store_stats = db.session.query(
        ScrapedPrice.store,
        db.func.count(ScrapedPrice.id)
    ).group_by(ScrapedPrice.store).all()
    
    # Recent logs
    recent_logs = ScrapingLog.query.order_by(
        ScrapingLog.started_at.desc()
    ).limit(10).all()
    
    # Recent products
    recent_products = ScrapedPrice.query.order_by(
        ScrapedPrice.scraped_at.desc()
    ).limit(20).all()
    
    return render_template('admin/scraping_dashboard.html',
                         total_products=total_products,
                         total_prices=total_prices,
                         recent_prices=recent_prices,
                         store_stats=store_stats,
                         recent_logs=recent_logs,
                         recent_products=recent_products)

@admin_scraping.route('/admin/scraping/test', methods=['POST'])
@login_required  
def test_scraping():
    """Test scraping a single product"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product_name = request.form.get('product_name', '').strip()
    store = request.form.get('store', 'tesco')
    
    if not product_name:
        return jsonify({'error': 'Product name required'}), 400
    
    try:
        # Test scraping
        results = supermarket_scraper.scrape_product(product_name, stores=[store])
        
        products_found = results.get(store, [])
        saved_count = 0
        
        # Save first 3 results to database
        for product in products_found[:3]:
            try:
                price_record = save_scraped_price(product)
                db.session.commit()
                saved_count += 1
            except Exception as e:
                db.session.rollback()
                continue
        
        return jsonify({
            'success': True,
            'products_found': len(products_found),
            'products_saved': saved_count,
            'sample_products': [
                {
                    'name': p.name,
                    'price': float(p.price),
                    'store': p.store,
                    'url': p.url
                } for p in products_found[:5]
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_scraping.route('/admin/scraping/category', methods=['POST'])
@login_required
def scrape_category():
    """Scrape a category across stores"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    category = request.form.get('category', '').strip()
    stores = request.form.getlist('stores')
    
    if not category:
        return jsonify({'error': 'Category required'}), 400
    
    if not stores:
        stores = ['tesco', 'sainsburys']
    
    try:
        # Create session ID
        session_id = str(uuid.uuid4())[:8]
        
        # Scrape category
        results = supermarket_scraper.scrape_category(category, stores=stores)
        
        total_saved = 0
        store_results = {}
        
        for store_name, store_data in results.items():
            store_saved = 0
            
            # Create log entry
            log = ScrapingLog(
                session_id=session_id,
                store=store_name,
                category=category,
                status='completed'
            )
            
            products_found = 0
            
            for search_term, products in store_data.items():
                products_found += len(products)
                
                # Save products (limit to prevent overload)
                for product in products[:10]:  
                    try:
                        price_record = save_scraped_price(product, category)
                        db.session.commit()
                        store_saved += 1
                        total_saved += 1
                    except Exception as e:
                        db.session.rollback()
                        continue
            
            log.products_found = products_found
            log.products_saved = store_saved
            log.completed_at = datetime.utcnow()
            
            db.session.add(log)
            store_results[store_name] = store_saved
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'total_saved': total_saved,
            'store_results': store_results,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_scraping.route('/admin/scraping/cleanup', methods=['POST'])
@login_required
def cleanup_old_data():
    """Clean up old scraping data"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    days = int(request.form.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    try:
        # Delete old prices
        old_prices = ScrapedPrice.query.filter(ScrapedPrice.scraped_at < cutoff)
        price_count = old_prices.count()
        old_prices.delete()
        
        # Delete old logs
        old_logs = ScrapingLog.query.filter(ScrapingLog.started_at < cutoff)
        log_count = old_logs.count()
        old_logs.delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'prices_deleted': price_count,
            'logs_deleted': log_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_scraping.route('/admin/scraping/products')
@login_required
def list_products():
    """List scraped products with pagination"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    store = request.args.get('store', '')
    search = request.args.get('search', '')
    
    query = ScrapedPrice.query.join(ScrapedProduct)
    
    if store:
        query = query.filter(ScrapedPrice.store == store)
    
    if search:
        query = query.filter(ScrapedProduct.name.ilike(f'%{search}%'))
    
    products = query.order_by(ScrapedPrice.scraped_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get available stores
    stores = db.session.query(ScrapedPrice.store).distinct().all()
    stores = [s[0] for s in stores]
    
    return render_template('admin/scraping_products.html',
                         products=products,
                         stores=stores,
                         current_store=store,
                         current_search=search)

@admin_scraping.route('/admin/scraping/logs')
@login_required
def scraping_logs():
    """View scraping logs"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = ScrapingLog.query
    
    if status:
        query = query.filter(ScrapingLog.status == status)
    
    logs = query.order_by(ScrapingLog.started_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('admin/scraping_logs.html',
                         logs=logs,
                         current_status=status)

@admin_scraping.route('/api/scraping/price-history/<int:product_id>')
@login_required
def price_history(product_id):
    """Get price history for a product"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = ScrapedProduct.query.get_or_404(product_id)
    
    # Get price history for last 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    prices = ScrapedPrice.query.filter(
        ScrapedPrice.product_id == product_id,
        ScrapedPrice.scraped_at >= cutoff
    ).order_by(ScrapedPrice.scraped_at).all()
    
    # Group by store
    store_data = {}
    for price in prices:
        if price.store not in store_data:
            store_data[price.store] = []
        
        store_data[price.store].append({
            'date': price.scraped_at.isoformat(),
            'price': float(price.price)
        })
    
    return jsonify({
        'product': product.name,
        'stores': store_data
    })
