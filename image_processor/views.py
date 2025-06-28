from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.urls import reverse
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
    get_preset_categories, PRESET_SIZES, process_image_with_size_limit, calculate_dimensions
)
from .db_utils import retry_on_db_error, ensure_db_connection, close_db_connections

@retry_on_db_error(max_retries=3, delay=1)
def home(request):
    """
    Main view for bulk image processing
    """
    if request.method == 'POST':
        # Get num_images from POST data (form submission)
        num_images = int(request.POST.get('num_images', 1))
        num_images = max(1, min(num_images, 20))  # Limit between 1 and 20
        
        form = BulkImageProcessingForm(request.POST, request.FILES, num_images=num_images)
        
        if form.is_valid():
            # Create a new session for this processing batch
            session = ImageProcessingSession.objects.create()
            
            processed_count = 0
            num_images = form.cleaned_data.get('num_images', 1)
            
            for i in range(num_images):
                image_field = f'image_{i}'
                
                if image_field in request.FILES:
                    image_file = request.FILES[image_field]
                    
                    # Validate image
                    is_valid, validation_message = validate_image_file(image_file)
                    if not is_valid:
                        messages.error(request, f"Image {i+1}: {validation_message}")
                        continue
                    
                    # Get image information
                    original_info = get_image_info(image_file)
                    if not original_info:
                        messages.error(request, f"Image {i+1}: Could not read image information")
                        continue
                    
                    # Calculate dimensions
                    unit = form.cleaned_data.get(f'dimension_unit_{i}', 'pixels')
                    dpi = form.cleaned_data.get(f'dpi_{i}', 300)
                    
                    # Ensure DPI is valid
                    if dpi is None or dpi <= 0:
                        dpi = 300
                    
                    width, height = calculate_dimensions(
                        original_info, unit, dpi,
                        form.cleaned_data.get(f'output_width_{i}'),
                        form.cleaned_data.get(f'output_height_{i}'),
                        form.cleaned_data.get(f'cm_width_{i}'),
                        form.cleaned_data.get(f'cm_height_{i}'),
                        form.cleaned_data.get(f'inch_width_{i}'),
                        form.cleaned_data.get(f'inch_height_{i}')
                    )
                    
                    if not width or not height:
                        messages.error(request, f"Image {i+1}: Invalid dimensions")
                        continue
                    
                    # Additional validation for Cloudinary upload
                    try:
                        # Validate file format
                        if not image_file.content_type.startswith('image/'):
                            messages.error(request, f"Image {i+1}: Invalid file format. Please upload an image file.")
                            continue
                        
                        # Check file size (Cloudinary has limits)
                        if image_file.size > 100 * 1024 * 1024:  # 100MB limit
                            messages.error(request, f"Image {i+1}: File too large. Maximum size is 100MB.")
                            continue
                        
                        # Validate image format using Pillow
                        try:
                            # Reset file pointer
                            image_file.seek(0)
                            # Try to open with Pillow to validate
                            with Image.open(image_file) as img:
                                img.verify()  # Verify the image
                            # Reset file pointer again
                            image_file.seek(0)
                        except Exception as img_error:
                            messages.error(request, f"Image {i+1}: Invalid image file. Please upload a valid image.")
                            continue
                        
                    except Exception as validation_error:
                        messages.error(request, f"Image {i+1}: File validation failed.")
                        continue
                    
                    print(f"DEBUG: Creating ImageProcessingRequest with DPI: {dpi}, Width: {width}, Height: {height}")
                    
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
                    
                    # Store the original file for processing
                    img_request._original_file = image_file
                    
                    # Check for file size target
                    target_file_size_kb = form.cleaned_data.get(f'target_file_size_kb_{i}')
                    
                    if target_file_size_kb and target_file_size_kb > 0:
                        target_size_bytes = target_file_size_kb * 1024
                        print(f"DEBUG: Processing with size limit: {target_file_size_kb} KB")
                        try:
                            success, error_message = process_image_with_size_limit(
                                img_request,
                                target_size_bytes=target_size_bytes
                            )
                            print(f"DEBUG: Size-limited processing result - Success: {success}, Message: {error_message}")
                        except Exception as e:
                            print(f"DEBUG: Exception in size-limited processing: {str(e)}")
                            success, error_message = False, f"Processing error: {str(e)}"
                    else:
                        # Process with standard method
                        print(f"DEBUG: Processing with standard method")
                        try:
                            success, error_message = process_image(img_request)
                            print(f"DEBUG: Processing result - Success: {success}, Message: {error_message}")
                            if not success:
                                print(f"DEBUG: Image processing failed: {error_message}")
                        except Exception as e:
                            print(f"DEBUG: Exception in image processing: {str(e)}")
                            success, error_message = False, f"Processing error: {str(e)}"
                    
                    print(f"DEBUG: Final result - Success: {success}, Processed count: {processed_count}")
                    if success:
                        processed_count += 1
                        print(f"DEBUG: Incremented processed count to: {processed_count}")
                    else:
                        messages.error(request, f"Image {i+1}: {error_message}")
                else:
                    messages.error(request, f"Image {i+1}: No file uploaded")
            
            if processed_count > 0:
                messages.success(request, f"Successfully processed {processed_count} image(s)")
                return redirect('processing_results', session_id=session.session_id)
            else:
                messages.error(request, "No images were processed successfully")
                session.delete()  # Clean up empty session
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # GET request - use URL parameter or default to 1
        num_images = int(request.GET.get('num_images', 1))
        num_images = max(1, min(num_images, 20))  # Limit between 1 and 20
        form = BulkImageProcessingForm(num_images=num_images)
    
    context = {
        'form': form,
        'num_images': num_images,
        'max_images': 20,  # Maximum allowed images
        'preset_categories': get_preset_categories(),
        'presets_json': json.dumps(PRESET_SIZES),
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
            # With Cloudinary storage, files are automatically managed by the cloud provider
            # No need to manually delete files
            
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
            pass  # Fall through to re-render form with errors
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
            original_filename=image_file.name,
            original_width=original_info['width'],
            original_height=original_info['height'],
            original_file_size=original_info['size'],
        )
        
        # Store the original file for processing
        img_request._original_file = image_file
        
        target_file_size_kb = form.cleaned_data.get(f'target_file_size_kb_{i}')
        
        if target_file_size_kb and target_file_size_kb > 0:
            target_size_bytes = target_file_size_kb * 1024
            print(f"DEBUG: Processing with size limit: {target_file_size_kb} KB")
            try:
                success, error_message = process_image_with_size_limit(
                    img_request,
                    target_size_bytes=target_size_bytes
                )
                print(f"DEBUG: Size-limited processing result - Success: {success}, Message: {error_message}")
            except Exception as e:
                print(f"DEBUG: Exception in size-limited processing: {str(e)}")
                success, error_message = False, f"Processing error: {str(e)}"
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
