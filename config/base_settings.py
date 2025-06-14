"""
BASE SETTINGS
"""
import os
SESSION_SAVE_EVERY_REQUEST = True
from pathlib import Path
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DB_PASSWORD = config('DB_PASSWORD')  # no need for str(), config returns string


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Set the URL prefix for static files
STATIC_URL = '/static/'

# Specify the directory where static files are collected
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')

# Specify additional directories to search for static files
import os

STATICFILES_DIRS = [
    BASE_DIR / "static",           # your global assets
]


MEDIA_URL = '/media/'

# Specify the directory where uploaded media files are stored
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



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
    'django_browser_reload',  # when debug load automaticaly browser
    'django_extensions', # For Documentation
    # My Apps
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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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

# ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300
SOCIALACCOUNT_AUTO_SIGNUP = False
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_SIGNUP_REQUIRED_FIELDS = ['first_name']
# disable sign out confirmation
ACCOUNT_LOGOUT_ON_GET = True
# # disable sign in confirmation
SOCIALACCOUNT_LOGIN_ON_GET = True
# # ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USERNAME_REQUIRED = False
# #
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_AUTHENTICATION_METHOD = 'email'
# Will remember you
# ACCOUNT_SESSION_REMEMBER = True

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
SOCIALACCOUNT_ADAPTER = "users.adapters.AutoLinkSocialAccountAdapter"

# # CrispyForms
# CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
#
# CRISPY_TEMPLATE_PACK = 'bootstrap5'

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
HIJACK_USE_BOOTSTRAP = True
HIJACK_REGISTER_ADMIN = False
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_URL_ALLOWED_ATTRIBUTES = ['username', ]
HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_and_staff"
