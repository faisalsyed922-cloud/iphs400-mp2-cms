# Token budget plan

(Part 5.4 of the manual. Written before my first /implement, Tue Oct 6, ~5 pm.)

## What my account has

`/model` shows Opus, Sonnet 5.5, and Haiku. No `opusplan` option.

## Plan

| Stage | Model | Effort | My estimate (% of a 5-hour window) |
|---|---|---|---|
| `/research`, quick lookups | Haiku | low | small, a few % |
| `/grill-with-docs`, `/to-spec`, `/to-tickets` | Sonnet 5.5 | high | 50% (one long session) |
| `/implement` + `/tdd` (per ticket) | Sonnet 5.5 | medium | 10% |
| `/code-review` (per ticket) | Sonnet 5.5 | high, lower if tight | 2% |

I'm using Sonnet for planning instead of Opus because Opus uses the limits faster and I'm doing the whole project in about a day.

## Baseline so far

Setup + Exercise A: **13% of the 5-hour window, 7% of the weekly cap** (Sonnet 5.5, medium). So 1% of a window ≈ 0.5% of the week.

## Forecast

Remaining work with 7 tickets:
- Grill + spec + tickets: 50%
- 7 tickets × 10% = 70%
- 7 reviews × 2% = 14%
- **Total ≈ 134% of a 5-hour window ≈ 2 windows.**

**How much of the week:** at ~0.5% weekly per 1% of a window, that's about 70% more of the weekly cap, ending around 80% total. It fits, but not with much room, and 10% per ticket might be optimistic.

## If I'm wrong, what I cut first

1. Lower effort for `/code-review`.
2. Medium (or low) effort for implementing; `/clear` between every ticket.
3. Stay at 7 tickets, not 9.
4. Plan B (OpenRouter) for the last tickets, only if `usage_report.py` says OVER BUDGET.

I'll re-check with `uv run python scripts/usage_report.py --remaining N` after T01 and after T03.
