"""
Image Storage Manager for HomeGrubHub
Handles both filesystem and database storage options
"""

import os
import secrets
import base64
from PIL import Image
from io import BytesIO
from flask import current_app, url_for
from werkzeug.utils import secure_filename
from recipe_app.db import db


class ImageStorageManager:
    """Manages image storage with support for filesystem and database storage"""
    
    @staticmethod
    def get_storage_type():
        """Get the configured storage type"""
        return current_app.config.get('IMAGE_STORAGE_TYPE', 'filesystem')
    
    @staticmethod
    def get_storage_path():
        """Get the configured storage path"""
        return current_app.config.get('IMAGE_STORAGE_PATH', 'D:/HomeGrubHub_Images')
    
    @staticmethod
    def validate_image(file):
        """Validate uploaded image file"""
        if not file or not file.filename:
            return False, "No file selected"
        
        # Check file extension
        filename = secure_filename(file.filename.lower())
        if not ('.' in filename and 
                filename.rsplit('.', 1)[1] in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', {'jpg', 'jpeg', 'png', 'gif'})):
            return False, "Invalid file type. Please upload JPG, PNG, or GIF images."
        
        # Check file size
        max_size = current_app.config.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            return False, f"File too large. Maximum size is {max_size // (1024*1024)}MB."
        
        # Try to open as image
        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)  # Reset file pointer after verify
            return True, "Valid image file"
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    @staticmethod
    def process_image(file, category='profiles', max_size=(300, 300), quality=85):
        """Process and resize image"""
        img = Image.open(file)
        
        # Convert to RGB if necessary (handles RGBA, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # For profile images, handle aspect ratio better
        if category == 'profiles':
            # Calculate aspect ratios
            img_ratio = img.width / img.height
            target_ratio = max_size[0] / max_size[1]
            
            if img_ratio > target_ratio:
                # Image is wider - crop from sides
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                right = left + new_width
                img = img.crop((left, 0, right, img.height))
            elif img_ratio < target_ratio:
                # Image is taller - crop from top/bottom
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                bottom = top + new_height
                img = img.crop((0, top, img.width, bottom))
            # If ratios are equal, no cropping needed
        
        # Resize image
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return output
    
    @staticmethod
    def save_image_filesystem(file, category='profiles'):
        """Save image to filesystem (D: drive)"""
        try:
            # Validate image
            is_valid, message = ImageStorageManager.validate_image(file)
            if not is_valid:
                return None, message
            
            # Process image
            processed_image = ImageStorageManager.process_image(file, category)
            
            # Generate unique filename
            random_hex = secrets.token_hex(16)
            filename = f"{random_hex}.jpg"
            
            # Create category directory if it doesn't exist
            storage_path = ImageStorageManager.get_storage_path()
            category_path = os.path.join(storage_path, category)
            os.makedirs(category_path, exist_ok=True)
            
            # Save file
            file_path = os.path.join(category_path, filename)
            with open(file_path, 'wb') as f:
                f.write(processed_image.getvalue())
            
            return filename, "Image saved successfully"
            
        except Exception as e:
            return None, f"Error saving image: {str(e)}"
    
    @staticmethod
    def save_image_database(file, category='profiles'):
        """Save image to database as BLOB"""
        try:
            # Validate image
            is_valid, message = ImageStorageManager.validate_image(file)
            if not is_valid:
                return None, message
            
            # Process image
            processed_image = ImageStorageManager.process_image(file, category)
            
            # Convert to base64 for database storage
            image_data = base64.b64encode(processed_image.getvalue()).decode('utf-8')
            
            # Generate unique ID
            unique_id = secrets.token_hex(16)
            
            # Save to database
            from recipe_app.models.models import ImageStorage
            db_image = ImageStorage(
                id=unique_id,
                category=category,
                filename=file.filename,
                data=image_data,
                mime_type='image/jpeg'
            )
            db.session.add(db_image)
            db.session.commit()
            
            return unique_id, "Image saved to database successfully"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Error saving image to database: {str(e)}"
    
    @staticmethod
    def save_image(file, category='profiles'):
        """Save image using configured storage method"""
        storage_type = ImageStorageManager.get_storage_type()
        
        if storage_type == 'database':
            return ImageStorageManager.save_image_database(file, category)
        else:
            return ImageStorageManager.save_image_filesystem(file, category)
    
    @staticmethod
    def get_image_url(filename, category='profiles'):
        """Get URL for image based on storage type"""
        if not filename:
            return None
        
        storage_type = ImageStorageManager.get_storage_type()
        
        if storage_type == 'database':
            return url_for('main.serve_image', image_id=filename)
        else:
            return url_for('main.serve_filesystem_image', category=category, filename=filename)
    
    @staticmethod
    def delete_image(filename, category='profiles'):
        """Delete image from storage"""
        if not filename:
            return True
        
        storage_type = ImageStorageManager.get_storage_type()
        
        try:
            if storage_type == 'database':
                from recipe_app.models.models import ImageStorage
                db_image = ImageStorage.query.get(filename)
                if db_image:
                    db.session.delete(db_image)
                    db.session.commit()
            else:
                storage_path = ImageStorageManager.get_storage_path()
                file_path = os.path.join(storage_path, category, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return True
        except Exception as e:
            print(f"Error deleting image {filename}: {e}")
            return False


class ImageOptimizer:
    """Additional image optimization utilities"""
    
    @staticmethod
    def create_thumbnail(image_data, size=(150, 150)):
        """Create thumbnail from image data"""
        img = Image.open(BytesIO(image_data))
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=80, optimize=True)
        return output.getvalue()
    
    @staticmethod
    def create_webp_version(image_data, quality=80):
        """Create WebP version for better compression"""
        img = Image.open(BytesIO(image_data))
        
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, optimize=True)
        return output.getvalue()
