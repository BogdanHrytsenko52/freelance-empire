"""Small scheduler helpers; deployment owns the actual cron or Task Scheduler job."""

import sys
from pathlib import Path


def process_tick_command() -> str:
    """Return a quoted command suitable for cron or Windows Task Scheduler."""
    manage_py = Path(__file__).resolve().parents[1] / "manage.py"
    return f'"{sys.executable}" "{manage_py}" process_game_tick --max-days 7'
