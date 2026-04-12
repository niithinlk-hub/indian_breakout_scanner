from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

Scalar = str | int | float | bool | None


@dataclass(slots=True)
class SignalResult:
    """Container for a single technical signal evaluation."""

    name: str
    status: str
    passed: bool
    explanation: str
    metrics: dict[str, Scalar] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoreResult:
    """Aggregated breakout score output for one instrument."""

    total_score: float
    component_scores: dict[str, float]
    rating: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExplanationResult:
    """Human-readable explanation for a flagged setup."""

    explanation: str
    trader_summary: str
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Quote:
    """Normalized quote record."""

    symbol: str
    last_price: float
    timestamp: datetime | None = None


@dataclass(slots=True)
class ScanJobResult:
    """Result of processing a single symbol in the scanner pipeline."""

    symbol: str
    success: bool
    payload: dict[str, Any] | None = None
    error: str | None = None


DateLike = date | datetime | str
