# 0002: Firebase instead of Supabase for accounts

**Status:** accepted, 2026-09-26. Supersedes [0001](0001-optional-accounts-with-supabase.md).

## Context

0001 picked Supabase before any project was created. Two free-plan limits then
came up: only two active projects per account, and free projects pause after
about a week of low use. A portfolio link can sit untouched for a week, and a
paused project means sign-in is broken for whoever clicks it next.

## Options

1. **Keep Supabase, reuse an existing project.** No code change, but users are
   shared with that other app and the pausing problem remains.
2. **Firebase Auth + Firestore (Spark plan).** Google and email/password
   sign-in, no card, several free projects, and no pausing when idle. Only the
   page changes; the API never handled logins.
3. **Separate auth (e.g. Clerk) plus a separate database.** Two services and two
   sets of keys for a feature this size.

Firebase Studio, Extensions and Dynamic Links are being retired, but Auth and
Firestore are not on any deprecation list as of this date.

## Decision

Option 2. Everything else from 0001 stands: sign-in stays optional, guests keep
history in `localStorage`, guest history moves into the account on first
sign-in, and the API stays stateless about users (the page sends
`previous_scores`).

Details:

- Interviews live at `users/{uid}/interviews/{id}` as `{ json, created_at }`.
  The entry is stored as a JSON string because Firestore rejects nested arrays
  and `undefined`, and reports can contain both.
- Google sign-in uses a pop-up, not a redirect. Redirect sign-in has extra
  setup on sites not hosted on Firebase Hosting, and a pop-up keeps an
  in-progress interview on screen.
- The SDK is loaded from `gstatic.com` at a pinned version, only when
  `FIREBASE_CONFIG` is set.

## Consequences

- `firestore.rules` is the whole security boundary for saved history. It has to
  be published in the Firebase console; it is not deployed from this repo.
- The Firebase web config sits in `web/index.html`. It is public by design.
- No email confirmation: Firebase signs a new email/password user in at once, so
  there is no mail-sending limit to trip over. The trade-off is that addresses
  aren't verified, which is acceptable for a practice tool.
