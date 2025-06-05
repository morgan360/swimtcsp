# Accounts
[Index](index.md)

We are using the Customer User Model (AbstractBaseUser) withn a one to one 
extension to profile.
[video](https://www.youtube.com/watch?v=Ae7nc1EGv-A)


When you define a custom user model in Django, you need to update any fields 
in other models that have relations with the user model to use the <span style="color: red;">settings.AUTH_USER_MODEL </span> instead of auth.User. This is required to avoid conflicts and ensure proper integration with your custom user model.

[Web Site](https://medium.com/@ksarthak4ever/django-custom-user-model-allauth-for-oauth-20c84888c318)

 ```Python
from users import User
from customuser.settings import AUTH_USER_MODEL
use the get_user_model() method from django.contrib.auth
```