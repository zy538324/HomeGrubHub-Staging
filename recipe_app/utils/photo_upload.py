"""
Photo Upload Service for Recipe Images
Handles image upload, processing, and storage
"""

import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app, request
from typing import Optional, Tuple, List, Dict
import base64
import io

class PhotoUploadService:
    """Service for handling recipe photo uploads"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Image sizes for different uses
    SIZES = {
        'thumbnail': (150, 150),
        'medium': (400, 400),
        'large': (800, 800),
        'original': None  # Keep original size
    }
    
    def __init__(self):
        self.upload_folder = os.path.join(current_app.root_path, 'static', 'recipe_images')
        self.ensure_upload_directory()
    
    def ensure_upload_directory(self):
        """Ensure upload directory exists"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder, exist_ok=True)
            
        # Create subdirectories for different sizes
        for size_name in self.SIZES.keys():
            size_dir = os.path.join(self.upload_folder, size_name)
            if not os.path.exists(size_dir):
                os.makedirs(size_dir, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def upload_recipe_image(self, file, recipe_id: int) -> Optional[Dict]:
        """
        Upload and process recipe image
        
        Args:
            file: Flask file upload object
            recipe_id: ID of the recipe
            
        Returns:
            dict: Information about uploaded images or None if failed
        """
        try:
            # Validate file
            if not file or file.filename == '':
                return None
                
            if not self.allowed_file(file.filename):
                return None
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > self.MAX_FILE_SIZE:
                return None
            
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{recipe_id}_{uuid.uuid4().hex}.{file_extension}"
            
            # Process and save images in different sizes
            image_paths = self._process_and_save_image(file, unique_filename)
            
            return {
                'filename': unique_filename,
                'paths': image_paths,
                'file_size': file_size,
                'extension': file_extension
            }
            
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None
    
    def upload_base64_image(self, base64_data: str, recipe_id: int) -> Optional[Dict]:
        """
        Upload image from base64 data (useful for camera capture)
        
        Args:
            base64_data: Base64 encoded image data
            recipe_id: ID of the recipe
            
        Returns:
            dict: Information about uploaded images or None if failed
        """
        try:
            # Parse base64 data
            if ',' in base64_data:
                header, data = base64_data.split(',', 1)
            else:
                data = base64_data
                header = ''
            
            # Decode image
            image_data = base64.b64decode(data)
            image = Image.open(io.BytesIO(image_data))
            
            # Determine format
            image_format = image.format.lower() if image.format else 'jpeg'
            if image_format == 'jpeg':
                extension = 'jpg'
            else:
                extension = image_format
            
            # Generate unique filename
            unique_filename = f"{recipe_id}_{uuid.uuid4().hex}.{extension}"
            
            # Convert to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Process and save images
            image_paths = self._process_and_save_pil_image(image, unique_filename)
            
            return {
                'filename': unique_filename,
                'paths': image_paths,
                'file_size': len(image_data),
                'extension': extension
            }
            
        except Exception as e:
            print(f"Error uploading base64 image: {e}")
            return None
    
    def _process_and_save_image(self, file, filename: str) -> Dict:
        """Process uploaded file and save in multiple sizes"""
        # Open image
        image = Image.open(file)
        return self._process_and_save_pil_image(image, filename)
    
    def _process_and_save_pil_image(self, image: Image.Image, filename: str) -> Dict:
        """Process PIL image and save in multiple sizes"""
        image_paths = {}
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        for size_name, dimensions in self.SIZES.items():
            try:
                # Create size-specific directory path
                size_dir = os.path.join(self.upload_folder, size_name)
                file_path = os.path.join(size_dir, filename)
                
                if dimensions:
                    # Resize image maintaining aspect ratio
                    resized_image = self._resize_image(image, dimensions)
                else:
                    # Original size
                    resized_image = image
                
                # Save image
                resized_image.save(file_path, 'JPEG', quality=85, optimize=True)
                
                # Store relative path for web access
                relative_path = f"recipe_images/{size_name}/{filename}"
                image_paths[size_name] = relative_path
                
            except Exception as e:
                print(f"Error saving {size_name} image: {e}")
        
        return image_paths
    
    def _resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize image maintaining aspect ratio"""
        # Calculate new size maintaining aspect ratio
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Create new image with desired size and paste resized image centered
        new_image = Image.new('RGB', size, (255, 255, 255))
        
        # Calculate position to center the image
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        
        new_image.paste(image, (x, y))
        return new_image
    
    def delete_recipe_images(self, filename: str) -> bool:
        """Delete all sizes of a recipe image"""
        try:
            for size_name in self.SIZES.keys():
                file_path = os.path.join(self.upload_folder, size_name, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting images: {e}")
            return False
    
    def get_image_url(self, filename: str, size: str = 'medium') -> Optional[str]:
        """Get URL for recipe image"""
        if not filename:
            return None
            
        if size not in self.SIZES:
            size = 'medium'
            
        return f"/static/recipe_images/{size}/{filename}"
    
    def validate_image_data(self, data: bytes) -> bool:
        """Validate if data is a valid image"""
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            return True
        except Exception:
            return False
