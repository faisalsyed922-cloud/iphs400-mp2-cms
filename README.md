# IPHS 400 — Mini-Project #2 starter (Web CMS)

Click **Use this template** → name your repo **`iphs400-mp2-cms`** → make it **Public**.
Do not fork: a fork arrives without an Issues tab, and your tickets live in Issues.

## Start here

1. `docs/manual_iphs400_mp2-web-cms_20260922.md` — the manual. Read Part 0 and Part 1 first.
2. `docs/mp2-grading-rubric_20260922.md` — how you are graded. Read it **before** you build.
3. `docs/mp2-setup_context-threshold-hook_20260922.md` — Exercise A, in Part 4 of the manual.

## Run it

```bash
uv sync
cp .env.example .env
uv run cms serve        # then open http://localhost:8000/admin  -> "T00: hello admin"
```

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

*(Required. Replace this section: name the models and skills you used, quote two
prompts you really sent, describe one real model failure, and include a
"Backends used" table if you ever switched providers.)*
