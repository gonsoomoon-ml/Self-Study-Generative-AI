# K-Style 이커머스 유스케이스 디렉토리

이 디렉토리는 K-Style 이커머스 플랫폼의 다양한 유스케이스들을 체계적으로 관리합니다.

## 📁 디렉토리 구조

```
use_cases/
├── customer_support/        # 고객 지원 (기존 메인 유스케이스)
├── product_recommendation/  # 상품 추천 시스템
├── sales_assistant/         # 판매 지원 어시스턴트
└── [미래 유스케이스들...]
```

## 🎯 각 유스케이스별 표준 구조

각 유스케이스는 다음과 같은 표준 구조를 따릅니다:

```
{use_case_name}/
├── README.md                    # 유스케이스 설명 및 가이드
├── agent.py                     # 메인 에이전트 코드
├── tools/                       # 유스케이스 전용 도구들
│   ├── __init__.py
│   ├── {tool1}.py
│   └── {tool2}.py
├── notebooks/                   # Jupyter 노트북 튜토리얼
│   ├── 01-prototype.ipynb
│   ├── 02-memory.ipynb
│   ├── 03-gateway.ipynb
│   ├── 04-runtime.ipynb
│   └── 05-frontend.ipynb
├── ui/                          # UI 컴포넌트
│   ├── streamlit_app.py
│   └── components.py
├── config/                      # 설정 파일들
│   ├── prompts.yaml
│   └── settings.json
└── tests/                       # 테스트 코드
    ├── test_agent.py
    └── test_tools.py
```

## 🔄 유스케이스 간 공유 컴포넌트

공통으로 사용되는 컴포넌트들은 `shared/` 디렉토리에 위치합니다:

- **agents**: 재사용 가능한 에이전트 베이스 클래스
- **memory**: 공통 메모리 시스템
- **tools**: 범용 도구들
- **ui_components**: 재사용 가능한 UI 컴포넌트
- **utils**: 공통 유틸리티 함수들

## 🚀 새로운 유스케이스 추가하기

1. **디렉토리 생성**
   ```bash
   mkdir -p use_cases/{new_use_case}/{tools,notebooks,ui,config,tests}
   ```

2. **템플릿 복사**
   ```bash
   cp use_cases/customer_support/README.md use_cases/{new_use_case}/
   # 내용 수정
   ```

3. **에이전트 구현**
   ```bash
   # agent.py 작성
   # tools/ 디렉토리에 도구들 구현
   ```

4. **노트북 튜토리얼 작성**
   ```bash
   # notebooks/ 디렉토리에 5개 Lab 노트북 작성
   ```

5. **UI 개발**
   ```bash
   # ui/streamlit_app.py 구현
   ```

## 🎯 현재 구현된 유스케이스

### 🛍️ Customer Support (고객 지원)
- **목적**: 패션/뷰티 고객 지원 자동화
- **주요 기능**: 반품, 교환, 스타일링 조언
- **상태**: ✅ 완료 (기존 메인 유스케이스)

### 🎯 Product Recommendation (상품 추천)
- **목적**: AI 기반 개인화 상품 추천
- **주요 기능**: 협업 필터링, 콘텐츠 기반 추천, 트렌드 분석
- **상태**: 🚧 개발 예정

### 💼 Sales Assistant (판매 지원)
- **목적**: 판매 사원을 위한 AI 어시스턴트
- **주요 기능**: 고객 분석, 판매 전략, 재고 관리
- **상태**: 🚧 개발 예정

## 🔧 개발 가이드라인

### 코딩 표준
- **언어**: Python 3.12+
- **프레임워크**: Strands Agents + Amazon Bedrock
- **UI**: Streamlit
- **패키지 관리**: UV

### 네이밍 컨벤션
- **디렉토리**: `snake_case`
- **파일**: `snake_case.py`
- **클래스**: `PascalCase`
- **함수/변수**: `snake_case`

### 의존성 관리
- 각 유스케이스는 독립적인 의존성 가능
- 공통 의존성은 메인 `pyproject.toml`에 정의
- 특화 의존성은 유스케이스 디렉토리에 `requirements.txt` 추가

### 테스트
- 각 유스케이스는 `tests/` 디렉토리에 테스트 코드 포함
- 단위 테스트 + 통합 테스트
- pytest 프레임워크 사용

## 🚀 확장 로드맵

### Phase 1 (현재)
- ✅ Customer Support

### Phase 2 (단기)
- 🎯 Product Recommendation
- 💼 Sales Assistant

### Phase 3 (중기)
- 📊 Analytics Dashboard
- 🏪 Inventory Management
- 📱 Mobile Commerce

### Phase 4 (장기)
- 🎮 Virtual Try-On
- 🌐 Multi-language Support
- 🤖 Voice Commerce

---

**💡 새로운 유스케이스 아이디어가 있으시면 언제든 추가해보세요!**