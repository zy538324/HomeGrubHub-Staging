"""
Scheduled scraping tasks using Celery
Handles daily price updates and category scraping
"""
from celery import Celery
from datetime import datetime, timedelta
import uuid
import logging
from typing import List, Dict
from recipe_app.db import create_app, db
from recipe_app.supermarket_scraper import supermarket_scraper
from recipe_app.models.scraping_models import (
    ScrapedProduct, ScrapedPrice, ScrapingLog, 
    save_scraped_price, find_or_create_product
)

# Configure Celery
app = create_app()
celery = Celery(app.import_name)
celery.conf.update(app.config)

# Setup logging
logger = logging.getLogger(__name__)

class TaskContext:
    """Context manager for Celery tasks with Flask app context"""
    def __enter__(self):
        self.app_context = app.app_context()
        self.app_context.push()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()

@celery.task(bind=True)
def scrape_store_category(self, store: str, category: str, session_id: str = None):
    """Scrape a specific category from a specific store"""
    
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
    
    with TaskContext():
        # Create scraping log
        log = ScrapingLog(
            session_id=session_id,
            store=store,
            category=category,
            status='pending'
        )
        db.session.add(log)
        db.session.commit()
        
        try:
            start_time = datetime.utcnow()
            
            # Scrape the category
            results = supermarket_scraper.scrape_category(category, stores=[store])
            
            products_found = 0
            products_saved = 0
            errors = 0
            
            if store in results:
                for search_term, products in results[store].items():
                    products_found += len(products)
                    
                    for product_data in products:
                        try:
                            # Save to database
                            price_record = save_scraped_price(product_data, category)
                            db.session.commit()
                            products_saved += 1
                            
                        except Exception as e:
                            errors += 1
                            logger.error(f"Error saving product {product_data.name}: {e}")
                            db.session.rollback()
            
            # Update log
            duration = (datetime.utcnow() - start_time).total_seconds()
            log.products_found = products_found
            log.products_saved = products_saved
            log.errors_count = errors
            log.duration_seconds = duration
            log.status = 'completed'
            log.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Completed scraping {store}/{category}: {products_saved} products saved")
            
            return {
                'store': store,
                'category': category,
                'products_found': products_found,
                'products_saved': products_saved,
                'errors': errors,
                'duration': duration
            }
            
        except Exception as e:
            # Update log with error
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"Failed scraping {store}/{category}: {e}")
            raise


@celery.task(bind=True)
def scrape_product_across_stores(self, product_name: str, stores: List[str] = None):
    """Scrape a specific product across multiple stores"""
    
    session_id = str(uuid.uuid4())[:8]
    
    with TaskContext():
        if stores is None:
            stores = ['tesco', 'sainsburys', 'asda', 'morrisons']
        
        results = {}
        total_saved = 0
        
        for store in stores:
            try:
                # Create log for this store
                log = ScrapingLog(
                    session_id=session_id,
                    store=store,
                    search_term=product_name,
                    status='pending'
                )
                db.session.add(log)
                db.session.commit()
                
                start_time = datetime.utcnow()
                
                # Scrape the store
                store_results = supermarket_scraper.scrape_product(product_name, stores=[store])
                
                products_found = len(store_results.get(store, []))
                products_saved = 0
                
                # Save products to database
                for product_data in store_results.get(store, []):
                    try:
                        price_record = save_scraped_price(product_data)
                        db.session.commit()
                        products_saved += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving {product_data.name} from {store}: {e}")
                        db.session.rollback()
                
                # Update log
                duration = (datetime.utcnow() - start_time).total_seconds()
                log.products_found = products_found
                log.products_saved = products_saved
                log.duration_seconds = duration
                log.status = 'completed'
                log.completed_at = datetime.utcnow()
                db.session.commit()
                
                results[store] = products_saved
                total_saved += products_saved
                
                # Delay between stores
                import time
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error scraping {product_name} from {store}: {e}")
                results[store] = 0
        
        return {
            'product': product_name,
            'results': results,
            'total_saved': total_saved
        }


