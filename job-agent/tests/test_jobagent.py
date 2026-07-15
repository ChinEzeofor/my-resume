"""Tests for job-agent. Run: python -m pytest, or python job-agent/tests/test_jobagent.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobagent.models import Job, parse_pay
from jobagent.profile import Profile
from jobagent.ranker import rank
from jobagent.sources import fetch_sample


def test_parse_pay_hourly():
    lo, hi, raw = parse_pay("$19 - $40 / hour")
    assert lo == 19 and hi == 40


def test_parse_pay_annual_to_hourly():
    lo, hi, _ = parse_pay("$45,000 - $60,000 a year")
    # 45000 / 2080 ~= 21.6 ; 60000 / 2080 ~= 28.8
    assert 20 < lo < 23 and 27 < hi < 30


def test_parse_pay_k_suffix():
    lo, hi, _ = parse_pay("60k")
    assert hi and 28 < hi < 30


def test_parse_pay_none():
    assert parse_pay("") == (None, None, "")
    assert parse_pay("competitive salary") == (None, None, "competitive salary")


def _profile() -> Profile:
    return Profile(
        name="Test User",
        skills=["customer service", "html", "troubleshooting"],
        keywords=["help desk", "it support", "entry level", "remote"],
        target_titles=["IT Support Technician", "Help Desk Technician"],
        years_experience=0,
        has_degree=False,
        min_pay_hourly=17,
    )


def test_entry_level_beats_senior():
    jobs = fetch_sample()
    ranked = rank(jobs, _profile())
    titles = [s.job.title.lower() for s in ranked]
    # An entry-level help-desk role should outrank the senior sysadmin/architect.
    entry_idx = next(i for i, t in enumerate(titles) if "tier 1" in t or "entry" in t)
    senior_idx = next((i for i, t in enumerate(titles) if "senior" in t or "principal" in t), len(titles))
    assert entry_idx < senior_idx


def test_senior_roles_score_low_likelihood():
    jobs = fetch_sample()
    ranked = {s.job.title: s for s in rank(jobs, _profile(), min_fit=0.0)}
    senior = next((s for t, s in ranked.items() if "Senior" in t), None)
    if senior:  # senior role may be filtered by min_fit; only assert if present
        assert senior.likelihood < 0.4


def test_min_pay_filter():
    p = _profile()
    p.min_pay_hourly = 100  # absurdly high -> filters out hourly roles
    ranked = rank(fetch_sample(), p)
    for s in ranked:
        assert s.job.pay_mid_hourly is None or s.job.pay_mid_hourly >= 100


def test_it_support_role_ranks_well():
    ranked = rank(fetch_sample(), _profile(), min_fit=0.0)
    top5 = [s.job.title for s in ranked[:5]]
    assert any("IT Support" in t or "Help Desk" in t or "Technical Support" in t for t in top5)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
