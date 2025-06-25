"""
Middleware for handling database connections in serverless environments.
"""
import logging
from django.db import connection
from .db_utils import close_db_connections

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    """
    Middleware to handle database connections in serverless environments.
    Ensures connections are properly closed after each request.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Close database connections after response
        try:
            close_db_connections()
        except Exception as e:
            logger.warning(f"Error closing database connections: {e}")
        
        return response
    
    def process_exception(self, request, exception):
        """
        Handle exceptions and ensure database connections are closed.
        """
        try:
            close_db_connections()
        except Exception as e:
            logger.warning(f"Error closing database connections during exception: {e}")
        
        return None 