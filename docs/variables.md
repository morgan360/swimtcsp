[Index](index.md)

[enviornment variable](https://dev.to/earthcomfy/django-how-to-keep-secrets-safe-with-python-dotenv-5811)


pip install python-dotenv
create a .env in your root directory

SECRET_KEY = str(os.getenv('SECRET_KEY'))

- This is stored in manage.py, wsgi.py and asgi.py <br>
- DJANGO_SETTINGS_MODULE = str(os.getenv('SECRET_KEY'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                         str(os.getenv('DJANGO_SETTINGS_MODULE')))
- DJANGO_SETTINGS_MODULE = 'config.local_settings'
- DJANGO_SETTINGS_MODULE = 'config.production_settings'
- ./manage.py migrate

### Setup for Manage.py

```Python
def main():
    from dotenv import load_dotenv
    load_dotenv()  # loads the configs from .env
    """Run administrative tasks. Settings Location is stored in .env as DJANGO_SETTINGS_MODULE"""

    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                           str(os.getenv('DJANGO_SETTINGS_MODULE')))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

```