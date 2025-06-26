# Images Resizer - Professional Image Processing Tool

A Django-based web application for bulk image resizing with advanced options including custom dimensions, DPI settings, and batch download capabilities.

## Features

### 🖼️ Bulk Image Processing
- Upload and process up to 20 images simultaneously
- Individual settings for each image
- Support for JPEG, PNG, GIF, BMP, and TIFF formats
- File size limit: 10MB per image

### ⚙️ Easy Mode & Advanced Settings
- **Easy Mode**: Choose from 15+ presets for social media, web, print, and more
- **File Size Targets**: Automatically optimize images to specific file sizes (100KB to 5MB)
- **Advanced Mode**: Precise pixel-based resizing with custom dimensions
- **Physical Dimensions**: Set dimensions in centimeters or inches
- **DPI Control**: Adjustable DPI from 72 to 600 for print optimization
- **Copy Settings**: Apply settings to all images with one click

### 📦 Download Options
- Individual image downloads
- Bulk ZIP file downloads
- Optimized JPEG output with 95% quality
- Session-based file management

### 🎨 Modern UI/UX
- Material Design principles
- Responsive Bootstrap 5 layout
- SEO-optimized HTML structure
- Real-time image preview
- Progress indicators and validation

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or download the project**
```bash
cd images_resizer
```

2. **Install dependencies**
```bash
pip3 install -r requirements.txt
```

3. **Run database migrations**
```bash
python3 manage.py migrate
```

4. **Create a superuser (optional)**
```bash
python3 manage.py createsuperuser
```

5. **Start the development server**
```bash
python3 manage.py runserver
```

6. **Access the application**
- Main application: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/
- Default admin credentials: username=`admin`, password=`admin123`

## Usage Guide

### 1. Upload Images
- Click on the file input areas to select images
- Each image can be up to 10MB
- Supported formats: JPEG, PNG, GIF, BMP, TIFF
- Preview and file information appear automatically

### 2. Configure Settings
- **Easy Mode**: Select from preset purposes (Instagram Post, Web Medium, Print 4x6, etc.)
- **File Size**: Choose target file size (Very Small to High Quality)
- **Advanced Mode**: Set custom width and height in pixels
- **Physical Dimensions**: Optionally set real-world dimensions
- **DPI**: Choose quality setting (300 DPI recommended for print)
- **Copy Settings**: Use "Copy to All" to apply settings to multiple images

### 3. Process Images
- Click "Process Images" to start resizing
- Processing happens immediately with quality optimization
- Results page shows processing status and download options

### 4. Download Results
- **Individual Downloads**: Click download button for each image
- **Bulk Download**: Download all processed images as a ZIP file
- Files are automatically cleaned up after 7 days

## Project Structure

```
images_resizer/
├── images_resizer/          # Django project settings
│   ├── settings.py         # Configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI application
├── image_processor/        # Main application
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   ├── forms.py           # Form definitions
│   ├── utils.py           # Image processing utilities
│   ├── admin.py           # Admin interface
│   ├── urls.py            # App URL patterns
│   ├── templatetags/      # Custom template filters
│   └── templates/         # HTML templates
├── media/                 # User uploaded files
│   ├── uploads/           # Original images
│   └── processed/         # Processed images
├── static/               # Static files (CSS, JS, images)
└── requirements.txt      # Python dependencies
```

## Technical Details

### Backend
- **Framework**: Django 4.2.7
- **Image Processing**: Pillow (PIL) 10.1.0
- **File Handling**: Django's built-in file upload system
- **Database**: SQLite (default, easily configurable)

### Frontend
- **CSS Framework**: Bootstrap 5.3.2
- **Icons**: Material Icons
- **Fonts**: Roboto (Material Design)
- **JavaScript**: Vanilla JS with Bootstrap components

### Image Processing Features
- High-quality Lanczos resampling
- Automatic color space optimization
- DPI preservation and adjustment
- Format conversion to optimized JPEG
- Batch processing with error handling

## API Endpoints

### Web Interface
- `/` - Home page with upload form
- `/results/<session_id>/` - Processing results
- `/history/` - Session history
- `/about/` - About page

### Downloads
- `/download/image/<image_id>/` - Single image download
- `/download/zip/<session_id>/` - ZIP download

### AJAX Endpoints
- `/ajax/validate-image/` - Image validation
- `/ajax/image-info/` - Image information

## Configuration

### Environment Variables
You can customize the application by setting these environment variables:

- `DEBUG`: Set to `False` for production
- `SECRET_KEY`: Use a secure secret key for production
- `ALLOWED_HOSTS`: Configure allowed hosts for production

### File Upload Limits
Edit `settings.py` to adjust:
- `FILE_UPLOAD_MAX_MEMORY_SIZE`: Maximum file size (default: 50MB)
- `DATA_UPLOAD_MAX_MEMORY_SIZE`: Maximum form data size (default: 50MB)

## Security Features

- CSRF protection on all forms
- File type validation
- File size limits
- Automatic session cleanup
- Safe filename handling
- XSS prevention in templates

## Performance Optimization

- Efficient image processing with Pillow
- Lazy loading of images
- Optimized database queries
- Compressed static files
- Progressive JPEG output

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile responsive design
- Touch-friendly interface
- Progressive enhancement

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues, feature requests, or questions:
1. Check the existing documentation
2. Review the FAQ in the About page
3. Create an issue with detailed information

## Changelog

### v1.0.0 (Initial Release)
- Bulk image upload and processing
- Material Design UI
- ZIP download functionality
- Session management
- Admin interface
- Mobile responsive design # Upadate aaj
