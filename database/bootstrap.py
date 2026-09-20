"""Bootstrap schema and first admin, or explicit local demo identities. Never runs implicitly."""
import argparse
import json
import os
import secrets
from pathlib import Path
from apps.api.database import make_engine,initialize,transaction
from apps.api.models import Identity,Worker

def main():
    p=argparse.ArgumentParser();p.add_argument("--admin-user-id");p.add_argument("--demo",action="store_true");args=p.parse_args()
    if args.demo and os.getenv("DEV_AUTH","").lower()!="true":raise SystemExit("Demo bootstrap requires DEV_AUTH=true.")
    engine=make_engine(os.environ["DATABASE_URL"]);initialize(engine)
    tokens={}
    with transaction(engine) as s:
        if args.admin_user_id:
            if not s.get(Identity,args.admin_user_id):s.add(Identity(id=args.admin_user_id,role="admin"))
        elif args.demo:
            for role in ("principal","worker","admin"):
                user_id="demo-"+role
                if not s.get(Identity,user_id):
                    s.add(Identity(id=user_id,role=role));s.flush()
                    if role=="worker":s.add(Worker(user_id=user_id))
                tokens[secrets.token_urlsafe(24)]=user_id
        else:raise SystemExit("Choose --admin-user-id (Supabase subject) or --demo.")
    if tokens:
        Path("demo-credentials.json").write_text(json.dumps(tokens,indent=2))
        print("Local credentials written to demo-credentials.json (gitignored). Set DEV_TOKENS_JSON to this file's compact JSON before starting the API.")
    else:print("Schema and initial admin ready. Invite other identities through the admin API.")

if __name__=="__main__":main()
