from PIL import Image, ImageEnhance
import io
import os
from django.core.files.base import ContentFile
from django.utils import timezone
import zipfile
import tempfile

# Preset configurations for common use cases
PRESET_SIZES = {
    # Social Media Presets
    'instagram_post': {'width': 1080, 'height': 1080, 'name': 'Instagram Post (Square)', 'category': 'Social Media'},
    'instagram_story': {'width': 1080, 'height': 1920, 'name': 'Instagram Story', 'category': 'Social Media'},
    'facebook_post': {'width': 1200, 'height': 630, 'name': 'Facebook Post', 'category': 'Social Media'},
    'facebook_cover': {'width': 1640, 'height': 859, 'name': 'Facebook Cover', 'category': 'Social Media'},
    'twitter_post': {'width': 1024, 'height': 512, 'name': 'Twitter Post', 'category': 'Social Media'},
    'linkedin_post': {'width': 1200, 'height': 627, 'name': 'LinkedIn Post', 'category': 'Social Media'},
    'youtube_thumbnail': {'width': 1280, 'height': 720, 'name': 'YouTube Thumbnail', 'category': 'Social Media'},
    
    # Web Presets
    'web_small': {'width': 800, 'height': 600, 'name': 'Web Small', 'category': 'Web'},
    'web_medium': {'width': 1280, 'height': 720, 'name': 'Web Medium (HD)', 'category': 'Web'},
    'web_large': {'width': 1920, 'height': 1080, 'name': 'Web Large (Full HD)', 'category': 'Web'},
    'web_4k': {'width': 3840, 'height': 2160, 'name': 'Web 4K', 'category': 'Web'},
    
    # Print Presets
    'print_4x6': {'width': 1800, 'height': 1200, 'name': '4×6 inch Print (300 DPI)', 'category': 'Print'},
    'print_5x7': {'width': 2100, 'height': 1500, 'name': '5×7 inch Print (300 DPI)', 'category': 'Print'},
    'print_8x10': {'width': 3000, 'height': 2400, 'name': '8×10 inch Print (300 DPI)', 'category': 'Print'},
    'print_a4': {'width': 2480, 'height': 3508, 'name': 'A4 Print (300 DPI)', 'category': 'Print'},
    
    # Email/Mobile Presets
    'email_small': {'width': 600, 'height': 400, 'name': 'Email Attachment (Small)', 'category': 'Email/Mobile'},
    'email_medium': {'width': 1024, 'height': 768, 'name': 'Email Attachment (Medium)', 'category': 'Email/Mobile'},
    'mobile_wallpaper': {'width': 1080, 'height': 1920, 'name': 'Mobile Wallpaper', 'category': 'Email/Mobile'},
    'desktop_wallpaper': {'width': 1920, 'height': 1080, 'name': 'Desktop Wallpaper', 'category': 'Email/Mobile'},
    
    # Custom Size Categories
    'thumbnail': {'width': 300, 'height': 300, 'name': 'Thumbnail', 'category': 'Other'},
    'avatar': {'width': 512, 'height': 512, 'name': 'Avatar/Profile Picture', 'category': 'Other'},
}

# File size processing - users can now specify any KB value directly

def process_image(image_request):
    """
    Process a single image according to the specifications
    """
    try:
        # Validate input parameters
        if not image_request.original_image:
            return False, "No original image provided"
        
        if image_request.output_width <= 0 or image_request.output_height <= 0:
            return False, "Invalid output dimensions"
        
        if image_request.dpi <= 0:
            return False, "Invalid DPI value"
        
        # Open the original image
        with Image.open(image_request.original_image.path) as img:
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize the image
            resized_img = img.resize(
                (image_request.output_width, image_request.output_height),
                Image.Resampling.LANCZOS
            )
            
            # Calculate DPI based on physical dimensions if provided
            dpi_value = image_request.dpi
            if image_request.dimension_width and image_request.dimension_height:
                try:
                    # Convert physical dimensions to inches if in cm
                    if image_request.dimension_unit == 'cm':
                        width_inches = image_request.dimension_width / 2.54
                        height_inches = image_request.dimension_height / 2.54
                    else:
                        width_inches = image_request.dimension_width
                        height_inches = image_request.dimension_height
                    
                    # Validate physical dimensions
                    if width_inches <= 0 or height_inches <= 0:
                        return False, "Invalid physical dimensions"
                    
                    # Calculate DPI based on pixel dimensions and physical dimensions
                    width_dpi = image_request.output_width / width_inches
                    height_dpi = image_request.output_height / height_inches
                    dpi_value = int(min(width_dpi, height_dpi))
                    
                    # Validate calculated DPI
                    if dpi_value <= 0:
                        dpi_value = image_request.dpi  # Fallback to original DPI
                        
                except (ValueError, ZeroDivisionError):
                    dpi_value = image_request.dpi  # Fallback to original DPI
            
            # Save the processed image
            output_buffer = io.BytesIO()
            resized_img.save(
                output_buffer, 
                format='JPEG', 
                quality=95,
                dpi=(dpi_value, dpi_value),
                optimize=True
            )
            
            # Create filename for processed image
            original_name = os.path.splitext(image_request.original_filename)[0]
            processed_filename = f"{original_name}_resized_{image_request.output_width}x{image_request.output_height}.jpg"
            
            # Save to model
            image_request.processed_image.save(
                processed_filename,
                ContentFile(output_buffer.getvalue()),
                save=False
            )
            
            # Update processing status
            image_request.is_processed = True
            image_request.processed_at = timezone.now()
            image_request.file_size = len(output_buffer.getvalue())
            image_request.save()
            
            return True, "Image processed successfully"
            
    except Exception as e:
        return False, f"Error processing image: {str(e)}"

