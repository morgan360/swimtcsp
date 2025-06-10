### Allauth Sign In
Google Development Console SwimTcsp (creditentials)
https://console.developers.google.com/
The templates for Allauth are kept in the templates directory.
There are two different signup views in Allauth:

1. account/signup.html
Used for regular email-based signups
Triggered at: /accounts/signup/
2. socialaccount/signup.html
Used only after a user signs in with Google/Facebook and has not yet completed profile signup
Triggered after OAuth login, e.g. /accounts/google/login/
This is the form you're seeing in your screenshot