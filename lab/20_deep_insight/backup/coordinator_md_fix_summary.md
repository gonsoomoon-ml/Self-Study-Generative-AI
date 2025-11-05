# coordinator.md 파일 누락 문제 해결 완료! 🎉

## 문제 발견
VPC Runtime을 배포했지만 실행 시 다음 에러 발생:
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/src/prompts/coordinator.md'
```

## 근본 원인 분석

### 1단계: Dockerfile 확인
- Dockerfile은 `COPY . .`로 모든 파일을 복사하므로 문제없음
- .dockerignore에 `#*.md` (주석 처리됨)로 .md 파일을 제외하지 않음

### 2단계: Toolkit의 dockerignore.template 발견! 🔍
CodeBuild 로그에서 발견:
```
Using dockerignore.template with 45 patterns for zip filtering
```

Toolkit이 자체 템플릿을 사용하여 source.zip을 생성!

**문제의 템플릿 내용**:
```dockerignore
# Documentation
docs/
*.md          ← 모든 .md 파일 제외!
!README.md    ← README.md만 포함
```

### 3단계: 파일 필터링 과정 이해

```
[로컬 소스 코드]
    ↓
[Toolkit의 dockerignore.template 적용]
    ↓ (*.md 파일들 제외, README.md만 포함)
[source.zip 생성 및 S3 업로드]
    ↓
[CodeBuild에서 다운로드]
    ↓
[Docker 빌드: COPY . .]
    ↓ (이미 source.zip에 없는 파일은 복사 불가!)
[Docker 이미지]
    ✗ coordinator.md 누락!
```

## 해결 방법

### 시도 1: 로컬 .dockerignore 수정 ❌
```dockerignore
*.md
!README.md
!src/prompts/*.md  ← 추가
```
**결과**: 실패! Toolkit이 자체 템플릿을 사용하므로 효과 없음

### 시도 2: Toolkit의 dockerignore.template 수정 ✅
**파일 경로**:
```
setup/.venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/
utils/runtime/templates/dockerignore.template
```

**수정 내용**:
```dockerignore
# Documentation
docs/
*.md
!README.md
!src/prompts/*.md  ← 이 줄 추가!
```

**결과**: 성공! 패턴 수가 45 → 46개로 증가

## 검증 결과

### 이전 Runtime (실패):
```
ERROR:strands.multiagent.graph:node_id=<coordinator>, error=<[Errno 2] No such file or directory: '/app/src/prompts/coordinator.md'>
```

### 수정 후 Runtime (성공!):
```
INFO:src.graph.nodes:[92m===== Coordinator started =====[0m
INFO:src.utils.strands_sdk_utils:[92mCOORDINATOR - Prompt Cache Disabled[0m
INFO:src.graph.nodes:[92m===== Coordinator completed =====[0m
```

**FileNotFoundError 없음!** 🎉

## 최종 Runtime 정보

- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-east-1:057716757052:runtime/bedrock_manus_runtime_vpc_test_1762215333-oowQa44mRP`
- **상태**: READY & OPERATIONAL ✅
- **Network Mode**: VPC
- **Coordinator Node**: 정상 작동 ✅
- **langchain Import**: 정상 (langchain_core.callbacks) ✅

## 교훈

1. **Toolkit의 숨겨진 동작**: `bedrock_agentcore_starter_toolkit`은 자체 dockerignore.template을 사용하여 source.zip을 생성합니다.

2. **로컬 .dockerignore의 한계**: 프로젝트의 .dockerignore는 Docker 빌드 시에만 적용되며, Toolkit의 source.zip 생성 과정에는 영향을 주지 않습니다.

3. **올바른 해결 방법**: Toolkit의 템플릿을 수정하거나, 향후 버전에서는 configure() 파라미터로 추가 패턴을 지정할 수 있기를 기대합니다.

## 다음 단계

이제 VPC Runtime이 완전히 작동하므로:
1. ✅ 전체 워크플로우 테스트 (CSV 분석 → PDF 보고서)
2. ✅ Production 계정 배포 준비
3. ✅ 문서화 및 가이드 작성

---

**작업 완료 시간**: 2025-11-04 00:23 UTC
**소요 시간**: 약 20분 (문제 분석 + 해결 + 검증)
