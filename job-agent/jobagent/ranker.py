"""Rank jobs by a blend of fit, likelihood-of-landing, and pay.

The user asked for the roles they're *most likely to get* at the *highest pay*.
Those two goals pull against each other, so we score each separately and
combine them with tunable weights.

  fit        - keyword overlap between the posting and the candidate's real
               skills / target titles. "Is this the kind of job they want?"
  likelihood - an honest estimate of whether the candidate clears the bar:
               seniority, years-of-experience, degree, and cert requirements
               are penalties; entry-level / no-degree / will-train signals are
               boosts. "Would they realistically get an interview?"
  pay        - normalized hourly pay. Missing pay scores as neutral, not zero,
               so unpaid-listed-but-good-fit roles aren't unfairly buried.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    Job,
    DEGREE_TERMS,
    ENTRY_TERMS,
    EXPERIENCE_RE,
    SENIORITY_TERMS,
)
from .profile import Profile

# Weights for the final blended score. Tuned toward the user's stated priority
# ("ones I'd be most likely to get" first, "highest pay" second) while keeping
# fit as a gate.
DEFAULT_WEIGHTS = {"fit": 0.4, "likelihood": 0.35, "pay": 0.25}

# Pay anchors (hourly USD) for normalizing pay into 0..1.
PAY_FLOOR = 15.0
PAY_CEIL = 60.0


@dataclass
class Scored:
    job: Job
    fit: float
    likelihood: float
    pay: float
    total: float
    reasons: list

    def to_dict(self) -> dict:
        d = self.job.to_dict()
        d.update(
            fit=round(self.fit, 3),
            likelihood=round(self.likelihood, 3),
            pay_score=round(self.pay, 3),
            score=round(self.total, 3),
            reasons=self.reasons,
        )
        return d


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\+#]+", text.lower()))


def fit_score(job: Job, profile: Profile) -> tuple[float, list[str]]:
    hay = job.haystack()
    hay_tokens = _tokenize(hay)
    reasons = []

    wanted = [w.lower() for w in (profile.skills + profile.keywords)]
    hits = [w for w in wanted if w in hay]
    skill_component = min(1.0, len(hits) / max(3, len(wanted) * 0.5)) if wanted else 0.0
    if hits:
        reasons.append("matches your skills/keywords: " + ", ".join(sorted(set(hits))[:6]))

    # Title alignment is worth a lot: a matching target title is a strong fit.
    title_hit = any(t.lower() in job.title.lower() for t in profile.target_titles)
    title_component = 1.0 if title_hit else (
        0.5 if any(_tokenize(t) & _tokenize(job.title) for t in profile.target_titles) else 0.0
    )
    if title_hit:
        reasons.append(f"title matches a target role")

    score = 0.6 * title_component + 0.4 * skill_component
    return score, reasons


def likelihood_score(job: Job, profile: Profile) -> tuple[float, list[str]]:
    """Honest estimate of clearing the hiring bar. Starts neutral and adjusts."""
    hay = job.haystack()
    score = 0.55
    reasons = []

    # Entry-level signals — good for a candidate early in their career.
    entry_hits = [t for t in ENTRY_TERMS if t in hay]
    if entry_hits:
        score += 0.25
        reasons.append("entry-level friendly (" + ", ".join(sorted(set(entry_hits))[:3]) + ")")

    # Seniority signals — bad if the candidate is junior.
    senior_hits = [t for t in SENIORITY_TERMS if t in hay]
    if senior_hits and profile.years_experience < 3:
        score -= 0.3
        reasons.append("posting looks senior (" + ", ".join(sorted(set(senior_hits))[:2]) + ")")

    # Years of experience requirement vs. what the candidate has.
    req_years = [int(m.group(1)) for m in EXPERIENCE_RE.finditer(hay)]
    if req_years:
        needed = max(req_years)
        if needed > profile.years_experience + 1:
            score -= min(0.35, 0.1 * (needed - profile.years_experience))
            reasons.append(f"asks for ~{needed}y experience; you have {profile.years_experience:g}")

    # Degree requirement vs. candidate.
    if any(t in hay for t in DEGREE_TERMS) and not profile.has_degree:
        score -= 0.2
        reasons.append("mentions a degree requirement you don't list")

    # Cert boost (e.g. CompTIA A+ for IT support).
    cert_hits = [c for c in profile.certifications if c.lower() in hay]
    if cert_hits:
        score += 0.1
        reasons.append("wants a cert you hold: " + ", ".join(cert_hits))

    return max(0.0, min(1.0, score)), reasons


def pay_score(job: Job) -> tuple[float, list[str]]:
    mid = job.pay_mid_hourly
    if mid is None:
        return 0.5, ["pay not listed (scored neutral)"]  # neutral, not zero
    norm = (mid - PAY_FLOOR) / (PAY_CEIL - PAY_FLOOR)
    norm = max(0.0, min(1.0, norm))
    return norm, [f"~${mid:.0f}/hr"]


def passes_filters(job: Job, profile: Profile) -> bool:
    if profile.min_pay_hourly and job.pay_mid_hourly is not None:
        if job.pay_mid_hourly < profile.min_pay_hourly:
            return False
    return True


def rank(
    jobs: list[Job],
    profile: Profile,
    weights: dict | None = None,
    min_fit: float = 0.15,
) -> list[Scored]:
    w = weights or DEFAULT_WEIGHTS
    out: list[Scored] = []
    for job in jobs:
        if not passes_filters(job, profile):
            continue
        fit, fr = fit_score(job, profile)
        if fit < min_fit:
            continue  # not the kind of job the candidate wants
        like, lr = likelihood_score(job, profile)
        pay, pr = pay_score(job)
        total = w["fit"] * fit + w["likelihood"] * like + w["pay"] * pay
        out.append(Scored(job, fit, like, pay, total, fr + lr + pr))
    out.sort(key=lambda s: s.total, reverse=True)
    return out