@celery.task(bind=True) 
def daily_price_update(self):
    """Daily task to update prices for common products"""
    
    session_id = f"daily_{datetime.now().strftime('%Y%m%d')}"
    
    with TaskContext():
        # Priority products to scrape daily
        priority_products = [
            'milk', 'bread', 'eggs', 'butter', 'chicken breast',
            'bananas', 'apples', 'potatoes', 'onions', 'rice'
        ]
        
        stores = ['tesco', 'sainsburys', 'asda']  # Start with major stores
        
        results = {}
        
        for product in priority_products:
            try:
                # Schedule individual product scraping
                task_result = scrape_product_across_stores.delay(product, stores)
                results[product] = f"Task scheduled: {task_result.id}"
                
                # Small delay between products
                import time
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scheduling scraping for {product}: {e}")
                results[product] = f"Error: {e}"
        
        logger.info(f"Daily price update scheduled for {len(priority_products)} products")
        return results


@celery.task(bind=True)
def weekly_category_update(self):
    """Weekly comprehensive category scraping"""
    
    session_id = f"weekly_{datetime.now().strftime('%Y%m%d')}"
    
    with TaskContext():
        categories = ['dairy', 'meat', 'vegetables', 'fruits', 'pantry']
        stores = ['tesco', 'sainsburys', 'asda', 'morrisons']
        
        scheduled_tasks = []
        
        for category in categories:
            for store in stores:
                try:
                    # Schedule category scraping with delay
                    task_result = scrape_store_category.apply_async(
                        args=[store, category, session_id],
                        countdown=len(scheduled_tasks) * 60  # 1 minute delay between tasks
                    )
                    
                    scheduled_tasks.append({
                        'task_id': task_result.id,
                        'store': store,
                        'category': category
                    })
                    
                except Exception as e:
                    logger.error(f"Error scheduling {store}/{category}: {e}")
        
        logger.info(f"Weekly update scheduled {len(scheduled_tasks)} scraping tasks")
        return {
            'scheduled_tasks': len(scheduled_tasks),
            'tasks': scheduled_tasks
        }


@celery.task(bind=True)
def cleanup_old_prices(self, days_to_keep: int = 90):
    """Clean up old price data to prevent database bloat"""
    
    with TaskContext():
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old prices
        old_prices = ScrapedPrice.query.filter(ScrapedPrice.scraped_at < cutoff_date)
        count = old_prices.count()
        old_prices.delete()
        
        # Delete old logs
        old_logs = ScrapingLog.query.filter(ScrapingLog.started_at < cutoff_date)
        log_count = old_logs.count()
        old_logs.delete()
        
        db.session.commit()
        
        logger.info(f"Cleaned up {count} old prices and {log_count} old logs")
        return {
            'prices_deleted': count,
            'logs_deleted': log_count,
            'cutoff_date': cutoff_date.isoformat()
        }


@celery.task(bind=True)
def price_alert_check(self):
    """Check for price alerts and notify users"""
    
    with TaskContext():
        from recipe_app.models.scraping_models import PriceAlert
        
        # Get active price alerts
        alerts = PriceAlert.query.filter_by(is_active=True).all()
        
        triggered_alerts = []
        
        for alert in alerts:
            # Get latest prices for the product
            latest_prices = alert.product.get_latest_prices()
            
            for price in latest_prices:
                # Check if price meets alert condition
                if alert.store_preference == 'any' or price.store == alert.store_preference:
                    if price.price <= alert.target_price:
                        # Alert triggered!
                        alert.last_triggered = datetime.utcnow()
                        alert.times_triggered += 1
                        
                        triggered_alerts.append({
                            'user_id': alert.user_id,
                            'product_name': alert.product.name,
                            'target_price': float(alert.target_price),
                            'current_price': float(price.price),
                            'store': price.store,
                            'savings': float(alert.target_price - price.price)
                        })
        
        db.session.commit()
        
        logger.info(f"Checked {len(alerts)} alerts, {len(triggered_alerts)} triggered")
        
        # Here you would send notifications (email, push, etc.)
        # For now, just return the results
        return {
            'alerts_checked': len(alerts),
            'alerts_triggered': len(triggered_alerts),
            'triggered_alerts': triggered_alerts
        }


# Celery beat schedule for periodic tasks
celery.conf.beat_schedule = {
    'daily-price-update': {
        'task': 'recipe_app.scraping_tasks.daily_price_update',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
    },
    'weekly-category-update': {
        'task': 'recipe_app.scraping_tasks.weekly_category_update', 
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
    },
    'cleanup-old-prices': {
        'task': 'recipe_app.scraping_tasks.cleanup_old_prices',
        'schedule': 60.0 * 60.0 * 24,  # Daily cleanup
    },
    'price-alert-check': {
        'task': 'recipe_app.scraping_tasks.price_alert_check',
        'schedule': 60.0 * 60.0 * 2,  # Every 2 hours
    },
}

celery.conf.timezone = 'Europe/London'
