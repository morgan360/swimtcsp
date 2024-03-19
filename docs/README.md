# Start a New Site

```
/| python3 -m venv venv | python3 -m venv venv |  |  |
| --- | --- | --- | --- |
| source venv/bin/activate | source venv/bin/activate |  |  |
| pip install django | pip install django |  |  |
| django-admin startproject core . | django-admin startproject core . |  |  |
| py http://manage.py startapp home | add home to settings |  |  |
| 'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'xxxxx',
        'USER': 'root',
        'PASSWORD': 'Morgan@8899',
        'HOST': 'localhost',
        'PORT': '3306',
    } |  |  |  |
| ALLOWED_HOSTS = ['*'] |  |  |  |
| make directory | templates
static
media |  |  |
| from django.shortcuts import render

def home(request):
    return render(request, 'home.html') | view in home |  |  |
| pip install mysqlclient |  |  |  |
| py http://manage.py/ makemigrations |  |  |  |
| py http://manage.py/ migrate |  |  |  |
| py http://manage.py createsuperuser |  |  |  |
| from django.urls import path
from .views import home

urlpatterns = [
    path('', home, name='home'),
] |  |  |  |
| path('', include('home.urls')),

from django.urls import path, include | core urls home |  |  |
| import os | import os |  |  |
| Settings

 | TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart',
            ],
        },
    },
] |  |  |
| pip install django-bootstrap-v5 | INSTALLED_APPS = (
    # ...
    "bootstrap5",
    # ...
) |  |  |
| pip install django-bootstrap-icons | INSTALLED_APPS = [
    'django_bootstrap_icons'
] |  |  |
| Static Files | STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"] |  |  |
| Media Files | MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
MEDIA_URL = '/media/' |  |  |
|  |  |  |  |
```
