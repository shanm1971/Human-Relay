import hashlib
import json
import logging
import secrets
from dataclasses import dataclass
import jwt
from sqlalchemy import select, func
from .models import *

class Problem(Exception):
    def __init__(self, code, message, status=400, category=None):
        self.code, self.message, self.status, self.category = code, message, status, category

def require(condition, code, message, status=400):
    if not condition: raise Problem(code, message, status)

def cents(value): return int(value * 100)
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def row(obj, exclude=()):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in exclude}
def count(s, model, *conditions): return s.scalar(select(func.count()).select_from(model).where(*conditions))

@dataclass
class Actor:
    role: str
    id: str
    organization_id: str | None = None

def audit(s, event_type, actor=None, task=None, request_id=None, **data):
    values = dict(event_type=event_type, event_data_json=data, request_id=request_id)
    if actor:
        values["organization_id"] = actor.organization_id
        if actor.role in ("agent", "worker"): values[actor.role+"_id"] = actor.id
    if task:
        values.update(task_id=task.id, organization_id=task.organization_id, agent_id=task.agent_id, worker_id=task.worker_id)
    s.add(Audit(**values))
    logging.getLogger("human_relay").info(json.dumps({k:v for k,v in values.items() if k != "event_data_json"}))

def authenticate(s, token, settings, request_id):
    require(bool(token), "UNAUTHENTICATED", "Bearer credential required.", 401)
    if token.startswith("hr_"):
        agent = s.scalar(select(Agent).where(Agent.api_key_hash == digest(token)))
        require(agent is not None and agent.status == "active", "UNAUTHENTICATED", "Invalid or revoked agent credential.", 401)
        org = s.get(Organization, agent.organization_id)
        require(org.status == "active", "SUSPENDED", "Organization suspended.", 403)
        agent.last_seen_at = now()
        actor = Actor("agent", agent.id, org.id)
        audit(s, "AGENT_AUTHENTICATED", actor, request_id=request_id)
        return actor
    if settings["dev_auth"] and token in settings["dev_tokens"]:
        user_id = settings["dev_tokens"][token]
    else:
        try:
            issuer = settings["supabase_url"].rstrip("/") + "/auth/v1"
            key = settings["jwks"].get_signing_key_from_jwt(token)
            claims = jwt.decode(token, key.key, algorithms=["ES256", "RS256"], audience="authenticated", issuer=issuer, options={"require": ["exp", "sub", "iss", "aud"]})
            user_id = claims["sub"]
        except Exception:
            raise Problem("UNAUTHENTICATED", "Invalid or expired login.", 401)
    identity = s.get(Identity, user_id)
    require(identity is not None and identity.status == "active", "NOT_INVITED", "Active closed-alpha invitation required.", 403)
    if identity.role == "worker":
        worker = s.scalar(select(Worker).where(Worker.user_id == user_id))
        require(worker is not None and worker.status == "active", "SUSPENDED", "Worker unavailable.", 403)
        return Actor("worker", worker.id)
    principal = s.scalar(select(Principal).where(Principal.user_id == user_id))
    return Actor(identity.role, user_id, principal.organization_id if principal else None)

def role(actor, *roles): require(actor.role in roles, "FORBIDDEN", "Actor cannot perform this operation.", 403)
def owned_org(s, actor):
    role(actor, "principal")
    org = s.get(Organization, actor.organization_id) if actor.organization_id else None
    require(org is not None and org.status == "active", "ORGANIZATION_REQUIRED", "Create an active organization first.", 409)
    return org

def create_org(s, actor, data):
    role(actor, "principal")
    require(actor.organization_id is None, "ORGANIZATION_EXISTS", "Principal already owns an organization.", 409)
    require(count(s, Organization) < 5, "ALPHA_CAPACITY", "Alpha organization limit reached.", 409)
    org = Organization(name=data.name)
    s.add(org); s.flush()
    s.add(Principal(organization_id=org.id, user_id=actor.id))
    actor.organization_id = org.id
    audit(s, "ORGANIZATION_CREATED", actor)
    return row(org)

def fund(s, actor, data, key):
    org = owned_org(s, actor)
    existing = s.scalar(select(CreditTransaction).where(CreditTransaction.dedupe_key == f"fund:{org.id}:{key}"))
    amount = cents(data.amount)
    if existing:
        require(existing.amount == amount, "IDEMPOTENCY_CONFLICT", "Key already used for another amount.", 409)
    else:
        org.credit_balance += amount
        s.add(CreditTransaction(organization_id=org.id, type="fund", amount=amount, dedupe_key=f"fund:{org.id}:{key}"))
        audit(s, "CREDITS_FUNDED", actor, amount_cents=amount)
    return row(org)

def save_agent(s, actor, data, agent_id=None):
    org = owned_org(s, actor)
    key = None
    if agent_id:
        agent = s.get(Agent, agent_id)
        require(agent is not None and agent.organization_id == org.id, "NOT_FOUND", "Agent not found.", 404)
    else:
        require(count(s, Agent) < 20, "ALPHA_CAPACITY", "Alpha agent limit reached.", 409)
        key = "hr_" + secrets.token_urlsafe(32)
        agent = Agent(organization_id=org.id, api_key_hash=digest(key))
        s.add(agent)
    for name, value in data.model_dump().items():
        if name == "allowed_capabilities": continue
        setattr(agent, name, cents(value) if name in ("max_task_price", "hourly_limit", "daily_limit", "monthly_limit") else value)
    s.flush()
    for old in s.scalars(select(AgentPermission).where(AgentPermission.agent_id == agent.id)): s.delete(old)
    s.flush()
    for capability in set(data.allowed_capabilities):
        s.add(AgentPermission(agent_id=agent.id, capability=capability, max_price=agent.max_task_price))
    audit(s, "AGENT_AUTHORITY_UPDATED", actor, agent_id_changed=agent.id)
    result = row(agent, ("api_key_hash",))
    result["allowed_capabilities"] = data.allowed_capabilities
    if key: result["api_key"] = key
    return result

def save_worker(s, actor, data):
    role(actor, "worker")
    worker = s.get(Worker, actor.id)
    worker.availability = data.availability
    worker.minimum_task_price = cents(data.minimum_task_price)
    worker.maximum_active_tasks = data.maximum_active_tasks
    for old in s.scalars(select(WorkerCapability).where(WorkerCapability.worker_id == worker.id)): s.delete(old)
    s.flush()
    for capability in set(data.capabilities):
        s.add(WorkerCapability(worker_id=worker.id, capability=capability, minimum_price=worker.minimum_task_price, enabled=capability not in data.blocked_categories))
    audit(s, "WORKER_CAPABILITIES_UPDATED", actor)
    return row(worker, ("user_id",))
