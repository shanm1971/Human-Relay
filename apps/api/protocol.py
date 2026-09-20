import json
from urllib.parse import urlparse
from jsonschema import Draft202012Validator
from sqlalchemy import select
from .core import *
from .policy import screen, check_schema, bounded_json

LIVE = ("active", "revision_requested", "awaiting_agent_review", "admin_review")
CHAT = ("active", "revision_requested", "awaiting_agent_review")

def capacity(s,w): return w.maximum_active_tasks-count(s,Task,Task.worker_id==w.id,Task.status.in_(LIVE))
def permission(s,a,cap):
    role(a,"agent")
    p=s.scalar(select(AgentPermission).where(AgentPermission.agent_id==a.id,AgentPermission.capability==cap,AgentPermission.allowed.is_(True)))
    require(p is not None,"CAPABILITY_NOT_AUTHORIZED","Capability not authorized by principal.",403)
    return p

def public_worker(s,w):
    offers=list(s.scalars(select(Offer).where(Offer.worker_id==w.id)))
    accepted=[o for o in offers if o.accepted_at]
    from statistics import median
    return {"worker_id":w.public_worker_id,"status":w.availability,"minimum_price":w.minimum_task_price/100,"quality_score":w.quality_score,
        "completion_rate":w.tasks_completed/max(1,w.tasks_completed+w.tasks_failed),
        "schema_compliance_rate":w.schema_valid/max(1,w.schema_attempts),
        "median_response_seconds":median([o.accepted_at-o.created_at for o in accepted]) if accepted else None,
        "current_capacity":max(0,capacity(s,w)),"maximum_active_tasks":w.maximum_active_tasks,
        "capabilities":[{"type":c.capability,"level":c.verification_level} for c in s.scalars(select(WorkerCapability).where(WorkerCapability.worker_id==w.id,WorkerCapability.enabled.is_(True)))]}

def search(s,a,data):
    permission(s,a,data.capability)
    matches=[]
    for w in s.scalars(select(Worker).where(Worker.status=="active",Worker.quality_score>=data.minimum_quality_score,Worker.minimum_task_price<=cents(data.max_price)).order_by(Worker.public_worker_id)):
        if data.available_now and w.availability!="available":continue
        if capacity(s,w)<=0:continue
        cap=s.scalar(select(WorkerCapability).where(WorkerCapability.worker_id==w.id,WorkerCapability.capability==data.capability,WorkerCapability.enabled.is_(True),WorkerCapability.minimum_price<=cents(data.max_price)))
        if cap: matches.append({**public_worker(s,w),"capability":data.capability})
    audit(s,"HUMAN_SEARCHED",a,capability=data.capability,matches=len(matches))
    return {"matches":matches[:data.limit]}

def view_offer(s,o):
    task=s.scalar(select(Task).where(Task.task_offer_id==o.id))
    return {"id":o.id,"task_offer_id":o.id,"task_id":task.id if task else None,"status":o.status,"agent_id":o.agent_id,"agent_name":s.get(Agent,o.agent_id).display_name,"actor_type":"AI agent",
        "capability":o.capability,"objective":o.objective,"instructions":o.instructions,"context":o.context_json,"response_schema":o.response_schema_json,"offered_price":o.offered_price/100,"deadline_at":o.deadline_at,"max_revisions":o.max_revisions}

def offer_for(s,a,offer_id):
    o=s.get(Offer,offer_id)
    require(o is not None and ((a.role=="agent" and o.agent_id==a.id) or (a.role=="worker" and o.worker_id==a.id)),"NOT_FOUND","Offer not found.",404)
    return o

def task_for(s,a,task_id):
    t=s.get(Task,task_id)
    require(t is not None and ((a.role=="agent" and t.agent_id==a.id) or (a.role=="worker" and t.worker_id==a.id) or a.role=="admin"),"NOT_FOUND","Task not found.",404)
    return t

def view_task(s,t):
    offer=view_offer(s,s.get(Offer,t.task_offer_id))
    return {**offer,"id":t.id,"task_id":t.id,"status":t.status,"revision_count":t.revision_count,"completed_at":t.completed_at,"failure_reason":t.failure_reason,"session_open":t.status in CHAT}

