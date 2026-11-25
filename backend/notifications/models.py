from django.db import models


class NotificationType(models.TextChoices):
    NEW_EVENT = "new_event", "New Event"
    PROJECT_COMPLETED = "project_completed", "Project Completed"
    DEADLINE_SOON = "deadline_soon", "Deadline Soon"
    PAYOUT = "payout", "Payout"
    PENALTY = "penalty", "Penalty"
    NEW_CONTRACT = "new_contract", "New Contract"


class Notification(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    text = models.TextField()
    type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "is_read"]),
            models.Index(fields=["company", "-created_at"]),
        ]

    def __str__(self) -> str:
        state = "read" if self.is_read else "unread"
        return f"[{self.type} | {state}] {self.title} ({self.company.name})"
