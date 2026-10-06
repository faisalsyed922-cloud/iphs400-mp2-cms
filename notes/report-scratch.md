# MP2 report scratch — running log

Raw notes as things happen. Rough is fine; the report gets written from this later.
Save in the repo as `notes/report-scratch.md`.

---

## Drift (report Q2 — need ONE real instance)
<!-- What drifted? (renamed field, dropped rule, extra feature) Which catch found it: CONTEXT.md mismatch / wrong test / /code-review? Ticket #? -->

-

## Model failures (README — need ONE)
<!-- What it got wrong, how you noticed, what you did -->

-

## Prompts I actually used (README — need TWO, quoted exactly)

1. `/tdd Implement decide() in .claude/hooks/ctx_guard.py so the failing tests in tests/test_ctx_guard.py pass. Do not change the tests.`
   → Worked: 10/10 green, tests untouched (verified with `git diff --stat`).
2. `Commit and push everything with the message "setup: template configured, T00 green". First show me git status and confirm .env and cms.db are not being committed.`
   → Claude checked `git check-ignore` and a dry-run `git add -A` before committing. Adding the safety check to the prompt made it verify, not assume.

## Grill decisions that were MINE (report Q1)
<!-- Especially where you overrode the recommendation. What it suggested → what you chose → why -->

-

## /code-review pushback (A5)
<!-- Findings you disagreed with + your reason. Ticket # -->

-

## Skills — what and why (report Q3)

- `/setup-matt-pocock-skills` — configured GitHub as tracker. Its `/ask-matt` answer also offered `/implement-spec` (whole spec at once, parallel subagents). Chose NOT to use it: grading needs one ticket per session with a review comment on each.
- `/tdd` — for Exercise A. It skipped its own "confirm seams first" step because the tests were already given and the seam (`decide()`) was named in the prompt.

## Bugs / regrets / surprises

- **Skills weren't actually in the template.** Manual says "pinned skills" are included, but `.claude/skills/` only had `PINNED.md`. `/setup-matt-pocock-skills` came back "unknown command" until I ran `npx skills@latest add mattpocock/skills` myself. Chose **Copy** over symlink so the files live in the repo.
- **Clone failed** with "Could not resolve to a Repository" — my GitHub username is `faisalsyed922-cloud`, not `faisalsyed922`. Found it with `gh auth status`.
- **Started Claude with `--dangerously-skip-permissions`** for the first commit, then switched to plain `claude` — on a "commit everything" request that flag could have pushed `.env`. Now using auto mode.
- `pytest` not on PATH; Claude ran tests with `.venv/bin/python -m pytest`.

## Budget numbers (report Q4)
<!-- Paste usage_report.py output after T01 and T03. Plan vs actual. -->

Baseline after setup + Exercise A: **5h 13% · weekly 7%** (Sonnet 5.5, medium).

| Stage | Planned % of 5h | Actual % | Notes |
|---|---|---|---|
| setup + Exercise A | — | 13% | weekly 7% |
| grill/spec/tickets | | | |
| per ticket (avg) | | | |

## Backend switches (only if Plan B)

- None. Anthropic / Claude Pro throughout so far.

## What I'd add next (report Q4)

-

---

## Timeline

| Time | What happened |
|---|---|
| Tue 3:40 pm | Started (past Tue deadline; grace runs to Wed 2:40 pm) |
| ~3:50 | Repo created from template; clone fixed (`-cloud` username) |
| ~3:57 | Skills installed via npx from PINNED.md |
| ~4:06 | Setup committed `e20e461` |
| ~4:14 | Exercise A green (10/10), committed; status line meter live |
