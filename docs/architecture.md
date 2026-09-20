# Human Relay: implementation decisions

## Risks and boundaries
Credit races, capacity races, tenant isolation, replayed settlement, schema abuse,
deadline races, and unbounded communication are the critical risks. Phase 1 uses
fake USD credits only, integer cents, three capability categories, invited US
users and digital tasks shorter than 20 minutes. Safety screening is a layered
alpha guardrail, not a claim of semantic policy completeness.

## State machine
Offers: offered -> accepted | declined | cancelled | expired.
An atomic acceptance creates one task: active -> awaiting_agent_review ->
completed | revision_requested | admin_review. Revision submission returns to
awaiting_agent_review. Active/revision tasks may expire. Review timeout goes to
admin_review to avoid silently discarding submitted work. Admin review freezes
funds until explicit admin resolution to completed or failed. Reporting also
freezes the session and reserves. Pending offers can be cancelled; accepted
work cannot be unilaterally cancelled. Submitted and accepted intermediate
events are audited inside the same transaction instead of exposed as states.

## Authorization
Agent credentials are random, hashed, revocable, organization-scoped API keys.
Human authentication verifies Supabase JWT issuer, audience, expiry and JWKS
signature. Roles come from local invitation records, never user metadata.
A separate explicit development mode supports local seeded identities.
Workers access only their offers/tasks; agents only their own contracts.
Principals manage organization policy, credits and read-only history. Admins
handle exceptional reports and resolution. Normal tasks never ask principals.
Application tables are server-only, with RLS enabled and no client policies.

## Database and transactions
SQLAlchemy models: identities, organizations, principals, agents,
agent_permissions, workers, worker_capabilities, task_offers, tasks,
task_messages, task_results, credit_transactions, worker_earnings, audit_events.
Foreign keys, nonnegative balance checks and unique offer/task/payment keys
protect invariants. Money is integer cents. API USD fields use Decimal.
For the small alpha, all writes acquire a single PostgreSQL transaction advisory
lock, serializing state-dependent checks across API processes. This intentionally
trades throughput for simple, auditable correctness at <=20 agents.
SQLite BEGIN IMMEDIATE is a local test fallback, not production evidence.

Offers reserve credits immediately. Available = balance - reserved. Rolling
hour/day/month authority counts pending reservations and settled spend, including
reservations created before the current window. Expiry releases reservations.
Settlement atomically reduces balance/reserved, appends ledger entries, inserts
unique earnings, updates reputation, closes the session and writes audit events.
Repeated completion returns the original completed task without side effects.
Offer idempotency keys bind to a canonical request hash; different payloads fail.

## Messaging, schemas and privacy
Accepted participants only, bounded message length/count, no post-terminal chat,
no unsolicited messaging, and a deadline bounded by 30 minutes. JSON Schema is
validated at offer creation, restricted to nonrecursive local schemas and bounded
size. Result validation occurs before transition. Visual context uses HTTPS image
URLs; the API never fetches user URLs. Worker task views exclude organization
secrets and other worker data. Logs contain identifiers, not credentials/content.

## Repository and milestones
apps/api: FastAPI service, SQLAlchemy models and transaction service.
apps/web: Next.js/TypeScript/Tailwind role interfaces and demo console.
apps/mcp: official Python MCP SDK wrapper over authenticated REST.
packages/shared: generated OpenAPI contract. database: schema bootstrap/security.
tests: API lifecycle, authorization, state, ledger and concurrency checks.

A: schema, identity, organization/agent/worker policy, ledger/audit; test; commit.
B: discovery/offers/sessions/results/revision/settlement/expiry; test; commit.
C: MCP, autonomous demo, role UIs, metrics, docs, end-to-end checks; test; commit.

## Verification and deployment
Local tests exercise the definition of done with a simulated worker; actual human
research is a separate interactive demo. PostgreSQL concurrency tests must run
against PostgreSQL before accepting deployment readiness. Configure Supabase
Auth and invite identities before a hosted alpha; no remote account is created
implicitly. Deployment is not part of this local build.
