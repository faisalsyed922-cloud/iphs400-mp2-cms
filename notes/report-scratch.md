# MP2 report scratch — running log

Raw notes as things happen. Rough is fine; the report gets written from this later.
Save in the repo as `notes/report-scratch.md`.

---

## Drift (report Q2 — need ONE real instance)
<!-- What drifted? (renamed field, dropped rule, extra feature) Which catch found it: CONTEXT.md mismatch / wrong test / /code-review? Ticket #? -->

- **Grill Q21: it merged `cms publish` and `cms deploy` into one command.** Its recommendation was "render, show summary, ask y/N, then push" all in `cms publish`. But the manual (Part 7) and the template already have two separate commands, and required capability #7 says `cms publish` writes `site/`. **Who spotted it:** my guide chat (a separate Claude conversation I used to walk through the manual) pointed out that the manual and template already split the commands. I agreed and sent the correction to Claude Code before it reached the spec, and told it to keep the split. Claude checked `app/cli.py`, confirmed `publish` and `deploy` were already separate subcommands, admitted it had muddled it, and updated CONTEXT.md ("Publish run" = render + check, new term "Deploy", "Live" = as of latest Deploy). Cheapest possible catch: no code written yet.

- **T04, caught by me: wrong client name on the live site.** The deployed site's header said "Knox County Historical Society" (the manual's default example client) and the footer said "IPHS 400 Mini-Project #2". My client is Delta Tau Delta, Chi Chapter, and CONTEXT.md and the spec both say so, but the template default was never replaced. 96 green tests and two reviewers per ticket missed it because no test checked the site name; I only saw it by opening the real page. Lesson: look at the actual output, not just the test count. My naming call: the site leads with "Delta Tau Delta at Kenyon College", with "Chi Chapter" coming after. Reason: it makes more sense for people without deep knowledge of Delt chapters. **"Barebones" design:** decided to wait until after T08 to decide whether to add a 9th ticket for public-site design, since Pages and navigation (T07) will change the layout anyway.

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
   → **Honesty note for the AI Use Statement:** I worked through the project with a separate Claude chat as a guide. It walked me through the manual, flagged several issues (Q21 merge, email vs username, the weakened javascript test), and helped word some prompts, including the q21 line. The client, my overrides and their reasons (chairs editing their pages, term years on bylines, event date, keeping 8 tickets, images as stretch, own-laptop reasoning) were mine. Say all this in the README.

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

Spec + tickets:
- Spec = issue #1. Claude stopped before publishing to check test seams and to ask before creating labels on the remote repo (spec, ticket, ready-for-agent, stretch didn't exist).
- **Mismatch: login by email vs username** (flagged by my guide chat). The grill said `cms reset-password <username>`, but the template's `client_as` test helper and seed users log in by email. Told it login uses email everywhere so the tickets wouldn't fight the test helper.
- Told it the 7 required capabilities come first, and my extras (images, event date, backup, lockout, fingerprints) go last so they can be cut.
- `/to-tickets` proposed 8 core + 5 stretch. My calls: kept T02 and T07 whole (one session each), T05 blocked only by T01, **kept T06 password reset separate** so I have 8 core instead of the 7 minimum (safety margin), accepted the time-based "pending release" shortcut until fingerprints.
- **Images stay stretch.** Considered making T09 a core ticket since it was my grill override, but images aren't one of the 7 capabilities and the chapter doesn't need photos right away. Stretch tickets get only the `stretch` label so the `ticket` count stays at 8.

