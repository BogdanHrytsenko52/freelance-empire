from rest_framework import serializers

from .models import Company

PROTECTED_COMPANY_FIELDS = {
    "id",
    "owner",
    "balance",
    "reputation",
    "level",
    "completed_contracts",
    "created_at",
}


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "balance",
            "reputation",
            "level",
            "completed_contracts",
            "created_at",
        ]
        read_only_fields = fields


class CompanyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "balance",
            "reputation",
            "level",
            "completed_contracts",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "balance",
            "reputation",
            "level",
            "completed_contracts",
            "created_at",
        ]

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError(
                "Назва компанії має містити щонайменше 3 символи"
            )
        if Company.objects.filter(name__iexact=cleaned).exists():
            raise serializers.ValidationError(
                "Компанія з такою назвою уже існує"
            )
        return cleaned

    def validate(self, attrs):  # Цей валідатор лише для однієї компанії, один юзер не володіє багатьма компаніями
        request = self.context.get("request")
        if request and hasattr(request.user, "company"):
            raise serializers.ValidationError(
                "У вас уже є створена компанія"
            )  # Переписати за потреби
        return attrs


class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name"]

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError(
                "Назва компанії має містити хоча б 3 символи"
            )
        qs = Company.objects.filter(name__iexact=cleaned)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)  # Уникнення повтору назви компанії юзера
        if qs.exists():
            raise serializers.ValidationError(
                "Компанія з такою назвою уже існує"
            )
        return cleaned

    def validate(self, attrs):
        forbidden = sorted(set(self.initial_data.keys()) & PROTECTED_COMPANY_FIELDS)
        if forbidden:
            raise serializers.ValidationError(
                {field: "Це поле не можна змінювати напряму" for field in forbidden}
            )
        return attrs
