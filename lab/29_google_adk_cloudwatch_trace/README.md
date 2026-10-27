# Google ADK + Claude on Bedrock → OpenInference → ADOT → CloudWatch (고객 질문 4개 검증)

| 콘솔 GenAI Observability → Bedrock AgentCore (Agents, 12h) | 콘솔 GenAI Observability → Model Invocations (Sonnet 5.5) | CloudWatch Omni → Agent overview | Claude Code + aws-core 플러그인으로 Omni 스팬 조회 |
|---|---|---|---|
| ![AgentCore Observability](img/agentcore-observability.png) | ![Model Invocations](img/bedrock-model-invocation.png) | ![Omni Agent overview](img/cloudwatch-omni.png) | ![Omni via plugin](img/omni-plugin.png) |

고객 질문(on AWS CloudWatch): **(a)** Multi-turn LLM invocation tracing for Google ADK via OpenInference · **(b)** PII masking for OpenInference · **(c)** A dashboard with a separate SSO/MFA login for users without AWS account access · **(d)** Analytics on the tracing dashboard

검증 환경: Google ADK 2.13 + Claude Sonnet 5.5 on Amazon Bedrock(ADK `AnthropicLlm` 네이티브, LiteLLM 없음), OpenInference ADK 1.0.5, ADOT 0.21, 2026-10-27. 실험 기록과 문서 근거는 [DETAILS.md](DETAILS.md).

## (a) ADK 멀티턴 LLM 호출 추적 — 됩니다

> 질문: Multi-turn LLM invocation tracing for Google ADK via OpenInference

**짧은 답**: Google ADK(모델: Claude Sonnet 5.5 on Amazon Bedrock) + `openinference-instrumentation-google-adk` + ADOT(AWS Distro for OpenTelemetry, 스팬을 CloudWatch로 보내는 AWS판 OpenTelemetry SDK) 조합으로 멀티턴 대화가 세션 단위로 CloudWatch에 묶여 추적됩니다. 실제 계정에서 3턴 세션이 콘솔 GenAI Observability(Sessions → Traces 3 → Spans)와 CloudWatch Omni(Agent overview: 세션 10·트레이스 28·토큰 12.9k)에 표시되는 것을 확인했습니다(2026-10-27).

**핵심**
- **구조**: 세션 → 트레이스(턴 1개) → 스팬입니다. 턴마다 OpenInference 스팬 3개(invocation → invoke_workflow → agent_run, 툴 호출 시 execute_tool 추가)와 ADK 내장 LLM 스팬 1개(`invoke_agent`, scope `gcp.vertex.agent`)가 같은 traceId로 묶입니다.
- **구현 포인트**: `Runner.run_async(user_id=, session_id=)`를 키워드 인자로 전달합니다. Python ADOT는 `AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT=true`를 켜야 본문이 스팬에 남습니다. Transaction Search(스팬 100%를 `aws/spans` 로그 그룹에 저장하는 CloudWatch 설정)를 계정·리전에 먼저 활성화해야 스팬이 수신되고 콘솔 뷰가 동작하며, 첫 수집은 10분 이상 지연될 수 있습니다.
- **토큰·비용 집계**: 콘솔 Agent view의 Total tokens·cost는 스팬이 아니라 **Bedrock 모델 호출 기록**으로 계산되며, 호출 로그 합과 정확히 일치합니다(툴 호출 왕복 포함).

**근거**: [DETAILS.md](DETAILS.md) → "동작 흐름", "(a) 멀티턴 추적"(세션 키 두 개: `session.id` / `gen_ai.conversation.id`), "Total tokens 집계 원인 실험", "Bedrock 구성 결과". 스크린샷 `img/agentcore-observability.png`, `img/cloudwatch-omni.png`.

## (b) OpenInference PII 마스킹 — OpenInference 플래그만으로는 부족하고, ADOT 마스킹 + 로그 경로 차단으로 해결됩니다

> 질문: PII masking for OpenInference

**짧은 답**: CloudWatch는 PII를 자동으로 찾아 가리지 않으므로 마스킹은 애플리케이션에서 스팬을 내보내기 전에 끝내야 합니다. OpenInference의 공식 스위치(`OPENINFERENCE_HIDE_INPUTS/OUTPUTS`)는 OpenInference가 만든 스팬만 가리고, ADK가 만든 LLM 스팬의 프롬프트·응답(`llm.input_messages.*`)은 그대로 남습니다. ADOT의 `AWS_REDACT_SPAN_ATTRIBUTES`를 쓰면 출처와 무관하게 모든 스팬에서 해당 속성이 `REDACTED`로 바뀌며, 실제 계정에서 PII 잔존 0을 확인했습니다(2026-10-27).

