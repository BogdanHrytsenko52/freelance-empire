from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class TransactionType(models.TextChoices):
    CONTRACT_PAYMENT = "contract_payment", "Contract Payment"
    SALARY = "salary", "Salary"
    OPERATING_EXPENSE = "operating_expense", "Operating Expense"
    PENALTY = "penalty", "Penalty"
    EVENT_REWARD = "event_reward", "Event Reward"
    EVENT_COST = "event_cost", "Event Cost"


class Transaction(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (знак суми amount — з Богданом та Артемом):
    # Варіант 1 (поточний, під game.ts Артема): сума зберігається зі знаком:
    #   дохід > 0 (contract_payment, event_reward),
    #   витрата < 0 (salary, operating_expense, penalty, event_cost).
    # Варіант 2: зберігати завжди додатне число, а знак визначати за полем type.
    # Якщо Богдан у simulation/economy.py створюватиме витрати з плюсом,
    # потрібно узгодити один формат до інтеграції.
    # =========================================================================
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
    )
    description = models.CharField(max_length=255, blank=True, default="")
    game_day = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-game_day", "-created_at"]
        indexes = [
            models.Index(fields=["company", "game_day"]),
            models.Index(fields=["company", "type"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount=Decimal("0.00")),
                name="transaction_amount_non_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(game_day__gte=1),
                name="transaction_game_day_min_1",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.type}] {self.amount} (day {self.game_day}, {self.company.name})"
