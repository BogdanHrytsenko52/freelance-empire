from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from employees.models import Specialization


class ProjectStatus(models.TextChoices):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (статуси проєкту — з Богданом та Артемом):
    # У game.ts Артема зазначено, що статуси проєкту ще не узгоджені.
    # Поки закладаємо базовий життєвий цикл:
    #   active    — проєкт у роботі
    #   rework    — повернуто на доопрацювання (якщо після submit низька якість)
    #   completed — успішно зданий і оплачений
    #   failed    — провалений (наприклад, прострочений дедлайн у симуляції)
    # =========================================================================
    ACTIVE = "active", "Active"
    REWORK = "rework", "Rework"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class TaskStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"


class Project(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    contract = models.OneToOneField(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="project",
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    quality = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат deadline — з Богданом):
    # Варіант 1 (поточний, під game.ts): ціле число — граничний ігровий день здачі
    #   (current_game_day + contract.deadline).
    # Варіант 2: DateTimeField, якщо дедлайни прив'язані до реального часу.
    # =========================================================================
    deadline = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress__gte=0, progress__lte=100),
                name="project_progress_range",
            ),
            models.CheckConstraint(
                condition=models.Q(quality__gte=0, quality__lte=100),
                name="project_quality_range",
            ),
            models.CheckConstraint(
                condition=models.Q(deadline__gte=1),
                name="project_deadline_min_1",
            ),
        ]

    def __str__(self) -> str:
        return f"Project #{self.pk}: {self.contract.title} ({self.status})"


class ProjectTask(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    required_specialization = models.CharField(
        max_length=20,
        choices=Specialization.choices,
    )
    work_total = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    work_done = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(work_total__gte=1),
                name="task_work_total_min_1",
            ),
            models.CheckConstraint(
                condition=models.Q(work_done__lte=models.F("work_total")),
                name="task_work_done_lte_total",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.work_done}/{self.work_total}, {self.status})"


class Assignment(models.Model):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (скільки завдань може робити один працівник одночасно):
    # Варіант 1 (поточний): у БД забороняємо дублікат пари (task, employee),
    #   а обмеження «1 працівник = 1 активне завдання» перевіряємо в projects/services.py
    #   через employee.availability == "busy" (це стикується із забороною звільнення
    #   зайнятого працівника в employees/services.py).
    # Варіант 2: якщо працівник може працювати над кількома завданнями паралельно —
    #   достатньо прибрати перевірку availability == "busy" у projects/services.py.
    # =========================================================================
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "employee"],
                name="unique_task_employee_assignment",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee.name} -> {self.task.title}"
