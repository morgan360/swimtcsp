## CSS not loading for Admin when DEBUG = False

```Python
STATIC_URL = '/static/'  # URL prefix for static files (e.g., CSS, JavaScript, images)
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')

MEDIA_URL = '/media/'

# Define the directory where uploaded media files are stored
MEDIA_ROOT = BASE_DIR / 'media'

```

pip install whitenoise

```Python
# settings.py
MIDDLEWARE = [
    # ... your other middleware ...
    'whitenoise.middleware.WhiteNoiseMiddleware',
]
```

### Reverse Lookup
Include App Namespace: If your categories view is located within an app and you're using the include() function with 
an app namespace in your project's urls.py, you need to include the app namespace when reversing the URL. For example, if your app is named 'lessons' and you've set the app namespace as 'lessons', the correct {% url %} tag might look like: {% url 'lessons:categories' %}