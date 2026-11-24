"""NPC negotiation service with repository-owned history and safe local fallback."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.conf import settings

from .groq_client import AiUnavailableError, GroqClient
from .prompts import NPC_SYSTEM_PROMPT, npc_prompt
from .validators import (
    NegotiationAction,
    NegotiationBounds,
    NpcReply,
    parse_npc_reply,
    validate_message,
)


@dataclass(frozen=True)
class NpcContext:
    contract_id: str
    name: str
    company: str
    personality: str
    requirements: str
    bounds: NegotiationBounds


class ChatRepository(Protocol):
    def history(
        self, *, contract_id: str, player_id: str, limit: int
    ) -> list[dict[str, str]]: ...
    def append(
        self, *, contract_id: str, player_id: str, role: str, content: str
    ) -> None: ...
    def request_count(self, *, player_id: str) -> int: ...


def fallback_reply(context: NpcContext) -> NpcReply:
    budget = (context.bounds.minimum_budget + context.bounds.maximum_budget) / Decimal(
        "2"
    )
    deadline = (context.bounds.minimum_deadline + context.bounds.maximum_deadline) // 2
    return NpcReply(
        f"Дякую. Розгляньмо умови проєкту {context.company}.",
        NegotiationAction.COUNTER_OFFER,
        budget,
        deadline,
    )


class NegotiationService:
    def __init__(self, *, repository: ChatRepository, client: GroqClient):
        self.repository = repository
        self.client = client

    def reply(self, *, player_id: str, context: NpcContext, message: str) -> NpcReply:
        message = validate_message(message, max_length=settings.AI_MAX_MESSAGE_LENGTH)
        if (
            self.repository.request_count(player_id=player_id)
            >= settings.AI_REQUESTS_PER_MINUTE
        ):
            raise ValueError("AI request rate limit exceeded.")
        history = self.repository.history(
            contract_id=context.contract_id,
            player_id=player_id,
            limit=settings.AI_MAX_HISTORY_MESSAGES,
        )
        if len(history) >= settings.AI_MAX_NEGOTIATION_MESSAGES:
            raise ValueError("Negotiation message limit exceeded.")
        self.repository.append(
            contract_id=context.contract_id,
            player_id=player_id,
            role="player",
            content=message,
        )
        try:
            raw = self.client.complete(
                system=NPC_SYSTEM_PROMPT,
                user=npc_prompt(
                    name=context.name,
                    company=context.company,
                    personality=context.personality,
                    requirements=context.requirements,
                )
                + "\nPlayer message: "
                + message,
            )
            reply = parse_npc_reply(raw, bounds=context.bounds)
        except (AiUnavailableError, ValueError):
            reply = fallback_reply(context)
        self.repository.append(
            contract_id=context.contract_id,
            player_id=player_id,
            role="npc",
            content=reply.message,
        )
        return reply
