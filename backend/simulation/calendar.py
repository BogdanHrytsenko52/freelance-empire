"""Durable global game-clock calculations with test-controlled time support."""

from datetime import datetime

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from .models import GameClock


def get_clock(*, now: datetime | None = None, create: bool = True) -> GameClock | None:
    """Return the singleton clock, creating it at a timezone-aware moment if needed."""
    now = now or timezone.now()
    if timezone.is_naive(now):
        raise ValueError("The simulation clock requires a timezone-aware datetime.")
    try:
        return GameClock.objects.get(singleton_id=1)
    except GameClock.DoesNotExist:
        if not create:
            return None
        try:
            return GameClock.objects.create(singleton_id=1, started_at=now)
        except IntegrityError:
            return GameClock.objects.get(singleton_id=1)


def current_game_day(clock: GameClock, *, now: datetime | None = None) -> int:
    """Return elapsed whole game days, where one real duration is one game day."""
    now = now or timezone.now()
    if timezone.is_naive(now):
        raise ValueError("The simulation clock requires a timezone-aware datetime.")
    elapsed_seconds = max(0, (now - clock.started_at).total_seconds())
    return int(elapsed_seconds // settings.GAME_DAY_DURATION_SECONDS)


def pending_game_days(clock: GameClock, *, now: datetime | None = None) -> range:
    """Yield days after the latest successful day through the current game day."""
    return range(clock.last_processed_day + 1, current_game_day(clock, now=now) + 1)
