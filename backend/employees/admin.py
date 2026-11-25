from django.contrib import admin

from .models import Candidate, Employee, EmployeeSkill


class EmployeeSkillInline(admin.TabularInline):
    model = EmployeeSkill
    extra = 1


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "company",
        "specialization",
        "level",
        "salary",
        "productivity",
        "availability",
        "hired_at",
    )
    list_filter = ("specialization", "level", "availability")
    search_fields = ("name", "company__name")
    readonly_fields = ("hired_at",)
    inlines = [EmployeeSkillInline]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "specialization",
        "level",
        "expected_salary",
        "is_available",
        "created_at",
    )
    list_filter = ("specialization", "level", "is_available")
    search_fields = ("name",)
    readonly_fields = ("created_at",)
