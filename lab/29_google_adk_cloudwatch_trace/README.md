# Google ADK → OpenInference → ADOT → CloudWatch 추적 테스트 (Knox Q2(a)/(b))

Google ADK 에이전트의 멀티턴 대화를 OpenInference 계측 + ADOT로 CloudWatch에 보내고,
세션 그룹핑과 PII 마스킹 동작을 실제로 확인한 테스트입니다.

## 구성

| 파일 | 역할 |
|---|---|
| `agent.py` | ADK 에이전트(툴 1개) + 3턴 대화. 턴 1에 가짜 PII(이름·전화번호) 포함 |
| `run.sh` | ADOT(`opentelemetry-instrument`)로 실행. 모드: `plain` / `masked` / `redact` |
| `verify.py` | `aws/spans` 로그 그룹을 Logs Insights로 조회해 세션별 스팬·마스킹 상태 출력 |
| `run_q2b.sh` | Q2(b) 추가 실행 전용. `adot-redact`(ADOT 삭제만, OpenInference 플래그 없음) / `extract`(ADOT 기본 본문 분리 경로, 로그 exporter on) |
| `verify_q2b.py` | 스팬별 본문 속성의 **원시 값**과 에이전트 로그 그룹의 로그 이벤트를 출력(`__REDACTED__` vs `REDACTED` 구분용) |
| `.env.example` | `GOOGLE_API_KEY` 템플릿 (`.env`는 git-ignore) |

환경: Python 3.12 (uv venv), google-adk 2.13.0, openinference-instrumentation-google-adk 1.0.5,
aws-opentelemetry-distro 0.21.0. 리전 us-west-2, Transaction Search 활성 상태.

```bash
cp .env.example .env   # GOOGLE_API_KEY 입력
./run.sh plain          # A: 마스킹 없음
./run.sh masked         # B: OPENINFERENCE_HIDE_INPUTS/OUTPUTS=True
./run.sh redact         # C: B + AWS_REDACT_SPAN_ATTRIBUTES (ADOT)
.venv/bin/python verify.py --session-id <run.sh가 출력한 session_id>
```

## 동작 흐름

### 전체 파이프라인

```
 run.sh <mode>
   │  .env 로드(GOOGLE_API_KEY), OTEL_* / AGENT_OBSERVABILITY_ENABLED 등 환경변수 설정
   │  session_id = knox-adk-<mode>-<timestamp>
   ▼
 opentelemetry-instrument python agent.py --session-id ...     ← ADOT 런처
   │
   │  ┌──────────────────────────────────────────────────────────────┐
   │  │ 프로세스 시작 시 ADOT(aws_distro)가 자동 계측기를 붙임          │
   │  │  • openinference-instrumentation-google-adk  (CHAIN/AGENT/TOOL) │
   │  │  • httpx 계측                                   (POST 스팬)     │
   │  │  • ADK 2.x 내장 OTel 추적 gcp.vertex.agent      (LLM 스팬 생성)   │
   │  │    └ OpenInference 래퍼가 이 스팬 위에 llm.input_messages.* 를 직접 기록 │
   │  └──────────────────────────────────────────────────────────────┘
   ▼
 agent.py : InMemoryRunner.run_async(user_id=, session_id=, new_message=)  ×3턴
   │
   ▼
 OTel SDK (TracerProvider) ── OTLP http/protobuf ──▶ CloudWatch
                                                     ├─ aws/spans 로그 그룹 (모든 스팬)
                                                     ├─ X-Ray 인덱스 (기본 1% 샘플)
                                                     └─ GenAI Observability 콘솔
                                                        Agents › Sessions › Traces › Spans
   ▲
   │  verify.py : Logs Insights 2단계 조회
   │    ① @message like "<session_id>"  → traceId 수집
   │    ② 그 traceId의 모든 스팬 조회  → scope / kind / session.id / 마스킹 상태 출력
```

### 한 세션이 CloudWatch에 쌓이는 모양 (턴 1개 = 트레이스 1개)

