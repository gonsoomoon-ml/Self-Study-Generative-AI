# 🛍️ K-Style 이커머스 플랫폼

한국 패션/뷰티 전문 온라인 쇼핑몰을 위한 확장 가능한 AI 기반 멀티 유스케이스 플랫폼입니다.

## 🌟 플랫폼 개요

K-Style은 단순한 고객 지원을 넘어서 상품 추천, 판매 지원 등 다양한 이커머스 시나리오를 지원하는 확장 가능한 AI 플랫폼입니다.

### 🎯 지원 유스케이스

#### ✅ Customer Support (고객 지원) - 완료
- **패션/뷰티 전문**: 의류, 신발, 가방, 스킨케어, 메이크업 등 전문 상담
- **반품/교환 자동화**: 조건 확인부터 처리까지 원스톱 서비스
- **스타일링 조언**: K-Style 전문 스타일리스트의 코디 팁
- **VIP 고객 우대**: 등급별 차별화된 서비스 (골드, 다이아몬드)

#### 🚧 Product Recommendation (상품 추천) - 개발 예정
- **개인화 추천**: 고객별 맞춤 상품 추천
- **협업 필터링**: 유사한 고객들의 구매 패턴 분석
- **트렌드 분석**: 실시간 패션 트렌드 반영

#### 🚧 Sales Assistant (판매 지원) - 개발 예정
- **고객 분석**: 구매 패턴 및 선호도 분석
- **판매 성과**: 실시간 성과 모니터링
- **재고 관리**: 스마트 재고 최적화

### 🤖 AI 기반 고급 기능
- **개인화 메모리**: 고객 선호도, 구매 이력, 사이즈 정보 기억
- **멀티 도구 통합**: 로컬 도구 + AgentCore Gateway MCP 도구
- **실시간 응답**: 평균 1.2초 응답 시간
- **24/7 서비스**: 연중무휴 한국어 전문 상담

### 🏢 엔터프라이즈급 기능
- **확장 가능한 아키텍처**: AgentCore Runtime으로 자동 확장
- **보안**: JWT 인증, IAM 기반 접근 제어
- **관측성**: CloudWatch 통합 모니터링
- **고가용성**: 99.9% 가동 시간 SLA

## 📁 프로젝트 구조

```
K-Style-Ecommerce-Platform/
├── README.md                           # 플랫폼 개요 (이 파일)
├── ARCHITECTURE.md                     # 아키텍처 문서
├── start_customer_support.sh           # 고객 지원 빠른 시작
├── start_jupyter.sh                    # Jupyter Lab 빠른 시작
│
├── use_cases/                          # 유스케이스별 구현
│   ├── README.md                       # 유스케이스 가이드
│   ├── customer_support/               # ✅ 고객 지원 (완료)
│   │   ├── agent.py                    # 메인 에이전트
│   │   ├── tools/                      # 전용 도구들 (반품, 교환, 검색)
│   │   ├── notebooks/                  # 5개 Lab 튜토리얼
│   │   ├── ui/streamlit_app.py         # Streamlit UI
│   │   └── config/                     # 설정 파일들
│   ├── product_recommendation/         # 🚧 상품 추천 (개발 예정)
│   └── sales_assistant/                # 🚧 판매 지원 (개발 예정)
│
├── shared/                             # 공통 컴포넌트
│   ├── agents/                         # 재사용 가능한 에이전트 베이스
│   ├── memory/                         # 공통 메모리 시스템
│   ├── tools/                          # 범용 도구들
│   ├── ui_components/                  # 재사용 가능한 UI 컴포넌트
│   └── utils/                          # 공통 유틸리티
│
├── setup/                              # 환경 설정
│   ├── create_kstyle_env.sh            # 가상환경 설정 스크립트
│   ├── setup_aws.sh                    # AWS 환경 확인
│   └── pyproject.toml                  # Python 의존성
│
├── scripts/                            # 인프라 관리
│   ├── prereq.sh                       # 인프라 구성
│   ├── cleanup.sh                      # 리소스 정리
│   ├── list_ssm_parameters.sh          # 리소스 상태 확인
│   └── run_kstyle_app.sh               # 앱 실행
│
├── legacy/                             # 원본 파일 보관
│   └── original_files/                 # 변경 전 파일들
│
└── prerequisite/                       # 인프라 구성 요소
    └── lambda/                         # Lambda 함수들
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 프로젝트 디렉토리로 이동
cd /home/ubuntu/Self-Study-Generative-AI/lab/18_ec-customer-support-agent-bedrock_agent_core

# 가상환경 및 의존성 자동 설정
./setup/create_kstyle_env.sh

# AWS 환경 확인
./setup/setup_aws.sh
```

