from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def validate_candidate_skills(value) -> None:
    if not isinstance(value, dict):
        raise DjangoValidationError(
            "Навички кандидата мають бути словником формату {'coding': 65}."
        )
    for skill_name, skill_value in value.items():
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise DjangoValidationError("Назва навички має бути непорожнім рядком.")
        if (
            isinstance(skill_value, bool)
            or not isinstance(skill_value, int)
            or not (1 <= skill_value <= 100)
        ):
            raise DjangoValidationError(
                f"Значення навички '{skill_name}' має бути цілим числом від 1 до 100."
            )


class Specialization(models.TextChoices):
    FRONTEND = "frontend", "Frontend"
    BACKEND = "backend", "Backend"
    FULLSTACK = "fullstack", "Fullstack"
    DESIGNER = "designer", "Designer"
    QA = "qa", "QA"


class EmployeeLevel(models.TextChoices):
    JUNIOR = "junior", "Junior"
    MIDDLE = "middle", "Middle"
    SENIOR = "senior", "Senior"


class EmployeeAvailability(models.TextChoices):
    AVAILABLE = "available", "Available"
    BUSY = "busy", "Busy"
    SICK = "sick", "Sick"


# TODO / УЗГОДЖЕННЯ (з Богданом):
# Базові коефіцієнти продуктивності за рівнем працівника (0.70 / 1.00 / 1.40).
# Якщо Богдан винесе цю мапу в simulation/, можна буде імпортувати її звідти.
LEVEL_PRODUCTIVITY_MAP: dict[str, Decimal] = {
    EmployeeLevel.JUNIOR: Decimal("0.70"),
    EmployeeLevel.MIDDLE: Decimal("1.00"),
    EmployeeLevel.SENIOR: Decimal("1.40"),
}


class Employee(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employees",
    )
    name = models.CharField(max_length=100)
    specialization = models.CharField(
        max_length=20,
        choices=Specialization.choices,
    )
    level = models.CharField(
        max_length=20,
        choices=EmployeeLevel.choices,
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    productivity = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.10"))],
    )
    # TODO / УЗГОДЖЕННЯ (з Богданом та Артемом):
    # У БД зберігаємо розширений статус (available / busy / sick) для симуляції та івентів.
    # У EmployeeSerializer додатково віддаємо булеве поле is_available під game.ts Артема.
    availability = models.CharField(
        max_length=20,
        choices=EmployeeAvailability.choices,
        default=EmployeeAvailability.AVAILABLE,
    )
    hired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-hired_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_level_display()} {self.get_specialization_display()})"


class EmployeeSkill(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    skill_type = models.CharField(max_length=50)
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "skill_type"],
                name="unique_employee_skill",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=1, value__lte=100),
                name="employee_skill_value_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee.name}: {self.skill_type} ({self.value})"


class Candidate(models.Model):
    name = models.CharField(max_length=100)
    specialization = models.CharField(
        max_length=20,
        choices=Specialization.choices,
    )
    level = models.CharField(
        max_length=20,
        choices=EmployeeLevel.choices,
    )
    # TODO / УЗГОДЖЕННЯ (формат Candidate.skills):
    # У БД зберігаємо як JSON-словник {"coding": 65} (гарантує унікальність ключів),
    # а в CandidateSerializer конвертуємо в масив [{"skill": "coding", "value": 65}] під game.ts.
    skills = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_candidate_skills],
    )
    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "expected_salary"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_level_display()} {self.get_specialization_display()})"
