import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'images_resizer.settings')

# Add error handling
try:
    app = get_wsgi_application()
    
    # Initialize database if needed
    try:
        from django.core.management import execute_from_command_line
        from django.db import connection
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("[DEBUG] Database connection successful in API")
            
        # Run migrations if needed
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        print("[DEBUG] Database migrations completed")
        
    except Exception as db_error:
        print(f"[DEBUG] Database initialization error: {db_error}")
        # Continue anyway, the app might work without database
        
except Exception as e:
    print(f"Error initializing Django app: {e}")
    import traceback
    traceback.print_exc()
    raise 