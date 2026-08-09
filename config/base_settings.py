"""
BASE SETTINGS
"""
import os
import subprocess
from pathlib import Path
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DB_PASSWORD = config('DB_PASSWORD')  # no need for str(), config returns string


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Get version from git tags
def get_git_version():
    """
    Get version from git describe.
    Returns tag if on a tagged commit, otherwise tag + commit hash.
    Example: 'v1.0.0' or 'v1.0.0-5-g1a2b3c4'
    """
    try:
        version = subprocess.check_output(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        return version
    except:
        # Fallback if git not available or no tags exist
        return 'unknown'

VERSION = get_git_version()

# -------------------------
# OpenAI / chatbot
# -------------------------
# Single source of truth for every environment. Previously each settings file
# declared its own OpenAI block with a different default, and chatbot/views.py
# preferred os.getenv() over these values — so which model actually ran depended
# on whether the process environment happened to carry the variable. Read these
# through chatbot.helpers.client only.
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_CHAT_MODEL = config('OPENAI_CHAT_MODEL', default='gpt-5.4-mini')
OPENAI_EMBED_MODEL = config('OPENAI_EMBED_MODEL', default='text-embedding-3-small')
OPENAI_PROJECT = config('OPENAI_PROJECT', default='')

# FAQ retrieval tiers. A query is embedded once and scored against every FAQ:
#   >= FAQ_MATCH_THRESHOLD  -> serve the stored answer verbatim (no model call)
#   >= FAQ_MIN_CONFIDENCE   -> serve it, but hedged ("I'm not certain, but...")
#   below that              -> call the model, with any FAQ scoring above
#                              FAQ_CONTEXT_MIN_SCORE injected as grounding
#
# Calibrated by scoring 200 real historical questions from ChatbotQuery against
# the live FAQ set (see `manage.py faq_calibrate`):
#   0.73+       reliably the right entry — near-identical wording lands 0.88-1.00
#               ("Do i need to wear a swimming hat" 0.948, "What's coached lanes?"
#               0.895), and everything down to 0.748 was still correct
#   0.65-0.73   right topic, often the neighbouring entry ("What ages are the
#               swim lessons for?" matching the public-swim age FAQ at 0.727) —
#               worth showing, but only with a hedge
#   0.55-0.65   related enough to ground a prompt, not to quote. Below 0.65 the
#               wrong matches start ("lockers" -> showers at 0.634)
#   below 0.55  unrelated
# These rose from 0.68/0.58/0.50 when the query prefix was removed — see
# faq_index.query_text. Re-run faq_calibrate after any material corpus change,
# and re-calibrate from scratch if the embedding text on either side changes.
FAQ_MATCH_THRESHOLD = float(config('FAQ_MATCH_THRESHOLD', default=0.73))
FAQ_MIN_CONFIDENCE = float(config('FAQ_MIN_CONFIDENCE', default=0.65))
FAQ_CONTEXT_MIN_SCORE = float(config('FAQ_CONTEXT_MIN_SCORE', default=0.55))

# Both chatbot endpoints are public and every message spends OpenAI credits.
CHATBOT_MAX_MESSAGES_PER_HOUR = int(config('CHATBOT_MAX_MESSAGES_PER_HOUR', default=30))
CHATBOT_MAX_MESSAGE_CHARS = int(config('CHATBOT_MAX_MESSAGE_CHARS', default=500))

# Set the URL prefix for static files
STATIC_URL = '/static/'

# Specify the directory where static files are collected
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')

# Specify additional directories to search for static files
STATICFILES_DIRS = [
    BASE_DIR / "static",           # your global assets
]

MEDIA_URL = '/media/'

# Specify the directory where uploaded media files are stored
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },

    'handlers': {
        'chatbot_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'application.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },

    'loggers': {
        'chatbot': {  # anything under chatbot.* will use this
            'handlers': ['chatbot_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Application definition

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    # pre installed
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Allauth
    # Installed Apps
    "ckeditor",
     # Core Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Providers (optional)
    'allauth.socialaccount.providers.google',
    "crispy_forms",
    'import_export',
    "phonenumber_field",
    'django_filters',
    'django_admin_listfilter_dropdown',
    'hijack',
    'hijack.contrib.admin',  # add to admin panel
    'widget_tweaks', # Allows adding css to fields in form templates directly
    'django_recaptcha',
    'django_browser_reload',  # when debug load automaticaly browser
    'django_extensions', # For Documentation
    'rest_framework',
    'rangefilter',
    # My Apps
    'chatbot',
    'users',
    'home',
    'lessons',
    'lessons_orders',
    'swims',
    'swims_orders',
    'lessons_bookings',
    'timetable',
    'reports',
    'schools',
    'schools_bookings',
    'schools_orders',
    'shopping_cart',
    'boipa',
    'waiting_list',
    'navigation',
    'dashboard',
    'swimling_dashboard',
    'progress',
    'instructors',
    'coupons',
    'mailchimp',
    'anseo',
    "maintenance_mode",
    'finances',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'utils.middleware.PaymentGatewaySessionMiddleware',  # ✅ Must be after SessionMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # ✅ REQUIRED for django-allauth v65+
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hijack.middleware.HijackUserMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    'utils.middleware.SetSessionExpiryMiddleware',  # ✅ Your custom one
    'utils.middleware.CustomErrorPageMiddleware',   # Render 401/503 templates
# Maintanence mode toggle python manage.py maintenance_mode off/on
    "maintenance_mode.middleware.MaintenanceModeMiddleware"

]



REMOTE_TCSP_DB = {
    'HOST': config('REMOTE_TCSP_DB_HOST'),
    'PORT': config('REMOTE_TCSP_DB_PORT', cast=int),
    'USER': config('REMOTE_TCSP_DB_USER'),
    'PASSWORD': config('REMOTE_TCSP_DB_PASSWORD'),
    'NAME': config('REMOTE_TCSP_DB_NAME'),
    'CHARSET': config('REMOTE_TCSP_DB_CHARSET'),
}

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                # `allauth` needs this from django
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Mine
                'utils.context_processors.get_term_info',
                'utils.context_processors.term_status_for_active_schools',
                'utils.context_processors.footer_message',
                # 'utils.context_processors.current_term',
            ],
        },
    },
]



