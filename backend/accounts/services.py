"""Safe account-creation operations shared by API entry points."""

from django.db import transaction

from .models import User


@transaction.atomic
def register_user(*, username: str, email: str, password: str) -> User:
    """Create a player with Django's password hashing and no caller-controlled role."""
    return User.objects.create_user(
        username=username,
        email=email.strip().lower(),
        password=password,
    )
