"""User model and role definitions for Freelance Empire."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserRole(models.TextChoices):
    """Application roles; guests intentionally have no database record."""

    PLAYER = "player", "Player"
    MODERATOR = "moderator", "Moderator"
    ADMIN = "admin", "Admin"


class User(AbstractUser):
    """Project user with a unique email and a least-privilege game role."""

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.PLAYER,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_case_insensitive_unique",
            )
        ]

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()
