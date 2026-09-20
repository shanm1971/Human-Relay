from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Capability = Literal["web_research", "visual_verification", "content_judgment"]
class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

class OrganizationInput(Input):
    name: str = Field(min_length=1, max_length=100)

class CreditInput(Input):
    amount: Decimal = Field(gt=0, le=10000, decimal_places=2)

class AgentInput(Input):
    display_name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    allowed_capabilities: list[Capability] = Field(min_length=1, max_length=3)
    max_task_price: Decimal = Field(default=Decimal("10"), ge=1, le=20, decimal_places=2)
    hourly_limit: Decimal = Field(default=Decimal("20"), ge=1, le=10000, decimal_places=2)
    daily_limit: Decimal = Field(default=Decimal("40"), ge=1, le=10000, decimal_places=2)
    monthly_limit: Decimal = Field(default=Decimal("300"), ge=1, le=10000, decimal_places=2)
    max_concurrent_tasks: int = Field(default=3, ge=1, le=20)
    max_session_messages: int = Field(default=10, ge=1, le=10)
    max_revision_requests: int = Field(default=1, ge=0, le=1)

class WorkerInput(Input):
    capabilities: list[Capability] = Field(min_length=1, max_length=3)
    blocked_categories: list[Capability] = Field(default_factory=list, max_length=3)
    availability: Literal["available", "busy", "offline"] = "available"
    minimum_task_price: Decimal = Field(default=Decimal("3"), ge=1, le=20, decimal_places=2)
    maximum_active_tasks: int = Field(default=2, ge=1, le=5)

class SearchInput(Input):
    capability: Capability
    available_now: bool = True
    max_price: Decimal = Field(default=Decimal("20"), ge=1, le=20, decimal_places=2)
    minimum_quality_score: float = Field(default=0, ge=0, le=1)
    limit: int = Field(default=5, ge=1, le=20)

class OfferInput(Input):
    worker_id: str = Field(min_length=1, max_length=80)
    capability: Capability
    objective: str = Field(min_length=3, max_length=500)
    instructions: str = Field(min_length=3, max_length=5000)
    context: dict = Field(default_factory=dict)
    response_schema: dict
    offered_price: Decimal = Field(ge=1, le=20, decimal_places=2)
    deadline_minutes: int = Field(default=10, ge=1, lt=20)
    max_revisions: int = Field(default=1, ge=0, le=1)

class MessageInput(Input):
    message_type: Literal["text", "structured_question", "structured_answer"] = "text"
    content: str | dict

class RevisionInput(Input):
    reason: str = Field(min_length=3, max_length=1000)
    requested_fields: list[str] = Field(default_factory=list, max_length=30)

class ReportInput(Input):
    category: Literal["unsafe_task", "misleading_task", "missing_information", "abusive_agent", "scope_changed", "prohibited_content"]
    reason: str = Field(min_length=3, max_length=1000)

class ResolveInput(Input):
    outcome: Literal["completed", "failed"]
    reason: str = Field(min_length=3, max_length=1000)

class InviteInput(Input):
    user_id: str = Field(min_length=1, max_length=100)
    role: Literal["principal", "worker"]
    country: Literal["US"]
