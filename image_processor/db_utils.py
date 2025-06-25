"""
Database utility functions for handling connections in serverless environments.
"""
import logging
import time
from functools import wraps
from django.db import connection, DatabaseError
from django.conf import settings

logger = logging.getLogger(__name__)

def retry_on_db_error(max_retries=3, delay=1):
    """
    Decorator to retry database operations on connection errors.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Ensure connection is closed before retry
                    if attempt > 0:
                        connection.close()
                        time.sleep(delay * attempt)  # Exponential backoff
                    
                    return func(*args, **kwargs)
                    
                except (DatabaseError, Exception) as e:
                    last_exception = e
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    
                    if attempt == max_retries - 1:
                        logger.error(f"Database operation failed after {max_retries} attempts")
                        raise last_exception
                        
            return None
        return wrapper
    return decorator

def ensure_db_connection():
    """
    Ensure database connection is established and healthy.
    """
    try:
        # Test the connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def close_db_connections():
    """
    Close all database connections.
    """
    try:
        connection.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database connections: {e}") 