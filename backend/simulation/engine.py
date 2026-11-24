"""Global simulation orchestration that never completes a partial cycle."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .calendar import get_clock, pending_game_days
from .models import GameClock, GameDayRun
from .services import (
    GameDataAdapter,
    SimulationIntegrationBlockedError,
    UnavailableGameDataAdapter,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TickResult:
    processed_days: int = 0
    skipped_days: int = 0
    blocked_day: int | None = None
    dry_run: bool = False


class SimulationEngine:
    """Orchestrates ordered day processing through a Team Backend adapter."""

    def __init__(self, adapter: GameDataAdapter | None = None):
        self.adapter = adapter or UnavailableGameDataAdapter()

    def process_pending_days(
        self,
        *,
        now: datetime | None = None,
        max_days: int = 7,
        dry_run: bool = False,
    ) -> TickResult:
        """Process due days in order, stopping at the first incomplete integration."""
        if max_days <= 0:
            raise ValueError("max_days must be positive.")
        now = now or timezone.now()
        clock = get_clock(now=now, create=not dry_run)
        if clock is None:
            return TickResult(dry_run=True)

        due_days = list(pending_game_days(clock, now=now))[:max_days]
        if dry_run:
            return TickResult(processed_days=len(due_days), dry_run=True)

        processed = 0
        skipped = 0
        for game_day in due_days:
            outcome = self._process_day(clock=clock, game_day=game_day)
            if outcome == "completed":
                processed += 1
            elif outcome == "skipped":
                skipped += 1
            else:
                return TickResult(processed, skipped, blocked_day=game_day)
        return TickResult(processed, skipped)

    def _process_day(self, *, clock: GameClock, game_day: int) -> str:
        """Atomically process a day and advance the clock only after full success."""
        with transaction.atomic():
            clock = GameClock.objects.select_for_update().get(pk=clock.pk)
            if clock.last_processed_day >= game_day:
                logger.info("Skipping already completed game day %s", game_day)
                return "skipped"

            run, created = GameDayRun.objects.get_or_create(
                game_day=game_day,
                defaults={"status": GameDayRun.Status.RUNNING},
            )
            if not created and run.status == GameDayRun.Status.COMPLETED:
                return "skipped"
            if not created:
                run.status = GameDayRun.Status.RUNNING
                run.attempts += 1
                run.cycle_id = uuid.uuid4()
                run.detail = ""
                run.save(update_fields=["status", "attempts", "cycle_id", "detail"])

            logger.info(
                "Starting simulation game day %s (cycle %s)", game_day, run.cycle_id
            )
            try:
                company_count = self.adapter.process_day(game_day=game_day)
            except SimulationIntegrationBlockedError as error:
                run.status = GameDayRun.Status.BLOCKED
                run.detail = str(error)
                run.save(update_fields=["status", "detail"])
                logger.warning("Game day %s is blocked: %s", game_day, error)
                return "blocked"
            except Exception as error:
                run.status = GameDayRun.Status.FAILED
                run.detail = str(error)
                run.save(update_fields=["status", "detail"])
                logger.exception("Game day %s failed", game_day)
                raise

            run.status = GameDayRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.save(update_fields=["status", "completed_at"])
            clock.last_processed_day = game_day
            clock.save(update_fields=["last_processed_day", "updated_at"])
            logger.info(
                "Completed game day %s for %s companies", game_day, company_count
            )
            return "completed"