```
 session.id = knox-adk-plain-20261027-001352
 ├─ trace #1 (턴 1 "my name is Gildong Hong ...")
 │   └─ invocation [knox-adk-trace-test]        CHAIN  openinference  session.id ✔
 │       └─ invoke_workflow knox_trace_test_agent CHAIN  openinference  session.id ✔
 │           └─ agent_run [knox_trace_test_agent] AGENT  openinference  session.id ✔
 │               ├─ invoke_agent knox_trace_test_agent  LLM  gcp.vertex.agent
 │               │     gen_ai.usage.input/output_tokens, llm.input_messages.* (프롬프트 원문)
 │               │     gen_ai.conversation.id ✔   session.id ✘
 │               └─ POST generativelanguage.googleapis.com  httpx
 ├─ trace #2 (턴 2 "weather in Seoul")  + execute_tool get_weather (TOOL)
 └─ trace #3 (턴 3 "what was my name ...")
```

### 모드별로 바뀌는 지점

```
 mode    환경변수                                 가려지는 스팬
 ─────── ──────────────────────────────────────── ─────────────────────────────────
 plain   (없음)                                   없음 → PII 원문 저장
 masked  OPENINFERENCE_HIDE_INPUTS/OUTPUTS=True    openinference 스팬만 (__REDACTED__)
                                                  ADK LLM 스팬은 원문 그대로 ✘
 redact  masked + AWS_REDACT_SPAN_ATTRIBUTES=      모든 스팬 (ADOT 단계에서 REDACTED)
         'llm.input_messages.*,llm.output_messages.*,input.value,output.value,...'
```

핵심 두 가지:
- 스팬 출처가 둘(OpenInference 계측기 + ADK 내장 추적)이라 OpenInference 마스킹 플래그는 ADK의 LLM 스팬에 닿지 않는다. 둘 다 가리려면 ADOT 단계의 `AWS_REDACT_SPAN_ATTRIBUTES`가 필요하다.
- 세션 묶음은 OpenInference 루트 스팬의 `session.id`가 담당하고 토큰은 ADK LLM 스팬에만 있어, 콘솔의 Agent 단위 Total tokens 카드가 0으로 나온다. 토큰 합산은 `gen_ai.conversation.id`로 Logs Insights에서 직접 한다.

## 결과 (2026-10-27, us-west-2)

### (a) 멀티턴 추적
- 세 턴 모두 CloudWatch `aws/spans`에 도착. 턴 = 트레이스 1개, 3개 트레이스가 같은 `session.id`로 묶임.
- 스팬 출처가 **두 종류**로 섞여 들어온다.
  - `openinference.instrumentation.google_adk`: `invocation`(CHAIN) → `invoke_workflow`(CHAIN) → `agent_run`(AGENT) → `execute_tool`(TOOL). 모두 `session.id`, `user.id` 보유.
  - `gcp.vertex.agent` (ADK 2.x 내장 OTel 추적): `invoke_agent ...` LLM 스팬. `llm.input_messages.*`에 프롬프트 전문, `session.id` 없음(같은 트레이스 안에 있어 트레이스 뷰에서는 보임).
