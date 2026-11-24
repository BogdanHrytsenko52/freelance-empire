"""Server-owned event templates; text can later be varied by AI, never effects."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EventCategory(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class EventChoice:
    code: str
    effects: tuple[tuple[str, Decimal | int], ...]


@dataclass(frozen=True)
class EventTemplate:
    code: str
    category: EventCategory
    title: str
    duration_days: int
    weight: int
    choices: tuple[EventChoice, ...]


def _choices(*items):
    return tuple(EventChoice(*item) for item in items)


TEMPLATES = (
    EventTemplate(
        "client_referral",
        EventCategory.POSITIVE,
        "Client referral",
        2,
        3,
        _choices(("accept", (("reputation", 3),)), ("decline", (("reputation", 0),))),
    ),
    EventTemplate(
        "team_motivation",
        EventCategory.POSITIVE,
        "Team motivation",
        2,
        3,
        _choices(
            ("support", (("productivity", Decimal("1.2")),)),
            ("ignore", (("productivity", Decimal("1.0")),)),
        ),
    ),
    EventTemplate(
        "unexpected_reward",
        EventCategory.POSITIVE,
        "Unexpected reward",
        1,
        2,
        _choices(
            ("accept", (("balance", Decimal("500")),)), ("donate", (("reputation", 2),))
        ),
    ),
    EventTemplate(
        "employee_illness",
        EventCategory.NEGATIVE,
        "Employee illness",
        3,
        3,
        _choices(
            ("rest", (("productivity", Decimal("0.5")),)),
            ("reassign", (("reputation", -1),)),
            ("pressure", (("reputation", -3),)),
        ),
    ),
    EventTemplate(
        "equipment_failure",
        EventCategory.NEGATIVE,
        "Equipment failure",
        2,
        2,
        _choices(
            ("repair", (("balance", Decimal("-300")),)),
            ("workaround", (("productivity", Decimal("0.7")),)),
        ),
    ),
    EventTemplate(
        "critical_bug",
        EventCategory.NEGATIVE,
        "Critical bug",
        2,
        2,
        _choices(("fix", (("task_progress", -1),)), ("defer", (("reputation", -2),))),
    ),
    EventTemplate(
        "burnout",
        EventCategory.NEGATIVE,
        "Burnout",
        3,
        2,
        _choices(
            ("recover", (("productivity", Decimal("0.5")),)),
            ("ignore", (("reputation", -2),)),
        ),
    ),
    EventTemplate(
        "training",
        EventCategory.NEUTRAL,
        "Training offer",
        2,
        2,
        _choices(
            ("attend", (("balance", Decimal("-200")),)), ("skip", (("reputation", 0),))
        ),
    ),
    EventTemplate(
        "scope_change",
        EventCategory.NEUTRAL,
        "Scope change",
        2,
        2,
        _choices(
            ("accept", (("task_progress", -1),)), ("decline", (("reputation", -1),))
        ),
    ),
    EventTemplate(
        "marketing",
        EventCategory.NEUTRAL,
        "Marketing campaign",
        2,
        2,
        _choices(
            ("fund", (("balance", Decimal("-400")),)), ("skip", (("reputation", 0),))
        ),
    ),
)
