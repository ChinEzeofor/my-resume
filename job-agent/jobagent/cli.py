"""Command-line interface for job-agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .drafts import application_checklist, cover_letter
from .profile import Profile
from .ranker import DEFAULT_WEIGHTS, rank
from .sources import SOURCES, gather


def _load_profile(path: str) -> Profile:
    return Profile.load(path)


def _default_query(profile: Profile) -> str:
    # Default to a broad fetch and let the ranker decide relevance. Pass an
    # explicit --query to narrow the fetch (useful for large live sources).
    return ""


def cmd_find(args) -> int:
    profile = _load_profile(args.profile)
    query = args.query if args.query is not None else _default_query(profile)
    sources = args.source or (["sample"] if args.sample else ["remotive", "wwr"])

    jobs, errors = gather(sources, query=query, limit=args.limit)
    for e in errors:
        print(f"! {e}", file=sys.stderr)
    if not jobs:
        print("No jobs fetched. Try --sample for an offline demo.", file=sys.stderr)
        return 1

    ranked = rank(jobs, profile)[: args.top]

    if args.json:
        print(json.dumps([s.to_dict() for s in ranked], indent=2))
        return 0

    print(f"\nTop {len(ranked)} remote roles for {profile.name or 'you'} "
          f"(from {len(jobs)} postings across {', '.join(sources)}):\n")
    print(f"{'#':>2}  {'Score':>5}  {'Fit':>4}  {'Likely':>6}  {'Pay/hr':>8}  Title / Company")
    print("-" * 92)
    for i, s in enumerate(ranked, 1):
        pay = f"${s.job.pay_mid_hourly:.0f}" if s.job.pay_mid_hourly else "  n/a"
        title = (s.job.title[:44]).ljust(44)
        print(f"{i:>2}  {s.total*100:>4.0f}%  {s.fit*100:>3.0f}%  "
              f"{s.likelihood*100:>5.0f}%  {pay:>8}  {title} {s.job.company[:24]}")
    print()
    if args.why:
        for i, s in enumerate(ranked, 1):
            print(f"[{i}] {s.job.title} — {s.job.company}")
            print(f"    {s.job.url}")
            for r in s.reasons:
                print(f"      · {r}")
            print()
    print("Tip: `draft --index N` writes a cover-letter draft for row N. "
          "You review and submit it yourself.\n")
    return 0


def cmd_draft(args) -> int:
    profile = _load_profile(args.profile)
    query = args.query if args.query is not None else _default_query(profile)
    sources = args.source or (["sample"] if args.sample else ["remotive", "wwr"])
    jobs, errors = gather(sources, query=query, limit=args.limit)
    for e in errors:
        print(f"! {e}", file=sys.stderr)
    ranked = rank(jobs, profile)
    if not ranked:
        print("No ranked jobs to draft for.", file=sys.stderr)
        return 1
    if args.index < 1 or args.index > len(ranked):
        print(f"--index must be between 1 and {len(ranked)}.", file=sys.stderr)
        return 1
    scored = ranked[args.index - 1]

    print(application_checklist(scored, profile))
    print()
    letter = cover_letter(scored.job, profile)
    if args.out:
        Path(args.out).write_text(letter)
        print(f"Cover-letter draft written to {args.out}")
    else:
        print(letter)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jobagent",
        description="Find, rank, and draft applications for remote jobs "
                    "(human-in-the-loop; never auto-submits).",
    )
    p.add_argument("--profile", default=str(Path(__file__).parent.parent / "profile.json"),
                   help="Path to profile JSON (default: ../profile.json)")
    p.add_argument("--source", action="append", choices=list(SOURCES),
                   help="Source to use (repeatable). Default: remotive+wwr, or sample offline.")
    p.add_argument("--sample", action="store_true", help="Use the bundled offline dataset.")
    p.add_argument("--query", default=None, help="Search keywords (default: your first target title).")
    p.add_argument("--limit", type=int, default=100, help="Max postings to fetch per source.")

    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("find", help="List ranked matches.")
    f.add_argument("--top", type=int, default=15, help="How many to show.")
    f.add_argument("--json", action="store_true", help="Output JSON.")
    f.add_argument("--why", action="store_true", help="Explain each ranking.")
    f.set_defaults(func=cmd_find)

    d = sub.add_parser("draft", help="Write a cover-letter draft for one ranked job.")
    d.add_argument("--index", type=int, required=True, help="Row number from `find`.")
    d.add_argument("--out", help="Write the draft to this file instead of stdout.")
    d.set_defaults(func=cmd_draft)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
