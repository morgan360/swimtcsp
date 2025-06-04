# Setup Instructions


## Backend Setup

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Key libraries:
- Django 4.2.3
- django-allauth
- django-import-export
- crispy-bootstrap4 / crispy-bootstrap5
- django-hijack
- django-tailwind
- django-widget-tweaks
- mysqlclient (or pymysql)

## Frontend Setup

Install frontend dependencies:
```bash
npm install tailwindcss postcss autoprefixer
```

Add `tailwind.config.js` and PostCSS setup in `theme/static_src/`.

## Optional Tools
- Jupyter, ipykernel, etc. (for notebooks)
- python-dotenv (for managing .env files)
#

# 🛠 Developer Setup Notes (MySQL + Python Virtualenv)

### ✅ Python Version Compatibility
- Use a consistent Python version across all environments.
- Recommended: `Python 3.12`
- To install and verify:
  ```bash
  brew install python@3.12
  which python3.12
  python3.12 --version
