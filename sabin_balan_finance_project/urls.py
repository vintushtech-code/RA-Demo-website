"""
URL configuration for sabin_balan_finance_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404, HttpResponse, FileResponse
from django.contrib.staticfiles import finders
from login.views import admin_2fa_login, get_dashboard_analytics_context, llms_txt_view, llms_full_txt_view, robots_txt_view, sitemap_xml_view

# Enforce 2-Way Verification (2FA) for Django Admin site authentication
admin.site.login = admin_2fa_login

# Inject dynamic real-time ORM analytics & vault snapshot data into admin dashboard
original_admin_index = admin.site.index
def enhanced_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    try:
        extra_context.update(get_dashboard_analytics_context(request))
    except Exception:
        pass
    return original_admin_index(request, extra_context=extra_context)

admin.site.index = enhanced_admin_index

# Retrieve secret admin slug from settings
ADMIN_SECRET_PATH = getattr(settings, 'ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')

# Decoy honeypot handler for standard /admin/ probes
def admin_honeypot_404(request):
    raise Http404("Page not found")

def favicon_view(request):
    logo_path = finders.find('logo.png')
    if logo_path:
        try:
            return FileResponse(open(logo_path, 'rb'), content_type='image/png')
        except Exception:
            pass
    return HttpResponse(status=204)

urlpatterns = [
    path('favicon.ico', favicon_view),
    path('llms.txt', llms_txt_view, name='llms_txt'),
    path('llms-full.txt', llms_full_txt_view, name='llms_full_txt'),
    path('robots.txt', robots_txt_view, name='robots_txt'),
    path('sitemap.xml', sitemap_xml_view, name='sitemap_xml'),
    
    # Honeypot: Standard /admin/ access returns instant 404 camouflage
    path('admin/', admin_honeypot_404),
    
    # Secret Admin Portal Gateway
    path(f'{ADMIN_SECRET_PATH}/', admin.site.urls),
    
    # Public Client Web Application & Inquiries
    path('contact/', include('contactform.urls')),
    path('', include('login.urls')),
]

from django.views.static import serve
from django.urls import re_path

# Permanent media serving for user & admin uploads
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Global Custom Error Handlers for 404 Page Not Found and 500 Internal Server Error
handler404 = 'login.views.custom_404_view'
handler500 = 'login.views.custom_500_view'


