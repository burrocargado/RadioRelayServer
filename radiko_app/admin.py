from django.contrib import admin

# Register your models here.
from .models import Station, Program

admin.site.register(Station)
admin.site.register(Program)
