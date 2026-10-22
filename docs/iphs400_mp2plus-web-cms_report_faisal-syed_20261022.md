# MP2plus Report — Faisal Syed

| Id | Evidence |
|----|----------|
| S2 | tests/test_login_hardening.py; fixture reset_login_limiter in tests/conftest.py |
| F2 | issue #16; tests/test_taxonomy.py; mp2plus-categories-1280.png, mp2plus-categories-390.png |
| S1 | tests/test_access_matrix.py |
| P3 | CONTEXT.md Decisions table; docs/adr/ADR-003-deactivate-never-delete.md |
| P4 | before: commit 55aad0b; after: commit "P4: after"; see the P4 section |

## Anything left broken
- S2: Nothing broken. The lockout is kept in memory, so it resets if the server restarts.
- F2: test_list_has_no_categories_tags_or_bulk_actions dropped its "categor" check on purpose, because F2 adds a category filter; declared on issue #16.
- S1: Nothing broken.
- P3: Nothing broken.
- P4: P4 has no phase row of its own because I ran it in the terminal, not in Claude.

## P4

**Before** (notes/mp2plus-plan.md):
Tickets done: 9 · average weekly cost per ticket: 0.6%
Forecast: 4 tickets need ~2% of the weekly cap; 93% remains → FITS

**After:**
Tickets done: 10 · average weekly cost per ticket: 0.5%

| Phase | Turns | 5h spent | Weekly |
|---|---|---|---|
| S2 | 2 | 1.0% | 1.0% |
| T16 | 5 | 3.0% | 0.0% |
| S1 | 1 | 0.0% | 0.0% |
| P3 | 2 | 1.0% | 0.0% |

The forecast was about 0.5% weekly per exercise. S2 ended up costing 1.0% and F2 showed 0.0%. The gap is rounding in a whole-percent meter, not real cost, since F2 used three times more of the 5-hour window.