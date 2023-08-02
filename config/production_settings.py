from config.base_settings import *

DATABASES = {
    'other': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'morganmck$swimtcsp',
        'USER': 'morganmck',
        'PASSWORD': str(os.getenv('DB_PASSWORD')),
        'HOST': 'morganmck.mysql.eu.pythonanywhere-services.com',
    }
}

DEBUG = False
ALLOWED_HOSTS = ['tcsp-morganmck.eu.pythonanywhere.com']
