# Protocol reference and resolved ambiguities

All routes live under `/api/v1`; interactive OpenAPI is at `/docs` and the snapshot
is `packages/shared/openapi.json`. All credentials use `Authorization: Bearer …`.
Only offers and credit funding require `Idempotency-Key`; settlement and offer
acceptance are intrinsically idempotent. Message delivery is bounded, not deduped.

## Money and authority

API offer/search/funding inputs use USD decimal amounts with at most two decimal
places. Database, principal configuration responses, ledger and earnings use
integer cents; public worker minimums and task offered_price use USD. UI converts
explicitly. No cash, payout, payment processor or bank integration exists.

Reserve at offer creation; keep reserve through work/review; settle once on result
acceptance. Fee is 20%, rounded to nearest cent, with remainder to worker. Failed,
declined, cancelled or expired unsubmitted work releases reserve. Review disputes
hold reserve for admin resolution. Ledger types are fund/reserve/release/settle;
reserve and release affect reserved funds, not balance. Balance = funded - settled.
The unique worker-earning row stores gross, fee and net for each completed task.

Limits are rolling 1 hour, 24 hours and 30 days. Each limit includes all outstanding
reservations plus settled payments in that window. Pending offers count toward
agent concurrency. Worker capacity is occupied atomically at acceptance and remains
occupied through admin review. Maximum five new offers/minute/agent and five pending
offers/worker. Identical pending objectives to the same worker are rejected.

## Time and state

Deadline is absolute from offer creation, 1–19 minutes. Revisions do not extend it.
The API sweeps on requests; the separate sweeper handles idle-system expiry every
five seconds. A submitted result at deadline enters admin_review rather than losing
its reserve automatically. Reporting and explicit admin termination close messaging.
Audit records represent accepted/submitted intermediate steps in the transaction.

The spec's `failed` versus `admin_review` conflict is resolved in favor of its dispute
model: agent rejection enters admin_review. Only admin resolution can fail submitted
work and release its reserve. Admin review is a frozen, nonterminal accounting state.
No owner approval, dispatcher, worker bidding or out-of-task messaging exists.

## Result schema and content

Draft 2020-12 bounded subset: type, properties, required, additionalProperties,
items, min/maxItems, min/maxLength, minimum/maximum, enum, description and title.
Root must be an object; schema <=12 KB, depth <=8. No references, regex, recursive
definitions or composition. Result/context <=16 KB, depth <=12; messages <=4 KB,
all HTTP request bodies <=64 KB. Arbitrary files and uploads are not supported.
Visual verification requires 1–5 public HTTPS image links. Workers open them in
a separate tab without referrer; the server never fetches user-controlled URLs.

Worker-provided content is untrusted task data; consuming agents must not treat it
as system instructions. Lexical screening blocks recognized prohibited categories
and off-platform solicitations in offers/messages/revisions. It cannot detect every
paraphrase, language, indirect reference, or malicious intent. Worker reporting and
invitation-only scope are additional controls, not proof of universal detection.

## Metrics

Autonomous completion = completed tasks without intervention / all completed tasks.
Zero denominator returns null. Reports/review timeouts mark intervention. Quality
score uses a transparent prior: (9 + completed) / (10 + completed + failed).
Schema, revision, acceptance, response and completion metrics remain separate.
New-worker completion/schema rates are 0 until observed; quality starts at 0.9.
The search-to-offer metric is a count ratio, not attributed funnel conversion and
may exceed 1. Detailed attribution would require a search-session identifier.

## Errors

Errors return `{status:"rejected", error:{code,message,category}, request_id}`.
Key codes include UNAUTHENTICATED, NOT_INVITED, FORBIDDEN, NOT_FOUND,
CAPABILITY_NOT_AUTHORIZED, PRICE_NOT_AUTHORIZED, SPENDING_LIMIT,
INSUFFICIENT_CREDITS, CONCURRENCY_LIMIT, WORKER_CAPACITY, OFFER_RATE_LIMIT,
IDEMPOTENCY_CONFLICT, INVALID_STATE, SESSION_CLOSED, MESSAGE_LIMIT,
RESULT_SCHEMA_INVALID, REVISION_LIMIT and PROHIBITED_CAPABILITY_REQUEST.
Request shape errors use FastAPI's standard 422 `detail` format.
