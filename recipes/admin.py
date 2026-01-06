from django.contrib import admin

# Register your models here.
from .models import Ingredient, Cuisine
admin.site.register(Ingredient)
admin.site.register(Cuisine)