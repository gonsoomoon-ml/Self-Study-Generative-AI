# AWS Bedrock Mantle 기능 정리

## 개요

Amazon Bedrock는 두 개의 병렬 추론 엔드포인트를 제공한다:

| 엔드포인트 | URL 형식 | 지원 API | Invocation Logging |
|-----------|----------|----------|-------------------|
| `bedrock-runtime` (레거시) | `bedrock-runtime.{region}.amazonaws.com` | InvokeModel, Converse, Chat Completions, Messages | ✅ 지원 |
| `bedrock-mantle` (신규) | `bedrock-mantle.{region}.api.aws` | Responses API, Chat Completions, Messages | ❌ 미지원 |

## 핵심 사항

1. **Invocation Logging은 현재 `bedrock-runtime` 엔드포인트에서만 지원된다.**
   - 지원 대상: Converse, ConverseStream, InvokeModel, InvokeModelWithResponseStream
   - `bedrock-mantle` 엔드포인트(Responses API 등)는 아직 로깅 미지원

2. **Claude Opus 4.8은 두 엔드포인트 모두에서 사용 가능하다.**
   - `bedrock-runtime`: InvokeModel, Converse API 통해 호출
   - `bedrock-mantle`: Messages API, Responses API 통해 호출
   - 모델 ID: `anthropic.claude-opus-4-8`

3. **두 엔드포인트는 독립적으로 동작한다.**
   - `bedrock-mantle`는 `bedrock-runtime`의 번역 계층이 아님
   - 각각 별도의 API 표면을 제공하는 병렬 서비스임
   - Anthropic SDK는 `AnthropicBedrockMantle` 전용 클라이언트 클래스 제공

## 로깅이 필요한 경우의 권장 사항

Invocation Logging이 필요하면 `bedrock-runtime` 엔드포인트의 InvokeModel 또는 Converse API를 직접 사용할 것.

## 참고 자료

- [AWS Bedrock 엔드포인트 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)
- [Model Invocation Logging 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [Claude Opus 4.8 모델 카드](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-8.html) 