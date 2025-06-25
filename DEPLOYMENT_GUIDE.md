# Vercel + Supabase Deployment Guide

## Issue Resolution: Database Connection Error

The error "Cannot assign requested address" occurs due to IPv6/IPv4 networking issues between Vercel's serverless functions and Supabase PostgreSQL.

## Step-by-Step Solution

### 1. Environment Variables Setup

In your Vercel dashboard, set these environment variables:

```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.rhqveyfaxtvrujymspet.supabase.co:5432/postgres?sslmode=require
SECRET_KEY=[YOUR-DJANGO-SECRET-KEY]
DEBUG=False
ALLOWED_HOSTS=imagesresizer.vercel.app,localhost,127.0.0.1
```

### 2. Supabase Configuration

#### A. Enable SSL Connections
- Go to your Supabase project dashboard
- Navigate to Settings > Database
- Ensure "SSL Required" is enabled

#### B. Configure Connection Pooling (Optional but Recommended)
- In Supabase dashboard, go to Settings > Database
- Enable connection pooling
- Use the connection pooler URL if available

#### C. Firewall Settings
- Go to Settings > Database > Connection pooling
- Add Vercel's IP ranges to allowlist (if required)
- Or disable IP restrictions temporarily for testing

### 3. Database URL Format

Use this format for your DATABASE_URL:
```
postgresql://postgres:[PASSWORD]@db.rhqveyfaxtvrujymspet.supabase.co:5432/postgres?sslmode=require&connect_timeout=10
```

### 4. Local Testing

Test your database connection locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="your-supabase-connection-string"
export SECRET_KEY="your-secret-key"

# Run migrations
python manage.py migrate

# Test connection
python manage.py shell
```

In Django shell:
```python
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT 1")
    print("Database connection successful!")
```

### 5. Deployment Commands

```bash
# Deploy to Vercel
vercel --prod

# Or using Vercel CLI
vercel deploy --prod
```

### 6. Monitoring and Debugging

#### A. Check Vercel Logs
```bash
vercel logs [your-project-url]
```

#### B. Monitor Supabase Dashboard
- Check connection logs in Supabase dashboard
- Monitor query performance
- Check for connection limits

#### C. Test Database Connection
Create a simple test endpoint:

```python
# Add to views.py
@csrf_exempt
def test_db(request):
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return JsonResponse({"status": "success", "message": "Database connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
```

### 7. Alternative Solutions

#### A. Use Connection Pooling
If connection issues persist, consider using Supabase's connection pooler:

```python
# Update DATABASE_URL to use pooler
DATABASE_URL=postgresql://postgres:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

#### B. Use PgBouncer
Configure PgBouncer for connection pooling:

```python
# In settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '[PASSWORD]',
        'HOST': 'db.rhqveyfaxtvrujymspet.supabase.co',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'application_name': 'images_resizer',
        },
        'CONN_MAX_AGE': 0,  # Disable connection pooling for serverless
    }
}
```

### 8. Performance Optimizations

#### A. Connection Pooling Settings
```python
# In settings.py
DATABASES = {
    'default': {
        # ... other settings ...
        'CONN_MAX_AGE': 0,  # For serverless environments
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'application_name': 'images_resizer',
            'client_encoding': 'UTF8',
        },
    }
}
```

#### B. Query Optimization
- Use `select_related()` and `prefetch_related()` for related queries
- Implement database indexes for frequently queried fields
- Use bulk operations for multiple records

### 9. Troubleshooting Checklist

- [ ] Environment variables set correctly in Vercel
- [ ] Supabase SSL enabled
- [ ] Database URL format correct
- [ ] Firewall settings configured
- [ ] Connection pooling enabled (if needed)
- [ ] Vercel function timeout increased
- [ ] Database migrations applied
- [ ] Static files collected

### 10. Common Issues and Solutions

#### Issue: "Cannot assign requested address"
**Solution**: Use IPv4 connection or connection pooler

#### Issue: "Connection timeout"
**Solution**: Increase `connect_timeout` in database options

#### Issue: "Too many connections"
**Solution**: Use connection pooling or reduce `CONN_MAX_AGE`

#### Issue: "SSL connection required"
**Solution**: Ensure `sslmode=require` in DATABASE_URL

## Support

If issues persist:
1. Check Vercel function logs
2. Monitor Supabase dashboard
3. Test connection locally
4. Contact Supabase support for connection issues
5. Check Vercel documentation for serverless limitations 