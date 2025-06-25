from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import connection
import json
import mimetypes
import os
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import io
from datetime import date

from .models import ImageProcessingSession, ImageProcessingRequest
from .forms import BulkImageProcessingForm
from .utils import (
    process_image, create_zip_file, validate_image_file, get_image_info,
    get_preset_categories, PRESET_SIZES, process_image_with_size_limit
)

def home(request):
    """
    Home page with bulk image upload form
    """
    try:
        # Test database connection
        database_available = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                print("[DEBUG] Database connection successful")
        except Exception as db_error:
            print(f"[DEBUG] Database connection failed: {db_error}")
            database_available = False
            messages.warning(request, "Database is temporarily unavailable. Some features may not work.")
        
        # Test file system access
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                temp_file.write(b"test")
                temp_file.flush()
                print("[DEBUG] File system access successful")
        except Exception as fs_error:
            print(f"[DEBUG] File system access failed: {fs_error}")
            messages.error(request, "File system access error. Please try again later.")
            return render(request, 'image_processor/home.html', {
                'form': BulkImageProcessingForm(num_images=1),
                'num_images': 1,
                'max_images': 20,
                'preset_categories': get_preset_categories(),
                'presets_json': json.dumps(PRESET_SIZES),
            })
        
        # Test Pillow library
        try:
            from PIL import Image
            # Create a simple test image
            test_img = Image.new('RGB', (10, 10), color='red')
            test_buffer = io.BytesIO()
            test_img.save(test_buffer, format='JPEG')
            print("[DEBUG] Pillow library test successful")
        except Exception as pillow_error:
            print(f"[DEBUG] Pillow library test failed: {pillow_error}")
            messages.error(request, "Image processing library error. Please try again later.")
            return render(request, 'image_processor/home.html', {
                'form': BulkImageProcessingForm(num_images=1),
                'num_images': 1,
                'max_images': 20,
                'preset_categories': get_preset_categories(),
                'presets_json': json.dumps(PRESET_SIZES),
            })
        
        # Debug environment variables
        print(f"[DEBUG] VERCEL environment: {os.environ.get('VERCEL', 'Not set')}")
        print(f"[DEBUG] DEBUG setting: {os.environ.get('DEBUG', 'Not set')}")
        print(f"[DEBUG] DATABASE_URL present: {'DATABASE_URL' in os.environ}")
        print(f"[DEBUG] SECRET_KEY present: {'SECRET_KEY' in os.environ}")
        print(f"[DEBUG] CLOUDINARY_CLOUD_NAME present: {'CLOUDINARY_CLOUD_NAME' in os.environ}")
        
        # Test file storage
        try:
            from django.conf import settings
            print(f"[DEBUG] MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'Not set')}")
            print(f"[DEBUG] STATIC_ROOT: {getattr(settings, 'STATIC_ROOT', 'Not set')}")
            print(f"[DEBUG] DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        except Exception as storage_error:
            print(f"[DEBUG] Error getting storage settings: {storage_error}")
        
        # Debug URL routing
        print(f"[DEBUG] Request path: {request.path}")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] Request host: {request.get_host()}")
        print(f"[DEBUG] Request scheme: {request.scheme}")
        
        # Debug middleware
        try:
            from django.conf import settings
            print(f"[DEBUG] MIDDLEWARE: {getattr(settings, 'MIDDLEWARE', 'Not set')}")
        except Exception as middleware_error:
            print(f"[DEBUG] Error getting middleware settings: {middleware_error}")
        
        num_images = int(request.GET.get('num_images', 1))
        
        if request.method == 'POST':
            print(f"[DEBUG] Processing POST request with {num_images} images")
            print(f"[DEBUG] POST data keys: {list(request.POST.keys())}")
            print(f"[DEBUG] FILES keys: {list(request.FILES.keys())}")
            print(f"[DEBUG] CSRF token present: {'csrfmiddlewaretoken' in request.POST}")
            
            form = BulkImageProcessingForm(request.POST, request.FILES, num_images=num_images)
            
            if form.is_valid():
                print("[DEBUG] Form is valid, creating session")
                print(f"[DEBUG] Form cleaned data keys: {list(form.cleaned_data.keys())}")
                
                # Check if database is available
                if not database_available:
                    # Try in-memory processing without database
                    print("[DEBUG] Attempting in-memory processing without database")
                    try:
                        # Process images in memory and return them directly
                        processed_images = []
                        for i in range(num_images):
                            image_field = f'image_{i}'
                            
                            if image_field in request.FILES:
                                image_file = request.FILES[image_field]
                                
                                # Validate image
                                is_valid, message = validate_image_file(image_file)
                                if not is_valid:
                                    messages.error(request, f"Image {i+1}: {message}")
                                    continue
                                
                                # Get original image information
                                try:
                                    original_info = get_image_info(image_file)
                                except Exception as e:
                                    messages.error(request, f"Image {i+1}: Error reading image information")
                                    continue
                                
                                # Get target file size
                                target_file_size_kb = form.cleaned_data.get(f'target_file_size_kb_{i}')
                                
                                if target_file_size_kb and target_file_size_kb > 0:
                                    # Process with target file size
                                    try:
                                        from PIL import Image
                                        import io
                                        
                                        # Open and process image
                                        with Image.open(image_file) as img:
                                            if img.mode != 'RGB':
                                                img = img.convert('RGB')
                                            
                                            # Get dimensions (use original if not specified)
                                            width = form.cleaned_data.get(f'output_width_{i}', img.width)
                                            height = form.cleaned_data.get(f'output_height_{i}', img.height)
                                            
                                            # Resize image
                                            resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
                                            
                                            # Find optimal quality for target size
                                            target_size_bytes = target_file_size_kb * 1024
                                            low, high = 1, 100
                                            best_buffer = None
                                            
                                            while low <= high:
                                                quality = (low + high) // 2
                                                buffer = io.BytesIO()
                                                resized_img.save(buffer, format='JPEG', quality=quality, optimize=True)
                                                size = buffer.tell()
                                                
                                                if size <= target_size_bytes:
                                                    best_buffer = buffer
                                                    low = quality + 1
                                                else:
                                                    high = quality - 1
                                            
                                            if best_buffer:
                                                best_buffer.seek(0)
                                                processed_images.append({
                                                    'filename': f"{image_file.name.split('.')[0]}_resized_{width}x{height}.jpg",
                                                    'data': best_buffer.getvalue(),
                                                    'size': best_buffer.tell()
                                                })
                                            else:
                                                messages.error(request, f"Image {i+1}: Could not meet target file size")
                                                
                                    except Exception as e:
                                        messages.error(request, f"Image {i+1}: Processing error")
                                        continue
                                
                                else:
                                    # Process without target file size
                                    try:
                                        from PIL import Image
                                        import io
                                        
                                        with Image.open(image_file) as img:
                                            if img.mode != 'RGB':
                                                img = img.convert('RGB')
                                            
                                            width = form.cleaned_data.get(f'output_width_{i}', img.width)
                                            height = form.cleaned_data.get(f'output_height_{i}', img.height)
                                            
                                            resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
                                            
                                            buffer = io.BytesIO()
                                            resized_img.save(buffer, format='JPEG', quality=90, optimize=True)
                                            buffer.seek(0)
                                            
                                            processed_images.append({
                                                'filename': f"{image_file.name.split('.')[0]}_resized_{width}x{height}.jpg",
                                                'data': buffer.getvalue(),
                                                'size': buffer.tell()
                                            })
                                            
                                    except Exception as e:
                                        messages.error(request, f"Image {i+1}: Processing error")
                                        continue
                        
                        if processed_images:
                            # Create a ZIP file with processed images
                            import zipfile
                            import io
                            
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                                for img in processed_images:
                                    zip_file.writestr(img['filename'], img['data'])
                            
                            zip_buffer.seek(0)
                            
                            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                            response['Content-Disposition'] = 'attachment; filename="processed_images.zip"'
                            return response
                        else:
                            messages.error(request, "No images were processed successfully")
                            
                    except Exception as e:
                        print(f"[DEBUG] In-memory processing failed: {e}")
                        messages.error(request, "In-memory processing failed. Please try again later.")
                        
                    return render(request, 'image_processor/home.html', {
                        'form': form,
                        'num_images': num_images,
                        'max_images': 20,
                        'preset_categories': get_preset_categories(),
                        'presets_json': json.dumps(PRESET_SIZES),
                        'database_available': database_available,
                    })
                else:
                    # Create a new session
                    try:
                        session = ImageProcessingSession.objects.create()
                        print(f"[DEBUG] Created session with ID: {session.session_id}")
                    except Exception as session_error:
                        print(f"[DEBUG] Error creating session: {session_error}")
                        import traceback
                        traceback.print_exc()
                        messages.error(request, "Error creating processing session. Please try again.")
                        return render(request, 'image_processor/home.html', {
                            'form': form,
                            'num_images': num_images,
                            'max_images': 20,
                            'preset_categories': get_preset_categories(),
                            'presets_json': json.dumps(PRESET_SIZES),
                            'database_available': database_available,
                        })
                    
                    # Process each uploaded image
                    processed_count = 0
                    for i in range(num_images):
                        image_field = f'image_{i}'
                        
                        if image_field in request.FILES:
                            print(f"[DEBUG] Processing image {i+1}")
                            image_file = request.FILES[image_field]
                            
                            # Validate image
                            is_valid, message = validate_image_file(image_file)
                            if not is_valid:
                                print(f"[DEBUG] Image {i+1} validation failed: {message}")
                                messages.error(request, f"Image {i+1}: {message}")
                                continue
                            
                            # Get original image information
                            try:
                                original_info = get_image_info(image_file)
                                print(f"[DEBUG] Image {i+1} info: {original_info}")
                            except Exception as e:
                                print(f"[DEBUG] Error getting image info for {i+1}: {e}")
                                messages.error(request, f"Image {i+1}: Error reading image information")
                                continue
                            
                            # Get unit and dpi
                            unit = form.cleaned_data.get(f'dimension_unit_{i}', 'pixels')
                            dpi = form.cleaned_data.get(f'dpi_{i}')

                            # Ensure DPI has a value (default to 300 if not provided)
                            if dpi is None or dpi == '' or dpi <= 0:
                                dpi = 300
                            
                            width, height = None, None

                            try:
                                if unit == 'pixels':
                                    width = form.cleaned_data.get(f'output_width_{i}')
                                    height = form.cleaned_data.get(f'output_height_{i}')
                                    if not all([width, height]):
                                        messages.error(request, f"Image {i+1}: For pixel dimensions, please specify both width and height.")
                                        continue
                                elif unit == 'cm':
                                    dim_width = form.cleaned_data.get(f'cm_width_{i}')
                                    dim_height = form.cleaned_data.get(f'cm_height_{i}')
                                    if not all([dim_width, dim_height]):
                                        messages.error(request, f"Image {i+1}: For cm dimensions, please specify both width and height.")
                                        continue
                                    if dim_width <= 0 or dim_height <= 0:
                                        messages.error(request, f"Image {i+1}: Physical dimensions must be positive")
                                        continue
                                    width = int(round(dim_width * dpi / 2.54))
                                    height = int(round(dim_height * dpi / 2.54))
                                elif unit == 'inch':
                                    dim_width = form.cleaned_data.get(f'inch_width_{i}')
                                    dim_height = form.cleaned_data.get(f'inch_height_{i}')
                                    if not all([dim_width, dim_height]):
                                        messages.error(request, f"Image {i+1}: For inch dimensions, please specify both width and height.")
                                        continue
                                    if dim_width <= 0 or dim_height <= 0:
                                        messages.error(request, f"Image {i+1}: Physical dimensions must be positive")
                                        continue
                                    width = int(round(dim_width * dpi))
                                    height = int(round(dim_height * dpi))
                                
                                # Validate final dimensions
                                if not all([width, height]) or width <= 0 or height <= 0:
                                    messages.error(request, f"Image {i+1}: Invalid final dimensions calculated.")
                                    continue
                                    
                            except (ValueError, TypeError) as e:
                                print(f"[DEBUG] Error calculating dimensions for image {i+1}: {e}")
                                messages.error(request, f"Image {i+1}: Invalid dimension values")
                                continue
                            
                            # Create image processing request
                            try:
                                img_request = ImageProcessingRequest.objects.create(
                                    session=session,
                                    original_image=image_file,
                                    output_width=width,
                                    output_height=height,
                                    dpi=dpi,
                                    dimension_unit=unit,
                                    dimension_width=form.cleaned_data.get(f'cm_width_{i}') if unit == 'cm' else form.cleaned_data.get(f'inch_width_{i}'),
                                    dimension_height=form.cleaned_data.get(f'cm_height_{i}') if unit == 'cm' else form.cleaned_data.get(f'inch_height_{i}'),
                                    original_filename=image_file.name,
                                    original_width=original_info['width'],
                                    original_height=original_info['height'],
                                    original_file_size=original_info['size'],
                                )
                                print(f"[DEBUG] Created ImageProcessingRequest for image {i+1}")
                            except Exception as e:
                                print(f"[DEBUG] Error creating ImageProcessingRequest for image {i+1}: {e}")
                                messages.error(request, f"Image {i+1}: Error creating processing request")
                                continue
                            
                            # Check for file size target
                            target_file_size_kb = form.cleaned_data.get(f'target_file_size_kb_{i}')
                            
                            try:
                                if target_file_size_kb and target_file_size_kb > 0:
                                    print(f"[DEBUG] Processing image {i+1} with target file size: {target_file_size_kb} KB")
                                    target_size_bytes = target_file_size_kb * 1024
                                    success, error_message = process_image_with_size_limit(
                                        img_request,
                                        target_size_bytes=target_size_bytes
                                    )
                                else:
                                    print(f"[DEBUG] Processing image {i+1} with standard method")
                                    # Process with standard method
                                    success, error_message = process_image(img_request)
                                
                                if success:
                                    print(f"[DEBUG] Image {i+1} processed successfully")
                                    processed_count += 1
                                else:
                                    print(f"[DEBUG] Image {i+1} processing failed: {error_message}")
                                    messages.error(request, f"Image {i+1}: {error_message}")
                            except Exception as e:
                                print(f"[DEBUG] Error processing image {i+1}: {e}")
                                import traceback
                                traceback.print_exc()
                                messages.error(request, f"Image {i+1}: Processing error occurred")
                                continue
                    
                    if processed_count > 0:
                        print(f"[DEBUG] Successfully processed {processed_count} images")
                        messages.success(request, f"Successfully processed {processed_count} image(s)")
                        return redirect('processing_results', session_id=session.session_id)
                    else:
                        print("[DEBUG] No images were processed successfully")
                        messages.error(request, "No images were processed successfully")
                        session.delete()  # Clean up empty session
            else:
                print("[DEBUG] Form is invalid")
                print("Form errors:", form.errors)
                print("Form non-field errors:", form.non_field_errors())
                print(f"[DEBUG] Form data: {form.data}")
                print(f"[DEBUG] Form files: {form.files}")
                # Add form errors to messages for debugging
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Form error in {field}: {error}")
                for error in form.non_field_errors():
                    messages.error(request, f"Form error: {error}")
        else:
            form = BulkImageProcessingForm(num_images=num_images)
        
        context = {
            'form': form,
            'num_images': num_images,
            'max_images': 20,  # Maximum allowed images
            'preset_categories': get_preset_categories(),
            'presets_json': json.dumps(PRESET_SIZES),
            'database_available': database_available,
        }
        return render(request, 'image_processor/home.html', context)
    except Exception as e:
        print(f"[DEBUG] Unexpected error in home view: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, "An unexpected error occurred. Please try again.")
        form = BulkImageProcessingForm(num_images=1)
        context = {
            'form': form,
            'num_images': 1,
            'max_images': 20,
            'preset_categories': get_preset_categories(),
            'presets_json': json.dumps(PRESET_SIZES),
            'database_available': False,
        }
        return render(request, 'image_processor/home.html', context)

def processing_results(request, session_id):
    """
    Display processing results for a session
    """
    session = get_object_or_404(ImageProcessingSession, session_id=session_id)
    images = session.images.all().order_by('created_at')

    # Calculate time taken in seconds (from first created_at to last processed_at)
    if images.exists():
        first_created = images.order_by('created_at').first().created_at
        last_processed = images.filter(is_processed=True).order_by('-processed_at').first()
        if last_processed and last_processed.processed_at and first_created:
            time_taken_seconds = int((last_processed.processed_at - first_created).total_seconds())
        else:
            time_taken_seconds = None
    else:
        time_taken_seconds = None

    context = {
        'session': session,
        'images': images,
        'processed_count': images.filter(is_processed=True).count(),
        'total_count': images.count(),
        'time_taken_seconds': time_taken_seconds,
    }
    return render(request, 'image_processor/results.html', context)

def download_image(request, image_id):
    """
    Download a single processed image
    """
    img_request = get_object_or_404(ImageProcessingRequest, id=image_id, is_processed=True)
    
    if not img_request.processed_image:
        raise Http404("Processed image not found")
    
    try:
        response = HttpResponse(
            img_request.processed_image.read(),
            content_type='image/jpeg'
        )
        filename = f"{img_request.original_filename.split('.')[0]}_resized_{img_request.output_width}x{img_request.output_height}.jpg"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except FileNotFoundError:
        raise Http404("File not found")

def download_session_zip(request, session_id):
    """
    Download all processed images from a session as a ZIP file
    """
    session = get_object_or_404(ImageProcessingSession, session_id=session_id)
    processed_images = session.images.filter(is_processed=True)
    
    if not processed_images.exists():
        messages.error(request, "No processed images found in this session")
        return redirect('processing_results', session_id=session_id)
    
    zip_content, filename = create_zip_file(session)
    
    if zip_content:
        response = HttpResponse(zip_content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, f"Error creating ZIP file: {filename}")
        return redirect('processing_results', session_id=session_id)

@csrf_exempt
@require_http_methods(["POST"])
def ajax_image_info(request):
    """
    AJAX endpoint to get image information
    """
    if 'image' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No image provided'})
    
    image_file = request.FILES['image']
    
    # Validate image
    is_valid, message = validate_image_file(image_file)
    if not is_valid:
        return JsonResponse({'success': False, 'error': message})
    
    # Get image info
    info = get_image_info(image_file)
    if info:
        return JsonResponse({
            'success': True,
            'width': info['width'],
            'height': info['height'],
            'format': info['format'],
            'size': info['size']
        })
    else:
        return JsonResponse({'success': False, 'error': 'Could not read image information'})

def delete_session(request, session_id):
    """
    Delete a processing session and all associated files
    """
    session = get_object_or_404(ImageProcessingSession, session_id=session_id)
    
    if request.method == 'POST':
        try:
            # Delete associated files first
            for img_request in session.images.all():
                # Delete original image file
                if img_request.original_image:
                    try:
                        if os.path.exists(img_request.original_image.path):
                            os.remove(img_request.original_image.path)
                    except (OSError, ValueError):
                        pass  # File might already be deleted
                
                # Delete processed image file
                if img_request.processed_image:
                    try:
                        if os.path.exists(img_request.processed_image.path):
                            os.remove(img_request.processed_image.path)
                    except (OSError, ValueError):
                        pass  # File might already be deleted
            
            # Delete the session (this will cascade delete all related objects)
            session.delete()
            messages.success(request, "Session and all files deleted successfully")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Error deleting session: {str(e)}")
            return redirect('processing_results', session_id=session_id)
    
    context = {
        'session': session,
        'processed_count': session.images.filter(is_processed=True).count(),
    }
    return render(request, 'image_processor/confirm_delete.html', context)

def about(request):
    """
    About page with information about the image resizer
    """
    return render(request, 'image_processor/about.html')

@csrf_exempt
@require_http_methods(["POST"])
def ajax_validate_image(request):
    """
    AJAX endpoint to validate uploaded images
    """
    response_data = {}
    
    for key, file in request.FILES.items():
        if key.startswith('image_'):
            is_valid, message = validate_image_file(file)
            index = key.split('_')[1]
            response_data[index] = {
                'valid': is_valid,
                'message': message
            }
            
            if is_valid:
                info = get_image_info(file)
                if info:
                    response_data[index].update({
                        'width': info['width'],
                        'height': info['height'],
                        'format': info['format'],
                        'size_mb': round(info['size'] / (1024 * 1024), 2)
                    })
    
    return JsonResponse(response_data)

@csrf_exempt
@require_http_methods(["POST"])
def auto_delete_session(request):
    """
    AJAX endpoint to auto-delete sessions when users leave the page
    """
    try:
        import json
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            try:
                session = ImageProcessingSession.objects.get(session_id=session_id)
                
                # Delete associated files first
                for img_request in session.images.all():
                    # Delete original image file
                    if img_request.original_image:
                        try:
                            if os.path.exists(img_request.original_image.path):
                                os.remove(img_request.original_image.path)
                        except (OSError, ValueError):
                            pass  # File might already be deleted
                    
                    # Delete processed image file
                    if img_request.processed_image:
                        try:
                            if os.path.exists(img_request.processed_image.path):
                                os.remove(img_request.processed_image.path)
                        except (OSError, ValueError):
                            pass  # File might already be deleted
                
                # Delete the session (this will cascade delete all related objects)
                session.delete()
                
                return JsonResponse({'success': True, 'message': 'Session and all files deleted successfully'})
                
            except ImageProcessingSession.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Session not found'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error deleting session: {str(e)}'})
        else:
            return JsonResponse({'success': False, 'message': 'No session ID provided'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'})

def reprocess_image(request, image_id):
    """
    Reprocess an existing image with new settings.
    """
    original_request = get_object_or_404(ImageProcessingRequest, id=image_id)

    if request.method == 'POST':
        post_data = request.POST.copy()
        tfs_key = 'target_file_size_kb_0'
        if tfs_key in post_data and post_data[tfs_key]:
            try:
                post_data[tfs_key] = str(int(float(post_data[tfs_key])))
            except Exception:
                post_data[tfs_key] = ''
        form = BulkImageProcessingForm(post_data, num_images=1)
        if form.is_valid():
            session = ImageProcessingSession.objects.create()
            image_file = original_request.original_image
            original_info = get_image_info(image_file)

            # Re-use the processing logic from the home view
            if _process_form_entry(request, form, 0, session, image_file, original_info):
                messages.success(request, "Image re-processed successfully.")
                return redirect('processing_results', session_id=session.session_id)
            else:
                session.delete()  # Clean up empty session on failure
                # Fall through to re-render form with errors
        else:
            print("[DEBUG] Reprocess form is invalid:")
            print(form.errors)
            print(form.non_field_errors())
    else:
        # Pre-populate form with original settings
        initial_data = {
            'dimension_unit_0': original_request.dimension_unit,
            'dpi_0': original_request.dpi,
            'target_file_size_kb_0': int(original_request.file_size / 1024) if original_request.file_size else None,
        }
        if original_request.dimension_unit == 'pixels':
            initial_data['output_width_0'] = original_request.output_width
            initial_data['output_height_0'] = original_request.output_height
        elif original_request.dimension_unit == 'cm':
            initial_data['cm_width_0'] = original_request.dimension_width
            initial_data['cm_height_0'] = original_request.dimension_height
        elif original_request.dimension_unit == 'inch':
            initial_data['inch_width_0'] = original_request.dimension_width
            initial_data['inch_height_0'] = original_request.dimension_height
            
        form = BulkImageProcessingForm(num_images=1, initial=initial_data)

    context = {
        'form': form,
        'original_request': original_request
    }
    return render(request, 'image_processor/reprocess.html', context)

def _process_form_entry(request, form, i, session, image_file, original_info):
    """
    Helper function to process a single form entry for an image.
    Returns True on success, False on failure.
    """
    try:
        # Get unit and dpi
        unit = form.cleaned_data.get(f'dimension_unit_{i}', 'pixels')
        dpi = form.cleaned_data.get(f'dpi_{i}')

        # Ensure DPI has a value
        if not dpi or dpi <= 0:
            dpi = 300
        
        width, height = None, None

        if unit == 'pixels':
            width = form.cleaned_data.get(f'output_width_{i}')
            height = form.cleaned_data.get(f'output_height_{i}')
            if not all([width, height]):
                messages.error(request, f"Image {i+1}: For pixel dimensions, please specify both width and height.")
                return False
        elif unit == 'cm':
            dim_width = form.cleaned_data.get(f'cm_width_{i}')
            dim_height = form.cleaned_data.get(f'cm_height_{i}')
            if not all([dim_width, dim_height]):
                messages.error(request, f"Image {i+1}: For cm dimensions, please specify both width and height.")
                return False
            width = int(round(dim_width * dpi / 2.54))
            height = int(round(dim_height * dpi / 2.54))
        elif unit == 'inch':
            dim_width = form.cleaned_data.get(f'inch_width_{i}')
            dim_height = form.cleaned_data.get(f'inch_height_{i}')
            if not all([dim_width, dim_height]):
                messages.error(request, f"Image {i+1}: For inch dimensions, please specify both width and height.")
                return False
            width = int(round(dim_width * dpi))
            height = int(round(dim_height * dpi))
        
        # Validate final dimensions
        if not all([width, height]) or width <= 0 or height <= 0:
            messages.error(request, f"Image {i+1}: Invalid final dimensions calculated.")
            return False

        img_request = ImageProcessingRequest.objects.create(
            session=session,
            original_image=image_file,
            output_width=width,
            output_height=height,
            dpi=dpi,
            dimension_unit=unit,
            dimension_width=form.cleaned_data.get(f'cm_width_{i}') if unit == 'cm' else form.cleaned_data.get(f'inch_width_{i}'),
            dimension_height=form.cleaned_data.get(f'cm_height_{i}') if unit == 'cm' else form.cleaned_data.get(f'inch_height_{i}'),
            original_filename=image_file.name.split('/')[-1],
            original_width=original_info['width'],
            original_height=original_info['height'],
            original_file_size=original_info['size'],
        )
        
        target_file_size_kb = form.cleaned_data.get(f'target_file_size_kb_{i}')
        
        if target_file_size_kb and target_file_size_kb > 0:
            target_size_bytes = target_file_size_kb * 1024
            success, error_message = process_image_with_size_limit(
                img_request,
                target_size_bytes=target_size_bytes
            )
        else:
            success, error_message = process_image(img_request)
        
        if not success:
            messages.error(request, f"Image {i+1}: {error_message}")
            return False
            
        return True
        
    except (ValueError, TypeError) as e:
        messages.error(request, f"Image {i+1}: Invalid dimension values. Error: {e}")
        return False

def in_memory_process(request):
    """
    Process an uploaded image in memory and return the result as a download.
    No files are saved to disk or database.
    """
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        try:
            # Read image into Pillow
            img = Image.open(image_file)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Example: Resize (you can add more options)
            width = int(request.POST.get('width', img.width))
            height = int(request.POST.get('height', img.height))
            img = img.resize((width, height), Image.Resampling.LANCZOS)

            # Save to in-memory buffer
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=90)
            buffer.seek(0)

            # Prepare response
            response = HttpResponse(buffer, content_type='image/jpeg')
            response['Content-Disposition'] = f'attachment; filename="processed_{image_file.name.split(".")[0]}.jpg"'
            return response
        except Exception as e:
            return render(request, 'image_processor/in_memory_process.html', {
                'error': f'Error processing image: {e}'
            })
    return render(request, 'image_processor/in_memory_process.html')

def privacy_policy(request):
    return render(request, 'image_processor/privacy_policy.html')

def faq(request):
    return render(request, 'image_processor/faq.html')

def blog(request):
    context = {
        'today': date.today()
    }
    return render(request, 'image_processor/blog.html', context)

def terms(request):
    return render(request, 'image_processor/terms.html')

def contact(request):
    if request.method == 'POST':
        # Just show a success message, no backend email sending
        return render(request, 'image_processor/contact.html', {'request': request})
    return render(request, 'image_processor/contact.html', {'request': request})
