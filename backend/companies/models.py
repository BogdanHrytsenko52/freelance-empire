from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models.functions import Lower

company_name_validator = RegexValidator(
    regex=r"^[a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9\s\-&\"'.]+$",
    message=("Назва може містити лише літери, цифри, пробіли та символи - & \" ' ."),
)


class Company(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company",
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(3), company_name_validator],
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("100000.00"),
    )
    reputation = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    completed_contracts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-reputation", "-balance"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(reputation__gte=0, reputation__lte=100),
                name="company_reputation_range",
            ),
            models.CheckConstraint(
                condition=models.Q(level__gte=1),
                name="company_level_min_1",
            ),
            models.UniqueConstraint(
                Lower("name"),
                name="unique_company_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}, (lvl {self.level})"
