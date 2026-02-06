"""Notification types and data classes."""

from dataclasses import dataclass, field
from typing import Any
from config.constants import NotificationType


@dataclass
class Notification:
    """A notification to be dispatched to users."""
    type: NotificationType
    title: str
    description: str
    symbol: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    target_users: list[int] | None = None  # None = broadcast to all with matching interests
    urgency: str = "medium"  # low, medium, high, critical
    content_hash: str = ""   # For dedup

    def __post_init__(self) -> None:
        if not self.content_hash:
            import hashlib
            raw = f"{self.type.value}:{self.symbol}:{self.title}"
            self.content_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