WSGI_APPLICATION = 'core.wsgi.application'

# Use our CSRF failure view so 403s show our template
CSRF_FAILURE_VIEW = 'core.error_handlers.csrf_failure_view'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default Django auth
    'allauth.account.auth_backends.AuthenticationBackend',  # Allauth auth
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/Dublin'

USE_I18N = True

USE_TZ = True

# European Date Format (e.g., 31/12/2023)
DATE_FORMAT = 'd/m/Y'

# You can also set the short date format
SHORT_DATE_FORMAT = 'd/m/Y'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/


# Define the directory where Django should collect and store static files
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# New format for Django AllAuth ≥ 0.61+ compatibility
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/m',  # You had limit = 5 and timeout = 300 sec
}

ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = False
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_SIGNUP_REQUIRED_FIELDS = ['first_name']
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Disable Sites framework requirement for allauth
ALLAUTH_USESITES = False

#  Allauth social accounts
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'APP': {
            'client_id': config("GOOGLE_CLIENT_ID"),
            'secret': config("GOOGLE_CLIENT_SECRET"),
            'key': ''
        }
    }, 'facebook': {
        'METHOD': 'oauth2',
        # 'SDK_URL': '//connect.facebook.net/{locale}/sdk.js',
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
        'INIT_PARAMS': {'cookie': True},
        'FIELDS': [
            'id',
            'first_name',
            'last_name',
            'middle_name',
            'name',
            'name_format',
            'picture',
            'short_name'
        ],
        'EXCHANGE_TOKEN': True,
        # 'LOCALE_FUNC': 'path.to.callable',
        'VERIFIED_EMAIL': False,
        'VERSION': 'v13.0',
        'GRAPH_API_URL': 'https://graph.facebook.com/v13.0',
    }
}
ACCOUNT_FORMS = {
    'signup': 'users.forms.CustomSignupForm',
}
# Without this, a Google signup uses allauth's stock form and asks for no phone
# number, so the requirement on the email signup form was only ever half of the
# door. SOCIALACCOUNT_AUTO_SIGNUP is False, so this form is genuinely shown.
SOCIALACCOUNT_FORMS = {
    'signup': 'users.forms.CustomSocialSignupForm',
}
SOCIALACCOUNT_ADAPTER = "users.adapters.AutoLinkSocialAccountAdapter"

