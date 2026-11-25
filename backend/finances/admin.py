from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "type", "amount", "game_day", "created_at")
    list_filter = ("type", "game_day")
    search_fields = ("company__name", "description")
    readonly_fields = ("created_at",)
