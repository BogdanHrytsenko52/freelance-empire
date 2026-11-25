from rest_framework import serializers

from companies.models import Company


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    place = serializers.IntegerField(read_only=True)
    company_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Company
        fields = [
            "place",
            "company_id",
            "name",
            "reputation",
            "balance",
            "completed_contracts",
        ]
        read_only_fields = fields
