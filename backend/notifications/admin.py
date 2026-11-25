from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("company__name", "title", "text")
    readonly_fields = ("created_at",)
