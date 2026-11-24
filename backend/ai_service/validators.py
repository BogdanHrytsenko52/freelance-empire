"""Strict DTO validation for untrusted model output and negotiation input."""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class AiValidationError(ValueError):
    """Raised when user or model data violates a server-owned contract."""


class NegotiationAction(StrEnum):
    NONE = "none"
    COUNTER_OFFER = "counter_offer"
    ACCEPT_OFFER = "accept_offer"
    REJECT_OFFER = "reject_offer"


@dataclass(frozen=True)
class NegotiationBounds:
    minimum_budget: Decimal
    maximum_budget: Decimal
    minimum_deadline: int
    maximum_deadline: int


@dataclass(frozen=True)
class NpcReply:
    message: str
    action: NegotiationAction
    proposed_budget: Decimal | None
    proposed_deadline: int | None


def validate_message(message: str, *, max_length: int) -> str:
    message = message.strip()
    if not message or len(message) > max_length:
        raise AiValidationError(
            "Message must be non-empty and within the configured length limit."
        )
    return message


def parse_npc_reply(raw: str, *, bounds: NegotiationBounds) -> NpcReply:
    """Parse only the four public fields; ignore no unknown or malformed data."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AiValidationError("AI response is not valid JSON.") from error
    expected = {"message", "action", "proposed_budget", "proposed_deadline"}
    if (
        not isinstance(value, dict)
        or set(value) != expected
        or not isinstance(value["message"], str)
    ):
        raise AiValidationError("AI response does not match the required schema.")
    if not value["message"].strip() or len(value["message"]) > 1000:
        raise AiValidationError("AI response message is invalid.")
    try:
        action = NegotiationAction(value["action"])
    except ValueError as error:
        raise AiValidationError("AI response action is not allowed.") from error
    budget = value["proposed_budget"]
    if budget is not None:
        try:
            budget = Decimal(str(budget))
        except (InvalidOperation, ValueError) as error:
            raise AiValidationError("AI proposed budget is invalid.") from error
        if not bounds.minimum_budget <= budget <= bounds.maximum_budget:
            raise AiValidationError("AI proposed budget is outside server bounds.")
    deadline = value["proposed_deadline"]
    if deadline is not None and (
        not isinstance(deadline, int)
        or not bounds.minimum_deadline <= deadline <= bounds.maximum_deadline
    ):
        raise AiValidationError("AI proposed deadline is outside server bounds.")
    return NpcReply(value["message"].strip(), action, budget, deadline)
