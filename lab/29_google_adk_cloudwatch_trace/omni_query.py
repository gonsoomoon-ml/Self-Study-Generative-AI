"""Query spans from CloudWatch Omni programmatically (what the Omni skills / a coding agent do).

Uses the public cloudwatchomni API (SigV4, boto3 >= 1.43.1xx):
  StartTelemetryQuerySession -> StartTelemetryQuery(SQL) -> GetTelemetryQueryResults (poll)

    .venv/bin/python omni_query.py --session-id <adk session id> [--hours 6]
    .venv/bin/python omni_query.py --sql "SELECT ... FROM traces.default ..."
"""
import argparse, json, time
import boto3

ap = argparse.ArgumentParser()
ap.add_argument("--region", default="us-west-2")
ap.add_argument("--session-id", help="ADK session id (matches session.id or gen_ai.conversation.id)")
ap.add_argument("--hours", type=int, default=6)
ap.add_argument("--sql", help="raw Omni SQL instead of the built-in span query")
a = ap.parse_args()

omni = boto3.client("cloudwatchomni", region_name=a.region)

def run(sql: str):
    sid = omni.start_telemetry_query_session(sessionName="knox-adk-demo")["sessionId"]
    try:
        qid = omni.start_telemetry_query(sessionId=sid, queryString=sql)["queryId"]
        while True:
            r = omni.get_telemetry_query_results(queryId=qid)
            if r["status"] in ("Complete", "Failed", "Cancelled"):
                return r
            time.sleep(1)
    finally:
        omni.stop_telemetry_query_session(sessionId=sid)

if a.sql:
    sql = a.sql
else:
    sql = f"""
SELECT `@timestamp`, name, scope['name'] AS scope, traceId,
       attributes['session.id'] AS session_id,
       attributes['gen_ai.conversation.id'] AS conversation_id,
       attributes['gen_ai.request.model'] AS model,
       attributes['gen_ai.usage.input_tokens'] AS in_tok,
       attributes['gen_ai.usage.output_tokens'] AS out_tok,
       CAST(durationNano AS DOUBLE) / 1e6 AS ms
FROM traces.default
WHERE `@timestamp` BETWEEN NOW() - INTERVAL '{a.hours} HOUR' AND NOW()
  AND (attributes['session.id'] = '{a.session_id}' OR attributes['gen_ai.conversation.id'] = '{a.session_id}')
ORDER BY `@timestamp` ASC
LIMIT 100
"""
r = run(sql)
print("status:", r["status"])
if r["status"] != "Complete":
    print(json.dumps(r, default=str)[:1500]); raise SystemExit(1)
rows = r.get("rows", [])
print("rows:", len(rows))
cols = r.get("columns") or (list(rows[0].keys()) if rows and isinstance(rows[0], dict) else None)
print("columns:", cols)
for row in rows[:40]:
    print(" ", json.dumps(row, default=str, ensure_ascii=False)[:300])
