# Verification record

Verified locally on 2026-09-20. This is engineering verification, not the real-user
alpha study or a claim of production deployment.

## Automated checks

- 28 tests passed on PostgreSQL 17.6, including the complete account-to-payment
  scenario, credit/capacity races, duplicate acceptance/settlement, tenant/actor
  isolation, JWT signature/issuer/audience/expiry, RLS read denial, immutable audit,
  schema/revision/message/body limits, expiry and admin dispute resolution.
- Official MCP SDK: ten tools registered, tool-driven lifecycle, and real stdio
  subprocess initialize/list-tools/call-tool handshake passed.
- Next.js production build and TypeScript compilation passed.
- npm runtime dependency audit reported zero known vulnerabilities.
- API and web Docker images built successfully from their pinned dependencies.
- The final Linux API image passed all 28 tests against PostgreSQL (91.98 seconds),
  including concurrency, RLS isolation and MCP stdio. Windows PostgreSQL run also
  passed all 28 tests; SQLite run passed 27 with the PostgreSQL RLS test skipped.
- SQLite is an additional developer fallback; the RLS test is PostgreSQL-only.

One upstream Starlette/AnyIO deprecation warning is present; tests pass. Next.js
also warns about an unrelated home-directory lockfile outside this repository.

## Live browser definition-of-done check

Ran against the real local PostgreSQL API and production Next.js build, through
the principal and worker UIs, without modifying application rows manually:

1. Principal created Acme Research · Demo and funded $500 fake credits.
2. Principal created ResearchAgent-7 with web_research and a $10 per-task limit.
3. Worker enabled web_research and availability with a $3 minimum.
4. Agent console discovered the worker and created a $4 offer.
5. Worker accepted through the UI, opening the private task session.
6. Agent sent clarification and worker sent a response.
7. Worker submitted clearly labeled synthetic prices (39 monthly / 360 annual).
8. Agent checked the structured result and accepted automatically.
9. Console displayed payment released and agent workflow resumed.
10. Worker earnings displayed gross $4.00, fee $0.80, net $3.20.
11. Principal dashboard displayed $496 available, $0 reserved, one completed
    contract and 100% autonomous completion for that single synthetic test.

The browser check simulated the worker's research with explicit fixture data.
It did not verify a real website's prices or demonstrate real human labor-market
performance. There was no principal/admin intervention after the test agent launch.

## Not yet externally verified

Hosted Supabase authentication/session refresh and project advisors, production
hosting/TLS/rate limiting, actual invited humans, comprehensive semantic safety,
and the 100-task pilot. See deployment.md for the handoff checklist and limitations.
