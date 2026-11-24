"""Integration seams for the future Company, Employee, and Transaction models."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from .models import SimulationLock, SimulationOperation


class SimulationIntegrationBlockedError(RuntimeError):
    """Raised when a required team-owned domain model has not been integrated."""


class GameDataAdapter(Protocol):
    """Contract to implement once Team Backend's game models are available."""

    def process_day(self, *, game_day: int) -> int:
        """Process Company/Employee/Transaction work and return company count."""


class FinancialRepository(Protocol):
    """Adapter contract around Team Backend's Company and Transaction models."""

    def apply_transaction(
        self,
        *,
        company_identifier: str,
        amount: Decimal,
        operation_key: str,
        operation_type: str,
        description: str,
        game_day: int,
    ) -> None:
        """Atomically update the balance and create the authoritative Transaction."""


@dataclass(frozen=True)
class FinancialOperation:
    """A Decimal-only financial command to be persisted by the Team Backend adapter."""

    operation_key: str
    company_identifier: str
    game_day: int
    operation_type: str
    amount: Decimal
    description: str


class FinancialService:
    """Central gate for balance changes once the Transaction repository exists."""

    def __init__(self, repository: FinancialRepository):
        self.repository = repository

    def apply(self, operation: FinancialOperation) -> bool:
        """Apply once; positive amounts credit and negative amounts debit a company."""
        with transaction.atomic():
            record, created = SimulationOperation.objects.get_or_create(
                operation_key=operation.operation_key,
                defaults={
                    "game_day": operation.game_day,
                    "company_identifier": operation.company_identifier,
                    "operation_type": operation.operation_type,
                },
            )
            if not created and record.status == SimulationOperation.Status.COMPLETED:
                return False
            self.repository.apply_transaction(
                company_identifier=operation.company_identifier,
                amount=operation.amount,
                operation_key=operation.operation_key,
                operation_type=operation.operation_type,
                description=operation.description,
                game_day=operation.game_day,
            )
            record.status = SimulationOperation.Status.COMPLETED
            record.completed_at = timezone.now()
            record.save(update_fields=["status", "completed_at"])
        return True


class UnavailableGameDataAdapter:
    """Safe default that prevents falsely completing a partial game-day cycle."""

    def process_day(self, *, game_day: int) -> int:
        raise SimulationIntegrationBlockedError(
            "Company, Employee, and Transaction models are not available for integration."
        )


def acquire_simulation_lock(
    *, owner_id, now: datetime, lease_seconds: int = 300
) -> bool:
    """Acquire a database-backed lease compatible with SQLite's locking limits."""
    expires_at = now + timedelta(seconds=lease_seconds)
    try:
        SimulationLock.objects.get_or_create(name="global-game-tick")
    except IntegrityError:
        pass
    updated = (
        SimulationLock.objects.filter(name="global-game-tick")
        .filter(models.Q(locked_until__isnull=True) | models.Q(locked_until__lt=now))
        .update(owner_id=owner_id, locked_until=expires_at)
    )
    return updated == 1


def release_simulation_lock(*, owner_id) -> None:
    """Release only the caller's lease, never a competing worker's lease."""
    SimulationLock.objects.filter(name="global-game-tick", owner_id=owner_id).update(
        owner_id=None,
        locked_until=None,
    )


def reserve_operation(
    *, operation_key: str, game_day: int, company_identifier: str, operation_type: str
) -> bool:
    """Reserve an idempotent future financial operation by its unique key."""
    try:
        with transaction.atomic():
            SimulationOperation.objects.create(
                operation_key=operation_key,
                game_day=game_day,
                company_identifier=company_identifier,
                operation_type=operation_type,
            )
        return True
    except IntegrityError:
        return False


def complete_operation(*, operation_key: str) -> None:
    """Mark an adapter-applied operation complete inside its surrounding transaction."""
    SimulationOperation.objects.filter(operation_key=operation_key).update(
        status=SimulationOperation.Status.COMPLETED,
        completed_at=timezone.now(),
    )
