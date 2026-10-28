# 상세 근거 — Google ADK + Claude on Bedrock → OpenInference → ADOT → CloudWatch

[README.md](README.md)의 질문별 답을 뒷받침하는 검증 기록과 문서 근거다. 검증 환경: Google ADK 2.13.0 + Claude Sonnet 5.5 on Amazon Bedrock(ADK `AnthropicLlm` 네이티브, LiteLLM 없음), openinference-instrumentation-google-adk 1.0.5, aws-opentelemetry-distro 0.21.0, 2026-10-27.

목차: [동작 흐름](#동작-흐름) · [(a) 멀티턴 추적](#a-멀티턴-추적) · [(b) PII 마스킹](#b-pii-마스킹) · [Bedrock 구성](#bedrock-구성-adk--anthropicllm--bedrock-runtime) · [(c) SSO/MFA 대시보드](#c-ssomfa-대시보드) · [(d) 분석](#d-분석) · [코딩 에이전트에서 Omni 질의](#코딩-에이전트에서-omni-질의)

## 동작 흐름

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

한 세션이 CloudWatch에 쌓이는 모양(턴 1개 = 트레이스 1개):

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

## (a) 멀티턴 추적

- 세 턴 모두 `aws/spans`에 도착하고, 턴 = 트레이스 1개, 3개 트레이스가 같은 세션으로 묶인다. 콘솔 GenAI Observability → Bedrock AgentCore → Agents → Sessions view에 **Traces (3)** 으로 표시되고, 트레이스 상세에서 ADK LLM 스팬이 `aws.genai.span_kind = LLM`으로 인식되어 Model / Input tokens / Output tokens가 표시된다.
- **스팬 출처가 두 종류다.** `openinference.instrumentation.google_adk`(invocation → invoke_workflow → agent_run → execute_tool, 모두 `session.id` 보유)와 ADK 2.x 내장 추적 `gcp.vertex.agent`(`invoke_agent` LLM 스팬, 토큰과 프롬프트 전문 보유, `session.id` 없음). ADK LLM 스팬의 `llm.input_messages.*` 등 OpenInference 속성은 OpenInference ADK 1.0.5가 ADK의 `trace_call_llm` 훅을 패치해 ADK 스팬 위에 직접 써 넣는 것이며, 마스킹 트레이서(OITracer)를 거치지 않는다.
- **세션 키가 두 개**: OpenInference 스팬은 `session.id`, ADK LLM 스팬은 `gen_ai.conversation.id`. 조회·집계 시 두 속성을 OR로 묶어야 LLM 스팬이 빠지지 않는다. `session.id`는 `Runner.run_async(user_id=..., session_id=...)` 키워드 인자에서만 추출된다.
- **버전 의존성**: AWS AgentCore 문서(OpenInference ADK 0.1.x)는 `call_llm` LLM 스팬이 OpenInference scope로 나온다고 예시하지만, ADK 2.13 + OpenInference ADK 1.0.5에서는 LLM 스팬이 ADK 내장 scope에서만 나온다. 어떤 마스킹 플래그가 유효한지가 버전 쌍에 따라 달라지므로 실제 버전으로 재검증이 필요하다.
- 첫 수집은 10분 이상 지연될 수 있다(유실 아님).

### Total tokens 집계 방식

- **콘솔 Agent view의 Total tokens·cost는 스팬이 아니라 Bedrock 모델 호출 기록에서 계산된다.** Agents 표의 값(5.7K / $0.016, 7K / $0.009)이 Bedrock 호출 로그의 토큰 합(Sonnet 5.5 8건 5,678, Haiku 4.5 8건 6,960)과 일치한다. 화면: `img/agentcore-observability.png`.
- **스팬 합산은 툴 호출 턴에서 과소 집계된다.** ADK LLM 스팬은 턴당 1개라 툴 호출 왕복(두 번째 모델 호출)의 토큰을 빠뜨린다(스팬 합 Sonnet 4,341 vs 호출 기록 5,678). Logs Insights·Omni 등 스팬 기반 경로는 이 차이를 감안한다.
- **CloudWatch Omni도 ADK 토큰을 집계한다.** Agent overview에 Sessions 10, Traces 28, Total tokens 12.9k로 표시됐다(`img/cloudwatch-omni.png`). "Top 10 agents" 표의 Tokens 열은 0으로 나와 요약 카드와 불일치가 있었다.
- Logs Insights로 세션별 토큰을 합산할 때는 `gen_ai.conversation.id`로 필터한다(`session.id` 필터는 LLM 스팬을 놓쳐 0/null).
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

## (b) PII 마스킹

| 모드 | OpenInference 스팬 (CHAIN/AGENT/TOOL) | ADK 내장 LLM 스팬 (`gcp.vertex.agent`) |
|---|---|---|
| plain | 원문 저장 | 원문 저장 (이름·전화번호 그대로) |
| masked (`OPENINFERENCE_HIDE_*`) | `__REDACTED__` | **원문 그대로 남음** |
| redact (+ `AWS_REDACT_SPAN_ATTRIBUTES`) | `REDACTED` | `REDACTED` |
| adot-redact (`AWS_REDACT_SPAN_ATTRIBUTES`만, `run_q2b.sh`) | `REDACTED` (`invocation`·`execute_tool`의 `input.value`) | `REDACTED` (`input.value`, `llm.input_messages.*`) |
| extract (ADOT 기본 본문 분리, `run_q2b.sh`) | 본문 제거됨(`input.value`/`output.value` → 로그 이벤트로 이동) | **PII 잔존**: 중첩형 `llm.input_messages.N.message.contents.0.message_content.text`는 분리 대상 아님 |
| adk-nocontent (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, `run_q2b.sh`) | 원문(변화 없음) | **PII 잔존** (속성을 쓰는 주체가 ADK가 아니라 OpenInference 래퍼) |

- **결론**: OpenInference 플래그만으로는 부족하다. ADOT `AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,gen_ai.input.messages,gen_ai.output.messages'` **단독**으로 두 출처의 스팬이 모두 가려진다(17 스팬 중 PII 잔존 0). 와일드카드가 중첩 키까지 잡는다.
- **로그 경로는 별도로 막아야 한다.** `AGENT_OBSERVABILITY_ENABLED=true`면 ADOT가 로그 exporter를 켜고 ADK가 프롬프트·응답 전문이 든 `gen_ai.client.inference.operation.details` 로그 이벤트를 낸다. `AWS_REDACT_SPAN_ATTRIBUTES`는 스팬 프로세서라 이 이벤트에는 작용하지 않는다(확인: redact 상태에서도 ADK 이벤트 4건이 PII 포함으로 로그 그룹 도착). `OTEL_LOGS_EXPORTER=none`으로 끄거나, 로그 그룹을 격리해 CloudWatch Logs 데이터 보호 정책을 적용한다.
- **ADOT 기본 본문 분리(extract)만으로는 부족하다.** ADOT LLO 핸들러는 `input.value`, `llm.input_messages.{i}.message.content` 등 정해진 키만 로그로 옮기며, ADK 스팬의 중첩 키 `llm.input_messages.{i}.message.contents.{j}.message_content.text`는 대상이 아니라 PII가 남는다. 함정: `x-aws-log-stream`에 적은 로그 스트림을 ADOT가 만들어 주지 않아 없으면 `400`으로 조용히 실패하므로 미리 생성한다.
- **효과 없는 설정**: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`(속성을 쓰는 주체가 OpenInference 래퍼라 무효), `OPENINFERENCE_HIDE_*`(OpenInference 스팬만).
- **한계**: 속성 단위 전체 삭제라 부분 마스킹(전화번호만)은 커스텀 SpanProcessor 또는 OpenTelemetry Collector redaction 프로세서가 필요하다. CloudWatch Logs 데이터 보호 정책은 정책 이후 수집분만 마스킹하고 `logs:Unmask` 권한자만 원문을 보며, 관리형 식별자에 한국 항목(주민등록번호·휴대폰)이 없어 커스텀 정규식으로 정의한다. 스팬 본문을 지우면 트레이스 기반 품질 평가(AgentCore Evaluations)의 입력이 사라진다.

## Bedrock 구성 (ADK + AnthropicLlm → bedrock-runtime)

ADK Python에는 Bedrock 전용 모델 클래스가 없고 레지스트리의 `bedrock/*`는 LiteLLM으로만 연결된다. Bedrock이 `bedrock-runtime` 엔드포인트에서 Anthropic Messages API(`/anthropic`)를 네이티브로 제공하므로, ADK 내장 `AnthropicLlm`에 `AsyncAnthropic(base_url=…/anthropic, api_key=<단기 Bedrock 토큰>)` 클라이언트를 주입하면 LiteLLM·LangChain 없이 Claude on Bedrock을 호출할 수 있다(ADK 문서에 Bedrock 예시가 없는 비공식 조합이며 각 부분은 ADK·Bedrock 문서로 뒷받침된다). 단기 토큰은 `aws-bedrock-token-generator`가 AWS 자격 증명에서 만든다(최대 12시간).

| 실행 | 모델 | 스팬 | OpenInference 스팬 PII | ADK LLM 스팬 PII | LLM 토큰(in→out) |
|---|---|---|---|---|---|
| Haiku plain | Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) | 13 | 4/10 원문 | 3/3 원문 | 923→34, 863→38, 699→65 |
| Haiku redact | Haiku 4.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 938→34, 875→41, 699→77 |
| Sonnet plain | Sonnet 5.5 (`us.anthropic.claude-sonnet-5-5`) | 13 | 6/10 원문 | 3/3 원문 | 766→42, 692→46, 551→41 |
| Sonnet redact | Sonnet 5.5 | 13 | 0 (`REDACTED` 7) | 0 (`REDACTED` 3) | 791→38, 711→52, 551→60 |

- 스팬 트리·세션 그룹핑·마스킹 동작은 모델과 무관하게 동일하다(`trace_call_llm` 훅이 모델 클래스와 무관).
- **공급자 라벨 오류**: `gen_ai.request.model`은 Bedrock 모델 ID로 정확하지만 `gen_ai.provider.name=gcp.gemini`, `llm.provider=google`로 고정 기록된다. 공급자별 집계·비용 산정에서 Bedrock 호출이 Google로 분류될 수 있다.
- **Bedrock Model Invocation Logging**: 켜져 있으면 모든 호출의 요청·응답 본문이 `/aws/bedrock/model-invocation-logs`에 저장되고, 콘솔 GenAI Observability → Model Invocations 목록의 Input/Output 열에 원문이 표시된다(redact 세션 포함, `img/bedrock-model-invocation.png`). 스팬 마스킹은 여기에 영향이 없으므로 텍스트 본문 전달을 끄거나 계정 단위 CloudWatch Logs 데이터 보호 정책을 적용한다. Model Invocations의 Total tokens 5,678은 Sonnet 호출 8건의 합과 일치한다.

## (c) SSO/MFA 대시보드

기존 CloudWatch 대시보드 공유로는 요구를 충족하기 어렵고 CloudWatch Omni가 가장 가까운 답이다. 고객 리전(아일랜드 eu-west-1)은 Omni 제공 리전에 포함된다.

| 후보 | 로그인 | MFA | AWS 콘솔 접근 | 트레이스/세션 뷰 | 권한 분리 | 제약 |
|---|---|---|---|---|---|---|
| CloudWatch 대시보드 공유(이메일) | Cognito 사용자 풀, 비밀번호 | 문서에 언급 없음 | 불필요 | 불가(메트릭 위젯 중심, Logs 위젯은 기본 숨김) | 대시보드 단위 | 최대 5명. 공유 대상 전원이 계정의 모든 메트릭·EC2 태그 조회 권한을 받음 |
| CloudWatch 대시보드 공유(SAML SSO) | Cognito + SAML IdP | IdP 정책 | 불필요 | 불가 | 계정 내 모든 대시보드가 SSO 사용자 전원에게 열림 | 세분화 불가. GenAI 콘솔의 Sessions/Traces 페이지는 공유 대상 아님 |
| CloudWatch Omni | 조직 전용 URL `https://<domain>.cloudwatch-omni.global.app.aws`, IAM Identity Center(Okta·Entra 등 외부 IdP 연동) | IAM Identity Center/IdP 정책으로 강제 | 불필요 | 가능. 실제 스페이스에서 ADK 에이전트가 Agent overview에 세션 10·트레이스 28·토큰 12.9k로 집계됨(확인). 세션/트레이스 상세 뷰와 Omni 대시보드는 문서 기준 | Viewer/Editor/Space Admin/Custom 그랜트 + 데이터 스코프(행 단위) | 스페이스 = 계정+리전 단위. IAM Identity Center 인스턴스가 도메인과 같은 리전이어야 함(멀티리전 복제로 해결). 과금은 좌석이 아닌 데이터량(수집·저장·스캔 GB) 기준 |
| Amazon Managed Grafana | SAML 2.0 또는 IAM Identity Center | IdP 정책 | 불필요 | 직접 구성(CloudWatch·X-Ray 데이터 소스) | 사용자/팀별 폴더·대시보드 권한 | GenAI 전용 세션/트레이스 뷰 없음. 직접 만들어야 함 |

- Omni 설계: 도메인(로그인 URL·IdP 연결) 1개 아래 스페이스를 팀/환경별로 두고, 외부 사용자는 Viewer 그랜트 + 데이터 스코프로 자기 에이전트 행만 보게 제한한다. 데이터 스코프는 로그·트레이스 행만 거르므로 Custom 그랜트로 데이터셋/내보내기/AI 기능 액션도 함께 제한한다. 스팬 본문을 볼 수 있는 멤버는 PII까지 보므로 (b)의 마스킹이 선행돼야 한다.
- 제공 리전(2026-10-27 기준 11곳): 버지니아·오레곤·아일랜드·캐나다 중부·뭄바이·싱가포르·시드니·도쿄·프랑크푸르트·런던·상파울루. 미제공 리전 데이터는 CloudWatch 중앙화 규칙(AWS Organizations 필요)으로 지원 리전에 복제한다.
- 확인할 것: 외부 사용자가 봐야 하는 것이 메트릭 대시보드인지 세션/트레이스 본문인지, IdP(Okta/Entra 등)·MFA 정책이 IAM Identity Center에 연동 가능한지.

## (d) 분석

| 표면 | 성격 | 할 수 있는 것 | 제약 |
|---|---|---|---|
| 콘솔 GenAI Observability | 사전 구성 뷰 | Model Invocations(호출 수·토큰·TPM 쿼터·지연·오류·스로틀), Bedrock AgentCore(Agents → Sessions → Traces → Spans 드릴다운, 필터·시간 범위). 토큰·비용은 Bedrock 호출 기록 기반으로 가장 정확 | 커스텀 집계·차트 불가. Model Invocations는 Bedrock 호출만 |
| Transaction Search + Logs Insights | 자유 질의 | `aws/spans`에 스팬 100% 저장. 세션별 토큰 합, 툴 호출 빈도, 턴 수 분포, 오류 스팬 추출. 메트릭 필터 → 커스텀 메트릭·알람, Contributor Insights, 구독 필터 | 스팬 변환/보강 불가. 트레이스 요약 인덱싱 기본 1%(목록 뷰만 영향) |
| CloudWatch Omni | AI 보조 분석 + 품질 평가 | 에이전트별 토큰·지연·오류·세션 집계 뷰(확인). Omni SQL(로그·트레이스)/PromQL(메트릭), 자연어 질의 → 쿼리·차트·대시보드·알림 생성. Bedrock AgentCore Evaluations 기반 품질 평가(내장·커스텀 judge, 온라인 평가). 스레드·Slack 알림 | 평가기는 트레이스 본문을 judge 모델에 보내므로 (b) 마스킹과 충돌 가능 |

권장: 운영 지표(토큰·비용)는 콘솔 Agent view(에이전트 단위)와 Model Invocations(모델 단위), 임의 분석은 Logs Insights, 대화 품질은 Omni의 AgentCore Evaluations(CloudWatch 안의 유일한 수단), 외부 사용자 공유는 (c)와 같이 Omni 또는 Managed Grafana.

## 코딩 에이전트에서 Omni 질의

- **Agent Toolkit for AWS**: Claude Code에서 `/plugin install aws-core@claude-plugins-official` → `/reload-plugins`. aws-core 플러그인은 원격 AWS MCP Server(`aws-mcp`)와 skills(`aws-observability` 안에 `references/cloudwatch-omni/`)를 설치한다. Cursor/Kiro는 MCP 설정 + `npx skills add aws/agent-toolkit-for-aws/skills`.
- **동작 원리**: 로컬 AWS 자격 증명으로 공개 `cloudwatchomni` API(StartTelemetryQuerySession → StartTelemetryQuery(SQL) → GetTelemetryQueryResults)를 호출한다. Omni 웹 로그인이 아니라 IAM 권한 + 스페이스 그랜트로 인가된다. `omni_query.py`가 같은 API를 직접 호출하는 예다.
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

**프롬프트 2의 결과** (`img/omni-plugin.png`): 도구를 호출한 턴의 ADK LLM 스팬 하나에 시스템 프롬프트·전체 대화 이력·도구 호출·도구 결과·최종 답변·토큰이 모두 들어 있다. plain 실행이라 PII가 그대로 보이며 redact 실행에서는 같은 필드가 `REDACTED`로 나온다.

| 항목 | 값 | 속성 키 |
|---|---|---|
| 시스템 프롬프트 | "You are a concise travel helper. Use the get_weather tool when asked about weather. …" + ADK가 덧붙인 에이전트 이름/설명 | `llm.input_messages.0.message.content` (role=system) |
| 사용자 입력 (이번 턴) | "What is the weather like in Seoul right now?" | `llm.input_messages.3.message.contents.0.message_content.text` |
| 대화 이력 (같이 전송됨) | user: "Hi, my name is Gildong Hong and my phone number is 010-1234-5678. …" → model: "Nice to meet you, Gildong! …" | `llm.input_messages.1~2.…` |
| 도구 호출 | `get_weather`, 인자 `{"city": "Seoul"}` | `llm.output_messages.0.message.tool_calls.0.tool_call.function.{name,arguments}` |
| 도구 결과 | `{"city": "Seoul", "temp_c": 14, "condition": "clear"}` | `llm.input_messages.5.message.content` (role=tool) |
| 최종 답변 | "It's currently clear in Seoul with a temperature of 14°C (57°F). Pack light layers for your trip next week, Gildong!" | `llm.output_messages.0.message.contents.0.message_content.text` |
| 토큰 | 입력 692 / 출력 46 | `gen_ai.usage.{input,output}_tokens` |

- **traceId로 조회하면 스팬이 턴당 4개가 아니라 9개다.** Anthropic SDK 스팬 `anthropic.messages.create` 2개와 httpx `POST` 2개가 더 나오며, 이들은 `session.id`·`gen_ai.conversation.id`가 없어 세션 필터에서 빠진다. 툴 호출 턴의 Bedrock 호출 2번이 SDK 스팬에는 각각 기록되므로, 세션 기준 토큰 합과 콘솔(호출 기록 집계)의 차이가 여기서 생긴다.
- PII 주의: 어느 경로든 본문이 마스킹되지 않은 채 코딩 에이전트 컨텍스트로 들어온다. (b)의 캡처 시 마스킹이 선행돼야 한다.
