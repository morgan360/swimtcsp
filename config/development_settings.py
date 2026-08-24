from config.base_settings import *
from decouple import config
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True

# --- Core secrets/env (from .env in ~/dev-swimtcsp) ---
SECRET_KEY = config('SECRET_KEY')

# OpenAI settings live in base_settings.py — see the OpenAI/chatbot block there.

# --- BOIPA (New API - OAuth2) ---
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
NGROK                  = config('NGROK', default='http://localhost:4040').rstrip('/')

# Old BOIPA variables (deprecated but kept for reference)
# BOIPA_PASSWORD     = config('BOIPA_PASSWORD', default='')
# BOIPA_TOKEN_URL    = config('BOIPA_TOKEN_URL', default='')
# BRAND_ID           = config('BRAND_ID', default='')
# BOIPA_PAYMENT_URL  = config('BOIPA_PAYMENT_URL', default='')

CART_SESSION_ID = 'cart'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$dev-swimtcsp',   # ✅ dev DB
        'USER': 'morganmck',
        'PASSWORD': config("DB_PASSWORD"),
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
        # See the note in production_settings: the schema is utf8mb4, so the
        # connection says so explicitly rather than relying on a driver default.
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

ALLOWED_HOSTS = ["dev-morganmck.eu.pythonanywhere.com"]
CSRF_TRUSTED_ORIGINS = ["https://dev-morganmck.eu.pythonanywhere.com"]

# --- Email (M365) ---
EMAIL_BACKEND       = 'utils.email_backend.ReplyToEmailBackend'
EMAIL_HOST          = config('EMAIL_HOST')
EMAIL_PORT          = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL')
FROM_EMAIL          = DEFAULT_FROM_EMAIL  # Alias for legacy code

# --- Logging ---
LOG_BASE = '/home/morganmck/dev-swimtcsp/logs'
os.makedirs(LOG_BASE, exist_ok=True)

PAYMENTS_LOG_FILE_PATH = os.path.join(LOG_BASE, 'payments.log')
CART_LOG_FILE_PATH     = os.path.join(LOG_BASE, 'cart.log')
APP_LOG_FILE_PATH      = os.path.join(LOG_BASE, 'app.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'payments_file': {'level': 'DEBUG','class': 'logging.FileHandler','filename': PAYMENTS_LOG_FILE_PATH,'formatter': 'detailed'},
        'cart_file':     {'level': 'DEBUG','class': 'logging.FileHandler','filename': CART_LOG_FILE_PATH,'formatter': 'detailed'},
        'app_file':      {'level': 'DEBUG','class': 'logging.FileHandler','filename': APP_LOG_FILE_PATH,'formatter': 'detailed'},
        'console':       {'level': 'DEBUG','class': 'logging.StreamHandler','formatter': 'simple'},
    },
    'formatters': {
        'detailed': {'format': '{asctime} {levelname} {module} {message}', 'style': '{'},
        'simple':   {'format': '{levelname} {message}', 'style': '{'},
    },
    'loggers': {
        'payments':    {'handlers': ['payments_file'],         'level': 'DEBUG', 'propagate': False},
        'cart':        {'handlers': ['cart_file'],             'level': 'DEBUG', 'propagate': False},
        'application': {'handlers': ['app_file', 'console'],   'level': 'DEBUG', 'propagate': False},
    },
}

# --- Security (relaxed for dev) ---
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE    = False
SECURE_SSL_REDIRECT   = False
SECURE_HSTS_SECONDS   = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD   = False

SITE_ID = 3
FOOTER_MESSAGE = "Development Version"
