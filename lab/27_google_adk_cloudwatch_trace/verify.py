"""Query the aws/spans log group for one session and print what CloudWatch stored.

    .venv/bin/python verify.py --session-id <id> [--region us-west-2] [--minutes 60]

Two-step query:
  1. find every span whose raw JSON mentions the session id -> collect traceIds
  2. fetch every span of those traceIds (LLM/TOOL spans may not carry session.id)
Per span it prints: trace, scope (openinference vs ADK native), span kind, name,
whether input/output content is present and whether it reads __REDACTED__.
"""

import argparse
import json
import time
from collections import Counter, defaultdict

import boto3


def run_query(logs, log_group: str, query: str, minutes: int):
    end = int(time.time())
    qid = logs.start_query(
        logGroupName=log_group, startTime=end - minutes * 60, endTime=end, queryString=query
    )["queryId"]
    while True:
        res = logs.get_query_results(queryId=qid)
        if res["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            return res
        time.sleep(2)


def records(res):
    out = []
    for r in res.get("results", []):
        msg = next((f["value"] for f in r if f["field"] == "@message"), None)
        if msg:
            try:
                out.append(json.loads(msg))
            except json.JSONDecodeError:
                pass
    return out


def content_tag(attrs: dict, prefix: str) -> str:
    """Summarise content attributes: input.value / output.value or llm.*_messages.*"""
    v = attrs.get(f"{prefix}.value")
    if v is None:
        texts = [val for k, val in attrs.items()
                 if k.startswith(f"llm.{prefix}_messages.") and k.endswith(".text")]
        if not texts:
            return "-"
        v = " | ".join(str(t) for t in texts)
    v = str(v)
    return "REDACTED" if "__REDACTED__" in v else f"{len(v)}ch"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--session-id", required=True)
    p.add_argument("--region", default="us-west-2")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--log-group", default="aws/spans")
    p.add_argument("--show-pii", action="store_true", help="print a sample LLM input verbatim")
    args = p.parse_args()

    logs = boto3.client("logs", region_name=args.region)

    q1 = (f'fields @message | filter @message like "{args.session_id}" '
          f'| sort @timestamp asc | limit 500')
    seed = records(run_query(logs, args.log_group, q1, args.minutes))
    trace_ids = sorted({s["traceId"] for s in seed if "traceId" in s})
    print(f"session_id={args.session_id}  spans mentioning session: {len(seed)}  "
          f"traces: {len(trace_ids)}")
    if not trace_ids:
        print("no spans yet. spans usually appear within 2-5 minutes; retry.")
        return

    ors = " or ".join(f'traceId = "{t}"' for t in trace_ids)
    q2 = f"fields @message | filter {ors} | sort @timestamp asc | limit 1000"
    spans = records(run_query(logs, args.log_group, q2, args.minutes))
    spans.sort(key=lambda s: s.get("startTimeUnixNano", 0))

    by_trace = defaultdict(list)
    for s in spans:
        by_trace[s["traceId"]].append(s)

    scopes = Counter(s.get("scope", {}).get("name") for s in spans)
    kinds = Counter(s.get("attributes", {}).get("openinference.span.kind", "-") for s in spans)
    print(f"total spans in those traces: {len(spans)}")
    print(f"scopes: {dict(scopes)}")
    print(f"openinference.span.kind: {dict(kinds)}")

    for turn, tid in enumerate(trace_ids, start=1):
        print(f"\n--- turn {turn}  trace={tid}  spans={len(by_trace[tid])}")
        for s in by_trace[tid]:
            a = s.get("attributes", {})
            scope = s.get("scope", {}).get("name", "?")
            scope_short = "openinference" if "openinference" in scope else scope
            print(f"  {scope_short:22} kind={a.get('openinference.span.kind','-'):5} "
                  f"session.id={'Y' if a.get('session.id') else '-'} "
                  f"in={content_tag(a,'input'):8} out={content_tag(a,'output'):8} "
                  f"name={s.get('name','')[:45]}")

    if args.show_pii:
        for s in spans:
            a = s.get("attributes", {})
            if a.get("openinference.span.kind") == "LLM" or "llm.input_messages.1.message.contents.0.message_content.text" in a:
                k = "llm.input_messages.1.message.contents.0.message_content.text"
                print(f"\nsample LLM input ({s.get('scope',{}).get('name')}): {str(a.get(k) or a.get('input.value'))[:200]}")
                break


if __name__ == "__main__":
    main()