**핵심**
- **유효한 조합(확인)**: `AWS_REDACT_SPAN_ATTRIBUTES='llm.input_messages.*,llm.output_messages.*,input.value,output.value,gen_ai.input.messages,gen_ai.output.messages'` + `OTEL_LOGS_EXPORTER=none`.
- **같이 막아야 하는 경로 두 곳**: ① ADOT 로그 경로 — ADK가 프롬프트 전문이 든 로그 이벤트를 따로 내보내므로 `OTEL_LOGS_EXPORTER=none`으로 닫습니다. ② Bedrock Model Invocation Logging — 켜져 있으면 모든 호출의 요청·응답 원문이 저장되므로 텍스트 본문 전달을 끄거나 CloudWatch Logs 데이터 보호 정책을 적용합니다.

**근거**: [DETAILS.md](DETAILS.md) → "(b) PII 마스킹"(6개 설정 조합 매트릭스, 효과 없는 설정, 와일드카드 동작, 부분 마스킹 한계, 한국 식별자 커스텀 정규식, 평가 입력 트레이드오프), "ADOT 로그 경로 실험", "Bedrock 구성 결과"(호출 로그 원문 확인). 재현 스크립트 `run.sh masked|redact`, `run_q2b.sh`, `verify_q2b.py`.

## (c) AWS 계정 없는 사용자를 위한 별도 SSO/MFA 로그인 대시보드 — CloudWatch Omni가 가장 가깝습니다

> 질문: A dashboard with a separate SSO/MFA login for users without AWS account access

**짧은 답**: 기존 CloudWatch 대시보드 공유 기능은 메트릭 위젯 중심이고 세션/트레이스 뷰를 공유할 수 없어 요구에 맞지 않습니다. CloudWatch Omni는 조직 전용 URL(`https://<domain>.cloudwatch-omni.global.app.aws`)에 IAM Identity Center(외부 IdP·MFA 연동)로 로그인하며 AWS 콘솔 접근이 필요 없고, 실제 스페이스에서 ADK 에이전트의 세션·트레이스·토큰이 집계되는 것을 확인했습니다(2026-10-27). 아일랜드(eu-west-1)는 Omni 제공 리전입니다.

**핵심**
- **Omni 권한 모델**: 사용자별 Viewer/Editor/Space Admin/Custom 그랜트와 행 단위 데이터 스코프로 외부 사용자가 자기 에이전트 데이터만 보게 제한할 수 있습니다.
- **대안**: Omni를 쓰지 않는 경우 Amazon Managed Grafana(SAML/IAM Identity Center 로그인)로 CloudWatch·X-Ray 데이터 소스 대시보드를 직접 구성합니다.

**근거**: [DETAILS.md](DETAILS.md) → "(c) SSO/MFA 대시보드"(후보 4개 비교표: 대시보드 공유 이메일/SAML·Omni·Managed Grafana, Omni 설계 포인트, 제공 리전 목록, 과금 기준, 고객 확인 질문). 스크린샷 `img/cloudwatch-omni.png`.

## (d) 트레이싱 대시보드에서의 분석 — 세 표면이 역할이 다르며, 코딩 에이전트에서도 같은 데이터를 질의할 수 있습니다

> 질문: Analytics on the tracing dashboard

**짧은 답**: CloudWatch에는 트레이스를 분석하는 표면이 세 가지 있고 깊이가 다릅니다. 콘솔 GenAI Observability는 사전 구성 뷰(모델별 호출·토큰·지연, 에이전트 → 세션 → 트레이스 → 스팬 드릴다운), Transaction Search + Logs Insights는 스팬 전량에 대한 자유 질의, CloudWatch Omni는 SQL/PromQL 질의와 AI 보조 분석, 그리고 Bedrock AgentCore Evaluations 기반 대화 품질 평가까지 제공합니다. ADK 에이전트로 세 표면 모두 동작을 확인했습니다(2026-10-27). 또한 Claude Code + aws-core 플러그인(Agent Toolkit for AWS)으로 Omni SQL을 실행해 한 LLM 스팬에서 시스템 프롬프트·사용자 입력·툴 호출·툴 결과·최종 답변·토큰을 한 번에 가져올 수 있습니다(스크린샷 `img/omni-plugin.png`).

**핵심**
- **운영 지표(토큰·비용·지연·오류)**: 에이전트 단위는 콘솔 Agent view(Bedrock 호출 기록 기반, 가장 정확), 모델 단위는 Model Invocations 뷰를 씁니다.
- **임의 분석(툴 실패율, 세션당 턴 수 등)**: Logs Insights(`aws/spans`) 또는 Omni SQL(`traces.default`)로 집계하며, 메트릭 필터로 커스텀 메트릭·알람을 만들 수 있습니다.
- **대화 품질**: Omni의 AgentCore Evaluations(내장 평가기 + 커스텀 judge, 온라인 평가)가 CloudWatch 안의 유일한 수단이며, (b)의 마스킹 정책과 함께 설계해야 합니다.

