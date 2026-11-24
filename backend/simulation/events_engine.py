"""Deterministic event selection and resolution DTOs, independent of ORM."""

from dataclasses import dataclass
from decimal import Decimal
from random import Random

from .event_templates import TEMPLATES, EventTemplate

EVENT_CHANCE = Decimal("0.15")
MAX_ACTIVE_EVENTS = 2


@dataclass(frozen=True)
class ActiveEvent:
    key: str
    template: EventTemplate
    started_day: int
    status: str = "pending"

    @property
    def expires_day(self):
        return self.started_day + self.template.duration_days


def generate_event(
    *,
    company_id: str,
    game_day: int,
    active_events: list[ActiveEvent],
    rng: Random,
    eligible: set[str] | None = None,
) -> ActiveEvent | None:
    """Select at most one eligible event per company-day with a stable key."""
    if len(
        [item for item in active_events if item.status == "pending"]
    ) >= MAX_ACTIVE_EVENTS or rng.random() >= float(EVENT_CHANCE):
        return None
    candidates = [
        item
        for item in TEMPLATES
        if (eligible is None or item.code in eligible)
        and not any(
            event.template.code == item.code and event.status == "pending"
            for event in active_events
        )
    ]
    if not candidates:
        return None
    template = rng.choices(
        candidates, weights=[item.weight for item in candidates], k=1
    )[0]
    return ActiveEvent(
        f"event:{company_id}:{game_day}:{template.code}", template, game_day
    )


def resolve_event(
    event: ActiveEvent, *, choice_code: str, game_day: int
) -> tuple[tuple[str, Decimal | int], ...]:
    """Return server-owned effects once; adapters persist status atomically."""
    if event.status != "pending" or game_day > event.expires_day:
        raise ValueError("Event cannot be resolved.")
    for choice in event.template.choices:
        if choice.code == choice_code:
            return choice.effects
    raise ValueError("Unknown event choice.")


def modifier_active(*, start_day: int, end_day: int, game_day: int) -> bool:
    return start_day <= game_day <= end_day
