# MP2 report scratch — running log

Raw notes as things happen. Rough is fine; the report gets written from this later.
Save in the repo as `notes/report-scratch.md`.

---

## Drift (report Q2 — need ONE real instance)
<!-- What drifted? (renamed field, dropped rule, extra feature) Which catch found it: CONTEXT.md mismatch / wrong test / /code-review? Ticket #? -->

- **Grill Q21: it merged `cms publish` and `cms deploy` into one command.** Its recommendation was "render, show summary, ask y/N, then push" all in `cms publish`. But the manual (Part 7) and the template already have two separate commands, and required capability #7 says `cms publish` writes `site/`. I caught it by comparing against the manual before it reached the spec, and told it to keep the split. Claude checked `app/cli.py`, confirmed `publish` and `deploy` were already separate subcommands, admitted it had muddled it, and updated CONTEXT.md ("Publish run" = render + check, new term "Deploy", "Live" = as of latest Deploy). Cheapest possible catch: no code written yet.

## Model failures (README — need ONE)
<!-- What it got wrong, how you noticed, what you did -->

- **Grill batched questions.** The manual says `/grill-with-docs` asks one question at a time; round 1 dumped 8 questions at once with recommendations. Easier to rubber-stamp everything that way. I answered each one separately and overrode three.

## Setup snags (minor)

- Transcript hook names files `your-name` unless `CMS_STUDENT` is set in `.env` — not mentioned in the manual. Added `CMS_STUDENT=Faisal Syed` and renamed the saved transcripts.

## Prompts I actually used (README — need TWO, quoted exactly)

1. `/tdd Implement decide() in .claude/hooks/ctx_guard.py so the failing tests in tests/test_ctx_guard.py pass. Do not change the tests.`
   → Worked: 10/10 green, tests untouched (verified with `git diff --stat`).
2. Grill round 3 answer (sent to `/grill-with-docs`):
   > q17: add an optional event date, because many of our posts are events like rush and philanthropy. q21: keep the templates split. cms publish renders site/ and shows the summary, and refuses if a draft would show up. cms deploy pushes to gh-pages and asks me to confirm first. dont merge them, the manual and grader expect both. the repo is public, so keep unapproved photos out of the image folder. yes on everything else

   → Caught the Q21 drift (see Drift section) and overrode Q17. Claude confirmed the template already split the commands and fixed CONTEXT.md.
   → **Honesty note for the AI Use Statement:** I worked through the project with a separate Claude chat as a guide, and the q21 wording was drafted there with me before I sent it. Say so in the README.

3. (backup) `Commit and push everything with the message "setup: template configured, T00 green". First show me git status and confirm .env and cms.db are not being committed.`
   → Claude checked `git check-ignore` and a dry-run `git add -A` before committing.

## Grill decisions that were MINE (report Q1)
<!-- Especially where you overrode the recommendation. What it suggested → what you chose → why -->

Round 1 (8 questions):
- **Q1 OVERRIDE — who edits Pages.** It recommended admin-only Pages. I said the community service chair should handle the Community Service page and the alumni relations chair the History page. As president I don't want to be the sole person who can make changes — that's the exact problem we have now with one alum running the old site.
- **Q4 — publishing.** Editors can mark their own posts published, but I give final approval: only I run `cms publish`.
- **Q5 OVERRIDE (partial) — bylines.** It suggested display name + optional title. I want full name AND title AND the year of their term, because people change positions every year and "Secretary" alone would point to the wrong person later.
- **Q8 OVERRIDE — images.** It recommended no images this version. I want images: it's a fraternity site and social chairs will want event and service photos.
- **Q8 follow-up — how images work.** Claude laid out the risks of real uploads: SVG can carry script, phone photos carry GPS location (the personal-info must-not), and stripping it needs a new dependency (Pillow). Chose (b): an admin-managed image folder, referenced by relative path; only images used by Published content get copied at publish. Tradeoff: I'm the one who adds photos, against my Q1 reason. Uploads = stretch goal.

