# Create a New Project

[Index](index.md)

| What For                 | Command                                                                                                                                                                            |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Create Project Directory | MD ...                                                                                                                                                                             |
| New Environment          | python3 -m venv venv                                                                                                                                                               |
| Activate env             | source venv/bin/activate                                                                                                                                                           |
| Install                  | pip install django                                                                                                                                                                 |
| Start a project          | django-admin startproject core .                                                                                                                                                   |
| New App                  | py manage.py startapp home                                                                                                                                                         |
| Database                 | <p>'default': { 'ENGINE': 'django.db.backends.mysql',<br>'NAME': 'xxxxx',<br>'USER': 'root',<br>'PASSWORD': 'Morgan@8899',<br>'HOST': 'localhost',<br>'PORT': '3306',<br>}<br></p> |
| Config                   | ALLOWED\_HOSTS = \['\*']                                                                                                                                                           |
| Make Directories         | templates,static,media                                                                                                                                                             |
| View in Home             | <p>from django.shortcuts import render<br>def home(request):<br>return render(request, 'home.html')</p>                                                                            |
| Needed for MySql         | pip install mysqlclient                                                                                                                                                            |
| Note                     | Set up Custom User before Migrations                                                                                                                                               |
| make file                | py manage.py makemigrations                                                                                                                                                        |
| apply file               | py manage.py migrate                                                                                                                                                               |
| Create User              | py manage.py createsuperuser                                                                                                                                                       |
| urls.py                  | [Go to Code](newproject.md#url-code)                                                                                                                                               |
| Settings                 | [Go to Code](newproject.md#settings)                                                                                                                                               |
| Install Bootstrap        | pip install django-bootstrap-v5                                                                                                                                                    |
| Add to settings          | "bootstrap5",                                                                                                                                                                      |
| Install Icons            | pip install django-bootstrap-icons                                                                                                                                                 |
| Add to Settings          | 'django\_bootstrap\_icons',                                                                                                                                                        |
| Static Files             | <p>STATIC_URL = 'static/'<br>STATICFILES_DIRS = [BASE_DIR / "static"]</p>                                                                                                          |
| Media Files              | <p>MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')<br>MEDIA_URL = '/media/'</p>                                                                                                      |

### Url-Code

```Python
from django.urls import path,include
from .views import home

urlpatterns = [
    path('', home, name='home'),
```

### Settings

```Python
import OS

TEMPLATES = [
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
]
```

### STATIC and MEDIA cofiguration

```Python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('blog/', include('blog.urls', namespace='blog')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Settings for Media and Static

```Phyton
# Set the URL prefix for static files
STATIC_URL = '/static/'

# Define the directory where Django should collect and store static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Define additional directories where Django should look for static files during development
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # Add any other directories if needed
]

MEDIA_URL = '/media/'

# Define the directory where uploaded media files are stored
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### Transfering site

pip freeze > requirements.txt
