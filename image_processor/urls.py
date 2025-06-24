from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('results/<uuid:session_id>/', views.processing_results, name='processing_results'),
    path('download/<int:image_id>/', views.download_image, name='download_image'),
    path('download/session/<uuid:session_id>/', views.download_session_zip, name='download_session_zip'),
    path('delete/<uuid:session_id>/', views.delete_session, name='delete_session'),
    path('about/', views.about, name='about'),
    path('reprocess/<int:image_id>/', views.reprocess_image, name='reprocess_image'),
    path('in-memory/', views.in_memory_process, name='in_memory_process'),
    # New SEO/Content pages
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('faq/', views.faq, name='faq'),
    path('blog/', views.blog, name='blog'),
    path('terms/', views.terms, name='terms'),
    path('contact/', views.contact, name='contact'),
    
    # AJAX endpoints
    path('ajax/image-info/', views.ajax_image_info, name='ajax_image_info'),
    path('ajax/validate-image/', views.ajax_validate_image, name='ajax_validate_image'),
    path('delete-session-ajax/', views.auto_delete_session, name='auto_delete_session'),
] 