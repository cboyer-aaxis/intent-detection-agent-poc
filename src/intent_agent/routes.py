from enum import Enum


class Route(str, Enum):
    """Valid routing targets. The string values are the canonical labels the model must emit."""

    HYBRID_SEARCH = "Hybrid Search"
    EXACT_MATCH = "Exact Match"
    ASK_AND_FIND = "Ask&Find"

    @classmethod
    def labels(cls) -> list[str]:
        return [r.value for r in cls]

    @classmethod
    def from_label(cls, label: str) -> "Route | None":
        """Lenient lookup: tolerates case, whitespace, and 'Ask & Find' style spacing."""
        normalized = _normalize(label)
        for route in cls:
            if _normalize(route.value) == normalized or _normalize(route.name) == normalized:
                return route
        return None


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum() or ch == "&")
