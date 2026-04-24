import os
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-stratix-default-key-123')

# --- CLOUDFLARE PROXY & SECURITY SETTINGS ---
# Tell Django it is sitting behind a secure Cloudflare proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Explicitly trust your production domain for logins and photo uploads
CSRF_TRUSTED_ORIGINS = [
    'https://portal.stratixjm.com',
    'https://stratix-dashboard.azurewebsites.net',
]

# Ensure your domain and the underlying Azure URL are allowed
ALLOWED_HOSTS = [
    'portal.stratixjm.com', 
    'stratix-dashboard.azurewebsites.net',
    'localhost', 
    '127.0.0.1'
]

# --- DYNAMIC URL CONFIGURATION ---
prod_url = config('PRODUCTION_URL', default='portal.stratixjm.com')
if prod_url:
    if not prod_url.startswith('http'):
        if f'https://{prod_url}' not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(f'https://{prod_url}')
    else:
        if prod_url not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(prod_url)

# This variable is now available for your email logic
PRODUCTION_URL = prod_url.replace('https://', '').replace('http://', '')

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
    'django_cleanup.apps.CleanupConfig'
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'login'

CORS_ALLOW_ALL_ORIGINS = True
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# --- SAFE REDIS CONFIGURATION ---
REDIS_URL = config('REDIS_URL', default=None)

# Only attempt to use Redis if the URL is present and starts with a valid scheme
if REDIS_URL and any(REDIS_URL.startswith(s) for s in ['redis://', 'rediss://', 'unix://']):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    # Fallback to In-Memory if Redis is misconfigured or missing
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

AZURE_ACCOUNT_NAME = config('AZURE_ACCOUNT_NAME', default='')
AZURE_ACCOUNT_KEY = config('AZURE_ACCOUNT_KEY', default='')
AZURE_CONTAINER = config('AZURE_CONTAINER', default='site-photos')

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "account_name": AZURE_ACCOUNT_NAME,
                "account_key": AZURE_ACCOUNT_KEY,
                "azure_container": AZURE_CONTAINER,
                "overwrite_files": False,
            },
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
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

EMAIL_BACKEND = 'reports.email_backend.HighPriorityEmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int) 
EMAIL_USE_TLS = True   
EMAIL_USE_SSL = False  
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='clientrelations@stratixjm.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

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
        "reports", "reports.Project", "reports.Site", "reports.Report", 
        "reports.SitePhoto", "reports.SiteIssue", "reports.SupportTicket",
        "reports.ActivityAlert", "reports.Client", "reports.UserProfile", "auth"
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
    "theme": "cyborg", 
    "dark_mode_theme": "cyborg",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-warning",
    "brand_colour": "navbar-warning",
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
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
