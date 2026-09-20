# Human Relay

The human capability layer for autonomous agents. A runnable, machine-first
closed-alpha implementation with simulated USD accounting. No real payments.

## What is built

- FastAPI + SQLAlchemy + PostgreSQL: invitation-based identities, organizations,
  hashed agent credentials, advance spending authority, pseudonymous capability
  discovery, direct offers, atomic acceptance, private sessions, schema-validated
  results, one revision, idempotent settlement, expiry, reports and admin resolution.
- Next.js + TypeScript + Tailwind: worker, principal, admin and agent-demo screens.
- Official Python MCP SDK: all ten requested tools over stdio.
- Append-only audit/ledger/earnings, integer-cent accounting, worker and agent
  metrics, rolling spending limits, bounded schemas and basic policy screening.
- Docker Compose, OpenAPI contract, bootstrap command, automated tests and runbook.

Read [architecture](docs/architecture.md), [protocol decisions](docs/protocol.md),
[verification](docs/verification.md) and [deployment](docs/deployment.md).

## Run locally (PowerShell)

Use Python 3.14, Node 22+, Docker Desktop and an unused port. From this directory:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
docker compose up -d db
$env:DATABASE_URL='postgresql+psycopg://relay:local-development-only@127.0.0.1:55432/relay?connect_timeout=5'
$env:DEV_AUTH='true'
.venv/Scripts/python -m database.bootstrap --demo
$env:DEV_TOKENS_JSON=Get-Content demo-credentials.json -Raw
$env:WEB_ORIGIN='http://127.0.0.1:3217'
.venv/Scripts/python -m uvicorn apps.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

In a second terminal, start the independent timeout worker using the same database:

```powershell
$env:DATABASE_URL='postgresql+psycopg://relay:local-development-only@127.0.0.1:55432/relay?connect_timeout=5'
.venv/Scripts/python -m apps.api.sweeper
```

In a third terminal:

```powershell
cd apps/web
npm ci
npm run build
npm run start -- --port 3217 --hostname 127.0.0.1
```

Open http://127.0.0.1:3217. API docs: http://127.0.0.1:8000/docs.
`demo-credentials.json` maps each local token to its role. Paste a token into
the developer sign-in field. The file is gitignored. Re-running demo bootstrap
rotates those local tokens; restart the API to activate the new token mapping.
Development authentication is disabled by default and must never be exposed publicly.

The default frontend API address is `http://127.0.0.1:8000`. To change it, set
`NEXT_PUBLIC_API_URL` in `apps/web/.env.local` and rebuild. CORS must match the
exact browser origin in `WEB_ORIGIN`. A service on port 3000 was already present
in the build environment, so this runbook uses 3217.

## Interactive definition-of-done demo

1. Sign in as the demo principal. Create an organization and add $500 fake credits.
2. Open Agents. Create an agent allowing web research with a $10 per-task limit.
   Save the one-time key, then choose **Use in agent demo**.
3. In another tab, sign in with the worker token. Open Capabilities, enable web
   research, choose available, set $3 minimum, and save.
4. In the agent console, supply a real public pricing URL and run the workflow.
5. The worker accepts the direct offer, reads the task, exchanges a task message,
   researches the supplied public page, then fills the structured result form.
6. The console checks the result shape and basic business conditions, accepts it,
   releases fake payment and resumes. The worker sees $3.20 earnings on a $4 task.

The principal does not approve or manage the task after agent authorization.
The showcase uses deterministic agent code, not an LLM or automatic AI matching.
Its result validation checks schema, nonnegative prices and an HTTPS source; it
does not independently establish the truth of a worker's research.

## MCP

Configure one process per authorized agent:

```json
{
  "mcpServers": {
    "human-relay": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "apps.mcp.server"],
      "cwd": "/absolute/path/to/human-relay",
      "env": {
        "HUMAN_RELAY_URL": "http://127.0.0.1:8000",
        "HUMAN_RELAY_AGENT_KEY": "YOUR_ONE_TIME_AGENT_KEY"
      }
    }
  }
}
```

Tools: `search_humans`, `get_human_capabilities`, `hire_human`, `get_human_task`,
`message_human`, `get_human_messages`, `get_human_result`,
`request_human_revision`, `accept_human_result`, `cancel_human_task`.

`hire_human` requires a stable `idempotency_key`. Poll `get_human_task` with
`task_offer_id` until it returns a `task_id`, then use the task ID. Cancellation
accepts an offer ID and applies only before worker acceptance. MCP stdio is local;
no unauthenticated network MCP listener is created.

CLI showcase:

```powershell
$env:HUMAN_RELAY_AGENT_KEY='YOUR_AGENT_KEY'
$env:HUMAN_RELAY_URL='http://127.0.0.1:8000'
.venv/Scripts/python -m apps.mcp.demo_agent --url https://YOUR_PUBLIC_PRICING_PAGE
```

## Tests

```powershell
.venv/Scripts/python -m pytest -q
$env:TEST_DATABASE_URL='postgresql+psycopg://relay:local-development-only@127.0.0.1:55432/relay?connect_timeout=5'
.venv/Scripts/python -m pytest -q
```

PostgreSQL tests create and drop uniquely named test schemas only. The database
user needs schema-creation permission. Tests never reuse the live application's
tables. Unset `TEST_DATABASE_URL` to return to per-test SQLite databases.

## Deployment status

This is a locally verified alpha implementation, not an already hosted service.
Supabase JWT verification and browser login are implemented; connecting a hosted
Supabase project, provisioning real invitations, verifying live JWT refresh and
running an actual 5-worker/3-agent pilot remain deployment work. Basic lexical
safety screening is intentionally limited; see the deployment runbook.

The target of 100 completed tasks and >80% autonomous completion requires a real
alpha study. Synthetic test completion does not establish that product outcome.
