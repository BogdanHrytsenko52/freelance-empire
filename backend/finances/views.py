from decimal import Decimal

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
# Додати унікальний ключ для кожної
from companies.permissions import HasCompany

from .models import Transaction, TransactionType
from .serializers import CompanyFinanceSummarySerializer, TransactionSerializer


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()

        queryset = Transaction.objects.filter(company=self.request.user.company)

        tx_type = self.request.GET.get("type")
        if tx_type:
            normalized_type = tx_type.lower().strip()
            if normalized_type not in set(TransactionType.values):
                return Transaction.objects.none()
            queryset = queryset.filter(type=normalized_type)

        game_day_param = self.request.GET.get("game_day")
        if game_day_param:
            try:
                game_day_value = int(game_day_param)
            except (TypeError, ValueError):
                return Transaction.objects.none()
            queryset = queryset.filter(game_day=game_day_value)

        return queryset


class CompanyFinanceView(generics.GenericAPIView):
    serializer_class = CompanyFinanceSummarySerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        queryset = Transaction.objects.filter(company=company)

        zero = Decimal("0.00")
        money_field = DecimalField(max_digits=12, decimal_places=2)

        totals = queryset.aggregate(
            total_income=Coalesce(
                Sum("amount", filter=Q(amount__gt=zero)),
                Value(zero),
                output_field=money_field,
            ),
            total_expenses_raw=Coalesce(
                Sum("amount", filter=Q(amount__lt=zero)),
                Value(zero),
                output_field=money_field,
            ),
        )

        total_income: Decimal = totals["total_income"]
        total_expenses: Decimal = abs(totals["total_expenses_raw"])
        net_profit: Decimal = total_income - total_expenses

        daily_rows = (
            queryset.values("game_day")
            .annotate(
                income=Coalesce(
                    Sum("amount", filter=Q(amount__gt=zero)),
                    Value(zero),
                    output_field=money_field,
                ),
                expenses_raw=Coalesce(
                    Sum("amount", filter=Q(amount__lt=zero)),
                    Value(zero),
                    output_field=money_field,
                ),
            )
            .order_by("game_day")
        )

        daily_stats = [
            {
                "game_day": row["game_day"],
                "income": row["income"],
                "expenses": abs(row["expenses_raw"]),
                "net": row["income"] - abs(row["expenses_raw"]),
            }
            for row in daily_rows
        ]

        summary_data = {
            "balance": company.balance,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "daily_stats": daily_stats,
        }
        serializer = self.get_serializer(summary_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
