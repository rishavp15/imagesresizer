release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn images_resizer.wsgi 