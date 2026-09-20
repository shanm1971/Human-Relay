"""An agent using the exact MCP tool implementation; the worker uses the web UI."""
import argparse
import time
import uuid
from .server import search_humans,hire_human,get_human_task,message_human,get_human_result,accept_human_result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--url",required=True);args=parser.parse_args()
    print("Searching human capabilities...",flush=True)
    matches=search_humans("web_research")["matches"]
    if not matches:raise SystemExit("No eligible workers available. Enable availability in the worker dashboard.")
    worker=sorted(matches,key=lambda w:(-w["quality_score"],w["minimum_price"]))[0]
    print(f'Selected {worker["worker_id"]}: quality {worker["quality_score"]}, minimum ${worker["minimum_price"]:.2f}',flush=True)
    offer=hire_human(worker["worker_id"],"web_research","Verify current Pro plan pricing","Inspect the public page. Report monthly and annual prices and a source URL.",{"url":args.url},{"type":"object","properties":{"monthly_price":{"type":"number","minimum":0},"annual_price":{"type":"number","minimum":0},"source_url":{"type":"string"}},"required":["monthly_price","annual_price","source_url"]},max(4,worker["minimum_price"]),10,str(uuid.uuid4()))
    print("Task offer sent. Waiting for a human worker...",flush=True)
    while time.time()<offer["deadline_at"]:
        current=get_human_task(task_offer_id=offer["id"])
        if current["status"]=="accepted":break
        if current["status"] in ("cancelled","declined","expired"):raise SystemExit(current["status"])
        time.sleep(2)
    else:raise SystemExit("Offer deadline elapsed.")
    tid=current["task_id"];print("Worker accepted. Human session opened.",flush=True)
    message_human(tid,"Please verify both monthly billing and annual billing, and include the source URL.")
    while time.time()<offer["deadline_at"]:
        result=get_human_result(tid)
        if result["status"]=="awaiting_agent_review" and result["schema_valid"]:
            value=result["result"]
            if value["monthly_price"]>=0 and value["annual_price"]>=0 and value["source_url"].startswith("https://"):
                print("Human response received. Result valid.",flush=True)
                accept_human_result(tid)
                print("Payment released. Agent workflow resumed.",flush=True);return
            raise SystemExit("Result failed demo business validation. Review or dispute via API.")
        if result["status"] not in ("active","revision_requested","awaiting_agent_review"):raise SystemExit(result["status"])
        time.sleep(2)
    raise SystemExit("Task deadline elapsed.")

if __name__=="__main__":main()
