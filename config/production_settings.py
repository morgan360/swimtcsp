from config.base_settings import *
from decouple import config
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = False

# --- Core secrets/env (prod reads from real env) ---
SECRET_KEY = config('SECRET_KEY')

# OpenAI settings live in base_settings.py — see the OpenAI/chatbot block there.

# --- BOIPA Configuration ---
# =============================================================================
# NEW API (OAuth2) - Active as of Dec 2025
# =============================================================================
BOIPA_CLIENT_ID        = config('BOIPA_CLIENT_ID')
BOIPA_MERCHANT_ID      = config('BOIPA_CLIENT_ID')  # Alias for compatibility
BOIPA_ACCOUNT_NAME     = config('BOIPA_ACCOUNT_NAME')
BOIPA_ACCOUNT_ID       = config('BOIPA_ACCOUNT_ID')
BOIPA_APP_ID           = config('BOIPA_APP_ID')
BOIPA_APP_KEY          = config('BOIPA_APP_KEY')
BOIPA_API_BASE_URL     = config('BOIPA_API_BASE_URL')
BOIPA_ACCESS_TOKEN_URL = config('BOIPA_ACCESS_TOKEN_URL')
BOIPA_HPP_LINKS_URL    = config('BOIPA_HPP_LINKS_URL')
BOIPA_TRANSACTIONS_URL = config('BOIPA_TRANSACTIONS_URL')
BOIPA_API_VERSION      = config('BOIPA_API_VERSION', default='2021-03-22')
NGROK                  = config('NGROK', default='https://www.tcsp.ie').rstrip('/')

# =============================================================================
# OLD API (Legacy) - ROLLBACK ONLY
# To rollback to old API, comment out NEW API section above and uncomment below:
# =============================================================================
# BOIPA_MERCHANT_ID  = config('BOIPA_MERCHANT_ID')
# BOIPA_PASSWORD     = config('BOIPA_PASSWORD')
# BOIPA_TOKEN_URL    = config('BOIPA_TOKEN_URL')
# HPP_FORM           = config('HPP_FORM')
# NGROK              = config('NGROK', default='http://localhost:4040').rstrip('/')
# BRAND_ID           = config('BRAND_ID')
# BOIPA_PAYMENT_URL  = config('BOIPA_PAYMENT_URL')

CART_SESSION_ID = 'cart'

# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$swimtcsp',
        'USER': 'morganmck',
        'PASSWORD': config("DB_PASSWORD"),
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
        # charset is explicit rather than left to the driver's default: the
        # schema is utf8mb4 (users migration 0017) and a connection negotiating
        # anything narrower would reintroduce the four-byte failure it fixed.
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# --- Hosts / CSRF ---
ALLOWED_HOSTS = ['www.tcsp.ie', 'tcsp.ie']
CSRF_TRUSTED_ORIGINS = ['https://www.tcsp.ie', 'https://tcsp.ie']

# --- Maintenance mode ---
MAINTENANCE_MODE_IGNORE_URLS = (
    r'^/admin/.*',
    r'^/accounts/login/?$',
    r'^/accounts/logout/?$',
    r'^/accounts/password/reset/.*$',
    r'^/accounts/signup/?$',
    r'^/users/login/?$',
    r'^/users/logout/?$',
    r'^/boipa/payment-response/?$',  # Allow BOIPA callbacks during maintenance
)

# --- Email (M365) ---
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST')
EMAIL_PORT          = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL')
FROM_EMAIL          = DEFAULT_FROM_EMAIL  # Alias for legacy code

# --- Logging ---
LOG_BASE = '/home/morganmck/swimtcsp/logs'
os.makedirs(LOG_BASE, exist_ok=True)

PAYMENTS_LOG_FILE_PATH = os.path.join(LOG_BASE, 'payments.log')
CART_LOG_FILE_PATH     = os.path.join(LOG_BASE, 'cart.log')
APP_LOG_FILE_PATH      = os.path.join(LOG_BASE, 'app.log')
BOIPA_LOG_FILE_PATH    = os.path.join(LOG_BASE, 'boipa.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {'format': '{asctime} {levelname} {module} {message}', 'style': '{'},
        'simple':   {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'payments_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': PAYMENTS_LOG_FILE_PATH,
            'formatter': 'detailed'
        },
        'cart_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': CART_LOG_FILE_PATH,
            'formatter': 'detailed'
        },
        'app_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': APP_LOG_FILE_PATH,
            'formatter': 'detailed'
        },
        'boipa_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BOIPA_LOG_FILE_PATH,
            'formatter': 'detailed'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'payments': {
            'handlers': ['payments_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'cart': {
            'handlers': ['cart_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'application': {
            'handlers': ['app_file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'boipa': {
            'handlers': ['boipa_file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
    },
}

# --- Security hardening ---
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True
SECURE_SSL_REDIRECT   = True
SECURE_HSTS_SECONDS   = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # enable if you control all subdomains
SECURE_HSTS_PRELOAD   = False

SITE_ID = 2
FOOTER_MESSAGE = "Production Version"
