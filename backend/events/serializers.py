from rest_framework import serializers

from .models import CompanyEvent, EventChoice


class EventChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventChoice
        fields = ["id", "text"]
        read_only_fields = fields


class CompanyEventSerializer(serializers.ModelSerializer):
    # Витягуємо поля з шаблону на верхній рівень JSON
    title = serializers.CharField(source="template.title", read_only=True)
    description = serializers.CharField(source="template.description", read_only=True)
    kind = serializers.CharField(source="template.kind", read_only=True)
    choices = EventChoiceSerializer(source="template.choices", many=True, read_only=True)
    chosen_option_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = CompanyEvent
        fields = [
            "id",
            "title",
            "description",
            "kind",
            "status",
            "choices",
            "chosen_option_id",
            "applied_effects",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = fields


class ChooseEventOptionSerializer(serializers.Serializer):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат тіла POST /api/events/{id}/choose/ — з Артемом):
    # Закладаємо стандартний формат {"choice_id": <int>}.
    # =========================================================================
    choice_id = serializers.IntegerField(min_value=1)
