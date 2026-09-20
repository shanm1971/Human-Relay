from fastapi import Request, Body
from sqlalchemy import select
from .core import *
from .schemas import *
from .protocol import *

def register(app):
    run=app.state.run
    @app.post("/api/v1/humans/search")
    def search_humans(request:Request,data:SearchInput):return run(request,lambda s,a:search(s,a,data))

    @app.get("/api/v1/humans/{worker_id}/capabilities")
    def human(worker_id:str,request:Request):
        def action(s,a):
            role(a,"agent")
            w=s.scalar(select(Worker).where(Worker.public_worker_id==worker_id,Worker.status=="active"))
            require(w is not None,"NOT_FOUND","Worker not found.",404)
            return public_worker(s,w)
        return run(request,action)

    @app.post("/api/v1/task-offers")
    def offer(request:Request,data:OfferInput):return run(request,lambda s,a:create_offer(s,a,data,app.state.idem(request)))

    @app.get("/api/v1/task-offers/{offer_id}")
    def get_offer(offer_id:str,request:Request):return run(request,lambda s,a:view_offer(s,offer_for(s,a,offer_id)))

    @app.post("/api/v1/task-offers/{offer_id}/cancel")
    def cancel(offer_id:str,request:Request):return run(request,lambda s,a:close_offer(s,a,offer_id,"cancelled"))

    @app.get("/api/v1/worker/offers")
    def offers(request:Request):
        def action(s,a):
            role(a,"worker")
            return {"offers":[view_offer(s,o) for o in s.scalars(select(Offer).where(Offer.worker_id==a.id,Offer.status=="offered").order_by(Offer.created_at.desc()))]}
        return run(request,action)

    @app.post("/api/v1/worker/offers/{offer_id}/accept")
    def worker_accept(offer_id:str,request:Request):return run(request,lambda s,a:accept_offer(s,a,offer_id))

    @app.post("/api/v1/worker/offers/{offer_id}/decline")
    def decline(offer_id:str,request:Request):return run(request,lambda s,a:close_offer(s,a,offer_id,"declined"))

    @app.get("/api/v1/worker/tasks")
    def tasks(request:Request):
        def action(s,a):
            role(a,"worker")
            return {"tasks":[view_task(s,t) for t in s.scalars(select(Task).where(Task.worker_id==a.id).order_by(Task.created_at.desc()).limit(100))]}
        return run(request,action)

    @app.get("/api/v1/tasks/{task_id}")
    @app.get("/api/v1/worker/tasks/{task_id}")
    def get_task(task_id:str,request:Request):return run(request,lambda s,a:view_task(s,task_for(s,a,task_id)))

    @app.get("/api/v1/tasks/{task_id}/messages")
    @app.get("/api/v1/worker/tasks/{task_id}/messages")
    def messages(task_id:str,request:Request):
        def action(s,a):
            t=task_for(s,a,task_id)
            return {"messages":[row(m) for m in s.scalars(select(Message).where(Message.task_id==t.id).order_by(Message.created_at))]}
        return run(request,action)

    @app.post("/api/v1/tasks/{task_id}/messages")
    @app.post("/api/v1/worker/tasks/{task_id}/messages")
    def send(task_id:str,request:Request,data:MessageInput):return run(request,lambda s,a:message(s,a,task_id,data))

    @app.post("/api/v1/tasks/{task_id}/result")
    @app.post("/api/v1/worker/tasks/{task_id}/result")
    def result(task_id:str,request:Request,data:dict=Body(...)):return run(request,lambda s,a:submit(s,a,task_id,data))

    @app.get("/api/v1/tasks/{task_id}/result")
    def get_result(task_id:str,request:Request):
        def action(s,a):
            t=task_for(s,a,task_id);r=latest_result(s,t)
            return {"status":t.status,"result":r.result_json if r else None,"schema_valid":r.schema_valid if r else None}
        return run(request,action)

    @app.post("/api/v1/tasks/{task_id}/revision")
    def revise(task_id:str,request:Request,data:RevisionInput):return run(request,lambda s,a:revision(s,a,task_id,data))

    @app.post("/api/v1/tasks/{task_id}/accept")
    def accept(task_id:str,request:Request):
        def action(s,a):
            role(a,"agent");return settle(s,a,task_for(s,a,task_id))
        return run(request,action)

    @app.post("/api/v1/tasks/{task_id}/fail")
    def failed(task_id:str,request:Request,data:RevisionInput):return run(request,lambda s,a:fail(s,a,task_id,data))

    @app.post("/api/v1/worker/tasks/{task_id}/report")
    def reported(task_id:str,request:Request,data:ReportInput):return run(request,lambda s,a:report(s,a,task_id,data))

    @app.post("/api/v1/admin/tasks/{task_id}/resolve")
    def resolved(task_id:str,request:Request,data:ResolveInput):return run(request,lambda s,a:resolve(s,a,task_id,data))
