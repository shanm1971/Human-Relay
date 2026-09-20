from statistics import median
from fastapi import Request
from sqlalchemy import select
from .core import *
from .protocol import LIVE, view_task, public_worker, resolve

def metrics(s,org_id=None):
    tasks=list(s.scalars(select(Task).where(Task.organization_id==org_id))) if org_id else list(s.scalars(select(Task)))
    agent_ids=list(s.scalars(select(Agent.id).where(Agent.organization_id==org_id))) if org_id else list(s.scalars(select(Agent.id)))
    offers=list(s.scalars(select(Offer).where(Offer.agent_id.in_(agent_ids))))
    audits=list(s.scalars(select(Audit).where(Audit.organization_id==org_id))) if org_id else list(s.scalars(select(Audit)))
    done=[t for t in tasks if t.status=="completed"]
    terminal=[t for t in tasks if t.status in ("completed","failed","expired")]
    accepted=[o for o in offers if o.accepted_at]
    searches=sum(e.event_type=="HUMAN_SEARCHED" for e in audits)
    def rate(n,d):return round(n/d,4) if d else None
    def med(values):return round(median(values),2) if values else None
    return {"tasks_completed":len(done),"active_tasks":sum(t.status in LIVE for t in tasks),
        "autonomous_completion_rate":rate(sum(not t.intervention for t in done),len(done)),
        "task_success_rate":rate(len(done),len(terminal)),
        "offer_acceptance_rate":rate(len(accepted),len(offers)),
        "search_to_offer_ratio":rate(len(offers),searches),
        "median_offer_acceptance_seconds":med([o.accepted_at-o.created_at for o in accepted]),
        "median_completion_seconds":med([t.completed_at-t.created_at for t in done]),
        "median_messages_per_task":med([count(s,Message,Message.task_id==t.id,Message.sender_type!="system") for t in tasks]),
        "revision_rate":rate(sum(t.revision_count>0 for t in tasks),len(tasks)),
        "manual_admin_intervention_rate":rate(sum(t.intervention for t in tasks),len(tasks)),
        "cost_per_completed_task":sum(t.price for t in done)/100/len(done) if done else None,
        "agent_cancellation_rate":rate(sum(o.status=="cancelled" for o in offers),len(offers)),
        "worker_rejection_rate":rate(sum(o.status=="declined" for o in offers),len(offers))}

def agent_view(s,agent):
    data=row(agent,("api_key_hash",))
    data["allowed_capabilities"]=[p.capability for p in s.scalars(select(AgentPermission).where(AgentPermission.agent_id==agent.id,AgentPermission.allowed.is_(True)))]
    offers=list(s.scalars(select(Offer).where(Offer.agent_id==agent.id)))
    tasks=list(s.scalars(select(Task).where(Task.agent_id==agent.id)))
    n=len(offers);nt=len(tasks)
    data["reputation"]={"offer_acceptance_rate":sum(bool(o.accepted_at) for o in offers)/n if n else None,
        "task_completion_rate":sum(t.status=="completed" for t in tasks)/nt if nt else None,
        "worker_report_rate":count(s,Audit,Audit.agent_id==agent.id,Audit.event_type=="WORKER_REPORTED_TASK")/nt if nt else None,
        "task_cancellation_rate":sum(o.status=="cancelled" for o in offers)/n if n else None,
        "unsafe_task_attempts":count(s,Audit,Audit.agent_id==agent.id,Audit.event_type=="SAFETY_REJECTION"),
        "average_task_price":sum(o.offered_price for o in offers)/n/100 if n else None}
    return data

def register_dashboards(app):
    run=app.state.run
    @app.get("/api/v1/organization/dashboard")
    def principal_dashboard(request:Request):
        def action(s,a):
            org=owned_org(s,a)
            tx=list(s.scalars(select(CreditTransaction).where(CreditTransaction.organization_id==org.id,CreditTransaction.type=="settle")))
            return {"organization":row(org),"metrics":metrics(s,org.id),
                "daily_spending_cents":sum(t.amount for t in tx if t.created_at>=now()-86400),
                "monthly_spending_cents":sum(t.amount for t in tx if t.created_at>=now()-2592000),
                "agents":[agent_view(s,x) for x in s.scalars(select(Agent).where(Agent.organization_id==org.id))],
                "activity":[row(x) for x in s.scalars(select(Audit).where(Audit.organization_id==org.id).order_by(Audit.created_at.desc()).limit(100))],
                "tasks":[{"id":t.id,"status":t.status,"capability":t.capability,"price_cents":t.price,"agent_id":t.agent_id} for t in s.scalars(select(Task).where(Task.organization_id==org.id).order_by(Task.created_at.desc()).limit(100))]}
        return run(request,action)

    @app.get("/api/v1/worker/dashboard")
    def worker_dashboard(request:Request):
        def action(s,a):
            role(a,"worker");w=s.get(Worker,a.id)
            earnings=[row(e) for e in s.scalars(select(Earning).where(Earning.worker_id==w.id).order_by(Earning.created_at.desc()))]
            return {"profile":public_worker(s,w),"earnings":earnings,"total_earnings_cents":sum(e["net_amount"] for e in earnings),"pending_offers":count(s,Offer,Offer.worker_id==w.id,Offer.status=="offered")}
        return run(request,action)

    @app.get("/api/v1/admin/dashboard")
    def admin_dashboard(request:Request):
        def action(s,a):
            role(a,"admin")
            return {"metrics":metrics(s),"review_queue":[view_task(s,t) for t in s.scalars(select(Task).where(Task.status=="admin_review"))],
                "failed_tasks":[view_task(s,t) for t in s.scalars(select(Task).where(Task.status.in_(("failed","expired"))).limit(100))],
                "workers":[row(w,("user_id",)) for w in s.scalars(select(Worker))],
                "agents":[agent_view(s,a) for a in s.scalars(select(Agent))],
                "audit_events":[row(e) for e in s.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200))],
                "credit_ledger":[row(e) for e in s.scalars(select(CreditTransaction).order_by(CreditTransaction.created_at.desc()).limit(200))]}
        return run(request,action)

    @app.post("/api/v1/admin/{actor_type}/{actor_id}/suspend")
    def suspend(actor_type:str,actor_id:str,request:Request):
        def action(s,a):
            role(a,"admin");model={"workers":Worker,"agents":Agent,"organizations":Organization}.get(actor_type)
            require(model is not None,"NOT_FOUND","Actor type not found.",404)
            actor=s.get(model,actor_id);require(actor is not None,"NOT_FOUND","Actor not found.",404)
            actor.status="suspended";audit(s,"ACTOR_SUSPENDED",a,actor_type=actor_type,actor_id=actor_id)
            return {"status":"suspended"}
        return run(request,action)

    @app.post("/api/v1/admin/tasks/{task_id}/terminate")
    def terminate(task_id:str,request:Request):
        def action(s,a):
            role(a,"admin");t=s.get(Task,task_id)
            require(t is not None and t.status in LIVE,"INVALID_STATE","Live task required.",409)
            t.status="admin_review";t.intervention=True;t.failure_reason="Session terminated by administrator."
            audit(s,"ADMIN_SESSION_TERMINATED",a,t)
            return view_task(s,t)
        return run(request,action)