def create_zip_file(session):
    """
    Create a ZIP file containing all processed images from a session
    """
    try:
        # Create a temporary file for the ZIP
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            processed_images = session.images.filter(is_processed=True)
            
            for img_request in processed_images:
                if img_request.processed_image:
                    # Get the filename from the processed image
                    filename = os.path.basename(img_request.processed_image.name)
                    
                    # Add file to ZIP
                    zip_file.write(
                        img_request.processed_image.path,
                        filename
                    )
        
        # Read the ZIP file content
        with open(temp_zip.name, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Clean up temporary file
        os.unlink(temp_zip.name)
        
        return zip_content, f"images_session_{session.session_id}.zip"
        
    except Exception as e:
        return None, f"Error creating ZIP file: {str(e)}"

def validate_image_file(file):
    """
    Validate uploaded image file
    """
    try:
        # Check file size (max 10MB)
        if file.size > 10 * 1024 * 1024:
            return False, "File size must be less than 10MB"
        
        # Check if it's a valid image
        img = Image.open(file)
        img.verify()
        
        # Check format
        if img.format.lower() not in ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'tiff']:
            return False, "Unsupported image format"
        
        return True, "Valid image file"
        
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"

def get_image_info(image_file):
    """
    Get basic information about an uploaded image file
    """
    try:
        print(f"[DEBUG] get_image_info: processing file {image_file.name}")
        print(f"[DEBUG] File size: {image_file.size} bytes")
        
        # Open the image to get dimensions
        with Image.open(image_file) as img:
            width, height = img.size
            print(f"[DEBUG] Image dimensions: {width}x{height}, mode: {img.mode}")
            
            return {
                'width': width,
                'height': height,
                'size': image_file.size,
                'format': img.format,
                'mode': img.mode
            }
    except Exception as e:
        print(f"[DEBUG] Error in get_image_info: {e}")
        import traceback
        traceback.print_exc()
        raise

def calculate_optimal_dimensions(original_width, original_height, max_width=None, max_height=None):
    """
    Calculate optimal dimensions while maintaining aspect ratio
    """
    if not max_width and not max_height:
        return original_width, original_height
    
    aspect_ratio = original_width / original_height
    
    if max_width and max_height:
        # Fit within both constraints
        if original_width / max_width > original_height / max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
    elif max_width:
        new_width = max_width
        new_height = int(max_width / aspect_ratio)
    else:
        new_height = max_height
        new_width = int(max_height * aspect_ratio)
    
    return max(1, new_width), max(1, new_height)

def get_preset_categories():
    """Get presets organized by category"""
    categories = {}
    for key, preset in PRESET_SIZES.items():
        category = preset['category']
        if category not in categories:
            categories[category] = []
        categories[category].append({
            'key': key,
            'name': preset['name'],
            'width': preset['width'],
            'height': preset['height']
        })
    return categories

def find_optimal_quality(img, target_size_bytes, dpi_value):
    """
    Find the optimal JPEG quality to meet the target file size using binary search.
    """
    try:
        print(f"[DEBUG] find_optimal_quality: target_size={target_size_bytes}, dpi={dpi_value}")
        low = 1
        high = 100
        best_quality = -1
        best_image_buffer = None

        while low <= high:
            quality = (low + high) // 2
            print(f"[DEBUG] Testing quality: {quality}")
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, dpi=(dpi_value, dpi_value), optimize=True)
            size = buffer.tell()
            
            print(f"[DEBUG] Quality {quality} produced size: {size} bytes")

            if size <= target_size_bytes:
                best_quality = quality
                best_image_buffer = buffer
                low = quality + 1
            else:
                high = quality - 1
                
        print(f"[DEBUG] Best quality found: {best_quality}")
        return best_image_buffer, best_quality
        
    except Exception as e:
        print(f"[DEBUG] Error in find_optimal_quality: {e}")
        import traceback
        traceback.print_exc()
        return None, -1