- `session.id`는 `Runner.run_async(user_id=..., session_id=...)` 키워드 인자에서만 추출됨.
- 첫 턴의 스팬이 조회에 늦게 나타난 사례가 있었음(약 10분 이상). 유실이 아니라 수집 지연이며, 로컬 콘솔 exporter로 3개 트레이스 생성은 확인됨. 최종적으로 plain/masked/redact 세 세션 모두 3/3 턴, 17 스팬 확인.
- **버전 의존성(중요):** AWS AgentCore 문서(OpenInference ADK 0.1.13/0.1.14)는 `call_llm` LLM 스팬이 `openinference.instrumentation.google_adk` scope로 나온다고 예시하지만, 이번 조합(ADK 2.13.0 + OpenInference ADK 1.0.5)에서는 OpenInference LLM 스팬이 전혀 생성되지 않고 LLM 스팬은 ADK 내장 `gcp.vertex.agent`에서만 나왔다. 어떤 마스킹 플래그가 프롬프트를 가리는지가 ADK/OpenInference 버전 쌍에 따라 달라진다.
- **콘솔 확인(2026-10-27, 사용자 직접 확인):** CloudWatch 콘솔 → GenAI Observability → Bedrock AgentCore → Agents → `knox-adk-trace-test` → Sessions view에 `knox-adk-plain-20261027-001352`가 **Traces (3)** 으로 표시됨. 트레이스 상세에서 ADK 내장 `invoke_agent` 스팬(scope `gcp.vertex.agent`)이 `aws.genai.span_kind = LLM`, `gen_ai.usage.input_tokens = 419`, `gen_ai.usage.output_tokens = 77`, `aws.genai.token_count_total = 496`으로 인식되어 스팬 패널에 Model / Input tokens / Output tokens가 표시됨. 즉 ADOT가 이 scope도 모델 호출로 분류한다.
- 이 ADK 내장 LLM 스팬에는 `openinference.span.kind = LLM`, `llm.input_messages.*`, `gen_ai.conversation.id`(세션 ID와 동일 값)가 붙어 있다. **정정(소스 확인):** 스팬 자체는 ADK가 만들지만(`gcp.vertex.agent`), `llm.input_messages.*` 등 OpenInference 속성은 **OpenInference ADK 1.0.5가 ADK의 `trace_call_llm` 훅을 패치해 `get_current_span().set_attribute()`로 ADK 스팬 위에 직접 써 넣는 것**이다(`openinference/instrumentation/google_adk/_wrappers.py`). OITracer를 거치지 않으므로 `OPENINFERENCE_HIDE_*`가 적용되지 않는다. OpenInference 1.0.5는 LLM 스팬을 따로 만들지 않고, `session.id` 속성도 이 스팬에는 없다(세션 그룹핑은 OpenInference의 `invocation` 루트 스팬이 담당).
- **불일치 1건:** 트레이스 상세 상단 "Trace metrics"는 Spans 3, **Tokens 0** 으로 표시되는데, 하위 LLM 스팬에는 토큰 419→77이 있다. Agent view(Agents → `knox-adk-trace-test`)의 **Total tokens도 0, Total token cost는 "-"** 로 표시된다(Sessions/Traces 수는 정확). 아래 실험으로 원인을 좁혔다.

#### (a)-토큰 Agent view "Total tokens = 0" 원인 실험 (2026-10-27, 모두 콘솔에서 직접 확인)

가설마다 SpanProcessor(`SessionIdStamper`)로 스팬 속성을 바꿔 한 세션씩 보내고 Agent view 수치를 확인했다. 이 실험 코드(`sid`/`tok`/`bedrock`/`root` 모드)는 결론이 난 뒤 단순화를 위해 제거했으며, git 이력(lab/29 최초 커밋)에 남아 있다. Sessions/Traces는 매번 정확히 증가했고 Total tokens는 **다섯 번 모두 0** 이었다.

| # | 가설 | 실행 모드 / 조치 | 저장 확인(aws/spans) | 결과 |
|---|---|---|---|---|
| 1 | LLM 스팬에 `session.id`가 없어 세션 집계에서 빠진다 | `sid`: 모든 스팬에 `session.id`/`user.id` 복사 | LLM 스팬 `session.id=Y` | Total tokens 0 |
| 2 | `gen_ai.usage.total_tokens`/`gen_ai.system`이 없어 집계 키가 안 맞는다 | `tok`: LLM 스팬에 두 속성 추가 | 저장됨 | 0 |
| 3 | X-Ray 인덱싱 기본 1%라 집계 대상 트레이스가 샘플링에서 빠진다 | `Default` 인덱싱 규칙 100%로 상향 후 재전송 | 3개 트레이스 모두 인덱싱됨 | 0 |
| 4 | 인식된 모델 공급자(Bedrock)만 집계한다 | `bedrock`: `gen_ai.system=aws.bedrock`, 모델 ID를 Claude Haiku 4.5로 relabel(진단용) | 저장됨 | 0 |
| 5 | 루트(에이전트) 스팬의 토큰만 읽는다 | `root`: 트레이스별 토큰 합을 루트 `invocation` 스팬에 `gen_ai.usage.*`/`llm.token_count.*`로 기록 | 루트 스팬 3개에 `aws.genai.token_count_total` 298/442/554까지 저장됨 | 0 |

