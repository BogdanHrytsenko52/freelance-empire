"""Pure Decimal economic calculations, independent of unavailable ORM models."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

MONEY_QUANTUM = Decimal("0.01")
GAME_DAYS_PER_MONTH = Decimal("30")
STARTING_COMPANY_BALANCE = Decimal("100000.00")


def money(value: Decimal | int | str) -> Decimal:
    """Normalize monetary inputs to two decimal places without floats."""
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_profit(
    total_income: Decimal | int | str, total_expenses: Decimal | int | str
) -> Decimal:
    """Return income minus expenses according to the shared money policy."""
    return money(money(total_income) - money(total_expenses))


def calculate_contract_payment(
    agreed_budget: Decimal | int | str,
    quality_bonus: Decimal | int | str = Decimal("0"),
    penalties: Decimal | int | str = Decimal("0"),
) -> Decimal:
    """Return agreed budget plus bonuses minus any final penalties exactly once."""
    return money(money(agreed_budget) + money(quality_bonus) - money(penalties))


def calculate_daily_salary_cost(
    monthly_salaries: Iterable[Decimal | int | str],
) -> Decimal:
    """Calculate one game-day salary cost from monthly salaries over 30 days."""
    monthly_total = sum((money(salary) for salary in monthly_salaries), Decimal("0"))
    return money(monthly_total / GAME_DAYS_PER_MONTH)


def can_afford_optional_cost(
    balance: Decimal | int | str, cost: Decimal | int | str
) -> bool:
    """Mandatory costs may create debt; this helper is for optional purchases only."""
    return money(balance) >= money(cost)
