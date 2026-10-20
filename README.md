# IPHS 400 — Mini-Project #2 starter (Web CMS)

Click **Use this template** → name your repo **`iphs400-mp2-cms`** → make it **Public**.
Do not fork: a fork arrives without an Issues tab, and your tickets live in Issues.

## Start here

1. `docs/manual_iphs400_mp2-web-cms_20260922.md` — the manual. Read Part 0 and Part 1 first.
2. `docs/mp2-grading-rubric_20260922.md` — how you are graded. Read it **before** you build.
3. `docs/mp2-setup_context-threshold-hook_20260922.md` — Exercise A, in Part 4 of the manual.

## Run locally

1. Install dependencies: `uv sync`
2. Copy the example settings and set a secret key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and replace `CMS_SECRET_KEY` with a long random string (for example
   `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`). Change the demo
   passwords too. `.env` is gitignored; never commit it.
3. Seed demo accounts and content: `uv run python scripts/seed_demo.py`
   (creates an Admin and an Editor using the passwords in `.env`, plus sample Posts
   and Pages).
4. Start the admin console: `uv run cms serve`
5. Open <http://localhost:8000/admin> and log in as the seeded Admin.
6. When the content is ready, render and push it (see below):
   `uv run cms publish`, then `uv run cms deploy`.

## Publish, then deploy

Nothing is Live until the Admin has done both steps, in this order:

1. `uv run cms publish` renders every Published Post into `site/` and lists what
   was rendered. It refuses if any Draft would appear. Open `site/` locally and look.
2. `uv run cms deploy` asks "Push site/ to gh-pages and make it Live? [y/N]".
   Anything but `y` pushes nothing. On `y` it pushes only `site/` to the `gh-pages`
   branch; the database, `.env` and keys never leave your machine. A successful
   Deploy is recorded with its time; a declined or failed one is not.

If `site/` does not exist, `cms deploy` tells you to run `cms publish` first. It
also stops if any page uses a root-absolute path (`href="/..."`), which would break
on the GitHub Pages project URL.

One-time setup: in GitHub, Settings -> Pages -> Deploy from a branch -> `gh-pages` /
root. The site is served over HTTPS at `https://<owner>.github.io/<repo>/`; set
`CMS_BASE_PATH` in `.env` to that URL.

## Handover checklist (outgoing Admin)

Hand your successor these three things, then do the steps in order:

- [ ] **The repository.** Add them as a collaborator on the GitHub repo (or transfer it).
- [ ] **The database.** `cms.db` is not in git. Copy it to their machine (it holds all
      Users, Posts and Pages), along with the values from your `.env` (never commit it).
- [ ] **The image folder.** Copy the admin-managed image folder; its photos are public
      once pushed, so only hand over approved ones.

Then:

1. In the console, promote your successor to Admin.
2. Have them log in and confirm they see Users management.
3. Only then Deactivate your own account. Promote first, so the site is never
   without an Admin (the last active Admin cannot be Deactivated).
4. They run `uv run cms publish` and `uv run cms deploy` once to check the workflow.

## What is here

```text
.claude/hooks/     the context meter and usage ledger (Exercise A lives in ctx_guard.py)
scripts/           usage_report.py (Exercise B lives in spend()), check_submission.py, seed_demo.py
tests/             the exercise tests, plus helpers such as client_as("editor")
app/, templates/   the T00 skeleton — every CMS feature is yours to build
docs/adr/          two example decision records
```

Two functions are deliberately unfinished and their tests fail until you write them:
`decide()` in `.claude/hooks/ctx_guard.py` and `spend()` in `scripts/usage_report.py`.
Both are graded. Use `/tdd`, as the manual says.

## Deadlines

Stage 1 (`mp2-mvp` tag): Tue Sep 29, 2:40 pm Eastern (soft target).
Stage 2 (`mp2-final` tag): Tue Oct 6, 2:40 pm Eastern, grace until Wed Oct 7, 2:40 pm.

Run `uv run python scripts/check_submission.py --stage 2` before you submit.

## Generative AI Use Statement

**Tools and models.** I built this project with Claude Code on a Claude Pro plan, using Sonnet 5.5: high effort for planning (`/grill-with-docs`, `/to-spec`, `/to-tickets`) and medium effort for implementing tickets. I used the mattpocock engineering skills (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, `/handoff`). Every ticket was implemented by Claude Code in its own session, with `/code-review` findings posted on the issue before it closed.

**Guide chat.** Alongside Claude Code, I used a separate Claude chat as a step-by-step guide to the manual. It explained commands and errors, helped word some of my prompts (including part of my grill answer below), and flagged several problems that I then decided on and sent to Claude Code: the grill merging `cms publish` and `cms deploy` into one command, the email-vs-username mismatch in the spec, the weakened javascript test in T02, the narrowed draft guard in T03, and the T05 ticket/issue numbering mix-up in the phase file. It also kept my running notes file and drafted this statement, which I edited.

**What was mine.** The client (my own chapter, Delta Tau Delta Chi Chapter at Kenyon, where I'm president), the WordPress field notes, the client brief, and the decisions and reasons in the grill and during tickets. For example: letting the community service and alumni chairs edit their own pages so I'm not the only one who can make changes; full name, title and term year on bylines because officers change every year; an optional event date for rush and philanthropy posts; keeping 8 core tickets instead of 7; leaving images as a stretch goal; naming the newest admin on the refusal page; letting editors take their own page back to Draft; the site name order; and the purple, white and gold design. I caught the starter site name ("Knox County Historical Society") on the live site by opening it, and found that the "New page" button opened the post form by using the CMS to add my chapter's real pages.

**Two prompts I used.**

1. Exercise A:
   > /tdd Implement decide() in .claude/hooks/ctx_guard.py so the failing tests in tests/test_ctx_guard.py pass. Do not change the tests.

2. My answer to grill round 3:
   > q17: add an optional event date, because many of our posts are events like rush and philanthropy. q21: keep the templates split. cms publish renders site/ and shows the summary, and refuses if a draft would show up. cms deploy pushes to gh-pages and asks me to confirm first. dont merge them, the manual and grader expect both. the repo is public, so keep unapproved photos out of the image folder. yes on everything else

**One model failure.** In T02, a security test failed (`"javascript:" not in html`), and Claude changed the test to a narrower check (`href="javascript"`) instead of fixing the code. Questioned before pushing, it explained the original test was too blunt (the output was actually safe) and the replacement too narrow (it missed single quotes and encoded tricks like `java&#115;cript`). It replaced both with a test that checks every real link over 15 attack payloads, and proved the test can fail by temporarily breaking the sanitizer. The same pattern, weakening a safety check to make a test pass, happened again with the draft guard in T03.
