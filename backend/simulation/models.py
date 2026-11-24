"""Durable, global state for the game clock and simulation run coordination."""

import uuid

from django.db import models


class GameClock(models.Model):
    """The singleton global clock; it is never scoped to an individual company."""

    singleton_id = models.PositiveSmallIntegerField(
        default=1, unique=True, editable=False
    )
    started_at = models.DateTimeField()
    last_processed_day = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(singleton_id=1),
                name="simulation_game_clock_singleton_id",
            )
        ]

    def __str__(self) -> str:
        return "Global game clock"


class GameDayRun(models.Model):
    """One durable attempt record per game day, enabling safe retries."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        BLOCKED = "blocked", "Blocked"
        FAILED = "failed", "Failed"
        COMPLETED = "completed", "Completed"

    game_day = models.PositiveIntegerField(unique=True)
    cycle_id = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RUNNING
    )
    attempts = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    detail = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Game day {self.game_day}: {self.status}"


class SimulationLock(models.Model):
    """A short lease used instead of relying on SQLite row-level locks."""

    name = models.CharField(max_length=64, unique=True)
    owner_id = models.UUIDField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class SimulationOperation(models.Model):
    """Idempotency coordination for future Transaction-backed operations.

    This is not a financial ledger and does not duplicate the future Transaction
    model. It records only an operation key and lifecycle state.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    operation_key = models.CharField(max_length=255, unique=True)
    game_day = models.PositiveIntegerField()
    company_identifier = models.CharField(max_length=128)
    operation_type = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.operation_key
