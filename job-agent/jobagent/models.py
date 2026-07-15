"""Core data types and pay parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# Rough US hours-per-year for converting salaries to an hourly figure so that
# hourly and annual postings can be compared on one axis.
HOURS_PER_YEAR = 2080

# Words that indicate a posting expects seniority / credentials the way an
# entry-level candidate would read them. Used by the ranker to estimate how
# likely a given candidate is to actually land the role.
SENIORITY_TERMS = [
    "senior", "sr.", "lead", "principal", "staff", "architect", "manager",
    "director", "head of", "expert", "advanced",
]
EXPERIENCE_RE = re.compile(r"(\d+)\+?\s*(?:-\s*\d+\s*)?years?", re.I)
DEGREE_TERMS = [
    "bachelor", "b.s.", "b.a.", "bsc", "degree required", "master", "phd",
    "4-year degree", "four-year degree", "college degree",
]
ENTRY_TERMS = [
    "entry level", "entry-level", "no experience", "no degree", "junior",
    "trainee", "will train", "training provided", "tier 1", "tier i",
    "associate", "apprentice",
]


@dataclass
class Job:
    """A normalized job posting from any source."""

    id: str
    title: str
    company: str
    url: str
    source: str
    location: str = "Remote"
    description: str = ""
    tags: list = field(default_factory=list)
    # Normalized pay, per hour in USD. None when the posting gives no pay.
    pay_min_hourly: Optional[float] = None
    pay_max_hourly: Optional[float] = None
    raw_salary: str = ""
    posted_at: str = ""

    @property
    def pay_mid_hourly(self) -> Optional[float]:
        vals = [v for v in (self.pay_min_hourly, self.pay_max_hourly) if v]
        return sum(vals) / len(vals) if vals else None

    def haystack(self) -> str:
        """Lowercased blob used for keyword matching."""
        return " ".join(
            [self.title, self.company, self.description, " ".join(self.tags)]
        ).lower()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pay_mid_hourly"] = self.pay_mid_hourly
        return d


def parse_pay(text: str) -> tuple[Optional[float], Optional[float], str]:
    """Parse a free-form pay string into (min_hourly, max_hourly, raw).

    Handles common shapes like:
        "$19 - $40 / hour", "$45,000-$60,000 a year", "$25/hr", "60k".
    Returns (None, None, raw) when nothing parseable is found.
    """
    if not text:
        return None, None, ""
    raw = text.strip()
    low = raw.lower()

    # Pull all number-ish tokens, expanding "60k" -> 60000.
    nums: list[float] = []
    for m in re.finditer(r"\$?\s*([\d][\d,]*\.?\d*)\s*(k)?", low):
        token = m.group(1).replace(",", "")
        try:
            val = float(token)
        except ValueError:
            continue
        if m.group(2) == "k":
            val *= 1000
        # Ignore obvious non-pay numbers (e.g. "401k" handled by k already,
        # stray small integers like a "3" from "top 3%").
        nums.append(val)

    if not nums:
        return None, None, raw

    hourly = any(u in low for u in ["/hr", "/hour", "per hour", "an hour", "hourly"])
    annual = any(u in low for u in ["/yr", "/year", "per year", "a year", "annually", "annum"])
    # Heuristic: values >= 1000 are almost certainly annual salaries.
    if not hourly and not annual:
        annual = max(nums) >= 1000
        hourly = not annual

    lo, hi = min(nums), max(nums)
    if annual and not hourly:
        lo, hi = lo / HOURS_PER_YEAR, hi / HOURS_PER_YEAR
    # Guard against parsing junk as pay.
    if hi <= 0 or hi > 2000:
        return None, None, raw
    return round(lo, 2), round(hi, 2), raw
