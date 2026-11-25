from rest_framework.permissions import BasePermission

class HasCompany(BasePermission):
    message = "Спочатку створіть компанію"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "company")
        )
