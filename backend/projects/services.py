from decimal import Decimal

from typing import TypedDict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from notifications.models import Notification, NotificationType
from companies.models import Company
from contracts.models import ContractStatus
from contracts.services import get_current_game_day
from employees.models import Employee, EmployeeAvailability
from finances.models import Transaction, TransactionType

from .models import Assignment, Project, ProjectStatus, ProjectTask, TaskStatus

ACTIVE_PROJECT_STATUSES = (ProjectStatus.ACTIVE, ProjectStatus.REWORK)


@transaction.atomic
def assign_employee_to_task(
    *,
    company: Company,
    project_id: int,
    task_id: int,
    employee_id: int,
) -> Project:
    try:
        project = Project.objects.select_for_update().get(
            pk=project_id,
            company=company,
        )
    except Project.DoesNotExist as exc:
        raise NotFound("Проєкт не знайдено.") from exc

    if project.status not in ACTIVE_PROJECT_STATUSES:
        raise ValidationError(
            "Неможливо призначати працівників на завершений або провалений проєкт."
        )

    try:
        task = ProjectTask.objects.select_for_update().get(
            pk=task_id,
            project=project,
        )
    except ProjectTask.DoesNotExist as exc:
        raise NotFound("Завдання не знайдено в цьому проєкті.") from exc

    if task.status == TaskStatus.DONE:
        raise ValidationError("Неможливо призначити працівника на вже виконане завдання.")

    try:
        employee = Employee.objects.select_for_update().get(
            pk=employee_id,
            company=company,
        )
    except Employee.DoesNotExist as exc:
        raise ValidationError(
            {"employee_id": "Працівника не знайдено у вашій компанії."}
        ) from exc

    if employee.availability == EmployeeAvailability.SICK:
        raise ValidationError("Неможливо призначити працівника, який зараз хворіє.")

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (1 працівник = 1 завдання — з Богданом):
    # Варіант 1 (поточний): один працівник може працювати лише над одним завданням
    #   одночасно (availability == "busy"). Це напряму стикується із забороною
    #   звільнення зайнятого працівника в employees/services.py.
    # Варіант 2: якщо дозволити кілька завдань паралельно — прибрати цю перевірку.
    # =========================================================================
    if employee.availability == EmployeeAvailability.BUSY:
        raise ValidationError(
            "Цей працівник уже зайнятий іншим завданням. Спочатку зніміть його."
        )

    if Assignment.objects.filter(task=task, employee=employee).exists():
        raise ValidationError("Цей працівник уже призначений на це завдання.")

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (перевірка спеціалізації — з Богданом):
    # У симуляції Богдана закладено коефіцієнт 0.65 для суміжної спеціалізації,
    # тому зараз НЕ блокуємо призначення іншої спеціалізації.
    # Якщо вирішимо зробити сувору перевірку (тільки точний збіг + fullstack
    # для frontend/backend), можна додати валідацію тут.
    # =========================================================================

    Assignment.objects.create(task=task, employee=employee)

    employee.availability = EmployeeAvailability.BUSY
    employee.save(update_fields=["availability"])

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (перехід статусу завдання todo -> in_progress — з Богданом):
    # В API_CONTRACT.md зафіксовано, що статуси todo -> in_progress -> done змінює
    # виключно симуляція Богдана, тому зараз task.status тут НЕ змінюємо.
    # Якщо Богдан скаже переводити статус одразу при призначенні — розкоментуй:
    # if task.status == TaskStatus.TODO:
    #     task.status = TaskStatus.IN_PROGRESS
    #     task.save(update_fields=["status"])
    # =========================================================================

    return project


@transaction.atomic
def unassign_employee_from_task(
    *,
    company: Company,
    project_id: int,
    task_id: int,
    employee_id: int,
) -> Project:
    try:
        project = Project.objects.select_for_update().get(
            pk=project_id,
            company=company,
        )
    except Project.DoesNotExist as exc:
        raise NotFound("Проєкт не знайдено.") from exc

    if project.status not in ACTIVE_PROJECT_STATUSES:
        raise ValidationError(
            "Неможливо змінювати призначення у завершеному або проваленому проєкті."
        )

    try:
        task = ProjectTask.objects.select_for_update().get(
            pk=task_id,
            project=project,
        )
    except ProjectTask.DoesNotExist as exc:
        raise NotFound("Завдання не знайдено в цьому проєкті.") from exc

    try:
        employee = Employee.objects.select_for_update().get(
            pk=employee_id,
            company=company,
        )
    except Employee.DoesNotExist as exc:
        raise ValidationError(
            {"employee_id": "Працівника не знайдено у вашій компанії."}
        ) from exc

    assignment = Assignment.objects.filter(task=task, employee=employee).first()
    if assignment is None:
        raise ValidationError("Цей працівник не призначений на вказане завдання.")

    assignment.delete()

    has_other_active_assignments = Assignment.objects.filter(
        employee=employee,
        task__project__status__in=ACTIVE_PROJECT_STATUSES,
    ).exists()

    if (
        not has_other_active_assignments
        and employee.availability == EmployeeAvailability.BUSY
    ):
        employee.availability = EmployeeAvailability.AVAILABLE
        employee.save(update_fields=["availability"])

    return project

