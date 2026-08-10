from django.contrib import admin
from .models import CustomUser, Profile, Role, UserRole, Department, Skills


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email")
    search_fields = ("username", "email", "first_name", "last_name")


admin.site.register(Profile)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(Department)
admin.site.register(Skills)