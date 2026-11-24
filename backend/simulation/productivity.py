"""Pure, Decimal-based productivity and task-progress calculations."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Iterable, Mapping

WORK_QUANTUM = Decimal("0.0001")
SKILL_FACTORS = {
    "junior": Decimal("0.7"),
    "middle": Decimal("1.0"),
    "senior": Decimal("1.4"),
}
SPECIALIZATION_FACTORS = {
    "exact": Decimal("1.0"),
    "adjacent": Decimal("0.65"),
    "incompatible": Decimal("0"),
}
EVENT_MODIFIERS = {
    "normal": Decimal("1.0"),
    "sick": Decimal("0.5"),
    "bonus": Decimal("1.2"),
}


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(frozen=True)
class WorkerInput:
    identifier: str
    base_productivity: Decimal
    skill_level: str
    specialization_match: str
    event_modifier: str = "normal"
    available: bool = True


@dataclass(frozen=True)
class TaskInput:
    identifier: str
    required_work: Decimal
    completed_work: Decimal = Decimal("0")
    status: TaskStatus = TaskStatus.TODO


@dataclass(frozen=True)
class TaskProgressResult:
    identifier: str
    added_work: Decimal
    completed_work: Decimal
    status: TaskStatus


def work(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(WORK_QUANTUM, rounding=ROUND_HALF_UP)


def daily_work(worker: WorkerInput) -> Decimal:
    """Return available daily work using the agreed multiplier formula."""
    if not worker.available:
        return Decimal("0")
    return work(
        worker.base_productivity
        * SKILL_FACTORS[worker.skill_level]
        * SPECIALIZATION_FACTORS[worker.specialization_match]
        * EVENT_MODIFIERS[worker.event_modifier]
    )


def allocate_work(
    worker: WorkerInput,
    task_ids: Iterable[str],
    priorities: Mapping[str, Decimal] | None = None,
) -> dict[str, Decimal]:
    """Distribute a worker's finite daily capacity across active tasks."""
    task_ids = list(task_ids)
    if not task_ids:
        return {}
    available = daily_work(worker)
    weights = [
        Decimal("1")
        if priorities is None
        else Decimal(priorities.get(task_id, Decimal("1")))
        for task_id in task_ids
    ]
    total_weight = sum(weights, Decimal("0"))
    if not available or total_weight <= 0:
        return {task_id: Decimal("0") for task_id in task_ids}
    allocations = {
        task_id: work(available * weight / total_weight)
        for task_id, weight in zip(task_ids, weights, strict=True)
    }
    allocations[task_ids[0]] = work(
        allocations[task_ids[0]] + (available - sum(allocations.values(), Decimal("0")))
    )
    return allocations


def apply_task_progress(
    task: TaskInput, contributions: Iterable[Decimal | int | str]
) -> TaskProgressResult:
    """Cap work at the requirement and transition task state without ORM writes."""
    if task.status == TaskStatus.DONE:
        return TaskProgressResult(
            task.identifier, Decimal("0"), work(task.completed_work), TaskStatus.DONE
        )
    current = work(task.completed_work)
    required = work(task.required_work)
    added = min(
        max(sum((work(value) for value in contributions), Decimal("0")), Decimal("0")),
        max(required - current, Decimal("0")),
    )
    completed = work(current + added)
    status = (
        TaskStatus.DONE
        if completed >= required
        else (TaskStatus.IN_PROGRESS if added else task.status)
    )
    return TaskProgressResult(task.identifier, work(added), completed, status)


def project_progress(tasks: Iterable[TaskInput]) -> Decimal:
    """Return completed required work percentage, or zero for an empty project."""
    tasks = list(tasks)
    required = sum((work(task.required_work) for task in tasks), Decimal("0"))
    if required <= 0:
        return Decimal("0")
    completed = sum(
        (min(work(task.completed_work), work(task.required_work)) for task in tasks),
        Decimal("0"),
    )
    return work(min(Decimal("100"), completed * Decimal("100") / required))