class ProjectSubmissionResult(TypedDict):
    project: Project
    result: str
    payout: Decimal
    reputation_change: int
    is_overdue: bool

@transaction.atomic
def submit_project(*, company: Company, project_id: int) -> ProjectSubmissionResult:
    locked_company = Company.objects.select_for_update().get(pk=company.pk)

    try:
        project = (
            Project.objects.select_for_update()
            .select_related("contract")
            .get(pk=project_id, company=locked_company)
        )
    except Project.DoesNotExist as exc:
        raise NotFound("Проєкт не знайдено.") from exc

    if project.status not in ACTIVE_PROJECT_STATUSES:
        raise ValidationError("Цей проєкт уже завершений або провалений.")

    tasks_qs = project.tasks.all()
    if not tasks_qs.exists():
        raise ValidationError("У проєкті відсутні завдання для здачі.")

    if tasks_qs.exclude(status=TaskStatus.DONE).exists() or project.progress < 100:
        raise ValidationError(
            "Неможливо здати проєкт передчасно: усі завдання мають бути завершені (100%)."
        )

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (розрахунок виплати, якості та репутації — з Богданом):
    # 1. Чи викликати тут сервісну функцію Богдана з simulation/ (наприклад,
    #    evaluate_and_complete_project(project)), чи лишити базовий розрахунок тут?
    # 2. Поріг якості для повернення на доопрацювання (status="rework"):
    #    Зараз проєкт приймається завжди (щоб тести працювали без симуляції).
    #    Якщо Богдан затвердить поріг (наприклад, quality < 40 -> rework), додамо тут.
    # 3. Штраф за прострочений дедлайн: зараз при current_day > deadline
    #    виплачується 80% бюджету і репутація -5; при вчасній здачі — 100% і +5.
    # 4. Після створення застосунків finances/ та notifications/ обов'язково додати
    #    сюди створення Transaction(type="contract_payment") і Notification(type="project_completed").
    # =========================================================================
    current_day = get_current_game_day()
    is_overdue = current_day > project.deadline

    if is_overdue:
        payout = (project.contract.budget * Decimal("0.80")).quantize(Decimal("0.01"))
        reputation_change = -5
    else:
        payout = project.contract.budget
        reputation_change = 5

    locked_company.balance += payout
    locked_company.reputation = max(0, min(100, locked_company.reputation + reputation_change))
    locked_company.completed_contracts += 1
    locked_company.save(update_fields=["balance", "reputation", "completed_contracts"])

    Transaction.objects.create(
        company=locked_company,
        amount=payout,
        type=TransactionType.CONTRACT_PAYMENT,
        description=f"Виплата за проєкт «{project.contract.title}»",
        game_day=current_day,
    )
    Notification.objects.create(
        company=locked_company,
        title="Проєкт завершено",
        text=(
            f"Проєкт «{project.contract.title}» здано. "
            f"Виплата: {payout} ₴, зміна репутації: {reputation_change:+d}."
        ),
        type=NotificationType.PROJECT_COMPLETED,
    )

    project.status = ProjectStatus.COMPLETED
    project.completed_at = timezone.now()
    project.save(update_fields=["status", "completed_at"])

    contract = project.contract
    contract.status = ContractStatus.COMPLETED
    contract.save(update_fields=["status"])

    assigned_employee_ids = list(
        Assignment.objects.filter(task__project=project)
        .values_list("employee_id", flat=True)
        .distinct()
    )
    if assigned_employee_ids:
        busy_employees = Employee.objects.select_for_update().filter(
            pk__in=assigned_employee_ids,
            availability=EmployeeAvailability.BUSY,
        )
        for employee in busy_employees:
            still_busy = Assignment.objects.filter(
                employee=employee,
                task__project__status__in=ACTIVE_PROJECT_STATUSES,
            ).exists()
            if not still_busy:
                employee.availability = EmployeeAvailability.AVAILABLE
                employee.save(update_fields=["availability"])

    return {
        "project": project,
        "result": project.status,
        "payout": payout,
        "reputation_change": reputation_change,
        "is_overdue": is_overdue,
    }
