import time
from types import SimpleNamespace
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from apps.api.core import authenticate,Problem
from apps.api.database import transaction

def test_supabase_signature_issuer_audience_and_local_role(client):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    class JWKS:
        def get_signing_key_from_jwt(self,token):return SimpleNamespace(key=key.public_key())
    settings={"dev_auth":False,"dev_tokens":{},"supabase_url":"https://alpha.supabase.co","jwks":JWKS()}
    claims={"sub":"w","iss":"https://alpha.supabase.co/auth/v1","aud":"authenticated","exp":int(time.time())+100,"user_metadata":{"role":"admin"}}
    with transaction(client.app.state.engine) as s:
        valid=jwt.encode(claims,key,algorithm="RS256")
        assert authenticate(s,valid,settings,"test").role=="worker"
        for bad in ({"aud":"wrong"},{"iss":"https://other.invalid/auth/v1"},{"exp":1},{"sub":"uninvited"}):
            token=jwt.encode({**claims,**bad},key,algorithm="RS256")
            try:authenticate(s,token,settings,"test")
            except Problem as e:assert e.status in (401,403)
            else:raise AssertionError("Invalid claims accepted")
        wrong=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        try:authenticate(s,jwt.encode(claims,wrong,algorithm="RS256"),settings,"test")
        except Problem as e:assert e.status==401
        else:raise AssertionError("Forged token accepted")
