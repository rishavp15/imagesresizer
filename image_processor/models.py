from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
import uuid
import os
import re
import time

def cloudinary_upload_path(instance, filename):
    """Generate upload path for Cloudinary storage"""
    # Use session ID to organize files (shortened)
    session_id = str(instance.session.session_id)[:8] if instance.session else 'orphaned'
    
    # Clean filename - remove special characters and spaces, keep it short
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    
    # Clean the base name - remove special characters and replace spaces with underscores
    clean_base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
    clean_base_name = re.sub(r'_+', '_', clean_base_name)  # Replace multiple underscores with single
    clean_base_name = clean_base_name.strip('_')  # Remove leading/trailing underscores
    
    # Truncate base name to keep path short
    if len(clean_base_name) > 20:
        clean_base_name = clean_base_name[:20]
    
    # Add short timestamp to avoid conflicts
    timestamp = int(time.time()) % 1000000  # Use modulo to keep it shorter
    clean_name = f"{clean_base_name}_{timestamp}{ext}"
    
    # Create a shorter path structure for Cloudinary
    upload_path = f"img/{session_id}/{clean_name}"
    return upload_path

class ImageProcessingSession(models.Model):
    """Model to group multiple image processing requests"""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Session {self.session_id}"

class ImageProcessingRequest(models.Model):
    UNIT_CHOICES = [
        ('pixels', 'Pixels'),
        ('cm', 'Centimeters'),
        ('inch', 'Inches'),
    ]
    
    OUTPUT_FILE_TYPE_CHOICES = [
        ('jpg', 'JPG'),
        ('png', 'PNG'),
        ('webp', 'WebP'),
        ('bmp', 'BMP'),
        ('tiff', 'TIFF'),
    ]
    
    session = models.ForeignKey(ImageProcessingSession, on_delete=models.CASCADE, related_name='images')
    
    # Use default storage configuration from settings
    original_image = models.ImageField(upload_to=cloudinary_upload_path)
    processed_image = models.ImageField(upload_to=cloudinary_upload_path, null=True, blank=True)
    
    # Output file type
    output_file_type = models.CharField(max_length=4, choices=OUTPUT_FILE_TYPE_CHOICES, default='jpg', help_text="Output file format")
    
    # Output dimensions
    output_width = models.PositiveIntegerField(help_text="Width in pixels")
    output_height = models.PositiveIntegerField(help_text="Height in pixels")
    
    # Original dimensions (for comparison)
    original_width = models.PositiveIntegerField(null=True, blank=True, help_text="Original width in pixels")
    original_height = models.PositiveIntegerField(null=True, blank=True, help_text="Original height in pixels")
    original_file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Original file size in bytes")
    
    # Unit and physical dimensions (optional)
    dimension_unit = models.CharField(max_length=8, choices=UNIT_CHOICES, default='pixels', blank=True)
    dimension_width = models.FloatField(null=True, blank=True)
    dimension_height = models.FloatField(null=True, blank=True)
    
    # DPI settings
    dpi = models.PositiveIntegerField(default=300, help_text="Dots per inch")
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # File information
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.original_filename} - {self.output_width}x{self.output_height}"
    
    def save(self, *args, **kwargs):
        if self.original_image and not self.original_filename:
            # Extract filename from the uploaded file name
            if hasattr(self.original_image, 'name'):
                # For Cloudinary, the name might be a full path, so get the basename
                self.original_filename = os.path.basename(self.original_image.name)
            else:
                # Fallback if no name attribute
                self.original_filename = "uploaded_image"
        
        # Validate dimensions
        if self.output_width <= 0 or self.output_height <= 0:
            raise ValueError("Output dimensions must be positive")
        
        # Validate DPI
        if self.dpi is None or self.dpi <= 0:
            self.dpi = 300  # Default to 300 if invalid or None
        
        # Validate physical dimensions if provided
        if self.dimension_width is not None and self.dimension_height is not None:
            if self.dimension_width <= 0 or self.dimension_height <= 0:
                raise ValueError("Physical dimensions must be positive")
        
        super().save(*args, **kwargs)

@receiver(pre_delete, sender=ImageProcessingSession)
def delete_session_files(sender, instance, **kwargs):
    """
    Delete all files associated with a session before deleting the session
    Note: With Cloudinary storage, files are automatically managed by the cloud provider
    """
    # With Cloudinary storage, we don't need to manually delete files
    # The cloud storage provider handles file cleanup automatically
    pass

@receiver(pre_delete, sender=ImageProcessingRequest)
def delete_request_files(sender, instance, **kwargs):
    """
    Delete files associated with an image request before deleting the request
    Note: With Cloudinary storage, files are automatically managed by the cloud provider
    """
    # With Cloudinary storage, we don't need to manually delete files
    # The cloud storage provider handles file cleanup automatically
    pass
