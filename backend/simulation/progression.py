"""Deterministic company-level gates using historical income, not balance."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LevelRule:
    level: int
    name: str
    contracts: int
    reputation: int
    earned: Decimal
    max_projects: int


LEVELS = (
    LevelRule(1, "Freelancer", 0, 0, Decimal("0"), 1),
    LevelRule(2, "Small Team", 3, 10, Decimal("30000"), 2),
    LevelRule(3, "Studio", 10, 30, Decimal("150000"), 3),
    LevelRule(4, "Agency", 25, 60, Decimal("500000"), 5),
    LevelRule(5, "Enterprise", 50, 85, Decimal("1500000"), 8),
)


def company_level(
    *,
    completed_contracts: int,
    reputation: int,
    total_earned: Decimal,
    achieved_level: int = 1,
) -> LevelRule:
    qualified = [
        rule
        for rule in LEVELS
        if completed_contracts >= rule.contracts
        and reputation >= rule.reputation
        and total_earned >= rule.earned
    ]
    return max(
        (rule for rule in qualified if rule.level >= achieved_level),
        key=lambda rule: rule.level,
        default=next(rule for rule in LEVELS if rule.level == achieved_level),
    )


def can_accept_contract(
    *, level: int, active_projects: int, required_level: int
) -> bool:
    rule = next(rule for rule in LEVELS if rule.level == level)
    return level >= required_level and active_projects < rule.max_projects
