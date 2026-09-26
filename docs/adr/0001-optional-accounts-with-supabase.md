# 0001: Optional accounts with Supabase

**Status:** accepted, 2026-09-26

## Context

History lived only in the browser, so it didn't follow a user to another
device. The "vs last time" delta read one server-side JSON file shared by every
visitor, which mixed strangers' scores together and was wiped whenever Render's
free instance restarted. Users asked for Google and email/password sign-in.

## Options

1. **Roll our own auth in FastAPI** (password hashing, sessions, Google OAuth,
   a database on Render). Most code and the most ways to get security wrong, and
   Render's free tier has no persistent disk for a database.
2. **Firebase Auth + Firestore.** Easy sign-in, but a document store rather than
   the Postgres most roles ask for.
3. **Supabase Auth + Postgres, called straight from the page.** Google and
   email/password built in; row-level security keeps each user's rows private
   without the API ever handling a login.

## Decision

Option 3. Sign-in is **optional**: guests keep using the app with history in
`localStorage`, and it moves into their account on first sign-in. The API stays
stateless about users: the page sends `previous_scores` (its own last score per
competency) when an interview starts, and the shared profile file is deleted.

## Consequences

- The API needs no auth code and no new Python dependency.
- The table's RLS policies (`supabase/schema.sql`) are the whole security
  boundary for saved history. Disabling them would expose every user's data.
- The publishable key and project URL sit in `web/index.html`; both are public
  by design. The secret key must never appear in the page.
- A client could send made-up `previous_scores`. That only changes its own
  report's delta, so it is validated (0–1, at most 100) but not trusted further.
- FR-14 (bias new sessions toward weak areas) was never wired to the API and
  remains unimplemented.
