from django.contrib import admin
from authentication.models import UserProfile, PrivyProfile


admin.site.register(UserProfile)
admin.site.register(PrivyProfile)
