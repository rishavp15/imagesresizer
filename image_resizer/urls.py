from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.urls import path
from . import views

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about', 'privacy_policy', 'faq', 'blog', 'terms', 'contact']

    def location(self, item):
        from django.urls import reverse
        return reverse(item)

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # ... existing url patterns ...
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django_sitemap'),
] 