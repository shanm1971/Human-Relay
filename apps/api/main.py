import json
import os
import secrets
import logging
from contextlib import asynccontextmanager
import jwt
from fastapi import FastAPI, Request, Body, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from .database import make_engine, initialize, transaction
from .core import *
from .schemas import *

def create_app(database_url=None, dev_auth=None, dev_tokens=None, bootstrap=True):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./relay.db")
    development = dev_auth if dev_auth is not None else os.getenv("DEV_AUTH", "false").lower() == "true"
    if not development and not url.startswith("postgresql"):
        raise RuntimeError("Production requires PostgreSQL. Set DEV_AUTH=true only for local development.")
    engine = make_engine(url)
    if bootstrap: initialize(engine)
    supabase_url = os.getenv("SUPABASE_URL", "")
    settings = {"dev_auth": development, "dev_tokens": dev_tokens or json.loads(os.getenv("DEV_TOKENS_JSON", "{}")), "supabase_url": supabase_url,
                "jwks": jwt.PyJWKClient(supabase_url.rstrip("/")+"/auth/v1/.well-known/jwks.json") if supabase_url else None}
    app = FastAPI(title="Human Relay", version="0.1.0", description="Closed-alpha human capability protocol. Fake credits only.")
    app.state.engine = engine
    app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")], allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = secrets.token_hex(12)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return JSONResponse(status_code=exc.status, content={"status":"rejected", "error":{"code":exc.code, "message":exc.message, "category":exc.category}, "request_id":request.state.request_id})

    def run(request, operation):
        with transaction(engine) as s:
            actor = authenticate(s, request.headers.get("authorization", "").removeprefix("Bearer "), settings, request.state.request_id)
            # Expected rejections are committed so authentication, safety and schema attempts remain auditable.
            try:
                result = operation(s, actor)
            except Problem as exc:
                audit(s, "REQUEST_REJECTED", actor, request_id=request.state.request_id, code=exc.code)
                result = exc
        if isinstance(result, Problem): raise result
        return result

    def idem(request):
        key = request.headers.get("idempotency-key", "")
        require(1 <= len(key) <= 128, "IDEMPOTENCY_KEY_REQUIRED", "Supply an Idempotency-Key header (1–128 characters).")
        return key

    @app.get("/health")
    def health(): return {"status":"ok", "payments":"simulated", "development_auth":development}

    @app.get("/api/v1/me")
    def me(request: Request): return run(request, lambda s,a: {"role":a.role, "id":a.id, "organization_id":a.organization_id})

    @app.post("/api/v1/organizations")
    def org(request: Request, data: OrganizationInput): return run(request, lambda s,a:create_org(s,a,data))

    @app.post("/api/v1/organization/credits")
    def credits(request: Request, data: CreditInput): return run(request, lambda s,a:fund(s,a,data,idem(request)))

    @app.post("/api/v1/agents")
    def agent(request: Request, data: AgentInput): return run(request, lambda s,a:save_agent(s,a,data))

    @app.put("/api/v1/agents/{agent_id}/authority")
    def authority(agent_id: str, request: Request, data: AgentInput): return run(request, lambda s,a:save_agent(s,a,data,agent_id))

    @app.post("/api/v1/agents/{agent_id}/revoke")
    def revoke(agent_id: str, request: Request):
        def action(s,a):
            org = owned_org(s,a); agent = s.get(Agent,agent_id)
            require(agent is not None and agent.organization_id == org.id, "NOT_FOUND", "Agent not found.",404)
            agent.status = "revoked"; audit(s,"AGENT_REVOKED",a,revoked_agent_id=agent.id)
            return {"status":"revoked"}
        return run(request,action)

    @app.put("/api/v1/worker/profile")
    def profile(request: Request, data: WorkerInput): return run(request,lambda s,a:save_worker(s,a,data))

    @app.post("/api/v1/admin/invitations")
    def invite(request: Request, data: InviteInput):
        def action(s,a):
            role(a,"admin")
            require(s.get(Identity,data.user_id) is None,"ALREADY_INVITED","User already invited.",409)
            if data.role == "worker": require(count(s,Worker)<20,"ALPHA_CAPACITY","Alpha worker limit reached.",409)
            s.add(Identity(id=data.user_id,role=data.role,country=data.country)); s.flush()
            if data.role == "worker": s.add(Worker(user_id=data.user_id))
            audit(s,"IDENTITY_INVITED",a,invited_role=data.role)
            return {"status":"invited"}
        return run(request,action)

    app.state.run = run
    app.state.idem = idem
    return app
