# ADR-003: Deactivate officers who leave; never delete them

**Status:** accepted
**Date:** 2026-10-22

## Context

Chi Chapter officers change every year. The old site was run by one alum with no
way to hand it over, so the chapter lost control of its own history.

## Decision

When an officer leaves, an Admin deactivates their User account. It is never
deleted. Their posts and bylines stay, and their login stops working at once:
a deactivated User cannot log in, and an open session is refused on its next
request. There is no delete-user route.

Options rejected:

- **Delete the user.** `posts.author_id` references `users`, so deletion would
  orphan or remove their posts. History would vanish when people do.
- **Transfer their posts to the new officer.** It puts words under the wrong
  name and term year. A byline records who held which position when.

## Consequences

- Bylines (name, title, term year) are copied at first publish and never change.
- The `users` table only grows, at about one new officer per role per year. That
  is an accepted cost.
