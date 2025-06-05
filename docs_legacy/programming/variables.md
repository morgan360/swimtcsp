# variables

[Index](../index.md)

[enviornment variable](https://dev.to/earthcomfy/django-how-to-keep-secrets-safe-with-python-dotenv-5811)

pip install python-dotenv create a .env in your root directory

SECRET\_KEY = str(os.getenv('SECRET\_KEY'))

* This is stored in manage.py, wsgi.py and asgi.py\

* DJANGO\_SETTINGS\_MODULE = str(os.getenv('SECRET\_KEY')) os.environ.setdefault('DJANGO\_SETTINGS\_MODULE', str(os.getenv('DJANGO\_SETTINGS\_MODULE')))
* DJANGO\_SETTINGS\_MODULE = 'config.local\_settings'
* DJANGO\_SETTINGS\_MODULE = 'config.production\_settings'
* ./manage.py migrate

#### Setup for Manage.py

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
