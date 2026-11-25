from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from companies.models import Company

from .models import (
    LEVEL_PRODUCTIVITY_MAP,
    Candidate,
    Employee,
    EmployeeAvailability,
    EmployeeSkill,
)


@transaction.atomic
def hire_candidate(*, company: Company, candidate_id: int) -> Employee:
    locked_company = Company.objects.select_for_update().get(pk=company.pk)

    try:
        candidate = Candidate.objects.select_for_update().get(pk=candidate_id)
    except Candidate.DoesNotExist as exc:
        raise ValidationError({"candidate_id": "Кандидата не знайдено."}) from exc

    if not candidate.is_available:
        raise ValidationError({"candidate_id": "Цей кандидат уже найнятий."})

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (перевірка фінансів при наймі):
    # Варіант 1 (поточний): на балансі має бути щонайменше одна місячна зарплата
    #   кандидата (company.balance >= candidate.expected_salary).
    # Варіант 2 (як у ТЗ Богдана / UI Артема): блокувати лише за наявності боргу
    #   (locked_company.balance < 0).
    # Кошти при наймі НЕ списуються — щоденну зарплату (salary / 30) списує
    # економічний рушій Богдана під час симуляції ігрового дня.
    # =========================================================================
    if locked_company.balance < candidate.expected_salary:
        raise ValidationError(
            "Недостатньо коштів на балансі компанії для найму цього працівника."
        )

    employee = Employee.objects.create(
        company=locked_company,
        name=candidate.name,
        specialization=candidate.specialization,
        level=candidate.level,
        salary=candidate.expected_salary,
        productivity=LEVEL_PRODUCTIVITY_MAP.get(candidate.level, Decimal("1.00")),
    )

    if candidate.skills:
        skills_to_create = [
            EmployeeSkill(
                employee=employee,
                skill_type=skill_type,
                value=value,
            )
            for skill_type, value in candidate.skills.items()
        ]
        EmployeeSkill.objects.bulk_create(skills_to_create)

    candidate.is_available = False
    candidate.save(update_fields=["is_available"])

    return employee


@transaction.atomic
def fire_employee(*, employee: Employee) -> None:
    locked_employee = Employee.objects.select_for_update().get(pk=employee.pk)

    # TODO / УЗГОДЖЕННЯ (звільнення зайнятого працівника):
    # Варіант 1 (поточний): забороняємо звільнення, доки працівник на завданні (busy).
    # Варіант 2: автоматично знімати із завдання при звільненні.
    if locked_employee.availability == EmployeeAvailability.BUSY:
        raise ValidationError(
            "Неможливо звільнити працівника, поки він призначений на завдання. "
            "Спочатку зніміть його із завдання."
        )

    locked_employee.delete()
