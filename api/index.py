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
except Exception as e:
    print(f"Error initializing Django app: {e}")
    import traceback
    traceback.print_exc()
    raise 