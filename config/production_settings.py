from config.base_settings import *
from dotenv import load_dotenv
import os
import logging
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# Initialize environ
env = environ.Env()
# Reading .env file
env_file = os.path.join(BASE_DIR, '.env')
env.read_env(env_file)  # Provide the path to the .env file

# Environment variables
BOIPA_MERCHANT_ID = env('BOIPA_MERCHANT_ID')
BOIPA_PASSWORD = env('BOIPA_PASSWORD')
BOIPA_TOKEN_URL = env('BOIPA_TOKEN_URL')
HPP_FORM = env('HPP_FORM')
NGROK = env('NGROK', default='http://localhost:4040')

load_dotenv()  # loads the configs from .env

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$swimtcsp',
        'USER': 'morganmck',
        'PASSWORD': os.getenv("DB_PASSWORD"),  # Ensures the password is read from environment variables
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },  # Make sure to close the OPTIONS dictionary correctly
    }
}

DEBUG = False
ALLOWED_HOSTS = ['tcsp-morganmck.eu.pythonanywhere.com']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True  # Use TLS (True for Gmail)
EMAIL_HOST_USER = 'morganmcknight@gmail.com'  # Your Gmail email address
EMAIL_HOST_PASSWORD = 'rkjxohiawwncphgp'  # Your Gmail password or an app password
EMAIL_USE_SSL = False

PAYMENTS_LOG_FILE_PATH =  '/home/morganmck/swimtcsp/logs/payments.log'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'payments_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': PAYMENTS_LOG_FILE_PATH,
            'formatter': 'detailed',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'formatters': {
        'detailed': {
            'format': '{asctime} {levelname} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'payments': {
            'handlers': ['payments_file'],
            'level': 'DEBUG',
            'propagate': False,  # Prevent the payment logs from propagating to the root logger
        },
    },
}




FOOTER_MESSAGE = "Production Version"
