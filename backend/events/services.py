from decimal import Decimal
from typing import TypedDict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from companies.models import Company
from contracts.services import get_current_game_day
from employees.models import Employee, EmployeeAvailability
from finances.models import Transaction, TransactionType
from projects.models import Project, ProjectStatus

from .models import (
    CompanyEvent,
    EventChoice,
    EventEffect,
    EventEffectType,
    EventStatus,
)


class AppliedEffectSummary(TypedDict):
    effect_type: str
    value: str
    description: str


class EventChoiceResult(TypedDict):
    event: CompanyEvent
    effects: list[AppliedEffectSummary]


def _apply_single_effect(
    *,
    company: Company,
    effect: EventEffect,
    event_title: str,
    current_day: int,
) -> AppliedEffectSummary:
    if effect.effect_type == EventEffectType.BALANCE:
        amount = effect.value
        company.balance += amount
        if amount != Decimal("0.00"):
            tx_type = (
                TransactionType.EVENT_REWARD
                if amount > Decimal("0.00")
                else TransactionType.EVENT_COST
            )
            Transaction.objects.create(
                company=company,
                amount=amount,
                type=tx_type,
                description=effect.description or f"Івент «{event_title}»",
                game_day=current_day,
            )
        return {
            "effect_type": effect.effect_type,
            "value": str(amount),
            "description": effect.description or f"Зміна балансу: {amount}",
        }

    if effect.effect_type == EventEffectType.REPUTATION:
        delta = int(effect.value)
        company.reputation = max(0, min(100, company.reputation + delta))
        return {
            "effect_type": effect.effect_type,
            "value": str(delta),
            "description": effect.description or f"Зміна репутації: {delta:+d}",
        }

    if effect.effect_type == EventEffectType.EMPLOYEE_SICK:
        count = max(1, int(abs(effect.value)))
        candidates = list(
            Employee.objects.select_for_update()
            .filter(company=company, availability=EmployeeAvailability.AVAILABLE)
            .order_by("?")[:count]
        )
        for emp in candidates:
            emp.availability = EmployeeAvailability.SICK
            emp.save(update_fields=["availability"])
        return {
            "effect_type": effect.effect_type,
            "value": str(len(candidates)),
            "description": (
                effect.description
                or f"Працівників пішло на лікарняний: {len(candidates)}"
            ),
        }

    if effect.effect_type == EventEffectType.PROJECT_PROGRESS:
        delta = int(effect.value)
        active_project = (
            Project.objects.select_for_update()
            .filter(
                company=company,
                status__in=[ProjectStatus.ACTIVE, ProjectStatus.REWORK],
            )
            .first()
        )
        if active_project is not None:
            active_project.progress = max(0, min(100, active_project.progress + delta))
            active_project.save(update_fields=["progress"])
        return {
            "effect_type": effect.effect_type,
            "value": str(delta),
            "description": (
                effect.description or f"Зміна прогресу проєкту: {delta:+d}%"
            ),
        }

    return {
        "effect_type": effect.effect_type,
        "value": str(effect.value),
        "description": effect.description,
    }


@transaction.atomic
def choose_event_option(
    *,
    company: Company,
    event_id: int,
    choice_id: int,
) -> EventChoiceResult:
    locked_company = Company.objects.select_for_update().get(pk=company.pk)

    try:
        event = (
            CompanyEvent.objects.select_for_update()
            .select_related("template")
            .get(pk=event_id, company=locked_company)
        )
    except CompanyEvent.DoesNotExist as exc:
        raise NotFound("Івент не знайдено.") from exc

    if event.status != EventStatus.PENDING:
        raise ValidationError(
            "Рішення для цього івенту вже прийнято або його термін дії минув."
        )

    try:
        choice = EventChoice.objects.prefetch_related("effects").get(
            pk=choice_id,
            template=event.template,
        )
    except EventChoice.DoesNotExist as exc:
        raise ValidationError(
            {"choice_id": "Цей варіант вибору не належить до вказаного івенту."}
        ) from exc

    current_day = get_current_game_day()
    applied_effects: list[AppliedEffectSummary] = []

    for effect in choice.effects.all():
        summary = _apply_single_effect(
            company=locked_company,
            effect=effect,
            event_title=event.template.title,
            current_day=current_day,
        )
        applied_effects.append(summary)

    locked_company.save(update_fields=["balance", "reputation"])

    event.status = EventStatus.RESOLVED
    event.chosen_option = choice
    event.applied_effects = applied_effects
    event.resolved_at = timezone.now()
    event.save(
        update_fields=["status", "chosen_option", "applied_effects", "resolved_at"]
    )

    return {
        "event": event,
        "effects": applied_effects,
    }
