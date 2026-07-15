"""Job sources.

Each source pulls from a *legitimate, public* endpoint that is meant to be
consumed programmatically (documented JSON APIs / public RSS feeds). We do NOT
scrape applicant-tracking systems like iCIMS, Workday, or Greenhouse: those
prohibit automated access in their terms, actively block bots, and are exactly
where blind automation gets you rate-limited or flagged.

Sources included:
  - remotive  : https://remotive.com/api/remote-jobs  (documented public API)
  - remoteok  : https://remoteok.com/api               (public API, attribution asked)
  - wwr       : https://weworkremotely.com/*/rss        (public RSS feeds)
  - sample    : bundled offline dataset for testing without network

If your network blocks these hosts (many locked-down environments do), use
`--sample`, or run the tool from a machine with open outbound access.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from .models import Job, parse_pay

USER_AGENT = "job-agent/0.1 (personal job search; +https://github.com/)"
TIMEOUT = 20
DATA_DIR = Path(__file__).parent / "data"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("&amp;", "&").strip()


# --------------------------------------------------------------------------- #
# Remotive
# --------------------------------------------------------------------------- #
def fetch_remotive(query: str = "", limit: int = 100) -> list[Job]:
    url = "https://remotive.com/api/remote-jobs"
    params = []
    if query:
        params.append("search=" + urllib.request.quote(query))
    if limit:
        params.append(f"limit={limit}")
    if params:
        url += "?" + "&".join(params)
    payload = json.loads(_get(url))
    jobs = []
    for j in payload.get("jobs", []):
        lo, hi, raw = parse_pay(j.get("salary", ""))
        jobs.append(
            Job(
                id=f"remotive-{j.get('id')}",
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                url=j.get("url", ""),
                source="remotive",
                location=j.get("candidate_required_location", "Remote"),
                description=_strip_html(j.get("description", ""))[:4000],
                tags=j.get("tags", []) or [],
                pay_min_hourly=lo,
                pay_max_hourly=hi,
                raw_salary=raw,
                posted_at=j.get("publication_date", ""),
            )
        )
    return jobs


# --------------------------------------------------------------------------- #
# RemoteOK
# --------------------------------------------------------------------------- #
def fetch_remoteok(query: str = "", limit: int = 100) -> list[Job]:
    payload = json.loads(_get("https://remoteok.com/api"))
    jobs = []
    for j in payload:
        if not isinstance(j, dict) or "position" not in j:
            continue  # first element is a legal/attribution notice
        salary = ""
        if j.get("salary_min") and j.get("salary_max"):
            salary = f"${j['salary_min']}-${j['salary_max']} a year"
        lo, hi, raw = parse_pay(salary)
        jobs.append(
            Job(
                id=f"remoteok-{j.get('id')}",
                title=j.get("position", ""),
                company=j.get("company", ""),
                url=j.get("url", ""),
                source="remoteok",
                location=", ".join(j.get("location", "").split(",")) or "Remote",
                description=_strip_html(j.get("description", ""))[:4000],
                tags=j.get("tags", []) or [],
                pay_min_hourly=lo,
                pay_max_hourly=hi,
                raw_salary=raw,
                posted_at=j.get("date", ""),
            )
        )
    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in j.haystack()]
    return jobs[:limit]


# --------------------------------------------------------------------------- #
# We Work Remotely (RSS)
# --------------------------------------------------------------------------- #
class _RSSParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items: list[dict] = []
        self._cur: dict = {}
        self._tag = ""
        self._in_item = False

    def handle_starttag(self, tag, attrs):
        if tag == "item":
            self._in_item = True
            self._cur = {}
        self._tag = tag

    def handle_endtag(self, tag):
        if tag == "item":
            self._in_item = False
            self.items.append(self._cur)
        self._tag = ""

    def handle_data(self, data):
        if self._in_item and self._tag in ("title", "link", "description", "region", "category"):
            self._cur[self._tag] = self._cur.get(self._tag, "") + data


def fetch_wwr(query: str = "", limit: int = 100) -> list[Job]:
    # WWR category feeds. "customer-support" & "devops-sysadmin" hold most
    # help-desk / IT-support style roles.
    feeds = [
        "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    ]
    jobs = []
    for feed in feeds:
        try:
            parser = _RSSParser()
            parser.feed(_get(feed).decode("utf-8", "ignore"))
        except Exception:
            continue
        for it in parser.items:
            title = _strip_html(it.get("title", ""))
            company, _, role = title.partition(":")
            jobs.append(
                Job(
                    id="wwr-" + re.sub(r"\W+", "-", it.get("link", ""))[-40:],
                    title=(role or title).strip(),
                    company=company.strip(),
                    url=it.get("link", "").strip(),
                    source="wwr",
                    location=_strip_html(it.get("region", "")) or "Remote",
                    description=_strip_html(it.get("description", ""))[:4000],
                    tags=[_strip_html(it.get("category", ""))] if it.get("category") else [],
                )
            )
    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in j.haystack()]
    return jobs[:limit]


# --------------------------------------------------------------------------- #
# Sample (offline)
# --------------------------------------------------------------------------- #
def fetch_sample(query: str = "", limit: int = 100) -> list[Job]:
    payload = json.loads((DATA_DIR / "sample_jobs.json").read_text())
    jobs = []
    for j in payload:
        lo, hi, raw = parse_pay(j.get("salary", ""))
        jobs.append(
            Job(
                id=j["id"],
                title=j["title"],
                company=j.get("company", ""),
                url=j.get("url", ""),
                source="sample",
                location=j.get("location", "Remote"),
                description=j.get("description", ""),
                tags=j.get("tags", []),
                pay_min_hourly=lo,
                pay_max_hourly=hi,
                raw_salary=raw,
                posted_at=j.get("posted_at", ""),
            )
        )
    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in j.haystack()]
    return jobs[:limit]


SOURCES = {
    "remotive": fetch_remotive,
    "remoteok": fetch_remoteok,
    "wwr": fetch_wwr,
    "sample": fetch_sample,
}


def gather(source_names: Iterable[str], query: str = "", limit: int = 100) -> tuple[list[Job], list[str]]:
    """Fetch from each named source. Returns (jobs, errors)."""
    jobs: list[Job] = []
    errors: list[str] = []
    seen: set[str] = set()
    for name in source_names:
        fn = SOURCES.get(name)
        if not fn:
            errors.append(f"unknown source: {name}")
            continue
        try:
            for job in fn(query=query, limit=limit):
                key = (job.title.lower().strip(), job.company.lower().strip())
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(job)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            errors.append(f"{name}: network error ({e}). Try --source sample.")
        except Exception as e:  # noqa: BLE001 - surface, don't crash the run
            errors.append(f"{name}: {type(e).__name__}: {e}")
    return jobs, errors
