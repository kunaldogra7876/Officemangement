from django.contrib import admin
from .models import CustomUser, Profile, Role, UserRole, Department, Skills
# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(Department)
admin.site.register(Skills)
