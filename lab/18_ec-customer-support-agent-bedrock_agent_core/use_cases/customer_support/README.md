# 🛍️ Customer Support Use Case

K-Style 이커머스 고객 지원 유스케이스입니다.

## 📋 개요

한국 패션/뷰티 전문 온라인 쇼핑몰의 고객 지원을 자동화하는 AI 에이전트입니다.

### 🎯 주요 기능

- **반품 처리**: 고객의 반품 요청을 접수하고 처리합니다
- **교환 서비스**: 사이즈, 색상 등의 교환을 지원합니다
- **스타일링 조언**: 웹 검색을 통한 최신 스타일링 정보 제공
- **한국어 지원**: 자연스러운 한국어 대화 처리
- **VIP 고객 서비스**: 특별 고객을 위한 맞춤 서비스

### 🏗️ 아키텍처

이 유스케이스는 Amazon Bedrock AgentCore를 기반으로 구축되었습니다:

- **Memory**: 고객 선호도 및 상호작용 기록 저장
- **Gateway**: Lambda 함수를 통한 외부 시스템 연동
- **Runtime**: 에이전트 호스팅 및 실행 환경
- **Identity**: 고객 인증 및 권한 관리

## 📁 파일 구조

```
customer_support/
├── README.md                    # 이 파일
├── agent.py                     # 메인 에이전트 코드
├── tools/                       # 고객 지원 전용 도구들
│   ├── __init__.py
│   ├── return_tools.py          # 반품 처리 도구
│   ├── exchange_tools.py        # 교환 처리 도구
│   └── search_tools.py          # 웹 검색 도구
├── notebooks/                   # 단계별 튜토리얼
│   ├── 01-prototype.ipynb       # 기본 에이전트 프로토타입
│   ├── 02-memory.ipynb          # 메모리 시스템 구현
│   ├── 03-gateway.ipynb         # Gateway 통합
│   ├── 04-runtime.ipynb         # Runtime 배포
│   └── 05-frontend.ipynb        # Streamlit UI 구현
├── ui/                          # 사용자 인터페이스
│   ├── streamlit_app.py         # Streamlit 앱
│   └── components.py            # UI 컴포넌트들
├── config/                      # 설정 파일들
│   ├── prompts.yaml             # 프롬프트 템플릿
│   └── settings.json            # 에이전트 설정
└── tests/                       # 테스트 코드
    ├── test_agent.py            # 에이전트 테스트
    └── test_tools.py            # 도구 테스트
```

## 🚀 사용법

### 1. 환경 설정

```bash
# 가상환경 활성화
source .venv/bin/activate

# 의존성 설치 (프로젝트 루트에서)
uv install
```

### 2. AWS 설정

```bash
# AWS 자격 증명 설정
aws configure

# Bedrock 모델 액세스 확인
aws bedrock list-foundation-models --region us-east-1
```

### 3. 에이전트 실행

```bash
# Streamlit 앱 실행
streamlit run use_cases/customer_support/ui/streamlit_app.py

# 또는 직접 에이전트 사용
python use_cases/customer_support/agent.py
```

### 4. 튜토리얼 실행

각 Lab 노트북을 순서대로 실행하여 단계별로 학습할 수 있습니다:

```bash
jupyter lab use_cases/customer_support/notebooks/
```

## 🛠️ 개발 가이드

### 새로운 도구 추가

1. `tools/` 디렉토리에 새 파일 생성
2. `@tool` 데코레이터를 사용하여 함수 정의
3. `agent.py`에서 도구 import 및 등록

### 프롬프트 수정

`config/prompts.yaml` 파일에서 시스템 프롬프트와 응답 템플릿을 수정할 수 있습니다.

### UI 커스터마이징

`ui/streamlit_app.py`와 `ui/components.py`에서 사용자 인터페이스를 수정할 수 있습니다.

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest use_cases/customer_support/tests/

# 특정 테스트 실행
python -m pytest use_cases/customer_support/tests/test_agent.py
```

## 📊 모니터링

- **CloudWatch**: 에이전트 실행 로그 및 메트릭
- **AgentCore Memory**: 고객 상호작용 기록
- **Performance**: 응답 시간 및 성공률

## 🔧 트러블슈팅

### 일반적인 문제

1. **AWS 권한 오류**: IAM 역할에 Bedrock 권한 추가 필요
2. **메모리 문제**: AgentCore Memory 설정 확인
3. **도구 실행 오류**: 도구 함수의 타입 힌트 확인

### 로그 확인

```bash
# 에이전트 로그
tail -f logs/agent.log

# Streamlit 로그
streamlit run ui/streamlit_app.py --logger.level debug
```

## 🤝 기여하기

1. 이슈 생성 또는 기능 요청
2. 브랜치 생성 및 개발
3. 테스트 작성 및 실행
4. Pull Request 생성

## 📞 지원

- **문서**: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/)
- **예제**: `notebooks/` 디렉토리의 튜토리얼
- **이슈**: GitHub Issues를 통한 버그 리포트

---

**K-Style 고객 지원 에이전트와 함께 최고의 고객 경험을 제공하세요!** 🛍️✨