def create_offer(s,a,data,key):
    p=permission(s,a,data.capability)
    payload=data.model_dump(mode="json")
    hashed=digest(json.dumps(payload,sort_keys=True))
    existing=s.scalar(select(Offer).where(Offer.agent_id==a.id,Offer.idempotency_key==key))
    if existing:
        require(existing.payload_hash==hashed,"IDEMPOTENCY_CONFLICT","Key already used for another offer.",409)
        return view_offer(s,existing)
    bounded_json(data.context)
    check_schema(data.response_schema)
    try: screen(payload)
    except Problem as exc:
        audit(s,"SAFETY_REJECTION",a,category=exc.category)
        raise
    if data.capability=="visual_verification":
        images=data.context.get("images",[])
        require(isinstance(images,list) and 1<=len(images)<=5 and all(isinstance(u,str) and urlparse(u).scheme=="https" and urlparse(u).hostname and not urlparse(u).username for u in images),"IMAGES_REQUIRED","Supply 1–5 public HTTPS image URLs.",422)
    w=s.scalar(select(Worker).where(Worker.public_worker_id==data.worker_id,Worker.status=="active"))
    require(w is not None and w.availability=="available","WORKER_UNAVAILABLE","Worker is unavailable.",409)
    cap=s.scalar(select(WorkerCapability).where(WorkerCapability.worker_id==w.id,WorkerCapability.capability==data.capability,WorkerCapability.enabled.is_(True)))
    require(cap is not None and capacity(s,w)>0,"WORKER_UNAVAILABLE","Worker capability or capacity unavailable.",409)
    agent=s.get(Agent,a.id); price=cents(data.offered_price); org=s.get(Organization,a.organization_id)
    require(max(w.minimum_task_price,cap.minimum_price)<=price<=min(agent.max_task_price,p.max_price),"PRICE_NOT_AUTHORIZED","Price outside worker minimum or agent authority.",403)
    require(data.max_revisions<=agent.max_revision_requests,"REVISION_LIMIT","Revision limit exceeds authority.",403)
    pending=list(s.scalars(select(Offer).where(Offer.agent_id==a.id,Offer.status=="offered")))
    active=list(s.scalars(select(Task).where(Task.agent_id==a.id,Task.status.in_(LIVE))))
    require(len(pending)+len(active)<agent.max_concurrent_tasks,"CONCURRENCY_LIMIT","Agent concurrency limit reached.",409)
    require(count(s,Offer,Offer.agent_id==a.id,Offer.created_at>now()-60)<5,"OFFER_RATE_LIMIT","At most five offers per minute.",429)
    require(not any(o.worker_id==w.id and o.objective==data.objective for o in pending),"DUPLICATE_OFFER","An identical offer is pending.",409)
    require(count(s,Offer,Offer.worker_id==w.id,Offer.status=="offered")<5,"WORKER_OFFER_LIMIT","Worker pending offer limit reached.",429)
    reserved=sum(o.offered_price for o in pending)+sum(t.price for t in active)
    for seconds,limit in ((3600,agent.hourly_limit),(86400,agent.daily_limit),(2592000,agent.monthly_limit)):
        spent=sum(x.amount for x in s.scalars(select(CreditTransaction).where(CreditTransaction.agent_id==a.id,CreditTransaction.type=="settle",CreditTransaction.created_at>=now()-seconds)))
        require(reserved+spent+price<=limit,"SPENDING_LIMIT","Rolling spending limit reached.",403)
    require(org.credit_balance-org.reserved>=price,"INSUFFICIENT_CREDITS","Insufficient available simulated credits.",409)
    o=Offer(agent_id=a.id,worker_id=w.id,capability=data.capability,objective=data.objective,instructions=data.instructions,context_json=data.context,response_schema_json=data.response_schema,offered_price=price,deadline_at=now()+data.deadline_minutes*60,max_revisions=data.max_revisions,idempotency_key=key,payload_hash=hashed)
    s.add(o);s.flush();org.reserved+=price
    s.add(CreditTransaction(organization_id=org.id,agent_id=a.id,worker_id=w.id,offer_id=o.id,type="reserve",amount=price,dedupe_key=f"reserve:{o.id}"))
    audit(s,"TASK_OFFER_CREATED",a,offer_id=o.id)
    audit(s,"CREDITS_RESERVED",a,offer_id=o.id,amount_cents=price)
    return view_offer(s,o)

def release(s,o,t=None):
    agent=s.get(Agent,o.agent_id);org=s.get(Organization,agent.organization_id)
    org.reserved-=o.offered_price
    s.add(CreditTransaction(organization_id=org.id,agent_id=agent.id,worker_id=o.worker_id,offer_id=o.id,task_id=t.id if t else None,type="release",amount=o.offered_price,dedupe_key=f"release:{o.id}"))
    audit(s,"CREDITS_RELEASED",Actor("agent",agent.id,org.id),t,offer_id=o.id)

