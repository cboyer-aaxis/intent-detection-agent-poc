"""Rule-based Exact Match detection: queries of the form "{keyword}: {value}" with a configured keyword."""

import re
from pathlib import Path

import yaml


def load_keywords(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keywords = [str(k).strip() for k in data.get("keywords") or [] if str(k).strip()]
    for k in keywords:
        if ":" in k:
            raise ValueError(f"Exact Match keyword {k!r} in {path} must not contain ':'")
    return keywords


class ExactMatcher:
    def __init__(self, keywords: list[str]):
        self.keywords = keywords
        # Longest first so "part number" wins over a shorter keyword like "part".
        alternatives = "|".join(re.escape(k) for k in sorted(keywords, key=len, reverse=True))
        self._pattern = re.compile(rf"^\s*({alternatives})\s*:\s*(\S.*?)\s*$", re.IGNORECASE) if keywords else None

    def match(self, query: str) -> tuple[str, str] | None:
        """Return (keyword, value) if the query is "{keyword}: {value}" with a configured keyword."""
        if self._pattern and (m := self._pattern.match(query)):
            return m.group(1), m.group(2)
        return None
