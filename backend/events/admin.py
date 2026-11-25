from django.contrib import admin

from .models import CompanyEvent, EventChoice, EventEffect, EventTemplate


class EventChoiceInline(admin.TabularInline):
    model = EventChoice
    extra = 1


class EventEffectInline(admin.TabularInline):
    model = EventEffect
    extra = 1


@admin.register(EventTemplate)
class EventTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "kind", "weight", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("title", "description")
    inlines = [EventChoiceInline]


@admin.register(EventChoice)
class EventChoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "text")
    search_fields = ("text", "template__title")
    inlines = [EventEffectInline]


@admin.register(CompanyEvent)
class CompanyEventAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "template", "status", "created_at", "resolved_at")
    list_filter = ("status", "template__kind")
    search_fields = ("company__name", "template__title")
    readonly_fields = ("created_at", "resolved_at")
