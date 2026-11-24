"""Pure game-day deadline, penalty, and notification instructions."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .economy import money

DAILY_PENALTY_RATE = Decimal("0.02")
MAX_PENALTY_RATE = Decimal("0.30")


class DeadlineEvent(StrEnum):
    APPROACHING = "deadline_approaching"
    OVERDUE = "deadline_overdue"
    COMPLETED_ON_TIME = "completed_on_time"
    COMPLETED_LATE = "completed_late"


@dataclass(frozen=True)
class DeadlineResult:
    days_until_deadline: int
    overdue_days: int
    completed_on_time: bool | None
    event: DeadlineEvent | None


def deadline_result(
    *,
    current_day: int,
    deadline_day: int,
    completed_day: int | None = None,
    approaching_days: int = 2,
) -> DeadlineResult:
    """Evaluate an in-game deadline; completion on deadline day is on time."""
    effective_day = completed_day if completed_day is not None else current_day
    overdue = max(0, effective_day - deadline_day)
    on_time = None if completed_day is None else overdue == 0
    if completed_day is not None:
        event = (
            DeadlineEvent.COMPLETED_ON_TIME if on_time else DeadlineEvent.COMPLETED_LATE
        )
    elif overdue:
        event = DeadlineEvent.OVERDUE
    elif deadline_day - current_day <= approaching_days:
        event = DeadlineEvent.APPROACHING
    else:
        event = None
    return DeadlineResult(deadline_day - current_day, overdue, on_time, event)


def penalty_for_overdue_days(
    *, agreed_budget: Decimal | int | str, overdue_days: int
) -> Decimal:
    """Return the capped final-payment penalty, not a standalone debit instruction."""
    rate = min(Decimal(max(0, overdue_days)) * DAILY_PENALTY_RATE, MAX_PENALTY_RATE)
    return money(Decimal(agreed_budget) * rate)
