# Claude Code Plugin: Translate Toolkit

Claude Code 플러그인 시스템을 활용한 다국어 번역 플러그인 구현 실습

## 개요

Claude Code의 플러그인 시스템을 사용하여 **비개발자도 사용 가능한** 다국어 번역 도구를 구축했습니다.
플러그인은 마크다운(.md) 파일과 JSON 설정으로만 구성되며, 코딩이 필요하지 않습니다.

## 제안서

- `Claude_Code_Plugin_Proposal_Bedrock.docx` — 전체 제안서 (Amazon Bedrock 기반)

## 플러그인 구조

```
translate-toolkit/
├── .claude-plugin/
│   └── plugin.json                          # 플러그인 메타데이터 (필수)
├── commands/                                # [루트 레벨] 슬래시 커맨드
│   ├── translate.md                         # /translate — 인라인 텍스트 번역
│   ├── translate-file.md                    # /translate-file — 파일 단위 번역
│   └── glossary.md                          # /glossary — 용어집 관리
├── skills/                                  # [루트 레벨] AI 자동 참조 지식
│   └── translation-context/
│       └── SKILL.md                         # 번역 도메인 지식 (자동 참조)
├── agents/                                  # [루트 레벨] 서브에이전트
│   └── review-translator.md                 # @review-translator — 번역 품질 리뷰
├── hooks/                                   # [루트 레벨] 이벤트 트리거
│   ├── hooks.json                           # 파일 수정 시 번역 누락 경고
│   └── check-translation.sh                 # 훅 실행 스크립트
├── glossary/
│   └── terms.json                           # 프로젝트 전용 용어집 (10개 용어)
└── test/
    ├── README.md                            # 테스트용 영문 문서
    └── README.ko.md                         # 번역 결과 (한국어)
```

> **중요:** `commands/`, `skills/`, `agents/`, `hooks/` 디렉토리는 반드시 플러그인 **루트 레벨**에 위치해야 합니다.
> `.claude-plugin/` 내부에만 있으면 플러그인 로더가 인식하지 못합니다.

## 플러그인 구성요소 설명

| 구성요소 | 파일 | 역할 |
|----------|------|------|
| **Commands** | `commands/*.md` | 사용자가 `/translate` 등으로 직접 호출하는 명령어 |
| **Skills** | `skills/*/SKILL.md` | AI가 자동으로 참조하는 도메인 지식 (용어집 규칙, 스타일 가이드) |
| **Agents** | `agents/*.md` | 특정 작업에 특화된 AI 서브에이전트 (번역 품질 리뷰) |
| **Hooks** | `hooks/hooks.json` | 이벤트 기반 자동 실행 (파일 수정 시 번역 누락 경고) |
| **Glossary** | `glossary/terms.json` | 프로젝트 전용 용어집 (ko/ja 번역 매핑) |

## 핵심 커맨드

### /translate — 인라인 텍스트 번역
```
/translate-toolkit:translate "Claude Code is an AI coding agent" to Korean
```
- 용어집 자동 참조
- 코드 스니펫, 변수명, URL 보존
- 미등록 기술 용어 플래그

**실행 예시 1: 영어 → 한국어**
```
You> /translate-toolkit:translate "Claude Code plugin system enables non-developers
     to build AI tools with guardrails and observability" to Korean

Claude> Claude Code 플러그인 시스템은 비개발자가 가드레일과 옵저버빌리티를 갖춘
        AI 도구를 구축할 수 있게 해줍니다.

        Glossary terms applied: 3
          "plugin" → "플러그인"
          "guardrails" → "가드레일"
          "observability" → "옵저버빌리티"
```

**실행 예시 2: 한국어 → 영어**
```
You> /translate-toolkit:translate 에이전틱 에이아이 는 무엇인가? 를 영어로

Claude> What is Agentic AI?

        Glossary terms applied: 0
        Flagged: "에이전틱 에이아이" (Agentic AI) — not in glossary
```

### /translate-file — 파일 단위 번역
```
/translate-toolkit:translate-file README.md to Korean
```
- 번역 가능 콘텐츠(산문)와 코드를 자동 구분
- 출력: `README.ko.md` (로케일 규칙 적용)
- 용어집 적용 결과 리포트

**실행 예시:**
```
You> /translate-toolkit:translate-file test/README.md to Korean

Claude> Output file: test/README.ko.md
        Sections translated: 5 (개요, 기능, 빠른 시작, 구성, 아키텍처)
        Glossary terms applied: 10/10
          "Agent Runtime" → "에이전트 런타임"
          "observability" → "옵저버빌리티"
          "guardrails" → "가드레일"
          ... (all 10 terms matched)
        Missing glossary terms: 0
```

