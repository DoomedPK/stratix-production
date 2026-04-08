from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from reports.views import custom_logout
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reports.urls')),
    
    # 🚀 CUSTOM INTERCEPT FOR BRANDED PASSWORD RESET EMAIL
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        html_email_template_name='registration/password_reset_email_html.html',
        email_template_name='registration/password_reset_email.txt',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', custom_logout, name='logout'),
    
    # This securely serves images on Render's disk even when DEBUG=False
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