def process_image_with_size_limit(image_request, target_size_bytes):
    """
    Process image to meet a target file size.
    """
    try:
        print(f"[DEBUG] Starting process_image_with_size_limit for {image_request.original_filename}")
        print(f"[DEBUG] Target size: {target_size_bytes} bytes")
        
        with Image.open(image_request.original_image.path) as img:
            print(f"[DEBUG] Opened image: {img.size}, mode: {img.mode}")
            
            if img.mode != 'RGB':
                print(f"[DEBUG] Converting image from {img.mode} to RGB")
                img = img.convert('RGB')

            # Resize the image to the requested output dimensions
            print(f"[DEBUG] Resizing to {image_request.output_width}x{image_request.output_height}")
            resized_img = img.resize(
                (image_request.output_width, image_request.output_height),
                Image.Resampling.LANCZOS
            )

            # Calculate DPI
            dpi_value = image_request.dpi
            if image_request.dimension_width and image_request.dimension_height:
                if image_request.dimension_unit == 'cm':
                    width_inches = image_request.dimension_width / 2.54
                    height_inches = image_request.dimension_height / 2.54
                else:
                    width_inches = image_request.dimension_width
                    height_inches = image_request.dimension_height
                
                if width_inches > 0 and height_inches > 0:
                    width_dpi = image_request.output_width / width_inches
                    height_dpi = image_request.output_height / height_inches
                    dpi_value = int(min(width_dpi, height_dpi))
            
            print(f"[DEBUG] Using DPI: {dpi_value}")

            # Find the best quality setting for the target size
            print(f"[DEBUG] Finding optimal quality for target size {target_size_bytes}")
            output_buffer, final_quality = find_optimal_quality(resized_img, target_size_bytes, dpi_value)

            if not output_buffer:
                print(f"[DEBUG] Could not meet target file size {target_size_bytes}")
                return False, "Could not meet the file size target. Try a larger size."

            print(f"[DEBUG] Found optimal quality: {final_quality}")
            print(f"[DEBUG] Final buffer size: {output_buffer.tell()} bytes")

            # Save the processed image
            original_name = os.path.splitext(image_request.original_filename)[0]
            processed_filename = f"{original_name}_resized_{image_request.output_width}x{image_request.output_height}.jpg"
            
            print(f"[DEBUG] Saving processed image as: {processed_filename}")
            image_request.processed_image.save(
                processed_filename,
                ContentFile(output_buffer.getvalue()),
                save=False
            )
            
            image_request.is_processed = True
            image_request.processed_at = timezone.now()
            image_request.file_size = output_buffer.tell()
            image_request.save()

            print(f"[DEBUG] Successfully processed image with size: {output_buffer.tell()} bytes")
            return True, "Image processed successfully."

    except Exception as e:
        print(f"[DEBUG] Error in process_image_with_size_limit: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error processing image: {str(e)}"

def optimize_image_size(img, image_request, target_size_bytes, dpi_value):
    """
    Intelligent image size optimization using binary search and smart heuristics.
    Prioritizes user-defined dimensions.
    """
    user_width = image_request.output_width
    user_height = image_request.output_height

    # The primary strategy is to adjust quality to meet the target size
    # at the dimensions specified by the user.
    result = try_quality_optimization(img, user_width, user_height, target_size_bytes, dpi_value)

    # If the result from quality optimization is within the target size, that's perfect.
    if result and result[2] <= target_size_bytes:
        return result

    # If the user specified dimensions, and even the lowest quality at those dimensions
    # results in a file larger than the target, we should still respect the dimensions
    # and return the best effort. The new `try_quality_optimization` will provide this.
    if user_width and user_height:
        return result

    # Fallback to dimension reduction only if the user did NOT specify dimensions.
    # This part of the logic is preserved for future flexibility but may not be
    # reached with the current UI, which always provides dimensions.
    aspect_ratio = user_width / user_height
    best_result = try_smart_dimension_reduction(img, user_width, user_height, target_size_bytes, dpi_value, aspect_ratio)
    if best_result:
        return best_result
    
    # Final fallback to aggressive optimization.
    return try_aggressive_optimization(img, user_width, user_height, target_size_bytes, dpi_value, aspect_ratio)

def try_quality_optimization(img, width, height, target_size_bytes, dpi_value):
    """
    Try to achieve target size by adjusting quality only.
    Uses binary search for optimal quality.
    Returns the best result that is under the target size, or if that's not
    possible, returns the result with the lowest possible quality (smallest size).
    """
    low_quality, high_quality = 10, 95
    best_result_under_target = None
    best_size_diff = float('inf')

    # Keep track of the result with the lowest size in case we never get under the target.
    result_at_lowest_quality = None

    # It's more efficient to resize once before the loop.
    try:
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
    except ValueError:
        # This can happen if dimensions are invalid (e.g., zero or negative)
        # We should handle this gracefully.
        return None 

    # Check lowest quality first to get a baseline for smallest possible size
    output_buffer = io.BytesIO()
    resized_img.save(
        output_buffer,
        format='JPEG',
        quality=low_quality,
        dpi=(dpi_value, dpi_value),
        optimize=True
    )
    result_at_lowest_quality = (output_buffer.getvalue(), low_quality, len(output_buffer.getvalue()), width, height)


    while low_quality <= high_quality:
        mid_quality = (low_quality + high_quality) // 2
        
        output_buffer = io.BytesIO()
        resized_img.save(
            output_buffer,
            format='JPEG',
            quality=mid_quality,
            dpi=(dpi_value, dpi_value),
            optimize=True
        )
        
        current_size = len(output_buffer.getvalue())
        
        if current_size <= target_size_bytes:
            # This is a potential candidate for the best result under the target.
            size_diff = target_size_bytes - current_size
            if size_diff < best_size_diff:
                best_result_under_target = (output_buffer.getvalue(), mid_quality, current_size, width, height)
                best_size_diff = size_diff
            
            # We might be able to get a slightly larger file that is still under
            # the target, which means higher quality. So we search upwards.
            low_quality = mid_quality + 1
        else:
            # File is too big, need to reduce quality.
            high_quality = mid_quality - 1
    
    # If we found a result that meets the target, return it. Otherwise, return the smallest file we could create.
    return best_result_under_target if best_result_under_target is not None else result_at_lowest_quality

def try_smart_dimension_reduction(img, original_width, original_height, target_size_bytes, dpi_value, aspect_ratio):
    """
    Smart dimension reduction with quality optimization
    """
    # Calculate optimal starting dimensions based on target size
    target_pixels = estimate_pixels_for_size(target_size_bytes)
    scale_factor = min(1.0, (target_pixels / (original_width * original_height)) ** 0.5)
    
    # Try different scale factors around the estimated optimal
    scale_factors = [
        scale_factor * 1.2, scale_factor * 1.1, scale_factor, 
        scale_factor * 0.9, scale_factor * 0.8, scale_factor * 0.7
    ]
    
    best_result = None
    best_size_diff = float('inf')
    
    for scale in scale_factors:
        if scale > 1.0:
            continue
            
        new_width = max(100, int(original_width * scale))
        new_height = max(100, int(original_height * scale))
        
        # Try quality optimization for this dimension
        result = try_quality_optimization(img, new_width, new_height, target_size_bytes, dpi_value)
        if result:
            current_size = result[2]
            size_diff = abs(current_size - target_size_bytes)
            
            if current_size <= target_size_bytes and size_diff < best_size_diff:
                best_result = result
                best_size_diff = size_diff
            
            # If we're very close, stop early
            if current_size <= target_size_bytes * 1.02:
                break
    
    return best_result

def try_aggressive_optimization(img, original_width, original_height, target_size_bytes, dpi_value, aspect_ratio):
    """
    Aggressive optimization as final fallback
    """
    # Try very small dimensions with low quality
    scale_factors = [0.5, 0.4, 0.3, 0.2]
    qualities = [30, 25, 20, 15]
    
    best_result = None
    best_size_diff = float('inf')
    
    for scale in scale_factors:
        new_width = max(50, int(original_width * scale))
        new_height = max(50, int(original_height * scale))
        
        for quality in qualities:
            output_buffer = io.BytesIO()
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized_img.save(
                output_buffer,
                format='JPEG',
                quality=quality,
                dpi=(dpi_value, dpi_value),
                optimize=True
            )
            
            current_size = len(output_buffer.getvalue())
            size_diff = abs(current_size - target_size_bytes)
            
            if current_size <= target_size_bytes and size_diff < best_size_diff:
                best_result = (output_buffer.getvalue(), quality, current_size, new_width, new_height)
                best_size_diff = size_diff
    
    # If still no result, return the smallest possible
    if not best_result:
        output_buffer = io.BytesIO()
        resized_img = img.resize((50, int(50 / aspect_ratio)), Image.Resampling.LANCZOS)
        resized_img.save(
            output_buffer,
            format='JPEG',
            quality=10,
            dpi=(dpi_value, dpi_value),
            optimize=True
        )
        best_result = (output_buffer.getvalue(), 10, len(output_buffer.getvalue()), 50, int(50 / aspect_ratio))
    
    return best_result

def estimate_pixels_for_size(target_size_bytes):
    """
    Estimate how many pixels we need for a given file size
    Based on typical JPEG compression ratios
    """
    # Rough estimation: 1 pixel ≈ 0.1-0.3 bytes depending on content
    # For conservative estimate, use 0.2 bytes per pixel
    return int(target_size_bytes * 5)  # 1/0.2 = 5 