### /glossary — 용어집 관리
```
/translate-toolkit:glossary add "Post-Trained Model" = "사후학습 모델" = "ポストトレーニングモデル"
/translate-toolkit:glossary search "model"
/translate-toolkit:glossary list ko
/translate-toolkit:glossary import terms-import.csv
```

**실행 예시:**
```
You> /translate-toolkit:glossary list ko

Claude> | # | English Term       | Korean Translation   |
        |---|-------------------|---------------------|
        | 1 | Agent Runtime      | 에이전트 런타임       |
        | 2 | observability      | 옵저버빌리티          |
        | 3 | guardrails         | 가드레일              |
        | ...                                           |
        10 terms found with Korean translations.
```

### @review-translator — 번역 품질 리뷰
```
@review-translator check README.md against README.ko.md
```
- 유창성(1~5점), 정확성(1~5점) 평가
- 용어집 불일치 검출
- 코드/플레이스홀더 보존 검증

## 플러그인 설치 방법

### 1. 로컬 마켓플레이스 생성

플러그인을 배포하려면 Git 저장소 기반의 마켓플레이스가 필요합니다.

```
local-marketplace/
├── .claude-plugin/
│   └── marketplace.json    # 마켓플레이스 메타데이터
└── plugins/
    └── translate-toolkit/  # 플러그인 복사
```

**marketplace.json 형식:**
```json
{
  "name": "local-plugins",
  "description": "Local custom plugins",
  "owner": { "name": "local" },
  "plugins": [
    {
      "name": "translate-toolkit",
      "description": "Multilingual translation plugin",
      "source": "./plugins/translate-toolkit"
    }
  ]
}
```

마켓플레이스 디렉토리를 Git 저장소로 초기화:
```bash
cd local-marketplace
git init && git add -A && git commit -m "Add translate-toolkit plugin"
```

### 2. 마켓플레이스 등록 및 플러그인 설치

```bash
# 마켓플레이스 등록
claude plugin marketplace add /path/to/local-marketplace

# 플러그인 설치
claude plugin install translate-toolkit@local-plugins

# 설치 확인
claude plugin list
```

### 3. 플러그인 검증

설치 전에 플러그인 구조를 검증할 수 있습니다:
```bash
claude plugin validate /path/to/translate-toolkit
```

## plugin.json 형식

```json
{
  "name": "translate-toolkit",
  "version": "1.0.0",
  "description": "Multilingual translation plugin...",
  "author": {
    "name": "translate-team"
  }
}
```

**주의사항:**
- `author`는 반드시 객체 형식 (`{"name": "..."}`)이어야 함 (문자열 불가)
- `commands`, `skills`, `agents` 필드를 plugin.json에 넣지 않음 — 디렉토리 구조로 자동 발견
- hooks.json은 이벤트 이름(`PostToolUse`, `Stop` 등)을 키로 하는 레코드 형식

## hooks.json 형식

```json
{
  "description": "Hook description",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/script.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**지원 이벤트:** `PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `UserPromptSubmit`

## 용어집 (terms.json)

10개 기술 용어의 한국어/일본어 번역 매핑:

| English | Korean | Japanese |
|---------|--------|----------|
| Agent Runtime | 에이전트 런타임 | エージェントランタイム |
| observability | 옵저버빌리티 | オブザーバビリティ |
| guardrails | 가드레일 | ガードレール |
| plugin | 플러그인 | プラグイン |
| prompt caching | 프롬프트 캐싱 | プロンプトキャッシング |
| slash command | 슬래시 커맨드 | スラッシュコマンド |
| hook | 훅 | フック |
| skill | 스킬 | スキル |
| Post-Trained Model | 사후학습 모델 | ポストトレーニングモデル |
| fine-tuning | 파인튜닝 | ファインチューニング |

## 실습에서 배운 점

### 플러그인 설치 프로세스
1. **`plugin.json` 검증이 엄격함** — `author`는 객체, `commands`/`skills`/`agents` 필드 불가
2. **`hooks.json` 형식** — 배열이 아닌 이벤트명을 키로 하는 레코드 형식
3. **마켓플레이스 필수** — 플러그인 설치에는 Git 기반 마켓플레이스 등록이 필요
4. **`claude plugin validate`로 사전 검증** — 설치 전 구조 오류를 확인

### 플러그인 아키텍처
- 모든 로직은 마크다운으로 작성 (프로그래밍 언어 불필요)
- Commands: 사용자가 직접 호출하는 슬래시 명령어
- Skills: AI가 컨텍스트에 따라 자동으로 참조하는 지식
- Agents: 독립적인 프롬프트로 실행되는 서브에이전트
- Hooks: 셸 스크립트 기반 이벤트 트리거 (AI 미관여)

### Amazon Bedrock 연동
- 플러그인은 클라이언트 측에서 로컬 실행
- 모델 추론 요청만 Bedrock API로 전송
- 환경 변수: `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION`, `ANTHROPIC_MODEL`
