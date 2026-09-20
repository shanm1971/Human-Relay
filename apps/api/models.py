"""Persistence model. Monetary values are integer cents, timestamps are UTC epoch seconds."""
import time
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()
def uid(): return uuid.uuid4().hex
def now(): return time.time()

class Identity(Base):
    __tablename__ = "identities"
    id = Column(String, primary_key=True)
    role = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    country = Column(String, default="US", nullable=False)
    __table_args__ = (CheckConstraint("role in ('principal','worker','admin')"), CheckConstraint("country = 'US'"))

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    credit_balance = Column(Integer, default=0, nullable=False)
    reserved = Column(Integer, default=0, nullable=False)
    created_at = Column(Float, default=now, nullable=False)
    updated_at = Column(Float, default=now, onupdate=now)
    __table_args__ = (CheckConstraint("credit_balance >= 0 AND reserved >= 0 AND reserved <= credit_balance"),)

class Principal(Base):
    __tablename__ = "principals"
    id = Column(String, primary_key=True, default=uid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("identities.id"), unique=True, nullable=False)
    role = Column(String, default="owner")
    created_at = Column(Float, default=now)

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=uid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String, default="")
    status = Column(String, default="active", nullable=False)
    api_key_hash = Column(String, unique=True, nullable=False)
    max_task_price = Column(Integer, default=1000, nullable=False)
    hourly_limit = Column(Integer, default=2000, nullable=False)
    daily_limit = Column(Integer, default=4000, nullable=False)
    monthly_limit = Column(Integer, default=30000, nullable=False)
    max_concurrent_tasks = Column(Integer, default=3, nullable=False)
    max_session_messages = Column(Integer, default=10, nullable=False)
    max_revision_requests = Column(Integer, default=1, nullable=False)
    created_at = Column(Float, default=now, nullable=False)
    updated_at = Column(Float, default=now, onupdate=now)
    last_seen_at = Column(Float)

class AgentPermission(Base):
    __tablename__ = "agent_permissions"
    id = Column(String, primary_key=True, default=uid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    capability = Column(String, nullable=False)
    allowed = Column(Boolean, default=True, nullable=False)
    max_price = Column(Integer, nullable=False)
    created_at = Column(Float, default=now)
    __table_args__ = (UniqueConstraint("agent_id", "capability"),)

class Worker(Base):
    __tablename__ = "workers"
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("identities.id"), unique=True, nullable=False)
    public_worker_id = Column(String, unique=True, default=lambda: "worker_"+uid()[:12])
    status = Column(String, default="active", nullable=False)
    availability = Column(String, default="offline", nullable=False)
    minimum_task_price = Column(Integer, default=300, nullable=False)
    maximum_active_tasks = Column(Integer, default=2, nullable=False)
    quality_score = Column(Float, default=0.9, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    tasks_failed = Column(Integer, default=0, nullable=False)
    schema_attempts = Column(Integer, default=0, nullable=False)
    schema_valid = Column(Integer, default=0, nullable=False)
    created_at = Column(Float, default=now)
    updated_at = Column(Float, default=now, onupdate=now)

class WorkerCapability(Base):
    __tablename__ = "worker_capabilities"
    id = Column(String, primary_key=True, default=uid)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    capability = Column(String, nullable=False)
    verification_level = Column(String, default="self_declared")
    minimum_price = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(Float, default=now)
    __table_args__ = (UniqueConstraint("worker_id", "capability"),)

class Offer(Base):
    __tablename__ = "task_offers"
    id = Column(String, primary_key=True, default=uid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False, index=True)
    capability = Column(String, nullable=False)
    objective = Column(String, nullable=False)
    instructions = Column(String, nullable=False)
    context_json = Column(JSON, nullable=False)
    response_schema_json = Column(JSON, nullable=False)
    offered_price = Column(Integer, nullable=False)
    deadline_at = Column(Float, nullable=False, index=True)
    max_revisions = Column(Integer, nullable=False)
    status = Column(String, default="offered", nullable=False)
    idempotency_key = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    created_at = Column(Float, default=now, nullable=False)
    accepted_at = Column(Float)
    declined_at = Column(Float)
    expired_at = Column(Float)
    __table_args__ = (UniqueConstraint("agent_id", "idempotency_key"), CheckConstraint("offered_price between 100 and 2000"))

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=uid)
    task_offer_id = Column(String, ForeignKey("task_offers.id"), unique=True, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    capability = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    price = Column(Integer, nullable=False)
    revision_count = Column(Integer, default=0, nullable=False)
    intervention = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String)
    session_opened_at = Column(Float, default=now, nullable=False)
    completed_at = Column(Float)
    failed_at = Column(Float)
    created_at = Column(Float, default=now, nullable=False)
    updated_at = Column(Float, default=now, onupdate=now)

class Message(Base):
    __tablename__ = "task_messages"
    id = Column(String, primary_key=True, default=uid)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    sender_type = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    message_type = Column(String, nullable=False)
    content_json = Column(JSON, nullable=False)
    created_at = Column(Float, default=now, nullable=False)

class Result(Base):
    __tablename__ = "task_results"
    id = Column(String, primary_key=True, default=uid)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    result_json = Column(JSON, nullable=False)
    schema_valid = Column(Boolean, nullable=False)
    submitted_at = Column(Float, default=now, nullable=False)
    accepted_at = Column(Float)
    rejected_at = Column(Float)

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id = Column(String, primary_key=True, default=uid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"))
    worker_id = Column(String, ForeignKey("workers.id"))
    task_id = Column(String, ForeignKey("tasks.id"))
    offer_id = Column(String, ForeignKey("task_offers.id"))
    type = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="posted", nullable=False)
    dedupe_key = Column(String, unique=True, nullable=False)
    created_at = Column(Float, default=now, nullable=False)

class Earning(Base):
    __tablename__ = "worker_earnings"
    id = Column(String, primary_key=True, default=uid)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), unique=True, nullable=False)
    gross_amount = Column(Integer, nullable=False)
    platform_fee = Column(Integer, nullable=False)
    net_amount = Column(Integer, nullable=False)
    status = Column(String, default="simulated", nullable=False)
    created_at = Column(Float, default=now)

class Audit(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=uid)
    organization_id = Column(String)
    agent_id = Column(String)
    worker_id = Column(String)
    task_id = Column(String)
    request_id = Column(String)
    event_type = Column(String, nullable=False)
    event_data_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(Float, default=now, nullable=False)
