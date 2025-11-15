from config.base_settings import *
from decouple import config
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = False

# --- Core secrets/env (prod reads from real env) ---
SECRET_KEY = config('SECRET_KEY')

# OpenAI
OPENAI_API_KEY     = config("OPENAI_API_KEY")
OPENAI_CHAT_MODEL  = config("OPENAI_CHAT_MODEL", default="gpt-4o")
OPENAI_EMBED_MODEL = config("OPENAI_EMBED_MODEL", default="text-embedding-3-small")
OPENAI_PROJECT     = config("OPENAI_PROJECT", default="")

# --- BOIPA ---
BOIPA_MERCHANT_ID  = config('BOIPA_MERCHANT_ID')
BOIPA_PASSWORD     = config('BOIPA_PASSWORD')
BOIPA_TOKEN_URL    = config('BOIPA_TOKEN_URL')
HPP_FORM           = config('HPP_FORM')
NGROK              = config('NGROK', default='http://localhost:4040').rstrip('/')
BRAND_ID           = config('BRAND_ID')
BOIPA_PAYMENT_URL  = config('BOIPA_PAYMENT_URL')

CART_SESSION_ID = 'cart'

# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$swimtcsp',
        'USER': 'morganmck',
        'PASSWORD': config("DB_PASSWORD"),
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
        'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
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
