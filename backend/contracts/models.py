from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ContractStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    NEGOTIATING = "negotiating", "Negotiating"
    ACCEPTED = "accepted", "Accepted"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ChatSender(models.TextChoices):
    PLAYER = "player", "Player"
    NPC = "npc", "NPC"


class Contract(models.Model):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (власник контракту / пул контрактів):
    # Варіант 1 (поточний): спільний пул контрактів (company=None, поки status="available").
    #   Коли гравець починає переговори або приймає контракт, прив'язуємо його до company.
    # Варіант 2: контракти генеруються персонально для кожної компанії (company обов'язкове).
    # =========================================================================
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (зберігання NPC-клієнта — з Богданом):
    # Варіант 1 (поточний): дані NPC зберігаємо прямо в Contract (client_name,
    #   client_personality, client_bio), а в серіалізаторі віддаємо як client: {"name": ...}
    #   під game.ts Артема.
    # Варіант 2: винести в окрему модель NpcClient, якщо один клієнт даватиме кілька контрактів.
    # =========================================================================
    client_name = models.CharField(max_length=120)
    client_personality = models.CharField(max_length=120, blank=True, default="")
    client_bio = models.TextField(blank=True, default="")

    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат difficulty):
    # Варіант 1 (поточний, під game.ts): числова шкала 1..5.
    # Варіант 2: текстовий enum ("easy", "medium", "hard").
    # =========================================================================
    difficulty = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат deadline — з Богданом):
    # Варіант 1 (поточний, під game.ts): ціле число — кількість ігрових днів на виконання
    #   (поки контракт на біржі) або кінцевий номер ігрового дня (після прийняття).
    # Варіант 2: DateTimeField (реальна дата/час, якщо симуляція прив'язана до годинника).
    # =========================================================================
    deadline = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    requirements = models.TextField(blank=True, default="")

    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (генерація ProjectTask при прийнятті контракту — з Богданом):
    # Варіант 1 (поточний): AI-генератор Богдана може одразу класти список завдань сюди у форматі
    #   [{"title": "...", "required_specialization": "backend", "work_total": 100}].
    #   Якщо поле порожнє, наш accept_contract() згенерує стартові завдання за шаблоном від difficulty.
    # Варіант 2: прибрати це поле й завжди генерувати завдання за жорстким шаблоном.
    # =========================================================================
    task_templates = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.AVAILABLE,
    )

    # TODO / УЗГОДЖЕННЯ (ліміт переговорів у AI-чаті — з Богданом):
    # Лічильник раундів переговорів для ai_service/ (можна обмежити, наприклад, 5 повідомленнями).
    negotiations_count = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(difficulty__gte=1, difficulty__lte=5),
                name="contract_difficulty_range",
            ),
            models.CheckConstraint(
                condition=models.Q(deadline__gte=1),
                name="contract_deadline_min_1",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()}, {self.budget})"


# =============================================================================
# TODO / УЗГОДЖЕННЯ (чия модель ChatMessage — Тьома чи Богдан):
# За ТЗ ендпоінти GET/POST /api/contracts/{id}/chat/ реалізує Богдан (ai_service/).
# Якщо Богдан уже створив власну модель ChatMessage в ai_service/models.py —
# цей клас потрібно видалити звідси до міграцій, щоб не було дубліката.
# =============================================================================
class ChatMessage(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(
        max_length=10,
        choices=ChatSender.choices,
    )
    content = models.TextField()
    is_fallback = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"[{self.sender}] Contract #{self.contract_id}: {self.content[:40]}"