**근거**: [DETAILS.md](DETAILS.md) → "(d) 분석"(표면별 능력 비교, Logs Insights 검증 쿼리, Omni 집계 결과와 Top 10 표 불일치), "코딩 에이전트에서 Omni 데이터 가져오기"(프롬프트 3개, 한 스팬 결과 표, traceId 조회 시 SDK 스팬 9개 발견). 스크린샷 `img/bedrock-model-invocation.png`, `img/cloudwatch-omni.png`, `img/omni-plugin.png`.

## 빠른 시작

사전 조건: AWS 자격 증명(Claude Sonnet 5.5 모델 액세스), 해당 리전에 CloudWatch Transaction Search 활성화. API 키 파일은 필요 없다.

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt

./run.sh plain          # 마스킹 없음
./run.sh masked         # OPENINFERENCE_HIDE_INPUTS/OUTPUTS=True
./run.sh redact         # masked + AWS_REDACT_SPAN_ATTRIBUTES (ADOT)
.venv/bin/python verify.py --session-id <run.sh가 출력한 session_id>

./run_q2b.sh adot-redact | extract | adk-nocontent     # (b) 추가 실험
.venv/bin/python verify_q2b.py --session-id <session_id>
.venv/bin/python omni_query.py --session-id <session_id>   # CloudWatch Omni API로 스팬 조회
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `agent.py` | ADK 에이전트(툴 1개) + 3턴 대화. 턴 1에 가짜 PII(이름·전화번호) 포함. 모델은 ADK `AnthropicLlm` + Anthropic SDK → `bedrock-runtime/anthropic`(Anthropic Messages API, 단기 Bedrock 토큰) |
| `run.sh` | ADOT(`opentelemetry-instrument`)로 실행. 모드: `plain` / `masked` / `redact` |
| `verify.py` | `aws/spans` 로그 그룹을 Logs Insights로 조회해 세션별 스팬·마스킹 상태 출력 |
| `run_q2b.sh` | Q2(b) 추가 실행 전용. `adot-redact`(ADOT 삭제만, OpenInference 플래그 없음) / `extract`(ADOT 기본 본문 분리 경로, 로그 exporter on) / `adk-nocontent`(`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`) |
| `omni_query.py` | CloudWatch Omni 공개 API(`cloudwatchomni`: StartTelemetryQuerySession → StartTelemetryQuery(SQL) → GetTelemetryQueryResults)로 스팬을 조회. Omni skills/코딩 에이전트가 쓰는 경로와 동일 |
| `verify_q2b.py` | 스팬별 본문 속성의 **원시 값**과 에이전트 로그 그룹의 로그 이벤트를 출력(`__REDACTED__` vs `REDACTED` 구분용) |

## 상세 문서 (DETAILS.md)

1. [동작 흐름](DETAILS.md#동작-흐름) — 파이프라인, 세션→트레이스→스팬 트리, 모드별 차이(ASCII)
2. [(a) 멀티턴 추적](DETAILS.md#a-멀티턴-추적) — 스팬 출처 두 종류, 버전 의존성, 콘솔 확인, Total tokens 집계 원인 실험(가설 5개)과 검증 쿼리
3. [(b) PII 마스킹](DETAILS.md#b-pii-마스킹) — 설정 조합 6개 매트릭스, ADOT 로그 경로 실험, 효과 없는 설정과 한계
4. [Bedrock 구성 결과](DETAILS.md#bedrock-구성-결과-2026-10-27-adk-213--anthropicllm--bedrock-runtime) — ADK + AnthropicLlm 네이티브 경로, 공급자 라벨 버그, 호출 로그 원문
5. [(c) SSO/MFA 대시보드](DETAILS.md#c-ssomfa-대시보드-aws-계정-없는-사용자) — 후보 4개 비교, Omni 설계 포인트, 제공 리전
6. [(d) 분석](DETAILS.md#d-분석-트레이싱-대시보드) — 세 표면 비교, 권장 사용처
7. [코딩 에이전트에서 Omni 데이터 가져오기](DETAILS.md#코딩-에이전트claude-codecursor에서-omni-데이터-가져오기-2026-10-27-확인) — Agent Toolkit 플러그인, 프롬프트 3개, 한 스팬 결과 표
8. [세션 ID 기록](DETAILS.md#세션-id-기록)
