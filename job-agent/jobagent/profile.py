"""Load the candidate profile and (optionally) enrich it from a resume file."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class Profile:
    name: str = ""
    headline: str = ""
    # Skills / keywords the candidate genuinely has. Drives fit scoring and is
    # the ONLY material the draft generator is allowed to claim.
    skills: list = field(default_factory=list)
    # Roles the candidate is targeting; used to build source queries.
    target_titles: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    # Honest self-assessment used for the "likelihood" score.
    years_experience: float = 0.0
    has_degree: bool = False
    certifications: list = field(default_factory=list)
    # Preferences / filters.
    remote_only: bool = True
    part_time_ok: bool = True
    min_pay_hourly: float = 0.0
    locations_ok: list = field(default_factory=lambda: ["Remote", "US", "Anywhere"])
    # Free-text real experience the cover letter may draw on, honestly.
    experience_summary: str = ""
    contact_email: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        data = json.loads(Path(path).read_text())
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


def resume_text_from_html(path: str | Path) -> str:
    """Extract plain text from a resume HTML file (best effort)."""
    p = Path(path)
    if not p.exists():
        return ""
    parser = _TextExtractor()
    parser.feed(p.read_text(errors="ignore"))
    return re.sub(r"\s+", " ", parser.text()).strip()
