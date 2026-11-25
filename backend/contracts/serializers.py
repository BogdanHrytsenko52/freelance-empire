from rest_framework import serializers

from .models import Contract


class ContractClientSerializer(serializers.Serializer):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат об'єкта client — з Артемом і Богданом):
    # У game.ts Артем очікує client: { name: string }.
    # Додатково передаємо personality та bio для сторінки переговорів із NPC
    # (у TypeScript зайві поля не ламають інтерфейс { name: string }).
    # Якщо винесемо NPC в окрему модель NpcClient — просто замінимо цей клас
    # на ModelSerializer для NpcClient без зміни формату JSON.
    # =========================================================================
    name = serializers.CharField(source="client_name", read_only=True)
    personality = serializers.CharField(source="client_personality", read_only=True)
    bio = serializers.CharField(source="client_bio", read_only=True)


class ContractSerializer(serializers.ModelSerializer):
    client = ContractClientSerializer(source="*", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id",
            "client",
            "title",
            "description",
            "budget",
            "difficulty",
            "deadline",
            "requirements",
            "status",
            "negotiations_count",
            "created_at",
            "accepted_at",
        ]
        read_only_fields = fields
