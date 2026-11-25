from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "amount",
            "type",
            "description",
            "game_day",
            "created_at",
        ]
        read_only_fields = fields


class DailyFinanceStatSerializer(serializers.Serializer):
    game_day = serializers.IntegerField(read_only=True)
    income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    expenses = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class CompanyFinanceSummarySerializer(serializers.Serializer):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат відповіді GET /api/companies/me/finance/ — з Артемом):
    # Усі грошові поля віддаються рядками (DecimalField -> Money).
    # У daily_stats поле expenses віддається додатним числом ("1500.00"),
    # щоб на графіку Recharts стовпчики доходів і витрат будувалися зручно поруч,
    # а net = income - expenses може бути від'ємним.
    # =========================================================================
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_income = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_expenses = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    net_profit = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    daily_stats = DailyFinanceStatSerializer(many=True, read_only=True)
