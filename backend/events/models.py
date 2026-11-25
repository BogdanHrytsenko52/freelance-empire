from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class EventKind(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEGATIVE = "negative", "Negative"
    NEUTRAL = "neutral", "Neutral"


class EventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"
    EXPIRED = "expired", "Expired"


class EventEffectType(models.TextChoices):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (типи ефектів івентів — з Богданом):
    # Поки закладаємо базові ефекти, які може застосувати сервер одразу при виборі:
    #   balance          — зміна балансу (+ дохід / - витрата) + запис у Transaction
    #   reputation       — зміна репутації компанії (у межах 0..100)
    #   employee_sick    — переводить N вільних працівників у статус "sick"
    #   project_progress — зміна прогресу активного проєкту (якщо є)
    # Якщо Богдану для events_engine.py знадобляться інші типи — легко додати сюди.
    # =========================================================================
    BALANCE = "balance", "Balance"
    REPUTATION = "reputation", "Reputation"
    EMPLOYEE_SICK = "employee_sick", "Employee Sick"
    PROJECT_PROGRESS = "project_progress", "Project Progress"


class EventTemplate(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    kind = models.CharField(
        max_length=20,
        choices=EventKind.choices,
        default=EventKind.NEUTRAL,
    )
    # weight і is_active Боді (events_engine.py).
    weight = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_kind_display()})"


class EventChoice(models.Model):
    template = models.ForeignKey(
        EventTemplate,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=255)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"[{self.template.title}] {self.text}"


class EventEffect(models.Model):
    choice = models.ForeignKey(
        EventChoice,
        on_delete=models.CASCADE,
        related_name="effects",
    )
    effect_type = models.CharField(
        max_length=30,
        choices=EventEffectType.choices,
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.effect_type}: {self.value}"


class CompanyEvent(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="events",
    )
    template = models.ForeignKey(
        EventTemplate,
        on_delete=models.CASCADE,
        related_name="company_events",
    )
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
    )
    chosen_option = models.ForeignKey(
        EventChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_events",
    )
    # Зберігаємо фактично застосовані наслідки, щоб їх можна було показати в історії (/events/history/).
    applied_effects = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.name}: {self.template.title} ({self.status})"
