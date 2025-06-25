from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import uuid
import os

def upload_to_images(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    # For Cloudinary, just return the filename without path joining
    return f"uploads/{filename}"

def upload_to_processed(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"processed_{uuid.uuid4()}.{ext}"
    # For Cloudinary, just return the filename without path joining
    return f"processed/{filename}"

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
    original_image = models.ImageField(upload_to=upload_to_images)
    processed_image = models.ImageField(upload_to=upload_to_processed, null=True, blank=True)
    
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
            self.original_filename = self.original_image.name.split('/')[-1]
        
        # Validate dimensions
        if self.output_width <= 0 or self.output_height <= 0:
            raise ValueError("Output dimensions must be positive")
        
        # Validate DPI
        if self.dpi <= 0:
            self.dpi = 300  # Default to 300 if invalid
        
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
