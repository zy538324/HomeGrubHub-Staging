"""
Celery configuration for the Flask application
"""
import os
from celery import Celery

def make_celery(app):
    """Create and configure Celery instance"""
    
    # Configure Celery with Redis as broker and backend
    app.config.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    app.config.setdefault('CELERY_TASK_SERIALIZER', 'json')
    app.config.setdefault('CELERY_RESULT_SERIALIZER', 'json')
    app.config.setdefault('CELERY_ACCEPT_CONTENT', ['json'])
    app.config.setdefault('CELERY_TIMEZONE', 'Europe/London')
    app.config.setdefault('CELERY_ENABLE_UTC', True)
    
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    
    celery.conf.update(app.config)
    
    # Setup task context
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