def close_offer(s,a,offer_id,status):
    role(a,"worker" if status=="declined" else "agent")
    o=offer_for(s,a,offer_id)
    if o.status==status:return view_offer(s,o)
    require(o.status=="offered","INVALID_STATE","Only pending offers can be declined or cancelled.",409)
    o.status=status
    if status=="declined":o.declined_at=now()
    release(s,o);audit(s,"TASK_OFFER_DECLINED" if status=="declined" else "TASK_CANCELLED",a,offer_id=o.id)
    return view_offer(s,o)

def accept_offer(s,a,offer_id):
    role(a,"worker");o=offer_for(s,a,offer_id)
    if o.status=="accepted":return view_task(s,s.scalar(select(Task).where(Task.task_offer_id==o.id)))
    require(o.status=="offered","INVALID_STATE","Offer is no longer pending.",409)
    worker=s.get(Worker,a.id);agent=s.get(Agent,o.agent_id);org=s.get(Organization,agent.organization_id)
    require(agent.status=="active" and org.status=="active","AGENT_UNAVAILABLE","Agent or organization inactive.",409)
    require(capacity(s,worker)>0 and worker.availability=="available","WORKER_CAPACITY","Worker has no available capacity.",409)
    cap=s.scalar(select(WorkerCapability).where(WorkerCapability.worker_id==worker.id,WorkerCapability.capability==o.capability,WorkerCapability.enabled.is_(True)))
    require(cap is not None and o.offered_price>=max(cap.minimum_price,worker.minimum_task_price),"WORKER_UNAVAILABLE","Worker preferences changed.",409)
    permission(s,Actor("agent",agent.id,org.id),o.capability)
    o.status="accepted";o.accepted_at=now()
    t=Task(task_offer_id=o.id,organization_id=org.id,agent_id=agent.id,worker_id=worker.id,capability=o.capability,price=o.offered_price)
    s.add(t);s.flush()
    audit(s,"TASK_OFFER_ACCEPTED",a,t);audit(s,"TASK_SESSION_OPENED",a,t)
    return view_task(s,t)

def message(s,a,task_id,data):
    role(a,"agent","worker");t=task_for(s,a,task_id)
    require(t.status in CHAT,"SESSION_CLOSED","Task session is closed.",409)
    bounded_json(data.content,4000)
    require(bool(data.content),"EMPTY_MESSAGE","Message cannot be empty.",422)
    try: screen(data.content)
    except Problem as exc:
        audit(s,"SAFETY_REJECTION",a,t,category=exc.category);raise
    limit=s.get(Agent,t.agent_id).max_session_messages if a.role=="agent" else 10
    require(count(s,Message,Message.task_id==t.id,Message.sender_type==a.role)<limit,"MESSAGE_LIMIT","Message limit reached.",429)
    m=Message(task_id=t.id,sender_type=a.role,sender_id=a.id,message_type=data.message_type,content_json=data.content)
    s.add(m);s.flush();audit(s,"AGENT_MESSAGE_SENT" if a.role=="agent" else "WORKER_MESSAGE_SENT",a,t)
    return row(m)

def submit(s,a,task_id,data):
    role(a,"worker");t=task_for(s,a,task_id)
    require(t.status in ("active","revision_requested"),"INVALID_STATE","Task is not accepting results.",409)
    bounded_json(data)
    o=s.get(Offer,t.task_offer_id);worker=s.get(Worker,a.id)
    errors=list(Draft202012Validator(o.response_schema_json).iter_errors(data))
    worker.schema_attempts+=1
    if errors:
        audit(s,"RESULT_SCHEMA_REJECTED",a,t)
        raise Problem("RESULT_SCHEMA_INVALID","; ".join(e.message[:200] for e in errors[:3]),422)
    worker.schema_valid+=1
    result=Result(task_id=t.id,worker_id=a.id,result_json=data,schema_valid=True)
    s.add(result);t.status="awaiting_agent_review";s.flush()
    audit(s,"RESULT_SUBMITTED",a,t)
    return {"status":t.status,"result_id":result.id,"schema_valid":True}

def latest_result(s,t):return s.scalar(select(Result).where(Result.task_id==t.id).order_by(Result.submitted_at.desc()))

