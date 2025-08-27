"""
Image Storage Management Admin Interface
"""
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from recipe_app.db import db
from recipe_app.models.models import ImageStorage, User
from recipe_app.utils.image_storage import ImageStorageManager
import os


def admin_required(f):
    """Decorator to require admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@login_required
@admin_required
def image_storage_admin():
    """Admin page for managing image storage"""
    # Get storage statistics
    stats = {
        'storage_type': ImageStorageManager.get_storage_type(),
        'storage_path': ImageStorageManager.get_storage_path(),
        'total_images': 0,
        'database_images': 0,
        'filesystem_images': 0,
        'total_size_mb': 0
    }
    
    # Database statistics
    if ImageStorage.query.first():
        db_images = ImageStorage.query.all()
        stats['database_images'] = len(db_images)
        stats['total_size_mb'] = sum([img.file_size or 0 for img in db_images]) / (1024 * 1024)
    
    # Filesystem statistics
    storage_path = ImageStorageManager.get_storage_path()
    if os.path.exists(storage_path):
        for category in ['profiles', 'recipes']:
            category_path = os.path.join(storage_path, category)
            if os.path.exists(category_path):
                for filename in os.listdir(category_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        stats['filesystem_images'] += 1
                        file_path = os.path.join(category_path, filename)
                        if os.path.exists(file_path):
                            stats['total_size_mb'] += os.path.getsize(file_path) / (1024 * 1024)
    
    stats['total_images'] = stats['database_images'] + stats['filesystem_images']
    stats['total_size_mb'] = round(stats['total_size_mb'], 2)
    
    # Get recent images
    recent_images = []
    if ImageStorage.query.first():
        recent_db_images = ImageStorage.query.order_by(ImageStorage.created_at.desc()).limit(10).all()
        for img in recent_db_images:
            recent_images.append({
                'id': img.id,
                'filename': img.filename,
                'category': img.category,
                'storage': 'database',
                'size_kb': img.get_size_kb(),
                'created_at': img.created_at,
                'url': url_for('main.serve_image', image_id=img.id)
            })
    
    return render_template('admin/image_storage.html', 
                         title='Image Storage Management',
                         stats=stats,
                         recent_images=recent_images)


@login_required
@admin_required
def migrate_images():
    """Migrate images between storage types"""
    source_type = request.form.get('source_type')
    target_type = request.form.get('target_type')
    
    if source_type == target_type:
        flash('Source and target storage types cannot be the same.', 'error')
        return redirect(url_for('admin.image_storage_admin'))
    
    try:
        migrated_count = 0
        errors = []
        
        if source_type == 'database' and target_type == 'filesystem':
            # Migrate from database to filesystem
            db_images = ImageStorage.query.all()
            
            for db_image in db_images:
                try:
                    # Decode image data
                    import base64
                    from io import BytesIO
                    
                    image_data = base64.b64decode(db_image.data)
                    
                    # Create file on filesystem
                    storage_path = ImageStorageManager.get_storage_path()
                    category_path = os.path.join(storage_path, db_image.category)
                    os.makedirs(category_path, exist_ok=True)
                    
                    file_path = os.path.join(category_path, f"{db_image.id}.jpg")
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Update user records if this is a profile image
                    if db_image.category == 'profiles':
                        user = User.query.filter_by(profile_image=db_image.id).first()
                        if user:
                            user.profile_image = f"{db_image.id}.jpg"
                    
                    migrated_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to migrate {db_image.filename}: {str(e)}")
            
            # Clean up database records after successful migration
            if migrated_count > 0:
                ImageStorage.query.delete()
                db.session.commit()
        
        elif source_type == 'filesystem' and target_type == 'database':
            # Migrate from filesystem to database
            storage_path = ImageStorageManager.get_storage_path()
            
            for category in ['profiles', 'recipes']:
                category_path = os.path.join(storage_path, category)
                if os.path.exists(category_path):
                    for filename in os.listdir(category_path):
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            try:
                                file_path = os.path.join(category_path, filename)
                                
                                # Read file data
                                with open(file_path, 'rb') as f:
                                    file_data = f.read()
                                
                                # Encode as base64
                                import base64
                                encoded_data = base64.b64encode(file_data).decode('utf-8')
                                
                                # Create database record
                                file_id = os.path.splitext(filename)[0]
                                db_image = ImageStorage(
                                    id=file_id,
                                    category=category,
                                    filename=filename,
                                    data=encoded_data,
                                    mime_type='image/jpeg',
                                    file_size=len(file_data)
                                )
                                db.session.add(db_image)
                                
                                # Update user records if this is a profile image
                                if category == 'profiles':
                                    user = User.query.filter_by(profile_image=filename).first()
                                    if user:
                                        user.profile_image = file_id
                                
                                # Remove filesystem file
                                os.remove(file_path)
                                migrated_count += 1
                                
                            except Exception as e:
                                errors.append(f"Failed to migrate {filename}: {str(e)}")
        
        db.session.commit()
        
        if migrated_count > 0:
            flash(f'Successfully migrated {migrated_count} images from {source_type} to {target_type}.', 'success')
        if errors:
            flash(f'Encountered {len(errors)} errors during migration.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Migration failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.image_storage_admin'))


@login_required
@admin_required
def cleanup_orphaned_images():
    """Clean up orphaned images not referenced by any user"""
    try:
        orphaned_count = 0
        
        # Clean up database images
        if ImageStorage.query.first():
            db_images = ImageStorage.query.filter_by(category='profiles').all()
            for db_image in db_images:
                user = User.query.filter_by(profile_image=db_image.id).first()
                if not user:
                    db.session.delete(db_image)
                    orphaned_count += 1
        
        # Clean up filesystem images
        storage_path = ImageStorageManager.get_storage_path()
        profiles_path = os.path.join(storage_path, 'profiles')
        
        if os.path.exists(profiles_path):
            for filename in os.listdir(profiles_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    user = User.query.filter_by(profile_image=filename).first()
                    if not user:
                        file_path = os.path.join(profiles_path, filename)
                        os.remove(file_path)
                        orphaned_count += 1
        
        db.session.commit()
        flash(f'Cleaned up {orphaned_count} orphaned images.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Cleanup failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.image_storage_admin'))
