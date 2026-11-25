from django.contrib import admin

from .models import ChatMessage, Contract


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("sender", "content", "is_fallback", "created_at")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "client_name",
        "company",
        "budget",
        "difficulty",
        "deadline",
        "status",
        "negotiations_count",
        "created_at",
    )
    list_filter = ("status", "difficulty")
    search_fields = ("title", "client_name", "company__name")
    readonly_fields = ("created_at", "accepted_at")
    inlines = [ChatMessageInline]
