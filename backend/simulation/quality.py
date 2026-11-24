"""Deterministic quality scoring and project-acceptance outcomes."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from .economy import calculate_contract_payment, money
from .productivity import EVENT_MODIFIERS, SKILL_FACTORS, SPECIALIZATION_FACTORS, work

QUALITY_BASE = Decimal("40")
QUALITY_SKILL_WEIGHT = Decimal("25")
QUALITY_SPECIALIZATION_WEIGHT = Decimal("25")
QUALITY_QA_WEIGHT = Decimal("5")
QUALITY_EVENT_WEIGHT = Decimal("5")
REWORK_THRESHOLD = Decimal("60")
BONUS_THRESHOLD = Decimal("85")
QUALITY_BONUS_RATE = Decimal("0.10")


@dataclass(frozen=True)
class QualityContribution:
    completed_work: Decimal
    skill_level: str
    specialization_match: str
    event_modifier: str = "normal"
    has_qa: bool = False


class AcceptanceStatus(StrEnum):
    REWORK = "rework_required"
    ACCEPTED = "accepted"
    ACCEPTED_BONUS = "accepted_with_bonus"


@dataclass(frozen=True)
class AcceptanceResult:
    status: AcceptanceStatus
    quality: Decimal
    quality_bonus: Decimal
    payment: Decimal
    reputation_change: int


def project_quality(contributions: Iterable[QualityContribution]) -> Decimal:
    """Score 0..100 from work-weighted skill, fit, QA, and event modifiers."""
    items = [item for item in contributions if work(item.completed_work) > 0]
    if not items:
        return Decimal("0")
    total = sum((work(item.completed_work) for item in items), Decimal("0"))

    def weighted(value) -> Decimal:
        return (
            sum(
                (work(item.completed_work) * value(item) for item in items),
                Decimal("0"),
            )
            / total
        )

    skill = weighted(
        lambda item: SKILL_FACTORS[item.skill_level] / SKILL_FACTORS["senior"]
    )
    specialization = weighted(
        lambda item: SPECIALIZATION_FACTORS[item.specialization_match]
    )
    event = weighted(
        lambda item: EVENT_MODIFIERS[item.event_modifier] / EVENT_MODIFIERS["bonus"]
    )
    qa = Decimal("1") if any(item.has_qa for item in items) else Decimal("0")
    score = (
        QUALITY_BASE
        + skill * QUALITY_SKILL_WEIGHT
        + specialization * QUALITY_SPECIALIZATION_WEIGHT
        + qa * QUALITY_QA_WEIGHT
        + event * QUALITY_EVENT_WEIGHT
    )
    return min(Decimal("100"), max(Decimal("0"), work(score)))


def accept_project(
    *,
    is_complete: bool,
    quality: Decimal,
    agreed_budget: Decimal,
    penalties: Decimal = Decimal("0"),
) -> AcceptanceResult:
    """Produce a deterministic acceptance and payment instruction, never a DB write."""
    if not is_complete:
        raise ValueError("An incomplete project cannot be accepted.")
    quality = project_quality([]) if quality < 0 else min(Decimal("100"), quality)
    if quality < REWORK_THRESHOLD:
        return AcceptanceResult(
            AcceptanceStatus.REWORK, quality, Decimal("0"), Decimal("0"), -5
        )
    bonus = (
        money(agreed_budget * QUALITY_BONUS_RATE)
        if quality >= BONUS_THRESHOLD
        else Decimal("0")
    )
    payment = calculate_contract_payment(agreed_budget, bonus, penalties)
    return AcceptanceResult(
        AcceptanceStatus.ACCEPTED_BONUS if bonus else AcceptanceStatus.ACCEPTED,
        quality,
        bonus,
        payment,
        5 if bonus else 2,
    )