- 결론: **이 구성(AgentCore 외부, ADOT 런처, `OTEL_LOGS_EXPORTER=none`, `OTEL_METRICS_EXPORTER=none`)에서는 토큰 속성을 어떤 스팬(ADK LLM 스팬, OpenInference 루트 CHAIN 스팬)에 어떤 이름으로 넣어도 Agent/Trace 수준 토큰 합계에 반영되지 않았다.** 스팬 속성, `session.id`, 인덱싱 비율, 공급자 라벨, 루트 스팬 위치는 모두 원인이 아니다. 실험 5가 OpenInference 루트 스팬에서도 0이었으므로 ADK 고유 문제라고 단정할 수 없다.
- 검증하지 못한 가설: run.sh가 로그/메트릭 exporter를 꺼 두었다. AWS 문서의 AgentCore 외부 ADOT 설정은 이를 끄지 않으며 `x-aws-metric-namespace=bedrock-agentcore` 헤더는 메트릭 경로용이므로, Agent view의 토큰/비용 카드가 스팬이 아니라 **메트릭 경로**에서 계산될 가능성이 남아 있다. 두 exporter를 기본값으로 두고 한 번 더 실행하면 판별 가능(미실행, 원인 미확정 → 서비스 팀 확인 필요).
- 고객 답변에서의 의미: 세션·트레이스·스팬 단위 추적과 스팬별 토큰 조회는 되지만, 콘솔의 에이전트 단위 토큰/비용 합계 카드는 이 구성에서 0이므로 Logs Insights(`aws/spans`)나 Omni SQL로 직접 합산해야 한다. ADK 기본 구성에서는 LLM 스팬에 `session.id`가 없으므로 **`gen_ai.conversation.id`로 필터**해야 한다(검증 완료: stamper 없는 plain 세션에서 LLM 스팬 3개, 입력 953 / 출력 210 토큰).
  ```
  filter attributes.gen_ai.conversation.id = "<session_id>" and attributes.aws.genai.span_kind = "LLM"
  | stats sum(attributes.gen_ai.usage.input_tokens) as input_tokens,
          sum(attributes.gen_ai.usage.output_tokens) as output_tokens, count(*) as llm_spans
  ```
  (`attributes.session.id` 필터는 ADK LLM 스팬을 놓치므로 토큰 합이 0/null로 나온다.)
- 실험 뒤처리: X-Ray `Default` 인덱싱 규칙은 1%로 복원함. 실험 3~5(`tok` 재전송, `bedrock`, `root`)의 트레이스만 100% 인덱싱 상태로 전송됐고 실험 1~2(`sid`, 첫 `tok`)는 기본 1%에서 전송됐다. `bedrock` 모드 세션은 실제 Gemini 호출을 Bedrock 모델로 라벨만 바꾼 진단 데이터이므로 비용 분석에 쓰면 안 된다.

### (b) PII 마스킹

| 모드 | OpenInference 스팬 (CHAIN/AGENT/TOOL) | ADK 내장 LLM 스팬 (`gcp.vertex.agent`) |
|---|---|---|
| plain | 원문 저장 | 원문 저장 (이름·전화번호 그대로) |
| masked (`OPENINFERENCE_HIDE_*`) | `__REDACTED__` | **원문 그대로 남음** |
| redact (+ `AWS_REDACT_SPAN_ATTRIBUTES`) | `REDACTED` | `REDACTED` |
| adot-redact (`AWS_REDACT_SPAN_ATTRIBUTES`만, `run_q2b.sh`) | `REDACTED` (`invocation`·`execute_tool`의 `input.value`) | `REDACTED` (`input.value`, `llm.input_messages.*`) |
| extract (ADOT 기본 본문 분리, `run_q2b.sh`) | 본문 제거됨(`input.value`/`output.value` → 로그 이벤트로 이동) | **PII 잔존**: 중첩형 `llm.input_messages.N.message.contents.0.message_content.text`는 분리 대상 아님 |
| adk-nocontent (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, `run_q2b.sh`) | 원문(변화 없음) | **PII 잔존** (속성을 쓰는 주체가 ADK가 아니라 OpenInference 래퍼) |