# # CrispyForms

# ***  E-Commerce

# AXES PARAMETERS
AXES_FAILURE_LIMIT = 5  # Number of attempts before lockout
# AXES_LOCKOUT_TEMPLATE = 'your_lockout_template.html'  # Optional: Custom template to show on lockout
AXES_USERNAME_FORM_FIELD = 'login'

AXES_LOCKOUT_TEMPLATE = 'account/lockout.html'

# How cart sessions are stored
CART_SESSION_ID = 'cart'
# BOIPA_MERCHANT_ID=100121
# BRAND_ID=1001210000
# BOIPA_PASSWORD='qWGEJQQAkhROSTGpwS5O'
# BOIPA_TOKEN_URL="https://apiuat.test.boipapaymentgateway.com/token"
# BOIPA_PAYMENT_URL='https://apiuat.test.boipapaymentgateway.com/payments'
# HPP_FORM='https://cashierui-apiuat.test.boipapaymentgateway.com/'
# NGROK ='https://tcsp-morganmck.eu.pythonanywhere.com/'

# How many records can you upload
DATA_UPLOAD_MAX_NUMBER_FIELDS = 12000

# HIJACK APP
HIJACK_LOGIN_REDIRECT_URL = '/'
HIJACK_LOGOUT_REDIRECT_URL = '/users/user/'
HIJACK_DISPLAY_ADMIN_BUTTON = True
HIJACK_USE_BOOTSTRAP = False
HIJACK_REGISTER_ADMIN = False
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_URL_ALLOWED_ATTRIBUTES = ['username', ]
HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_and_staff"


# Default Email
DEFAULT_SUPPORT_EMAIL = "swimming@tcsp.ie"
# Mailchimp
MAILCHIMP_API_KEY = config("MAILCHIMP_API_KEY")
MAILCHIMP_SERVER_PREFIX = config("MAILCHIMP_SERVER_PREFIX")
MAILCHIMP_LIST_ID = config("MAILCHIMP_LIST_ID")

# Already done, but double check:
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_AGE = 86400

MAINTENANCE_MODE_IGNORE_URLS = (
    r'^/admin/.*',                 # allow all admin pages
    r'^/accounts/login/?$',        # Django default login
    r'^/accounts/logout/?$',       # Django default logout
    r'^/accounts/password_reset/?$',  # Django default password reset
    r'^/users/login/?$',           # your custom login if used
)


# Allow superusers and staff to bypass the maintenance page
MAINTENANCE_MODE_IGNORE_SUPERUSER = True
MAINTENANCE_MODE_IGNORE_STAFF = True

# Whitelist trusted IPs (your home/office or PythonAnywhere server)
MAINTENANCE_MODE_IGNORE_IP_ADDRESSES = [
    "3.248.36.76",   # tcsp.ie root domain resolves here
    "18.194.5.49",   # PythonAnywhere webapp server
    # add your home IP too if needed
]

# Google reCAPTCHA v2
RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY')

# Phone numbers
#
# These belong here rather than in a per-environment file. They were previously
# set in local_settings only, so dev and production ran with no default region:
# `PhoneNumberField.get_prep_value` had nothing to parse a bare national number
# like "0851639462" against, and silently stored the raw string instead of a
# valid number. Roughly 4,600 guardian numbers ended up unreadable that way and
# had to be repaired by `manage.py normalise_phone_numbers`.
#
# Every number is Irish, so IE is the region to fall back on when one is written
# without a country code. Storing E.164 keeps the value unambiguous even if the
# region is ever wrong or missing.
PHONENUMBER_DEFAULT_REGION = 'IE'
PHONENUMBER_DB_FORMAT = 'E164'
