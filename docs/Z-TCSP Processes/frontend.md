### Allauth Sign In
Google Development Console SwimTcsp (creditentials)
https://console.developers.google.com/
The templates for Allauth are kept in the templates directory.
There are two different signup views in Allauth:

1. account/signup.html
Used for regular email-based signups
Triggered at: /accounts/signup/<br>
2. socialaccount/signup.html
Used only after a user signs in with Google/Facebook and has not yet completed profile signup
Triggered after OAuth login, e.g. /accounts/google/login/
This is the form you're seeing in your screenshot

#### Remote Site Setup
Log in to Django Admin on your production site
Go to:
https://tcsp-morganmck.eu.pythonanywhere.com/admin/
1. Go to Sites
2. Find the entry where:
Domain: tcsp-morganmck.eu.pythonanywhere.com
Name: e.g. TCSP Production
3. If it doesn’t exist, create it.
Take note of the ID (e.g., 2).
Set SITE_ID in your production settings
4. In your production_settings.py (or wherever you're overriding for prod):

SITE_ID = 2  # Use the ID from the Sites admin (Remote as well?)
5. Add the Google Social App in Admin
Go to Social Accounts > Social Applications in the admin:

Provider: Google
Name: Google Login
Client ID and Secret: Use your credentials
Sites: Add the correct site (tcsp-morganmck.eu.pythonanywhere.com)