Accepted in Round 1: Q2 (shared machine, admin runs publish, remote access as stretch goal), Q3 (deactivate never delete, last admin can't be removed), Q6 (pages: nav order + show-in-nav, admin sets), Q7 (slug locked after first publish).

## /code-review pushback (A5)
<!-- Findings you disagreed with + your reason. Ticket # -->

- **T01 (#2):** `/implement` ran `/code-review` itself as two background agents (standards + spec). Fixed: duplicated login render, `cms serve` refuses the default secret key, `.env` loader strips quotes. Deferred: default-deny admin router → T05, 12-char password minimum → T06. Accepted: expiry test only checks cookie Max-Age; logout clears a signed cookie so a stolen cookie stays valid until expiry. (My view on that: it's fine, because we all just use our own laptops for this, so nobody else is on the machine to copy the cookie.)

## Ticket log

| Ticket | Issue | Commit | Tests | Notes |
|---|---|---|---|---|
| T01 login/logout/CSRF | #2 | 5007c3d | 38 pass | Changed `client_as` and `test_t00` on purpose (ticket said so). Added a `.env` loader in app/settings.py because there wasn't one. About 3 minutes of work. |
| T02 posts + preview | #3 | 9b212c4 | 59 pass | Review fixed: preview showed the viewer's byline instead of the author's, preview printed "None", missing CSRF tests on other POST routes. Deferred: refusal page naming the Admin → T05. **During TDD it weakened its own security test** (`"javascript:" not in html` → `href="javascript" not in html.lower()`) instead of changing the code. My guide chat flagged it; I asked Claude Code why before pushing. Outcome: both versions were wrong. The original failed because the output was *safe* (markdown-it prints a javascript: link as harmless plain text), so it was too blunt; the replacement missed single quotes and encodings, so it was too narrow. Claude replaced it with a test that parses every real href/src/action over 15 attack payloads (encoded `java&#115;cript`, tabs, single quotes, data:, vbscript:), then **proved the test can fail** by temporarily breaking the sanitizer (7 of 15 failed). Commit b345171, 73 tests. Strong report Q2 candidate. My takeaway: a green test doesn't mean everything is automatically good; a test could be passing because it is checking the wrong thing. |
| T03 cms publish | #4 | ddf7af2 | 83 pass | Builds index.html (5 latest), news.html, posts/<slug>.html. Draft guard builds in a side folder and only swaps in if no Draft appears. Review found a real bug: a Draft titled "News" or "Rush" would block every publish. **Claude fixed it by narrowing the guard to post pages only and changing the leak tests to match**, so a draft leaking onto the home or news page wouldn't be caught. Guide chat flagged it; I asked for a fix that keeps every page covered. Outcome: Claude switched the guard from matching titles to matching **post ids and slugs** (each post entry carries a `data-post-id` marker), checked on **every** page. Added a test that leaks a Draft onto index.html alone and expects a refusal naming index.html; disabled the guard to prove that test (and two other leak tests) fail. Second commit 874b438, 84 tests, pushed. Known limit it noted on #4: a Draft title pasted as plain text with no marker or link isn't detectable; only content that goes through the templates is covered. Same pattern as T02: **twice now, the model's first fix for a failing test was to weaken the safety check.** |
| T04 cms deploy | #5 | c43d824 | 96 pass | `cms deploy` asks to confirm (default no), only pushes site/, records the deploy time. Tests stub the push so nothing touches gh-pages. **Added an unrequested guard**: deploy refuses if site/ has root-absolute paths (`/style.css`), the exact MP1 bug the manual warns about. Scope creep, but small and it backs a ticket criterion, so I kept it. README got the publish-then-deploy steps and the handover checklist. Review fixed several weak tests. Claude left the real deploy to me as an outward-facing step, and was honest that one acceptance criterion (post actually live on Pages) wasn't verified yet. **When I opened the live site, I caught that it said "Knox County Historical Society" (the manual's default client) at the top and "IPHS 400 Mini-Project #2" in the footer.** It shouldn't say either anywhere; it's the Chi Chapter's site. 96 tests passed and two code reviews didn't notice, because nothing tested the site name. It also looks very barebones. |

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
- **Stage 1 checker, first run: 9/12.** (1) No compaction log: the hook only writes when you `/compact`, and I never had to because `/clear` between tickets kept every session short. Created the file with an honest note instead of faking an entry; plan to do a real `/compact` during T07. (2) Root-absolute paths in the *admin* templates (`/admin/posts`). Those never reach GitHub Pages, but the checker scans all templates, so Claude fixed them without changing the checker. (3) Tag missing, expected. Second run: 11/12, only the tag left.

## Budget numbers (report Q4)
<!-- Paste usage_report.py output after T01 and T03. Plan vs actual. -->

Status line after setup + Exercise A: 5h 13% · weekly 7% (Sonnet 5.5, medium). Those are absolute meter readings, not what MP2 cost.

Ledger after cleanup (setup + Ex A + Ex B, 10 turns): **8% of 5h spent, 1% weekly**. So the weekly cost per % of window is much lower than my plan assumed (I guessed ~0.5% weekly per 1%; actual ~0.13%). My weekly forecast in the budget plan is probably too pessimistic.

| Stage | Planned % of 5h | Actual % | Notes |
|---|---|---|---|
| setup + Ex A + Ex B | — | 8% | weekly 1%, "unlabelled" |
| grill/spec/tickets | 50% | **8%** (grill 5%, spec 1%, tickets 2%) | weekly 2%. Only 10 turns total: the grill batched 6–8 questions per turn, so 21 questions took 5 turns. Way overestimated. |
| per ticket (avg), incl. review | 10% + 2% = 12% | **4%** (T01 4%, T02 3%, T03 5%) | weekly ~0% each. `/implement` runs `/code-review` inside the same session, so review cost is folded into the ticket. T03 was the most expensive because of the draft-guard follow-up fix. |

After T03 (`usage_report.py --remaining 5`): "5 tickets need ~0% of the weekly cap; 88% remains → FITS". Total so far ~28% of one 5h window for everything (setup, exercises, planning, 3 tickets). My plan assumed ~134% for the whole project; I'll end up around a third of that. I overestimated every stage by 3–6×.

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
