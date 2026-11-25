from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from companies.models import Company
from employees.models import Specialization
from projects.models import Project, ProjectStatus, ProjectTask, TaskStatus

from .models import Contract, ContractStatus

# Базові шаблони завдань за рівнем складності (1..5),
# якщо AI-генератор Богдана не заповнив contract.task_templates.
DEFAULT_TASK_TEMPLATES: dict[int, list[dict[str, object]]] = {
    1: [
        {
            "title": "Верстка та інтерфейс",
            "required_specialization": Specialization.FRONTEND,
            "work_total": 60,
        },
        {
            "title": "Тестування функціоналу",
            "required_specialization": Specialization.QA,
            "work_total": 30,
        },
    ],
    2: [
        {
            "title": "Дизайн макетів",
            "required_specialization": Specialization.DESIGNER,
            "work_total": 50,
        },
        {
            "title": "Реалізація клієнтської частини",
            "required_specialization": Specialization.FRONTEND,
            "work_total": 80,
        },
        {
            "title": "Серверна логіка та API",
            "required_specialization": Specialization.BACKEND,
            "work_total": 80,
        },
    ],
    3: [
        {
            "title": "UI/UX проєктування",
            "required_specialization": Specialization.DESIGNER,
            "work_total": 70,
        },
        {
            "title": "Frontend-розробка",
            "required_specialization": Specialization.FRONTEND,
            "work_total": 110,
        },
        {
            "title": "Backend та база даних",
            "required_specialization": Specialization.BACKEND,
            "work_total": 120,
        },
        {
            "title": "QA та перевірка вимог",
            "required_specialization": Specialization.QA,
            "work_total": 60,
        },
    ],
    4: [
        {
            "title": "Дизайн-система та прототипи",
            "required_specialization": Specialization.DESIGNER,
            "work_total": 90,
        },
        {
            "title": "Складна клієнтська архітектура",
            "required_specialization": Specialization.FRONTEND,
            "work_total": 150,
        },
        {
            "title": "Високонавантажений Backend",
            "required_specialization": Specialization.BACKEND,
            "work_total": 160,
        },
        {
            "title": "Інтеграція модулів",
            "required_specialization": Specialization.FULLSTACK,
            "work_total": 110,
        },
        {
            "title": "Навантажувальне та регресійне тестування",
            "required_specialization": Specialization.QA,
            "work_total": 80,
        },
    ],
    5: [
        {
            "title": "Повний UX-аудит і дизайн",
            "required_specialization": Specialization.DESIGNER,
            "work_total": 120,
        },
        {
            "title": "Enterprise Frontend",
            "required_specialization": Specialization.FRONTEND,
            "work_total": 200,
        },
        {
            "title": "Enterprise Backend та безпека",
            "required_specialization": Specialization.BACKEND,
            "work_total": 220,
        },
        {
            "title": "Наскрізна інтеграція (Fullstack)",
            "required_specialization": Specialization.FULLSTACK,
            "work_total": 150,
        },
        {
            "title": "Повний цикл QA та приймальне тестування",
            "required_specialization": Specialization.QA,
            "work_total": 110,
        },
    ],
}


def get_current_game_day() -> int:
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (ігровий час — з Богданом):
    # Коли Богдан реалізує simulation/, замінити цю заглушку на імпорт його
    # функції (наприклад: from simulation.time import get_current_game_day).
    # =========================================================================
    return 1


def _build_tasks_for_project(project: Project, contract: Contract) -> list[ProjectTask]:
    valid_specializations = set(Specialization.values)
    raw_templates = contract.task_templates if isinstance(contract.task_templates, list) else []

    tasks: list[ProjectTask] = []
    for item in raw_templates:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        specialization = str(item.get("required_specialization", "")).lower().strip()
        work_total = item.get("work_total")

        if (
            not title
            or specialization not in valid_specializations
            or isinstance(work_total, bool)
            or not isinstance(work_total, int)
            or work_total < 1
        ):
            continue

        tasks.append(
            ProjectTask(
                project=project,
                title=title[:200],
                required_specialization=specialization,
                work_total=work_total,
                work_done=0,
                status=TaskStatus.TODO,
            )
        )

    # Якщо AI-генератор не передав валідних task_templates — беремо базовий шаблон за difficulty.
    if not tasks:
        fallback_templates = DEFAULT_TASK_TEMPLATES.get(
            contract.difficulty,
            DEFAULT_TASK_TEMPLATES[1],
        )
        tasks = [
            ProjectTask(
                project=project,
                title=str(item["title"]),
                required_specialization=str(item["required_specialization"]),
                work_total=int(item["work_total"]),
                work_done=0,
                status=TaskStatus.TODO,
            )
            for item in fallback_templates
        ]

    return tasks


@transaction.atomic
def accept_contract(*, company: Company, contract_id: int) -> Project:
    locked_company = Company.objects.select_for_update().get(pk=company.pk)

    try:
        contract = Contract.objects.select_for_update().get(pk=contract_id)
    except Contract.DoesNotExist as exc:
        raise NotFound("Контракт не знайдено.") from exc

    # Захист від чужих контрактів (якщо контракт уже закріплений за іншою компанією).
    if contract.company_id is not None and contract.company_id != locked_company.pk:
        raise NotFound("Контракт не знайдено.")

    if contract.status not in {ContractStatus.AVAILABLE, ContractStatus.NEGOTIATING}:
        raise ValidationError("Цей контракт уже недоступний для прийняття.")

    if Project.objects.filter(contract=contract).exists():
        raise ValidationError("За цим контрактом уже створено проєкт.")

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (ігрові обмеження на прийняття контракту — з Богданом):
    # 1. Ліміт складності за рівнем компанії:
    #    Якщо хочемо не давати складні контракти новачкам, можна розкоментувати:
    #    if contract.difficulty > locked_company.level:
    #        raise ValidationError("Рівень вашої компанії замалий для цього контракту.")
    # 2. Ліміт одночасних активних проєктів:
    #    Наприклад, максимум company.level + 1 активних проєктів одночасно.
    #    active_projects_count = Project.objects.filter(
    #        company=locked_company,
    #        status__in=[ProjectStatus.ACTIVE, ProjectStatus.REWORK],
    #    ).count()
    # 3. Заборона брати нові контракти при від'ємному балансі (боргу) — чи навпаки
    #    дозволяти, щоб гравець міг вибратися з боргу? Поки ДОЗВОЛЯЄМО.
    # =========================================================================

    current_day = get_current_game_day()
    final_deadline_day = current_day + contract.deadline

    contract.company = locked_company
    contract.status = ContractStatus.ACCEPTED
    contract.accepted_at = timezone.now()
    contract.deadline = final_deadline_day
    contract.save(update_fields=["company", "status", "accepted_at", "deadline"])

    project = Project.objects.create(
        company=locked_company,
        contract=contract,
        status=ProjectStatus.ACTIVE,
        progress=0,
        quality=0,
        deadline=final_deadline_day,
    )

    tasks = _build_tasks_for_project(project=project, contract=contract)
    ProjectTask.objects.bulk_create(tasks)

    return project
