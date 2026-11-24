"""Run due global simulation days outside the HTTP request lifecycle."""

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from simulation.engine import SimulationEngine
from simulation.services import acquire_simulation_lock, release_simulation_lock


class Command(BaseCommand):
    help = "Process due global game days in chronological order."

    def add_arguments(self, parser):
        parser.add_argument("--max-days", type=int, default=7)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        max_days = options["max_days"]
        if max_days <= 0:
            raise CommandError("--max-days must be positive.")

        if options["dry_run"]:
            result = SimulationEngine().process_pending_days(
                now=timezone.now(),
                max_days=max_days,
                dry_run=True,
            )
            self.stdout.write(f"Dry run: {result.processed_days} due game day(s).")
            return

        owner_id = uuid.uuid4()
        now = timezone.now()
        if not acquire_simulation_lock(owner_id=owner_id, now=now):
            raise CommandError(
                "Another simulation process currently owns the game-tick lock."
            )

        try:
            result = SimulationEngine().process_pending_days(now=now, max_days=max_days)
        finally:
            release_simulation_lock(owner_id=owner_id)

        if result.blocked_day is not None:
            raise CommandError(
                f"Game day {result.blocked_day} is blocked pending Team Backend model integration."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {result.processed_days} day(s); skipped {result.skipped_days}."
            )
        )
