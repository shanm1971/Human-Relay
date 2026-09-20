"""Bounded alpha policy and schema subset. No remote references or regex execution."""
import json
import re
import unicodedata
from jsonschema import Draft202012Validator, SchemaError
from .core import Problem, require

PROHIBITED = {
    "credential_access": r"password|credential|banking authentication|one.time (?:code|password)|\botp\b|login code|api[ _-]?key|access token",
    "identity_abuse": r"identity theft|impersonat|pretend to be",
    "illegal_activity": r"illegal activity|money launder|fraud|steal|stolen",
    "security_abuse": r"malware|ransomware|security bypass|bypass.{0,30}(?:security|captcha|authentication)|exploit vulnerability",
    "financial_transfer": r"financial transfer|wire transfer|transfer.{0,30}(?:money|funds|bitcoin)|send.{0,20}(?:money|bitcoin)",
    "weapons": r"weapons? procurement|buy.{0,20}(?:gun|weapon)|purchase.{0,20}(?:gun|weapon)",
    "controlled_substances": r"controlled substance|buy.{0,20}(?:cocaine|heroin|fentanyl)",
    "abuse": r"harass|stalk|doxx|sexual service|escort service",
    "high_stakes": r"medical diagnos|diagnose|legal representation|represent.{0,20}court|credit decision|employment decision|hiring decision|loan approval",
    "physical_danger": r"physical danger|physical task|visit.{0,20}(?:home|house)|break into",
    "off_platform": r"contact.{0,30}(?:telegram|whatsapp|email)|message me on|outside human relay",
}

def screen(payload):
    text = unicodedata.normalize("NFKC", json.dumps(payload,ensure_ascii=False)).lower()
    for category, pattern in PROHIBITED.items():
        if re.search(pattern,text):
            raise Problem("PROHIBITED_CAPABILITY_REQUEST",f"Human Relay does not support {category.replace('_',' ')} requests.",422,category)

ALLOWED_SCHEMA_KEYS = {"type","properties","required","additionalProperties","items","minItems","maxItems","minLength","maxLength","minimum","maximum","enum","description","title"}
def check_schema(schema):
    require(len(json.dumps(schema)) <= 12000,"SCHEMA_TOO_LARGE","Schema exceeds 12 KB.",422)
    require(schema.get("type") == "object","INVALID_SCHEMA","Result schema must have object type.",422)
    def walk(node,depth=0):
        require(depth <= 8 and isinstance(node,dict),"INVALID_SCHEMA","Schema depth or node invalid.",422)
        require(set(node) <= ALLOWED_SCHEMA_KEYS,"UNSUPPORTED_SCHEMA","Use the documented bounded JSON Schema subset; references, regex and composition are unsupported.",422)
        for sub in node.get("properties",{}).values(): walk(sub,depth+1)
        if "items" in node: walk(node["items"],depth+1)
        if isinstance(node.get("additionalProperties"),dict): walk(node["additionalProperties"],depth+1)
    try:
        Draft202012Validator.check_schema(schema)
        walk(schema)
    except (SchemaError,TypeError,AttributeError): raise Problem("INVALID_SCHEMA","Invalid JSON Schema.",422)

def bounded_json(value, limit=16000):
    try: text=json.dumps(value,allow_nan=False)
    except (ValueError,TypeError): raise Problem("INVALID_JSON","Only finite JSON values are supported.",422)
    require(len(text.encode())<=limit,"PAYLOAD_TOO_LARGE",f"Payload exceeds {limit} bytes.",413)
    def depth(v,d=0):
        require(d<=12,"INVALID_JSON","JSON nesting exceeds 12 levels.",422)
        if isinstance(v,dict):
            for child in v.values(): depth(child,d+1)
        if isinstance(v,list):
            for child in v: depth(child,d+1)
    depth(value)
