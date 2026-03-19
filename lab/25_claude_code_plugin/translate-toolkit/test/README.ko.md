# 에이전트 런타임 개요

에이전트 런타임은 내장된 옵저버빌리티와 가드레일을 갖춘 AI 기반 애플리케이션을 구축하기 위한 경량 프레임워크입니다.

## 기능

- **플러그인 시스템**: 슬래시 커맨드와 커스텀 스킬을 사용하여 기능을 확장합니다
- **프롬프트 캐싱**: 자동 프롬프트 캐싱으로 지연 시간과 비용을 절감합니다
- **훅 통합**: 파일 변경 시 자동화된 워크플로우를 트리거합니다
- **파인튜닝 지원**: 도메인 특화 작업을 위해 사후학습 모델을 커스터마이즈합니다

## 빠른 시작

```bash
npm install agent-runtime
export CLAUDE_CODE_USE_BEDROCK=1
```

```javascript
const { AgentRuntime } = require('agent-runtime');

const agent = new AgentRuntime({
  model: 'claude-sonnet-4-6',
  region: 'us-west-2'
});

agent.run('Translate this document to Korean');
```

## 구성

| 매개변수 | 타입 | 기본값 | 설명 |
|-----------|------|---------|-------------|
| `model` | string | `claude-sonnet-4-6` | 사용할 모델 ID |
| `region` | string | `us-west-2` | AWS 리전 |
| `enableGuardrails` | boolean | `true` | 콘텐츠 가드레일 활성화 |
| `cacheEnabled` | boolean | `true` | 프롬프트 캐싱 활성화 |

## 아키텍처

에이전트 런타임은 모델 추론을 위해 Amazon Bedrock에 연결됩니다. 모든 플러그인 정의(스킬, 커맨드, 훅)는 클라이언트 측에서 로컬로 실행됩니다. 모델 추론 요청만 Bedrock API 엔드포인트로 전송됩니다.

> **참고**: 배포 전에 IAM 역할에 `bedrock:InvokeModel` 권한이 있는지 확인하세요.

자세한 내용은 [API 문서](https://example.com/docs)를 참조하거나 Slack의 `#agent-runtime` 채널로 팀에 문의하세요.
