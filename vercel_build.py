#!/usr/bin/env python
"""
Vercel build script for Django application
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and return the result"""
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {command}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {command}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main build function"""
    print("🚀 Starting Vercel build process...")
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'images_resizer.settings')
    
    # Add project root to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt"):
        print("⚠️  Warning: Failed to install dependencies, continuing...")
    
    # Try to collect static files
    if not run_command("python manage.py collectstatic --noinput"):
        print("⚠️  Warning: Failed to collect static files, continuing...")
    
    # Try to run migrations
    if not run_command("python manage.py migrate --noinput"):
        print("⚠️  Warning: Failed to run migrations, continuing...")
    
    print("✅ Build completed!")

if __name__ == "__main__":
    main() 