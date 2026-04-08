import os
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# 🚀 SECURITY WARNING: In production, DEBUG will automatically be False if an ENV variable is set.
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-stratix-default-key-123')

# 🚀 Dynamic Allowed Hosts for AWS/GCP
ALLOWED_HOSTS = ['*'] if DEBUG else config('ALLOWED_HOSTS', default='*').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://stratix-dashboard.onrender.com',
    'https://stratixjm-dashboard.onrender.com',
]
# Add your production AWS URL here once you have it!
if config('PRODUCTION_URL', default=''):
    CSRF_TRUSTED_ORIGINS.append(config('PRODUCTION_URL'))

INSTALLED_APPS = [
    'jazzmin', 
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reports',
    'corsheaders',
    'rest_framework',
    'channels',
    'crispy_forms',
    'crispy_bootstrap5',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'reports.context_processors.live_alerts', 
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# 🚀 AWS / GCP DATABASE CONFIGURATION
# It defaults to local sqlite3, but will instantly switch to PostgreSQL if you provide a DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'login'

CORS_ALLOW_ALL_ORIGINS = True
CRISPY_TEMPLATE_PACK = 'bootstrap5'

REDIS_URL = config('REDIS_URL', default=None)
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {"hosts": [REDIS_URL]},
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

# ----------------------------------------------------------------------
# 🚀 DJANGO 5.1 STORAGE CONFIGURATION
# ----------------------------------------------------------------------
if not DEBUG:
    SUPABASE_PROJECT_REF = config('SUPABASE_PROJECT_REF', default='')
    AWS_ACCESS_KEY_ID = config('SUPABASE_S3_ACCESS_KEY', default='')
    AWS_SECRET_ACCESS_KEY = config('SUPABASE_S3_SECRET_KEY', default='')
    SUPABASE_STORAGE_BUCKET_NAME = config('SUPABASE_STORAGE_BUCKET_NAME', default='site-photos')

    if SUPABASE_PROJECT_REF and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        AWS_S3_ENDPOINT_URL = f'https://{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3'
        AWS_STORAGE_BUCKET_NAME = SUPABASE_STORAGE_BUCKET_NAME
        AWS_S3_REGION_NAME = 'us-east-1' 
        AWS_S3_SIGNATURE_VERSION = 's3v4'
        AWS_S3_FILE_OVERWRITE = False
        AWS_DEFAULT_ACL = None 
        AWS_S3_ADDRESSING_STYLE = 'path'
        AWS_QUERYSTRING_AUTH = False 
        
        AWS_S3_CUSTOM_DOMAIN = f'{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET_NAME}'
        AWS_S3_USE_SSL = True
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

        STORAGES = {
            "default": {
                "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# ----------------------------------------------------------------------
# EMAIL SMTP CONFIGURATION
# ----------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='clientrelations@stratixjm.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ----------------------------------------------------------------------
# JAZZMIN ADMIN UI CONFIGURATION
# ----------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Stratix Admin",
    "site_header": "Stratix Command",
    "site_brand": "STRATIX",
    "site_logo": "images/stratix-logo.png",
    "login_logo": "images/stratix-logo.png",
    "site_logo_classes": "img-circle",
    "site_icon": "images/stratix-logo.png",
    
    "welcome_sign": "Secure Command Center Authentication",
    "copyright": "Stratix Group Limited",
    "search_model": ["reports.Site", "auth.User", "reports.SupportTicket"],
    
    "user_avatar": None, 
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Return to Dashboard", "url": "dashboard_home", "icon": "fas fa-desktop"},
        {"name": "Global Map Tracker", "url": "global_map", "icon": "fas fa-globe"}
    ],
    "usermenu_links": [
        {"name": "Stratix Support", "url": "/support/", "icon": "fas fa-headset"},
        {"model": "auth.user"}
    ],
    
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    
    "custom_links": {
        "reports": [{
            "name": "Live Contractor Map", 
            "url": "global_map", 
            "icon": "fas fa-map-marked-alt text-info",
        }]
    },

    "order_with_respect_to": [
        "reports", 
        "reports.Project", 
        "reports.Site", 
        "reports.Report", 
        "reports.SitePhoto", 
        "reports.SiteIssue",
        "reports.SupportTicket",
        "reports.ActivityAlert", 
        "reports.Client", 
        "reports.UserProfile",
        "auth"
    ],
    
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield", 
        "auth.Group": "fas fa-users",
        "reports.Client": "fas fa-building",
        "reports.Project": "fas fa-project-diagram",
        "reports.Site": "fas fa-satellite-dish",
        "reports.Report": "fas fa-file-invoice",
        "reports.SitePhoto": "fas fa-camera",
        "reports.ActivityAlert": "fas fa-bell text-warning",
        "reports.UserProfile": "fas fa-id-card",
        "reports.SiteIssue": "fas fa-exclamation-triangle text-danger",
        "reports.SupportTicket": "fas fa-ticket-alt text-success",
    },
    
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    
    "custom_css": "css/stratix_admin.css", 
    "custom_js": None,
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    
    "brand_colour": "navbar-warning",     
    "accent": "accent-warning",            
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-warning",   
    
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    
    "theme": "cyborg", 
    "dark_mode_theme": "cyborg",
    
    "button_classes": {
        "primary": "btn-warning fw-bold text-dark", 
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'

# ----------------------------------------------------------------------
# 🚀 V2.0 AI ENGINE CONFIGURATION (GEMINI)
# ----------------------------------------------------------------------
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