Round 2 (Q9–Q15) — accepted all:
- Q9 assigned editors can publish a Page but not delete it; only Admin creates/deletes Pages.
- Q10 pages assigned to a person, not a position; deactivating them leaves the page unassigned with a warning. (Means re-assigning by hand every May.)
- Q11 byline title + term is a snapshot at first publish, so my term-year idea doesn't rewrite old posts.
- Q12 editors see everything but other people's items are read-only — answers my field-note worry about editors deleting each other's posts. No categories/tags/bulk actions; status is a big colored badge (my "status is hard to see" note).
- Q15 permission wall names the current Admin and a chapter contact — straight from my WordPress note that the error page didn't say who the admin was.
- Claude split "Published" (editor sets it) from "Live" (actually on the site) as two terms in CONTEXT.md.

Round 3 (Q16–Q21):
- Q16 accepted: editing a Live item changes it in place; "changed since last release" marker; my review of the publish summary is the gate.
- **Q17 OVERRIDE — event date.** It recommended no event date (write it in the body). I added an optional event date because a lot of our posts are events like rush and philanthropy.
- Q18 accepted: Home is a flagged Page + 5 latest posts; News lists all posts on one page.
- Q19 accepted: 12-char minimum, argon2, lock 10 min after 5 failures, 8-hour sessions, admin resets editor passwords, `cms reset-password` for the admin.
- Q20 accepted: `cms create-admin`, `cms backup` outside the repo, handover checklist in README (fixes the "what if the president graduates" problem).
- **Q21 OVERRIDE — keep publish/deploy split** (see Drift section).
- Final recap confirmed. Claude added 4 unasked defaults (event date shown separately, deploy fingerprints for "changed", deploy refuses stale site/, glossary terms) and asked me to veto any.
- No new ADRs: Claude said none of these met the bar (all follow from ADR-001 or are easy to reverse).

Accepted in Round 1: Q2 (shared machine, admin runs publish, remote access as stretch goal), Q3 (deactivate never delete, last admin can't be removed), Q6 (pages: nav order + show-in-nav, admin sets), Q7 (slug locked after first publish).

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
- **The template shipped with someone else's ledger rows.** First `usage_report.py` run showed 33% of a 5h window and 22% weekly, with Fable 5.1 and Sonnet 5 — models I never used. `head` showed rows dated Sep 29 at 55% weekly, a week before I started. Removed everything not dated Oct 6. Real numbers: 8% of a 5h window, 1% weekly. Lesson: check the data before trusting the forecast.
- Phase file wasn't set, so all my setup turns are "unlabelled". Set it to `grill` before starting.
- `/tdd` for `spend()` (Exercise B): 8/8 green, tests untouched. Again skipped "confirm seams" since tests were given.

## Budget numbers (report Q4)
<!-- Paste usage_report.py output after T01 and T03. Plan vs actual. -->

Status line after setup + Exercise A: 5h 13% · weekly 7% (Sonnet 5.5, medium). Those are absolute meter readings, not what MP2 cost.

Ledger after cleanup (setup + Ex A + Ex B, 10 turns): **8% of 5h spent, 1% weekly**. So the weekly cost per % of window is much lower than my plan assumed (I guessed ~0.5% weekly per 1%; actual ~0.13%). My weekly forecast in the budget plan is probably too pessimistic.

| Stage | Planned % of 5h | Actual % | Notes |
|---|---|---|---|
| setup + Ex A + Ex B | — | 8% | weekly 1%, "unlabelled" |
| grill/spec/tickets | 50% | | |
| per ticket (avg) | 10% | | |
| per review | 2% | | |

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
| ~4:20–4:50 | WordPress Playground field trip, field notes written |
| ~4:50 | Client chosen: Delta Tau Delta, Chi Chapter (I'm president). Brief written |
| ~5:00 | Exercise B green (8/8), budget plan written |
| ~5:08 | Found + removed template's stale ledger rows; phase set to `grill` |
