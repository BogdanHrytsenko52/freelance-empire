"""Reusable role permissions for future protected game API endpoints."""

from rest_framework.permissions import BasePermission

from .models import UserRole


class HasRole(BasePermission):
    """Base permission that allows authenticated active users in allowed roles."""

    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in self.allowed_roles
        )


class IsPlayer(HasRole):
    allowed_roles = (UserRole.PLAYER, UserRole.MODERATOR, UserRole.ADMIN)


class IsModerator(HasRole):
    allowed_roles = (UserRole.MODERATOR, UserRole.ADMIN)


class IsAdminRole(HasRole):
    allowed_roles = (UserRole.ADMIN,)
