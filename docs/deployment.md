# Hosted alpha runbook

## Supabase setup

Use a dedicated Supabase project with asymmetric JWT signing (ES256 or RS256).
Disable open signups and invite the actual US alpha users through Supabase Auth.
Backend verification uses the project's JWKS URL and checks signature, issuer,
audience, expiry and subject. It then checks a local active identity record.
No authorization trusts user_metadata. Local suspension is immediate; Supabase
session revocation alone may leave access tokens valid until expiry.

Set DATABASE_URL to a server-only PostgreSQL connection, SUPABASE_URL to the
project root URL, DEV_AUTH=false, and WEB_ORIGIN to the exact deployed web origin.
Set frontend NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
never put a service-role key, database password or agent key in public build vars.
Build the frontend after configuration. Use TLS and a reverse proxy with rate and
connection limits for public deployment. Install the pinned lockfiles.

Bootstrap schema and the initial admin with:

```text
python -m database.bootstrap --admin-user-id SUPABASE_AUTH_USER_UUID
```

Admin can then authorize principal/worker subjects via `/admin/invitations` or
the Workers screen. Country is an invitation assertion; no real KYC is implemented.
Bootstrap is initial infrastructure provisioning, not a normal task step.

## Database access

All application tables have RLS enabled with no direct-client policies. The API
is the only application data interface. Use a dedicated backend database role
with table access/RLS bypass restricted to these tables, never a browser key.
The initial local container uses its owner role for development. Do not reuse its
published password or localhost Compose settings on an exposed deployment.

Schema bootstrap is version 0.1 and uses SQLAlchemy create_all. It is idempotent
for initial creation but is not an incremental migration system. Before changing
a deployed schema, introduce a reviewed migration with backups and rollback plans.
The PostgreSQL initializer installs immutable triggers for audit, ledger and
earnings. Application paths do not expose SQL or arbitrary state mutation.

For Supabase's Data API, verify anon/authenticated cannot read any application
rows, and run Supabase advisors after bootstrap. Do not grant direct client access
to these tables. Review authenticated-role default grants for the target project.

## Workers and operations

Run the API, independent sweeper and web process. Keep clocks synchronized. Multiple
API processes/sweepers serialize writes using the same transaction advisory lock.
At the intended alpha scale this favors correctness over throughput; it is not a
high-volume marketplace design. Keep JWKS cache defaults bounded and plan key rotation.

The independent sweeper must be supervised and restarted on failure. Monitor error
logs, admin_review age, available credits and autonomous_completion_rate. Back up
PostgreSQL and test restoration. Audit output includes request and actor identifiers;
task content, API credentials and principal financial details are not logged.

## Remaining validation before admitting real users

1. Configure a real Supabase project; verify login, refresh, expiry and suspension
   with invited identities and confirm direct Data API isolation with advisors.
2. Set deployment-specific HTTPS URLs, CORS, secrets and infrastructure rate limits.
3. Evaluate basic safety filters against a representative abuse corpus. Current
   lexical rules are not sufficient to guarantee all prohibited intent is detected.
4. Exercise real public webpage and visual tasks with actual invited humans.
5. Run the 5-worker/3-agent, 100-task pilot and measure >80% autonomous completion.

## Documentation checked

- [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts)
- [Supabase changelog](https://supabase.com/changelog)
- [MCP server guide](https://modelcontextprotocol.io/docs/develop/build-server)
- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation)

Checked 2026-09-20; current package versions are pinned in requirements.lock and
apps/web/package-lock.json. No remote Supabase project was created or modified.