### 2. 고객 지원 에이전트 실행

```bash
# 방법 1: 빠른 시작 스크립트 (권장)
./start_customer_support.sh

# 방법 2: 직접 실행
streamlit run use_cases/customer_support/ui/streamlit_app.py
```

### 3. Jupyter Lab 실행

```bash
# 인터랙티브 선택 메뉴
./start_jupyter.sh

# 직접 Customer Support Lab 실행
jupyter lab use_cases/customer_support/notebooks/
```

### 4. 새로운 유스케이스 개발

```bash
# 상품 추천 개발 시작 (예시)
python use_cases/product_recommendation/agent.py

# 판매 지원 개발 시작 (예시)
python use_cases/sales_assistant/agent.py
```

## 📚 학습 경로

### 🎓 Customer Support 마스터하기
1. **Lab 1**: `use_cases/customer_support/notebooks/01-prototype.ipynb` - 기본 에이전트 생성
2. **Lab 2**: `use_cases/customer_support/notebooks/02-memory.ipynb` - 메모리 시스템
3. **Lab 3**: `use_cases/customer_support/notebooks/03-gateway.ipynb` - Gateway 통합
4. **Lab 4**: `use_cases/customer_support/notebooks/04-runtime.ipynb` - Runtime 배포
5. **Lab 5**: `use_cases/customer_support/notebooks/05-frontend.ipynb` - Streamlit UI

### 🏗️ 아키텍처 이해하기
- **ARCHITECTURE.md**: 전체 시스템 아키텍처
- **use_cases/README.md**: 유스케이스 확장 가이드
- **shared/README.md**: 공통 컴포넌트 활용법

## 🔧 개발 가이드

### 새로운 유스케이스 추가
```bash
# 1. 디렉토리 구조 생성
mkdir -p use_cases/{new_use_case}/{tools,notebooks,ui,config,tests}

# 2. 템플릿 복사
cp use_cases/customer_support/README.md use_cases/{new_use_case}/
cp use_cases/customer_support/agent.py use_cases/{new_use_case}/

# 3. 공통 컴포넌트 활용
# shared/agents/korean_agent.py 상속
# shared/tools/ 재사용
```

### 공통 컴포넌트 개발
- `shared/agents/`: 에이전트 베이스 클래스
- `shared/tools/`: 범용 도구 함수들
- `shared/ui_components/`: 재사용 가능한 UI

## 🚨 트러블슈팅

### 일반적인 문제

1. **가상환경 오류**
   ```bash
   ./setup/create_kstyle_env.sh
   source .venv/bin/activate
   ```

2. **AWS 권한 오류**
   ```bash
   aws configure
   ./setup/setup_aws.sh
   ```

3. **패키지 의존성 오류**
   ```bash
   uv sync
   # 또는
   pip install -r setup/requirements.txt
   ```

## 📖 참고 자료

- **Amazon Bedrock AgentCore**: [공식 문서](https://docs.aws.amazon.com/bedrock/)
- **Strands Agents**: 에이전트 프레임워크 문서
- **legacy/README.md**: 기존 파일 구조 참조

---

**🛍️ K-Style과 함께 차세대 이커머스 경험을 만들어보세요!**