- 결론: ADK에서는 OpenInference 플래그만으로 부족하다. ADK 자체 추적이 만드는 LLM 스팬은
  ADOT 수준 `AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,...'`로 가려야 한다.
  ADOT 변수 **단독**으로도 두 출처의 스팬이 모두 가려진다(세션 `knox-adk-adot-redact-20261027-032809`, 17 스팬 중 합성 PII 잔존 필드 0). OpenInference 플래그는 없어도 된다. 와일드카드 `llm.input_messages.*`가 중첩 키까지 잡는다.
- **ADOT 기본 본문 분리 경로(extract) 상세** (세션 `knox-adk-extract-20261027-033639`, 로그 스트림 생성 후):
  - ADOT의 LLO 핸들러(`amazon/opentelemetry/distro/llo_handler.py`)는 정해진 키 패턴만 스팬에서 떼어 로그 이벤트로 보낸다: `input.value`, `output.value`, `llm.input_messages.{i}.message.content`, `gen_ai.prompt.{i}.content`, `gen_ai.input.messages` 등. OpenInference 래퍼가 ADK 스팬에 쓰는 중첩형 `llm.input_messages.{i}.message.contents.{j}.message_content.text`는 패턴에 없어 **ADK LLM 스팬 3개에 PII가 그대로 남았다**.
  - 로그 그룹(`/aws/bedrock-agentcore/runtimes/knox-adk-trace-test`)에는 본문 이벤트 7건이 도착했고 7건 모두 PII 포함: ADK가 내는 `gen_ai.client.inference.operation.details` 4건(ADOT가 `AGENT_OBSERVABILITY_ENABLED=true`일 때 `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`를 기본 설정하므로 ADK가 본문 이벤트를 냄) + ADOT LLO 추출 3건. 이 로그 그룹에 CloudWatch Logs 데이터 보호 정책을 거는 구성이 된다.
  - **함정:** ADOT는 `OTEL_EXPORTER_OTLP_LOGS_HEADERS`의 `x-aws-log-stream`에 적은 로그 스트림을 만들어 주지 않는다. 스트림이 없으면 `400 The specified log stream does not exist`로 로그 export가 조용히 실패한다(ERROR 로그만 남고 프로세스는 정상 종료). `aws logs create-log-stream`으로 미리 만들어야 한다. 첫 extract 실행(`...-032821`)은 이 때문에 로그 이벤트가 0건이었다.
- **ADK 자체 스위치는 무효:** `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`(세션 `knox-adk-adk-nocontent-20261027-033532`)로도 ADK LLM 스팬 3개에 `llm.input_messages.*`와 PII가 남는다. 이 속성은 ADK가 아니라 OpenInference 래퍼가 쓰기 때문이다.
- **종합:** ADK 2.13 + OpenInference ADK 1.0.5 + ADOT 0.21 조합에서 캡처 시점에 모든 스팬의 본문을 확실히 없애는 방법은 ADOT `AWS_REDACT_SPAN_ATTRIBUTES` 하나뿐이었다. 본문 분리 경로를 쓰더라도 이 변수를 함께 걸어야 ADK LLM 스팬의 중첩 키가 정리된다.
- 캡처 시 마스킹은 되돌릴 수 없으므로 디버깅용 원문이 필요하면 수집 시 데이터 보호 정책(패턴 마스킹) 또는 읽기 시 Omni 데이터 스코프와 조합한다.
- 네 번째 선택지: 이 테스트는 `AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true`로 프롬프트 본문을 스팬에 남기고 `OTEL_LOGS_EXPORTER=none`으로 로그를 끈 상태였다. ADOT 기본값(변수 미설정)은 본문을 스팬에서 떼어 OTel 로그 이벤트로 보내므로, 스팬에는 PII가 남지 않고 로그 그룹 쪽에 CloudWatch Logs 데이터 보호 정책을 적용하는 구성이 된다.
- 테스트 부산물: plain/masked/extract/adk-nocontent 세션의 합성 PII가 `aws/spans`(계정 보존 기간 30일)와 `/aws/bedrock-agentcore/runtimes/knox-adk-trace-test`(7일)에 남아 있다. 합성 데이터라 위험은 낮다.

## 세션 ID 기록
`sessions.log`에 실행마다 session_id가 append 된다. CloudWatch 콘솔 → GenAI Observability → Bedrock AgentCore → Agents → Sessions view에서 같은 ID로 조회된다(확인됨).
