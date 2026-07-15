# job-agent

A personal, **human-in-the-loop** assistant for a remote job search. It:

1. **Finds** remote job postings from legitimate public job APIs.
2. **Ranks** them by a blend of *fit*, *likelihood you'd land it*, and *pay* —
   so you spend effort on roles you'd most likely get at the best pay.
3. **Drafts** an honest, tailored cover letter for the ones you pick.

It **never auto-submits an application.** You review every draft and click
submit yourself. Here's why that's a feature, not a limitation.

## Why it doesn't blindly auto-apply

The obvious dream is "a bot that applies to hundreds of jobs while I sleep." In
practice that backfires:

- **It mostly doesn't work.** Applicant-tracking systems (iCIMS, Workday,
  Greenhouse, LinkedIn, Indeed) actively block bots with CAPTCHAs, device
  fingerprinting, and rate limits. The iCIMS link that inspired this tool
  returns `403 Forbidden` to any automated fetch.
- **It can get you blacklisted.** Automated submission violates the Terms of
  Service of essentially every major job platform. Getting flagged can burn
  your account *and* your name in an employer's system.
- **Volume loses.** Employers increasingly detect and auto-reject mass/AI-blasted
  applications. For a remote help-desk role with hundreds of applicants, one
  tailored application from a real person beats 200 bot submissions.
- **Misrepresentation risk.** A bot answering screening/EEO questions *as you*,
  unsupervised, is a bad idea.

So this tool automates the tedious 90% — search, triage, ranking, first-draft
writing — and leaves the 10% that must be human (final review + submit) to you.
The result is faster *and* higher quality.

### Honesty guarantee

The draft generator may only claim facts that are in your `profile.json`. It
never invents skills, certifications, years of experience, or employers. Keep
`profile.json` accurate and your applications stay truthful.

## Install

Nothing to install — pure Python 3.9+ standard library, no dependencies.

```bash
cd job-agent
```

## Usage

```bash
# Offline demo with the bundled sample dataset (works with no network):
python -m jobagent --sample find --top 10
python -m jobagent --sample find --top 10 --why      # explain each ranking
python -m jobagent --sample draft --index 1          # cover letter for row 1
python -m jobagent --sample draft --index 1 --out cover.txt

# Live sources (run from a machine with open outbound internet):
python -m jobagent find --top 15
python -m jobagent --source remotive --source wwr find --query "help desk"
python -m jobagent find --json > results.json
```

By default `find` uses your `profile.json` in this folder. Point at another
with `--profile path/to/profile.json`.

### Live sources

| name       | endpoint                                   | notes                          |
|------------|--------------------------------------------|--------------------------------|
| `remotive` | `remotive.com/api/remote-jobs`             | documented public JSON API     |
| `remoteok` | `remoteok.com/api`                         | public JSON API (attribution)  |
| `wwr`      | `weworkremotely.com/*/rss`                 | public RSS category feeds      |
| `sample`   | bundled `jobagent/data/sample_jobs.json`   | offline testing                |

These are endpoints meant to be consumed programmatically. The tool
deliberately does **not** scrape ATS sites like iCIMS/Workday/Greenhouse.

> Note: in a locked-down/sandboxed network (including the environment this was
> built in), outbound access to these hosts may be blocked — you'll see a
> `network error` message. Use `--sample`, or run it from your own machine.

## How ranking works

Each posting gets three 0–100% sub-scores (see `jobagent/ranker.py`):

- **Fit** — keyword/title overlap with your `skills`, `keywords`, and
  `target_titles`. "Is this the kind of job you want?"
- **Likelihood** — an honest estimate of clearing the bar. Seniority terms,
  "N+ years", and degree requirements you don't have are *penalties*;
  entry-level / no-degree / will-train signals and certs you *do* have are
  *boosts*.
- **Pay** — normalized hourly pay (annual salaries converted at 2080 h/yr).
  Missing pay scores neutral, not zero.

Blended with weights `fit 0.40 / likelihood 0.35 / pay 0.25` (edit
`DEFAULT_WEIGHTS` in `ranker.py` to reprioritize).

## Your profile

`profile.json` is prefilled from the resume in this repo. **Edit it to reflect
reality** — every draft and score depends on it. Two high-leverage moves for
IT-support roles specifically:

- Add a **CompTIA A+** certification once earned — it's the standard entry
  credential and directly raises your likelihood score on these roles.
- Fill in any real troubleshooting / tech experience under `experience_summary`.

## Tests

```bash
python tests/test_jobagent.py     # or: python -m pytest job-agent/tests
```

## Layout

```
job-agent/
  profile.json            your candidate profile (edit this)
  jobagent/
    __main__.py           `python -m jobagent`
    cli.py                argparse CLI: find / draft
    sources.py            remotive / remoteok / wwr / sample fetchers
    ranker.py             fit + likelihood + pay scoring
    drafts.py             honest cover-letter + application checklist
    models.py             Job type + pay parsing
    profile.py            profile + resume-HTML text extraction
    data/sample_jobs.json offline sample dataset
  tests/test_jobagent.py
```
