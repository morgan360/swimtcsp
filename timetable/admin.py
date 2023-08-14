from django.contrib import admin
from .models import Events  # Import your model


@admin.register(Events)
class YourModelNameAdmin(admin.ModelAdmin):
    pass
