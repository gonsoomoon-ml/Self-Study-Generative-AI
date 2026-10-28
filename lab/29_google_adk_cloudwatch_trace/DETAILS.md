# 상세 근거 — Google ADK + Claude on Bedrock → OpenInference → ADOT → CloudWatch

[README.md](README.md)의 질문별 답을 뒷받침하는 검증 기록과 문서 근거다. 검증 환경: Google ADK 2.13.0 + Claude Sonnet 5.5 on Amazon Bedrock(ADK `AnthropicLlm` 네이티브, LiteLLM 없음), openinference-instrumentation-google-adk 1.0.5, aws-opentelemetry-distro 0.21.0, 2026-10-27.

목차: [동작 흐름](#동작-흐름) · [(a) 멀티턴 추적](#a-멀티턴-추적) · [(b) PII 마스킹](#b-pii-마스킹) · [Bedrock 구성 결과](#bedrock-구성-결과-2026-10-27-adk-213--anthropicllm--bedrock-runtime) · [(c) SSO/MFA 대시보드](#c-ssomfa-대시보드-aws-계정-없는-사용자) · [(d) 분석](#d-분석-트레이싱-대시보드) · [코딩 에이전트에서 Omni 데이터 가져오기](#코딩-에이전트claude-codecursor에서-omni-데이터-가져오기-2026-10-27-확인)

## 동작 흐름

### 전체 파이프라인

```
 run.sh <mode>
   │  OTEL_* / AGENT_OBSERVABILITY_ENABLED 등 환경변수 설정
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
   │     모델 = ADK AnthropicLlm(client=AsyncAnthropic(base_url=https://bedrock-runtime.<region>.amazonaws.com/anthropic,
   │                                                   api_key=provide_token()))  → Claude Sonnet 5.5 on Bedrock
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
 │               └─ POST bedrock-runtime.<region>.amazonaws.com/anthropic/v1/messages  httpx
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
- 스팬 출처가 둘(OpenInference 계측기 + ADK 내장 추적)이고, ADK LLM 스팬의 본문 속성은 OpenInference 래퍼가 마스킹 트레이서를 거치지 않고 `set_attribute`로 직접 쓰므로 `OPENINFERENCE_HIDE_*`가 닿지 않는다. 둘 다 가리려면 ADOT 단계의 `AWS_REDACT_SPAN_ATTRIBUTES`(스팬 속성 전용 프로세서)가 필요하다.
- 세션 묶음은 OpenInference 루트 스팬의 `session.id`가 담당하고 토큰은 ADK LLM 스팬에만 있다. 스팬 기준으로 세션별 토큰을 합산하려면 `gen_ai.conversation.id`로 LLM 스팬을 찾아야 한다.


## (a) 멀티턴 추적
- **세션 키가 두 개**: OpenInference 스팬은 `session.id`, ADK LLM 스팬은 `gen_ai.conversation.id`에 세션 ID가 있다. 조회·집계 시 두 속성을 OR로 묶어야 LLM 스팬이 빠지지 않는다.
- 세 턴 모두 CloudWatch `aws/spans`에 도착. 턴 = 트레이스 1개, 3개 트레이스가 같은 `session.id`로 묶임.
- 스팬 출처가 **두 종류**로 섞여 들어온다.
  - `openinference.instrumentation.google_adk`: `invocation`(CHAIN) → `invoke_workflow`(CHAIN) → `agent_run`(AGENT) → `execute_tool`(TOOL). 모두 `session.id`, `user.id` 보유.
  - `gcp.vertex.agent` (ADK 2.x 내장 OTel 추적): `invoke_agent ...` LLM 스팬. `llm.input_messages.*`에 프롬프트 전문, `session.id` 없음(같은 트레이스 안에 있어 트레이스 뷰에서는 보임).
- `session.id`는 `Runner.run_async(user_id=..., session_id=...)` 키워드 인자에서만 추출됨.
- 첫 턴의 스팬이 조회에 약 10분 이상 늦게 나타난 사례가 있었다. 유실이 아니라 수집 지연이며, 최종적으로 plain/masked/redact 세 세션 모두 3/3 턴이 확인됐다.
- **버전 의존성(중요):** AWS AgentCore 문서(OpenInference ADK 0.1.13/0.1.14)는 `call_llm` LLM 스팬이 `openinference.instrumentation.google_adk` scope로 나온다고 예시하지만, 이번 조합(ADK 2.13.0 + OpenInference ADK 1.0.5)에서는 OpenInference LLM 스팬이 전혀 생성되지 않고 LLM 스팬은 ADK 내장 `gcp.vertex.agent`에서만 나왔다. 어떤 마스킹 플래그가 프롬프트를 가리는지가 ADK/OpenInference 버전 쌍에 따라 달라진다.
- **콘솔 확인(2026-10-27):** CloudWatch 콘솔 → GenAI Observability → Bedrock AgentCore → Agents → `knox-adk-trace-test` → Sessions view에 한 세션이 **Traces (3)** 으로 표시됨. 트레이스 상세에서 ADK 내장 `invoke_agent` 스팬(scope `gcp.vertex.agent`)이 `aws.genai.span_kind = LLM`, `gen_ai.usage.input_tokens = 419`, `gen_ai.usage.output_tokens = 77`, `aws.genai.token_count_total = 496`으로 인식되어 스팬 패널에 Model / Input tokens / Output tokens가 표시됨. 즉 ADOT가 이 scope도 모델 호출로 분류한다.
- 이 ADK 내장 LLM 스팬에는 `openinference.span.kind = LLM`, `llm.input_messages.*`, `gen_ai.conversation.id`(세션 ID와 동일 값)가 붙어 있다. **소스 확인:** 스팬 자체는 ADK가 만들지만(`gcp.vertex.agent`), `llm.input_messages.*` 등 OpenInference 속성은 **OpenInference ADK 1.0.5가 ADK의 `trace_call_llm` 훅을 패치해 `get_current_span().set_attribute()`로 ADK 스팬 위에 직접 써 넣는 것**이다(`openinference/instrumentation/google_adk/_wrappers.py`). OITracer를 거치지 않으므로 `OPENINFERENCE_HIDE_*`가 적용되지 않는다. OpenInference 1.0.5는 LLM 스팬을 따로 만들지 않고, `session.id` 속성도 이 스팬에는 없다(세션 그룹핑은 OpenInference의 `invocation` 루트 스팬이 담당).
### Total tokens 집계 방식 (콘솔 Agent view vs 스팬 합산, 2026-10-27 콘솔 확인)

- **콘솔 Agent view의 Total tokens·Total token cost는 스팬이 아니라 Bedrock 모델 호출 기록에서 계산된다.** Agents 표의 값(`knox-adk-trace-test` 5.7K / $0.016, `knox-adk-bedrock-test` 7K / $0.009)이 각각 Bedrock 호출 로그의 토큰 합(Sonnet 5.5 8건 5,678, Haiku 4.5 8건 6,960)과 일치한다. 스팬 속성(`gen_ai.usage.*`, `session.id`, `gen_ai.system`), X-Ray 인덱싱 비율, 루트 스팬 위치를 바꿔도 이 값은 달라지지 않았다. 화면: `img/agentcore-observability.png`.
- **스팬 기반 합산은 툴 호출 턴에서 과소 집계된다.** 콘솔 값이 스팬 토큰 합(Sonnet 4,341 / Haiku 5,286)보다 크다. ADK LLM 스팬은 턴당 1개라 툴 호출 왕복(턴 2의 두 번째 모델 호출)의 토큰을 빠뜨리는 반면 호출 기록은 세션당 4건을 모두 센다. Logs Insights·Omni 등 스팬을 합산하는 경로는 이 차이를 감안해야 한다.
- **CloudWatch Omni에서도 집계된다(2026-10-27 콘솔 확인):** 같은 계정·리전에 Omni 스페이스를 만들자 Agent overview에 `knox-adk-trace-test`가 Active agents 1, Sessions 10, Traces 28, **Total tokens 12.9k**로 표시되고 "5 highest token-consuming agents" 차트에 토큰 시계열이 그려졌다. Omni 지원 프레임워크 표에 ADK가 없어도 Agents 목록에 잡혔다. 단 "Top 10 agents" 표의 Tokens 열은 0으로 표시되어 요약 카드(12.9k)와 불일치가 있었다(`img/cloudwatch-omni.png`).
- **권장:** 에이전트 단위 토큰·비용은 콘솔 Agent view(Bedrock 호출 기록 기반, 툴 호출 포함, 가장 정확), 모델 단위는 Model Invocations, 스팬 기반은 Omni/Logs Insights(툴 호출 왕복 누락 가능). ADK 기본 구성에서는 LLM 스팬에 `session.id`가 없으므로 Logs Insights에서는 **`gen_ai.conversation.id`로 필터**해야 한다(검증: 한 세션에서 LLM 스팬 3개, 입력 953 / 출력 210 토큰).
  ```
  filter attributes.gen_ai.conversation.id = "<session_id>" and attributes.aws.genai.span_kind = "LLM"
  | stats sum(attributes.gen_ai.usage.input_tokens) as input_tokens,
          sum(attributes.gen_ai.usage.output_tokens) as output_tokens, count(*) as llm_spans
  ```
  (`attributes.session.id` 필터는 ADK LLM 스팬을 놓치므로 토큰 합이 0/null로 나온다.)


## (b) PII 마스킹

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
  ADOT 변수 **단독**으로도 두 출처의 스팬이 모두 가려진다(17 스팬 중 합성 PII 잔존 필드 0). OpenInference 플래그는 없어도 된다. 와일드카드 `llm.input_messages.*`가 중첩 키까지 잡는다.
### ADOT 로그 경로 실험

- **ADOT 기본 본문 분리 경로(extract) 상세**:
  - ADOT의 LLO 핸들러(`amazon/opentelemetry/distro/llo_handler.py`)는 정해진 키 패턴만 스팬에서 떼어 로그 이벤트로 보낸다: `input.value`, `output.value`, `llm.input_messages.{i}.message.content`, `gen_ai.prompt.{i}.content`, `gen_ai.input.messages` 등. OpenInference 래퍼가 ADK 스팬에 쓰는 중첩형 `llm.input_messages.{i}.message.contents.{j}.message_content.text`는 패턴에 없어 **ADK LLM 스팬 3개에 PII가 그대로 남았다**.
  - 로그 그룹(`/aws/bedrock-agentcore/runtimes/knox-adk-trace-test`)에는 본문 이벤트가 도착했고 전부 PII 포함(이벤트 `attributes`/`body`를 직접 확인): ADK가 내는 `gen_ai.client.inference.operation.details` 4건(`gen_ai.input.messages`/`gen_ai.output.messages` 속성; ADOT가 `AGENT_OBSERVABILITY_ENABLED=true`일 때 `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`를 기본 설정하므로 ADK가 본문 이벤트를 냄) + ADOT LLO가 OpenInference 스팬의 `input.value`/`output.value`를 옮긴 이벤트(scope `openinference.instrumentation.google_adk`, 본문은 body) 3건. 이 로그 그룹에 CloudWatch Logs 데이터 보호 정책을 거는 구성이 된다.
- **extract + `AWS_REDACT_SPAN_ATTRIBUTES` 동시 적용**: 스팬은 두 출처 모두 PII 0(ADK LLM 스팬 3개 `REDACTED`). 로그 그룹에는 ADK 본문 이벤트 4건이 **PII 포함 그대로** 도착(redact는 스팬 프로세서라 로그 레코드에는 작용하지 않음), ADOT LLO 추출 이벤트 3건은 redact 이후 값이 복사되어 `REDACTED`로 도착. 즉 redact 변수는 스팬 전용이며, 로그 경로는 별도로 통제해야 한다(`OTEL_LOGS_EXPORTER=none`, 또는 로그 그룹 데이터 보호 정책). `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`를 비활성 값으로 명시해 ADK 본문 이벤트를 끄는 방법은 코드상 가능해 보이나 **미실행**.
  - **함정:** ADOT는 `OTEL_EXPORTER_OTLP_LOGS_HEADERS`의 `x-aws-log-stream`에 적은 로그 스트림을 만들어 주지 않는다. 스트림이 없으면 `400 The specified log stream does not exist`로 로그 export가 조용히 실패한다(ERROR 로그만 남고 프로세스는 정상 종료). `aws logs create-log-stream`으로 미리 만들어야 한다.
### 효과 없는 설정과 한계

- **ADK 자체 스위치는 무효:** `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`로도 ADK LLM 스팬 3개에 `llm.input_messages.*`와 PII가 남는다. 이 속성은 ADK가 아니라 OpenInference 래퍼가 쓰기 때문이다.
- **종합:** ADK 2.13 + OpenInference ADK 1.0.5 + ADOT 0.21 조합에서 캡처 시점에 모든 **스팬**의 본문을 확실히 없애는 방법은 ADOT `AWS_REDACT_SPAN_ATTRIBUTES` 하나뿐이었다. 본문 분리 경로를 쓰더라도 이 변수를 함께 걸어야 ADK LLM 스팬의 중첩 키가 정리된다. **로그 경로**(ADK 본문 이벤트)는 이 변수로 막히지 않으므로 로그 exporter를 끄거나 로그 그룹에 데이터 보호 정책을 적용해야 한다.
- 캡처 시 마스킹은 되돌릴 수 없으므로 디버깅용 원문이 필요하면 수집 시 데이터 보호 정책(패턴 마스킹) 또는 읽기 시 Omni 데이터 스코프와 조합한다.
- ADOT 기본값 구성: 이 테스트는 `AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true`로 프롬프트 본문을 스팬에 남기고 `OTEL_LOGS_EXPORTER=none`으로 로그를 끈 상태였다. ADOT 기본값(변수 미설정)은 본문을 스팬에서 떼어 OTel 로그 이벤트로 보내므로, 스팬에는 PII가 남지 않고 로그 그룹 쪽에 CloudWatch Logs 데이터 보호 정책을 적용하는 구성이 된다.


- **부분 마스킹 한계**: `AWS_REDACT_SPAN_ATTRIBUTES`는 속성 단위 전체 삭제다. 전화번호만 가리는 부분 마스킹은 커스텀 SpanProcessor 또는 OpenTelemetry Collector의 redaction/transform 프로세서가 필요하다.
- **CloudWatch Logs 데이터 보호 정책(문서 기준, 미실행)**: `aws/spans`와 본문 로그 그룹에 적용하면 정책 이후 수집분이 마스킹되고 `logs:Unmask` 권한자만 원문을 본다. 관리형 식별자에 한국 항목(주민등록번호·휴대폰)이 없어 커스텀 정규식(`CustomDataIdentifier`)으로 정의해야 한다(이메일·신용카드는 관리형 있음). Omni 데이터 스코프는 행 단위 접근 제한만 가능하고 필드를 가리지는 못한다.
- **평가 입력 트레이드오프**: 스팬 본문을 지우면 트레이스 기반 품질 평가(Bedrock AgentCore Evaluations)의 입력이 사라진다. 로그 이벤트 본문을 평가기가 읽는지는 미확인.

## Bedrock 구성 결과 (2026-10-27, ADK 2.13 + AnthropicLlm → bedrock-runtime)

ADK Python에는 Bedrock 전용 모델 클래스가 없고 레지스트리의 `bedrock/*`는 LiteLLM으로만 연결된다. 대신 Bedrock이
`bedrock-runtime` 엔드포인트에서 Anthropic Messages API(`/anthropic`)와 OpenAI Chat Completions(`/openai/v1`)를
네이티브로 제공하므로, ADK 내장 `AnthropicLlm`에 `AsyncAnthropic(base_url=…/anthropic, api_key=<단기 Bedrock 토큰>)`
클라이언트를 주입하면 LiteLLM·LangChain 없이 Claude on Bedrock을 호출할 수 있다(ADK 문서에는 Bedrock 예시가 없는
비공식 조합이며, 각 부분은 ADK·Bedrock 문서로 뒷받침된다). 단기 토큰은 `aws-bedrock-token-generator`가 AWS 자격 증명에서
만든다(최대 12시간).

| 실행 | 모델 | 스팬 | OpenInference 스팬 PII | ADK LLM 스팬 PII | LLM 토큰(in→out) |
|---|---|---|---|---|---|
| Haiku plain | Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) | 13 | 4/10 원문 | 3/3 원문 | 923→34, 863→38, 699→65 |
| Haiku redact | Haiku 4.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 938→34, 875→41, 699→77 |
| Sonnet plain | Sonnet 5.5 (`us.anthropic.claude-sonnet-5-5`) | 13 | 6/10 원문 | 3/3 원문 | 766→42, 692→46, 551→41 |
| Sonnet redact | Sonnet 5.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 791→38, 711→52, 551→60 |

- 스팬 트리·세션 그룹핑·마스킹 동작은 모델(Haiku/Sonnet)과 무관하게 동일하다. ADK의 `trace_call_llm` 훅이 모델 클래스와 무관하게
  동작하므로 OpenInference 래퍼가 ADK LLM 스팬에 본문을 쓰는 구조와 `AWS_REDACT_SPAN_ATTRIBUTES`의 효과가 그대로 나타난다.
- **공급자 라벨 오류:** `gen_ai.request.model`/`llm.model_name`은 Bedrock 모델 ID로 정확하지만 `gen_ai.provider.name=gcp.gemini`,
  `llm.provider=google`로 기록된다(ADK/OpenInference 래퍼의 고정값). 공급자별 집계·비용 산정에서 Bedrock 호출이 Google로
  분류될 수 있으므로 주의.
- **Bedrock Model Invocation Logs(서버 측):** 계정에 호출 로깅이 켜져 있어 `/aws/bedrock/model-invocation-logs`에 모든 호출의
  요청·응답 본문이 저장된다. 확인: 합성 PII가 포함된 이벤트 16건(Haiku 4.5 8건 + Sonnet 5.5 8건, operation `Messages`,
  `inputTokenCount`/`outputTokenCount` 포함). 캡처 시 스팬 마스킹(`AWS_REDACT_SPAN_ATTRIBUTES`)은 이
  로그에 영향을 주지 않는다. Bedrock을 쓰는 경우 (b)에 **추가 경로**로 호출 로깅 설정(텍스트 본문 전달 끄기,
  또는 해당 로그 그룹에 데이터 보호 정책)을 포함해야 한다.
- **콘솔 Model Invocations 뷰(2026-10-27 확인):** 모델 `us.anthropic.claude-sonnet-5-5` 선택 시 Invocations (16)
  목록(세션당 4회 = 3턴 + 툴 호출 왕복 1회 × 4세션), Input/Output 토큰 차트, Invocation count, 입력 토큰 크기 분포가 채워졌다.
  TTFT·프롬프트 캐시·스로틀·오류는 "No data", Latency 열은 "-". 목록의 Input/Output 열에 프롬프트·응답 원문이 그대로 표시되며
  **redact 세션의 호출도 포함**된다. 즉 스팬 마스킹은 이 뷰와 호출 로그에 영향을 주지 않는다. 같은 화면에 "To protect and mask
  your sensitive data, turn on CloudWatch Data protection at account level" 안내가 있다(계정 단위 데이터 보호 정책이 공식 경로).
  Sonnet 5.5 선택 시 Total tokens 차트 값 5,678은 Sonnet 호출 8건의 토큰 합(808+738+678+611+829+763+659+592)과 일치한다(`img/bedrock-model-invocation.png`).



## (c) SSO/MFA 대시보드 (AWS 계정 없는 사용자)

결론: 기존 CloudWatch 대시보드 공유 기능으로는 요구를 충족하기 어렵고, CloudWatch Omni가 가장 가까운 답이다. 고객 리전(아일랜드 eu-west-1)은 Omni 제공 리전에 포함된다.

### 후보 비교 (문서 기준 + Omni는 실제 스페이스에서 확인)

| 후보 | 로그인 | MFA | AWS 콘솔 접근 | 트레이스/세션 뷰 | 권한 분리 | 제약 |
|---|---|---|---|---|---|---|
| CloudWatch 대시보드 공유(이메일) | Cognito 사용자 풀, 비밀번호 | 문서에 언급 없음 | 불필요 | 불가(메트릭 위젯 중심, Logs 위젯은 기본 숨김) | 대시보드 단위 | 최대 5명. 공유 대상 전원이 계정의 모든 메트릭·EC2 태그 조회 권한을 받음 |
| CloudWatch 대시보드 공유(SAML SSO) | Cognito + SAML IdP | IdP 정책 | 불필요 | 불가 | 계정 내 모든 대시보드가 SSO 사용자 전원에게 열림 | 세분화 불가. GenAI 콘솔의 Sessions/Traces 페이지는 공유 대상 아님 |
| CloudWatch Omni | 조직 전용 URL `https://<domain>.cloudwatch-omni.global.app.aws`, IAM Identity Center(Okta·Entra 등 외부 IdP 연동) | IAM Identity Center/IdP 정책으로 강제 | 불필요 | 가능. 실제 스페이스에서 ADK 에이전트가 Agent overview에 세션 10·트레이스 28·토큰 12.9k로 집계됨(확인). 세션/트레이스 상세 뷰와 Omni 대시보드는 문서 기준 | Viewer/Editor/Space Admin/Custom 그랜트 + 데이터 스코프(행 단위) | 스페이스 = 계정+리전 단위. IAM Identity Center 인스턴스가 도메인과 같은 리전이어야 함(멀티리전 복제로 해결). 과금은 좌석이 아닌 데이터량(수집·저장·스캔 GB) 기준 |
| Amazon Managed Grafana | SAML 2.0 또는 IAM Identity Center | IdP 정책 | 불필요 | 직접 구성(CloudWatch·X-Ray 데이터 소스) | 사용자/팀별 폴더·대시보드 권한 | GenAI 전용 세션/트레이스 뷰 없음. 직접 만들어야 함 |

### Omni로 갈 때의 설계 포인트
- 도메인(로그인 URL·IdP 연결) 1개 아래 스페이스를 팀/환경별로 두고, 외부 사용자는 Viewer 그랜트 + 데이터 스코프로 자기 에이전트 행만 보게 제한한다.
- 데이터 스코프는 로그·트레이스 행만 거르고 메트릭·데이터셋 생성·내보내기·AI 요약에는 적용되지 않으므로, Custom 그랜트로 데이터셋/내보내기/AI 기능 액션도 함께 제한한다(문서 권고).
- 스팬 본문을 볼 수 있는 멤버는 PII까지 보므로 (b)의 마스킹이 선행돼야 한다.
- 첫 활성화 시 최대 7일치 기존 로그·트레이스를 백필한다(고객 관리 KMS 키 데이터 제외).
- 제공 리전(2026-10-27 기준 11곳): 버지니아·오레곤·아일랜드·캐나다 중부·뭄바이·싱가포르·시드니·도쿄·프랑크푸르트·런던·상파울루(GA 2026-09-23 3곳 + 2026-10-19 확장 8곳). 미제공 리전의 텔레메트리는 CloudWatch 중앙화 규칙(AWS Organizations 필요)으로 지원 리전에 복제해야 하며, 트레이스 중앙화는 소스 계정마다 Transaction Search가 켜져 있어야 한다. 중앙화는 소급 적용되지 않는다.

### 고객에게 확인할 것
- 외부 사용자가 봐야 하는 것이 메트릭 대시보드인지, 세션/트레이스 본문인지.
- IdP(Okta/Entra/기타)와 MFA 정책이 IAM Identity Center에 연동 가능한지.
- 데이터 거주지(data residency) 요건이 있는지.

## (d) 분석 (트레이싱 대시보드)

"분석"은 CloudWatch의 세 표면 중 어디를 쓰느냐에 따라 범위가 크게 다르다. 사전 구성 뷰(콘솔 GenAI Observability) → 자유 질의(Transaction Search + Logs Insights) → AI 보조 분석·품질 평가(CloudWatch Omni) 순으로 깊어진다.

### 표면별 분석 능력
- **① 콘솔 GenAI Observability (사전 구성, 문서 + 확인)**
  - Model Invocations: 호출 수·토큰·TPM 쿼터 사용률·지연·오류·스로틀·입력 크기 분포(확인: Sonnet 5.5 호출 16건, Total tokens 5,678이 호출 로그 합과 일치). Bedrock 모델 호출만 집계되며, 목록의 Input/Output 열에 원문이 보이므로 (b)의 호출 로그 경로와 연결된다.
  - Bedrock AgentCore 뷰: Agents → Sessions → Traces → Spans 드릴다운, capability/session/trace/span 필터와 시간 범위 선택. 세션 그룹핑과 스팬별 토큰은 정확(확인). Agent/Trace 수준 Total tokens·cost는 Bedrock 호출 기록 기반이라 툴 호출 왕복까지 포함해 정확(확인). 사전 구성 뷰라 필터·시간 범위 외의 커스텀 집계·차트는 불가.
- **② Transaction Search + CloudWatch Logs (자유 질의, 확인)**
  - 스팬이 `aws/spans` 로그 그룹에 100% 저장되므로 Logs Insights로 임의 집계 가능. 예: 세션별 토큰 합("Total tokens 집계 원인 실험" 절의 검증된 쿼리), 툴 호출 빈도, 턴 수 분포, 오류 스팬 추출.
  - 메트릭 필터로 커스텀 메트릭 추출 → CloudWatch 대시보드·알람. Contributor Insights(상위 N 기여자), 로그 이상 탐지, 구독 필터로 외부 전송.
  - 제약: 스팬 변환/보강 불가, 트레이스 요약 인덱싱 기본 1%(목록 뷰에 일부만, 스팬 자체는 전부 저장).
- **③ CloudWatch Omni (AI 보조 분석 + 품질 평가, 문서 + 일부 확인)**
  - 집계 뷰: 에이전트별 토큰·지연·오류·세션·트레이스, 사전 구성 "Agent Overview Dashboard"(확인, `img/cloudwatch-omni.png`). "Top 10 agents" 표의 Tokens 열이 0으로 표시되어 요약 카드(12.9k)와 불일치가 있었다. 커스텀 대시보드는 문서 기준.
  - 자유 질의: 로그·트레이스는 Omni SQL(`traces.default` 등), 메트릭은 PromQL. Omni agent에 자연어로 물으면 쿼리 생성·실행·차트화, 대시보드·알림 생성까지(문서 기준). SQL 질의는 아래 "코딩 에이전트에서 Omni 데이터 가져오기" 절에서 플러그인과 직접 API로 확인.
  - 품질 분석: 엔진은 Bedrock AgentCore Evaluations(스페이스 생성 시 `AgentCoreEvaluationRole` 연결)이고 Omni가 결과를 표시. 내장 평가기(정확성·일관성·툴 선택 등, 문서 기준)와 커스텀 judge 평가기, 온라인 평가(운영 중 지속)와 데이터셋 실험. 평가기는 트레이스 본문을 judge 모델에 보내므로 (b) 마스킹과 충돌 가능.
  - 협업: 스레드(조사 기록), Slack 알림, DevOps Agent 원인 조사(문서 기준).

### 권장 사용처
- 운영 지표(토큰·비용): 에이전트 단위는 콘솔 AgentCore Agent view(Bedrock 호출 기록 기반, 가장 정확), 모델 단위는 Model Invocations. 스팬 기반 Omni·Logs Insights는 툴 호출 왕복 누락에 유의.
- 대화 품질: AgentCore Evaluations(Omni에서 표시·운영) 외에는 CloudWatch 안에 대안이 없음. 마스킹 정책과 함께 설계.
- 임의 분석(특정 툴 실패율, 세션당 턴 수): ② Logs Insights가 가장 유연함.
- 외부 사용자 공유: (c)와 동일하게 Omni 대시보드 또는 Managed Grafana.

## 코딩 에이전트(Claude Code·Cursor)에서 Omni 데이터 가져오기 (2026-10-27 확인)

- **Agent Toolkit for AWS**: Claude Code에서 `/plugin install aws-core@claude-plugins-official` → `/reload-plugins`(CLI: `claude plugin install aws-core@claude-plugins-official`). aws-core 1.1.0은 원격 AWS MCP Server(`uvx mcp-proxy-for-aws-cli` → `https://aws-mcp.us-east-1.api.aws/mcp`)와 25개 skills를 설치하며, `aws-observability` skill 안에 `references/cloudwatch-omni/`(개념·SQL 질의·PromQL·대시보드·알림·평가)와 스크립트가 들어 있다. Cursor/Kiro는 MCP 설정 + `npx skills add aws/agent-toolkit-for-aws/skills`, AWS CLI 2.35+면 `aws configure agent-toolkit`.
- **동작 원리**: skills는 로컬 AWS 자격 증명으로 공개 `cloudwatchomni` API(SigV4, Smithy RPC v2 CBOR)를 호출한다. Omni 웹 로그인이 아니라 IAM 권한 + 스페이스 그랜트 두 겹으로 인가된다. CLI는 `aws cloudwatchomni …`(AWS CLI 2.35+ 또는 최신 boto3 필요).
- **직접 조회 예(`omni_query.py`)**: `traces.default` 테이블에 SQL. 세션 `knox-adk-plain-20261027-052755`로 13개 스팬(3 트레이스)과 `gen_ai.usage.*`, 모델 ID, duration을 가져왔다. 주의: ADK LLM 스팬은 `session.id`가 없고 `gen_ai.conversation.id`에 세션 ID가 있으므로 두 속성을 OR로 묶어야 한다.
  ```sql
  SELECT `@timestamp`, name, scope['name'] AS scope, traceId,
         attributes['session.id'] AS session_id, attributes['gen_ai.conversation.id'] AS conversation_id,
         attributes['gen_ai.request.model'] AS model,
         attributes['gen_ai.usage.input_tokens'] AS in_tok, attributes['gen_ai.usage.output_tokens'] AS out_tok
  FROM traces.default
  WHERE `@timestamp` BETWEEN NOW() - INTERVAL '6 HOUR' AND NOW()
    AND (attributes['session.id'] = '<session>' OR attributes['gen_ai.conversation.id'] = '<session>')
  ORDER BY `@timestamp`
  ```
- **Omni IDE 확장**(VS Code·Kiro·Cursor): 로컬 모드는 `.omni/`에 트레이스 저장(AWS 계정 불필요), 클라우드 모드는 스페이스 로그인. "Analyze with AI" 내장. MCP 서버를 직접 노출하지는 않는다.
- **Omni 없이 스팬만**: awslabs `cloudwatch-applicationsignals-mcp-server`의 `search_transaction_spans`(Logs Insights, `@data_format = "AWS-OTEL-TRACE-V1"`)로 `aws/spans` 조회 가능(Transaction Search 필요).
- PII 주의: 어느 경로든 본문이 마스킹되지 않은 채 코딩 에이전트 컨텍스트로 들어온다. (b)의 캡처 시 마스킹이 선행돼야 한다.

### 플러그인 경로 실제 동작 확인 (Claude Code, 2026-10-27)

`/reload-plugins` 후 `plugin:aws-core:aws-mcp`의 `aws___run_script` 도구가 올라오고, 그 샌드박스 안에서 `call_boto3("cloudwatchomni", "StartTelemetryQuerySession" → "StartTelemetryQuery" → "GetTelemetryQueryResults")`가 로컬 IAM 자격 증명(SigV4)으로 실행된다. 로컬 CLI/boto3 버전과 무관하다(구형 AWS CLI 문제 우회). 결과는 `omni_query.py` 직접 호출과 동일(13 스팬, 같은 토큰 값).

**그대로 입력해 볼 수 있는 프롬프트**

```text
1) 세션 목록
   Omni에서 knox-adk-trace-test 에이전트의 최근 6시간 세션별 트레이스 수, 토큰 합, LLM 지연 평균을 표로 보여줘.
   (session.id 또는 gen_ai.conversation.id 기준)

2) 한 턴의 전체 흐름 (추천)
   세션 knox-adk-plain-20261027-052755 에서 도구를 호출한 턴의 LLM 스팬(scope gcp.vertex.agent) 하나를 골라
   시스템 프롬프트, 사용자 입력, 도구 호출(이름·인자), 도구 결과, 최종 답변, 입력/출력 토큰을 한 표로 정리해줘.

3) PII 마스킹 검증
   같은 세션의 plain 실행과 redact 실행을 비교해, input.value / llm.input_messages.* 가 REDACTED 로 바뀌었는지 스팬별로 보여줘.
```

**프롬프트 2의 결과** (`img/omni-plugin.png`; traceId `6ae0365f4a2a1ceb91537c7d2d5f9144`, spanId `27c805a94af342f0`, `invoke_agent knox_trace_test_agent`, 1,815 ms, us.anthropic.claude-sonnet-5-5). 도구를 호출한 LLM 스팬은 세션에 1개뿐(턴 2)이며, 조회 조건은 `scope['name']='gcp.vertex.agent' AND attributes['gen_ai.conversation.id']='<session>' AND attributes['llm.output_messages.0.message.tool_calls.0.tool_call.function.name'] IS NOT NULL`.

| 항목 | 값 | 속성 키 |
|---|---|---|
| 시스템 프롬프트 | "You are a concise travel helper. Use the get_weather tool when asked about weather. …" + ADK가 덧붙인 에이전트 이름/설명 | `llm.input_messages.0.message.content` (role=system) |
| 사용자 입력 (이번 턴) | "What is the weather like in Seoul right now?" | `llm.input_messages.3.message.contents.0.message_content.text` |
| 대화 이력 (같이 전송됨) | user: "Hi, my name is Gildong Hong and my phone number is 010-1234-5678. …" → model: "Nice to meet you, Gildong! …" | `llm.input_messages.1~2.…` |
| 도구 호출 | `get_weather`, 인자 `{"city": "Seoul"}` | `llm.output_messages.0.message.tool_calls.0.tool_call.function.{name,arguments}` |
| 도구 결과 | `{"city": "Seoul", "temp_c": 14, "condition": "clear"}` | `llm.input_messages.5.message.content` (role=tool) |
| 최종 답변 | "It's currently clear in Seoul with a temperature of 14°C (57°F). Pack light layers for your trip next week, Gildong!" | `llm.output_messages.0.message.contents.0.message_content.text` |
| 토큰 | 입력 692 / 출력 46 | `gen_ai.usage.{input,output}_tokens` |

한 LLM 스팬에 시스템 프롬프트·전체 대화 이력·도구 호출·도구 결과·최종 답변·토큰이 모두 들어 있다(속성 57개). plain 실행이라 PII가 그대로 보이며 redact 실행에서는 같은 필드가 `REDACTED`로 나온다.

**traceId로 조회하면 스팬이 4개가 아니라 9개**: 세션 ID 필터에서는 턴당 OpenInference 스팬 3개 + ADK LLM 스팬 1개(+ TOOL)만 잡히지만, traceId로 조회하면 Anthropic SDK 스팬 `anthropic.messages.create`(scope `com.anthropic.sdk.python`, `aws.genai.span_kind=LLM`) 2개와 httpx `POST` 2개가 더 나온다. 도구 호출 턴은 Bedrock 호출이 2번(도구 호출 요청 → 도구 결과 전달)이고 ADK LLM 스팬은 턴당 1개라 토큰이 마지막 호출분만 기록되는 반면, SDK 스팬은 호출마다 1개다. 이 SDK/httpx 스팬에는 `session.id`·`gen_ai.conversation.id`가 없어 세션 필터에서 빠진다. 세션 기준 토큰 합과 콘솔(Bedrock 호출 기록 집계)의 차이가 여기서 생긴다.
