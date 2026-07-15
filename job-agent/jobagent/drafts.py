"""Generate an honest, tailored cover-letter draft for a chosen job.

Design rule: the draft may only assert facts that come from the candidate's
own profile. It never invents skills, certs, years of experience, or past
employers. Where the job wants something the candidate doesn't have, the draft
leans on transferable strengths and a willingness to learn instead of faking
qualifications. Every draft is marked as a DRAFT for the human to review and
edit before sending.
"""

from __future__ import annotations

import textwrap

from .models import Job
from .profile import Profile
from .ranker import Scored, fit_score


DISCLAIMER = (
    "--- DRAFT: review and edit before sending. This was generated from your "
    "profile only; verify every claim is accurate and add specifics where you "
    "can. Do not submit anything you haven't read. ---"
)


def _matched_skills(job: Job, profile: Profile) -> list[str]:
    hay = job.haystack()
    return [s for s in profile.skills if s.lower() in hay]


def cover_letter(job: Job, profile: Profile) -> str:
    matched = _matched_skills(job, profile)
    skills_line = (
        "In particular I bring " + ", ".join(matched) + "."
        if matched
        else "I'm early in my technical career and eager to grow into this role."
    )

    strengths = profile.experience_summary or (
        "I have hands-on customer-service and training experience and a track "
        "record of learning quickly on the job."
    )

    cert_line = ""
    if profile.certifications:
        cert_line = " I hold " + ", ".join(profile.certifications) + "."

    paragraphs = [
        "Dear Hiring Manager,",
        f"I'm writing to apply for the {job.title} position at {job.company}. {skills_line}",
        f"{strengths}{cert_line} I'm confident these strengths would let me support your "
        "users reliably and pick up your tools and processes quickly.",
        "I'm particularly drawn to this role because it's remote and lets me contribute "
        "while I continue building my technical skills. I'd welcome the chance to discuss "
        "how I can help your team.",
        "Thank you for your time and consideration.",
    ]
    signature = "\n".join(
        ["Sincerely,", profile.name or "[Your name]", profile.contact_email]
    )
    wrapped = "\n\n".join(textwrap.fill(p, width=88) for p in paragraphs)
    return f"{DISCLAIMER}\n\n{wrapped}\n\n{signature}\n\n{DISCLAIMER}"


def application_checklist(scored: Scored, profile: Profile) -> str:
    """A short, honest 'before you apply' checklist for this specific job."""
    job = scored.job
    # Only genuine gaps: requirements the candidate may not meet. Positive
    # notes (entry-level friendly, matched skills, held certs, pay) are excluded.
    def _is_gap(r: str) -> bool:
        positive = ("entry-level friendly", "matches", "you hold", "~$", "no major gaps")
        if any(p in r for p in positive):
            return False
        return any(k in r for k in ("looks senior", "asks for", "degree requirement"))

    gaps = [r for r in scored.reasons if _is_gap(r)]
    lines = [f"Before applying to: {job.title} @ {job.company}", f"  Link: {job.url}"]
    if job.pay_mid_hourly:
        lines.append(f"  Pay: ~${job.pay_mid_hourly:.0f}/hr ({job.raw_salary or 'estimated'})")
    lines.append(f"  Fit {scored.fit*100:.0f}% | Likelihood {scored.likelihood*100:.0f}% | Score {scored.total*100:.0f}%")
    if gaps:
        lines.append("  Gaps to address honestly in your application:")
        for g in gaps:
            lines.append(f"    - {g}")
    else:
        lines.append("  No major gaps detected — strong one to prioritize.")
    lines.append("  Apply on the company/original site yourself; review the draft first.")
    return "\n".join(lines)
