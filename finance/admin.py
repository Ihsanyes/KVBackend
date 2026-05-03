from django.contrib import admin
from django.apps import apps

# Register your models here.

apps_model = apps.get_app_config('finance').get_models()
for model in apps_model:
    admin.site.register(model)
