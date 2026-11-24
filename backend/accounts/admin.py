"""Django admin configuration for role assignment by authorized staff."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class FreelanceEmpireUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Freelance Empire", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Freelance Empire", {"fields": ("email", "role")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
