from config.base_settings import *
from dotenv import load_dotenv
load_dotenv()  # loads the configs from .env

DATABASES = {
    'other': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$swimtcsp',
        'USER': 'morganmck',
        'PASSWORD': 'Mango@8899',
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
    }
}

DEBUG = False
ALLOWED_HOSTS = ['tcsp-morganmck.eu.pythonanywhere.com']