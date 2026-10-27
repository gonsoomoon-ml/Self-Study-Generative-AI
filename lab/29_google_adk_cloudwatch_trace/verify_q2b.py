"""Q2(b) follow-up check: print RAW content attributes per span for a session, plus log events
in the agent log group (content-extraction path). Separate from verify.py on purpose."""
import argparse, json, sys, time
import boto3

ap = argparse.ArgumentParser()
ap.add_argument("--session-id", required=True)
ap.add_argument("--region", default="us-west-2")
ap.add_argument("--hours", type=float, default=3)
ap.add_argument("--log-group", default="/aws/bedrock-agentcore/runtimes/knox-adk-trace-test")
a = ap.parse_args()
logs = boto3.client("logs", region_name=a.region)
end = int(time.time()); start = end - int(a.hours * 3600)

def q(group, qs):
    qid = logs.start_query(logGroupName=group, startTime=start, endTime=end, queryString=qs, limit=200)["queryId"]
    while True:
        r = logs.get_query_results(queryId=qid)
        if r["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            return [{f["field"]: f["value"] for f in row} for row in r["results"]]
        time.sleep(2)

# 1) trace ids for the session, then all spans of those traces
rows = q("aws/spans", f'filter @message like "{a.session_id}" | stats count() by traceId')
tids = [r["traceId"] for r in rows if r.get("traceId")]
print(f"session={a.session_id} traces={len(tids)}")
if not tids:
    sys.exit(0)
tid_filter = " or ".join(f'traceId = "{t}"' for t in tids)
spans = q("aws/spans", f"filter {tid_filter} | fields name, scope.name as scope, traceId, "
          "attributes.input.value as inv, attributes.output.value as outv, "
          "attributes.llm.input_messages.0.message.content as llm_in0, "
          "attributes.llm.input_messages.1.message.content as llm_in1, "
          "attributes.llm.output_messages.0.message.content as llm_out0, "
          "attributes.gen_ai.input.messages as gin, attributes.gen_ai.output.messages as gout, "
          "attributes.aws.genai.span_kind as kind | sort traceId, name")
print(f"spans={len(spans)}")
def short(v):
    if v is None: return "-"
    v = str(v); return v if len(v) <= 28 else v[:25].replace("\n", " ") + f"...({len(v)}ch)"
for s in spans:
    print(f"  {s.get('kind','-'):5} {s.get('scope','')[:34]:34} {s.get('name','')[:36]:36} "
          f"input.value={short(s.get('inv'))} | llm.in0={short(s.get('llm_in0'))} | llm.in1={short(s.get('llm_in1'))} | llm.out0={short(s.get('llm_out0'))} | gen_ai.in={short(s.get('gin'))}")
pii = sum(1 for s in spans for k in ("inv","outv","llm_in0","llm_in1","llm_out0","gin","gout")
          if s.get(k) and ("Gildong" in s[k] or "010-1234" in s[k]))
print(f"span fields containing synthetic PII: {pii}")

# 2) log events in the agent log group (content-extraction path)
try:
    ev = q(a.log_group, f'filter @message like "{a.session_id}" or @message like "Gildong" | fields @timestamp, @message | sort @timestamp | limit 20')
    print(f"log events in {a.log_group} mentioning session/PII: {len(ev)}")
    for e in ev[:6]:
        print("   ", e["@timestamp"], short(e["@message"].replace("\n"," ")) if len(e["@message"])>300 else e["@message"][:300].replace("\n"," "))
except Exception as ex:
    print("log group query failed:", ex)
