"""Validated creative contract text; server code owns all economic parameters."""

import json
from dataclasses import dataclass

from .groq_client import AiUnavailableError, GroqClient
from .prompts import CONTRACT_SYSTEM_PROMPT
from .validators import AiValidationError

CATEGORIES = (
    "Landing Page",
    "Corporate Website",
    "Online Store",
    "REST API",
    "Web Application",
    "Mobile Application",
    "Automation",
)
PERSONALITIES = ("demanding", "friendly", "frugal", "impatient", "pedantic", "flexible")


@dataclass(frozen=True)
class ContractText:
    title: str
    description: str
    client_story: str
    company_name: str
    client_name: str
    requirements: tuple[str, ...]
    npc_personality: str


def fallback_contract(category: str) -> ContractText:
    return ContractText(
        f"{category} for Northwind",
        "A focused client project.",
        "The client needs a reliable delivery.",
        "Northwind Studio",
        "Olena Kovalenko",
        ("Clear scope", "Maintainable delivery"),
        "friendly",
    )


def parse_contract_text(raw: str, *, category: str) -> ContractText:
    if category not in CATEGORIES:
        raise AiValidationError("Unknown contract category.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AiValidationError("Contract text is not JSON.") from error
    expected = {
        "title",
        "description",
        "client_story",
        "company_name",
        "client_name",
        "requirements",
        "npc_personality",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected
        or value["npc_personality"] not in PERSONALITIES
        or not isinstance(value["requirements"], list)
        or not 1 <= len(value["requirements"]) <= 8
    ):
        raise AiValidationError("Contract text schema is invalid.")
    texts = [
        value[key]
        for key in expected
        if key != "requirements" and key != "npc_personality"
    ]
    if any(
        not isinstance(text, str) or not text.strip() or len(text) > 1000
        for text in texts
    ) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 300
        for item in value["requirements"]
    ):
        raise AiValidationError("Contract text contains invalid values.")
    return ContractText(
        value["title"].strip(),
        value["description"].strip(),
        value["client_story"].strip(),
        value["company_name"].strip(),
        value["client_name"].strip(),
        tuple(item.strip() for item in value["requirements"]),
        value["npc_personality"],
    )


class ContractTextGenerator:
    def __init__(self, client: GroqClient):
        self.client = client

    def generate(self, *, category: str) -> ContractText:
        if category not in CATEGORIES:
            raise AiValidationError("Unknown contract category.")
        try:
            return parse_contract_text(
                self.client.complete(
                    system=CONTRACT_SYSTEM_PROMPT, user=f"Category: {category}"
                ),
                category=category,
            )
        except (AiUnavailableError, AiValidationError):
            return fallback_contract(category)