def revision(s,a,task_id,data):
    role(a,"agent");t=task_for(s,a,task_id);o=s.get(Offer,t.task_offer_id)
    require(t.status=="awaiting_agent_review","INVALID_STATE","Task is not awaiting review.",409)
    require(t.revision_count<min(o.max_revisions,s.get(Agent,a.id).max_revision_requests),"REVISION_LIMIT","Revision limit reached.",409)
    screen(data.model_dump())
    result=latest_result(s,t);result.rejected_at=now()
    t.revision_count+=1;t.status="revision_requested"
    s.add(Message(task_id=t.id,sender_type="system",sender_id="system",message_type="system_event",content_json={"event":"revision_requested",**data.model_dump()}))
    audit(s,"REVISION_REQUESTED",a,t,reason=data.reason)
    return view_task(s,t)

def settle(s,a,t,admin=False):
    if t.status=="completed": return view_task(s,t)
    require(t.status==("admin_review" if admin else "awaiting_agent_review"),"INVALID_STATE","Task is not eligible for acceptance.",409)
    result=latest_result(s,t)
    require(result is not None and result.schema_valid,"RESULT_REQUIRED","Valid submitted result required.",409)
    org=s.get(Organization,t.organization_id);w=s.get(Worker,t.worker_id)
    org.reserved-=t.price;org.credit_balance-=t.price
    fee=(t.price*20+50)//100
    s.add(CreditTransaction(organization_id=org.id,agent_id=t.agent_id,worker_id=t.worker_id,task_id=t.id,offer_id=t.task_offer_id,type="settle",amount=t.price,dedupe_key=f"settle:{t.id}"))
    s.add(Earning(worker_id=w.id,task_id=t.id,gross_amount=t.price,platform_fee=fee,net_amount=t.price-fee))
    t.status="completed";t.completed_at=now();result.accepted_at=now();w.tasks_completed+=1
    w.quality_score=round((9+w.tasks_completed)/(10+w.tasks_completed+w.tasks_failed),4)
    audit(s,"RESULT_ACCEPTED",a,t);audit(s,"PAYMENT_RELEASED",a,t,gross_cents=t.price,fee_cents=fee)
    return view_task(s,t)

def fail(s,a,task_id,data):
    role(a,"agent");t=task_for(s,a,task_id)
    require(t.status=="awaiting_agent_review","INVALID_STATE","Only a submitted result can be disputed.",409)
    t.status="admin_review";t.intervention=True;t.failure_reason=data.reason
    audit(s,"TASK_FLAGGED_FOR_REVIEW",a,t,reason=data.reason)
    return view_task(s,t)

def report(s,a,task_id,data):
    role(a,"worker");t=task_for(s,a,task_id)
    require(t.status in LIVE,"INVALID_STATE","Report requires an unsettled task.",409)
    t.status="admin_review";t.intervention=True;t.failure_reason=data.reason
    audit(s,"WORKER_REPORTED_TASK",a,t,category=data.category,reason=data.reason)
    return view_task(s,t)

def expire(s):
    current=now()
    for o in s.scalars(select(Offer).where(Offer.status=="offered",Offer.deadline_at<=current)):
        o.status="expired";o.expired_at=current;release(s,o)
        audit(s,"TASK_EXPIRED",Actor("agent",o.agent_id,s.get(Agent,o.agent_id).organization_id),offer_id=o.id)
    for t in s.scalars(select(Task).where(Task.status.in_(CHAT))):
        o=s.get(Offer,t.task_offer_id)
        if min(o.deadline_at,t.session_opened_at+1800)>current:continue
        if t.status=="awaiting_agent_review":
            t.status="admin_review";t.intervention=True;t.failure_reason="Agent review deadline elapsed."
            audit(s,"REVIEW_TIMEOUT",task=t)
        else:
            t.status="expired";t.failed_at=current;t.failure_reason="Task deadline elapsed."
            w=s.get(Worker,t.worker_id);w.tasks_failed+=1
            w.quality_score=round((9+w.tasks_completed)/(10+w.tasks_completed+w.tasks_failed),4)
            release(s,o,t);audit(s,"TASK_EXPIRED",task=t)

def resolve(s,a,task_id,data):
    role(a,"admin");t=task_for(s,a,task_id)
    require(t.status=="admin_review","INVALID_STATE","Task is not in admin review.",409)
    if data.outcome=="completed":
        result=settle(s,a,t,True)
    else:
        t.status="failed";t.failed_at=now();t.failure_reason=data.reason
        w=s.get(Worker,t.worker_id);w.tasks_failed+=1
        w.quality_score=round((9+w.tasks_completed)/(10+w.tasks_completed+w.tasks_failed),4)
        release(s,s.get(Offer,t.task_offer_id),t);audit(s,"TASK_FAILED",a,t,reason=data.reason)
        result=view_task(s,t)
    audit(s,"ADMIN_RESOLVED",a,t,reason=data.reason)
    return result
