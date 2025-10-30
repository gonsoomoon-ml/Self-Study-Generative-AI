# 이커머스 고객 지원 멀티 에이전트 시스템

## 개요
Strands Agent SDK를 사용하여 이커머스 고객 지원 문의를 처리하는 멀티 에이전트 아키텍처의 개념 증명(PoC) 프로젝트입니다. 모든 에이전트가 한국어로 응답합니다.

## 아키텍처

```
고객 문의
      ↓
┌─────────────────────┐
│  오케스트레이터      │  ← 문의를 적절한 서브 에이전트로 라우팅
└─────────────────────┘
      ↓         ↓
      ↓         └──────────────────┐
      ↓                            ↓
┌──────────────┐          ┌───────────────┐
│ 서브-에이전트-01│         │ 서브-에이전트-02│
│   주문/배송   │          │   반품/결제    │
└──────────────┘          └───────────────┘
      ↓                            ↓
   도구:                        도구:
- 주문 상태 확인            - 반품 처리
- 배송 추적                 - 환불 상태 확인
                            - 교환 처리
```

## 구성 요소

### 1. 오케스트레이터 에이전트 (`orchestrator_agent.py`)
- **역할**: 고객 문의를 분석하고 적절한 전문 상담원에게 전달하는 메인 진입점
- **라우팅 로직**:
  - 주문/배송/추적 관련 문의 → 서브-에이전트-01
  - 반품/교환/환불/결제 관련 문의 → 서브-에이전트-02

### 2. 서브-에이전트-01: 주문/배송 상담원 (`sub_agent_orders.py`)
- **담당 업무**: 주문 상태 조회, 배송 추적, 배송 정보 안내
- **도구**:
  - `check_order_status(order_id)`: 주문 상태를 확인합니다
  - `track_delivery(tracking_number)`: 배송 위치를 추적합니다
- **시스템 프롬프트**: 한국어로 친절하게 응답하도록 설정됨

### 3. 서브-에이전트-02: 반품/결제 상담원 (`sub_agent_returns.py`)
- **담당 업무**: 반품 요청, 교환 절차, 환불 상태, 결제 문제 처리
- **도구**:
  - `process_return(order_id, reason)`: 반품 요청을 처리합니다
  - `check_refund_status(order_id)`: 환불 상태를 확인합니다
  - `process_exchange(order_id, new_item)`: 교환 요청을 처리합니다
- **시스템 프롬프트**: 한국어로 친절하게 응답하도록 설정됨

## 폴더 구조

```
21_customer_chat/
├── agent_tool_pattern/        # 원본 Orchestrator + Tools 패턴
│   ├── orchestrator_agent.py
│   ├── sub_agent_orders.py
│   ├── sub_agent_returns.py
│   ├── main.py
│   └── README.md
├── hybrid/                     # Graph + Hierarchical Hybrid 패턴 ⭐
│   ├── graphs/                # 그래프 정의
│   ├── agents/                # 에이전트들
│   ├── tools/                 # 도구 함수들
│   ├── hierarchies/           # 계층적 구조
│   ├── main.py
│   └── README.md
├── setup/                      # 환경 설정
├── ARCHITECTURE_PATTERNS.md   # 모든 패턴 설명
├── RECOMMENDED_PATTERN.md     # 추천 패턴 가이드 ⭐
└── README.md                  # 이 파일
```

## 설치 및 설정

### 1. Python 환경 생성
```bash
cd setup
./create_env.sh customer_chat 3.11
cd ..
```

이 스크립트는 다음을 자동으로 수행합니다:
- UV 패키지 매니저를 설치/확인합니다
- Python 3.11 가상 환경을 생성합니다
- Strands Agent SDK 및 필요한 모든 패키지를 설치합니다
- Jupyter 커널을 등록합니다
- 루트 디렉토리에 심링크를 생성합니다

### 2. 설치 확인
```bash
uv run python --version
uv pip list
```

## 사용 방법

### 1️⃣ Orchestrator + Tools 패턴 (원본)
```bash
cd agent_tool_pattern
uv run python main.py
```

### 2️⃣ Graph + Hierarchical Hybrid 패턴 ⭐ (추천)
```bash
cd hybrid
uv run python main.py
```

### 코드에서 직접 사용:

**Orchestrator 패턴:**
```python
from agent_tool_pattern.orchestrator_agent import handle_customer_query

response = handle_customer_query("주문번호 ORD12345는 어디에 있나요?")
print(response)
```

**Hybrid 패턴:**
```python
from hybrid.graphs.main_graph import execute_customer_support

result = await execute_customer_support("주문 취소하고 환불 받고 싶어요")
print(result)
```

## Sample Queries (한국어)

**주문 및 배송 문의:**
- "주문번호 ORD12345는 어디에 있나요? 아직 받지 못했어요."
- "운송장번호 TRK987654로 택배 추적해주실 수 있나요?"

**반품 및 결제 문의:**
- "주문번호 ORD67890 상품이 안 맞아서 반품하고 싶어요."
- "주문번호 ORD11111 환불이 처리되었나요?"
- "주문번호 ORD22222를 다른 사이즈로 교환하고 싶습니다."

## 예상 사용 사례

일반적인 이커머스 고객 지원에서 이 시스템이 처리할 수 있는 문의:
- 배송 지연 문의
- 주문 내역 확인
- 환불 요청
- 교환/반품 절차 안내
- 배송 추적
- 결제 문제

## 실행 예시 (한국어 응답)

```
[오케스트레이터] 고객 문의 접수: 주문번호 ORD12345는 어디에 있나요?
[오케스트레이터] 주문/배송 상담원으로 전달 중
[도구] 주문 상태 확인 중 - 주문번호: ORD12345

응답: 주문번호 ORD12345의 배송 상황을 확인해드렸습니다!

**현재 상태**: 배송 중
**예상 도착일**: 2일 후

더 자세한 배송 위치를 확인하고 싶으시다면 배송 추적번호를 알려주시면
실시간 배송 위치를 확인해드릴 수 있습니다.
```

## 주요 기능

- ✅ **한국어 지원**: 모든 에이전트가 자연스러운 한국어로 응답
- ✅ **멀티 에이전트 아키텍처**: 오케스트레이터가 적절한 서브 에이전트로 자동 라우팅
- ✅ **AWS Bedrock 통합**: Claude Sonnet 4 모델 사용
- ✅ **도구 호출**: 각 에이전트가 전문 도구를 사용하여 정보 조회 및 처리
- ✅ **실시간 응답**: AWS Bedrock을 통한 실시간 LLM 추론

## 참고 사항

이 프로젝트는 멀티 에이전트 아키텍처를 시연하는 **개념 증명(PoC)** 입니다.

프로덕션 환경에서는 다음 사항을 추가로 구현해야 합니다:
1. 실제 백엔드 API/데이터베이스 연동
2. 적절한 에러 핸들링
3. 세션 관리 구현
4. 로깅 및 모니터링 추가
5. 인증 및 권한 관리
6. 대화 히스토리 및 컨텍스트 관리 구현

## 기술 스택

- **Strands Agent SDK**: 멀티 에이전트 프레임워크
- **AWS Bedrock**: Claude Sonnet 4 모델 호스팅
- **Python 3.11**: 개발 언어
- **UV**: 패키지 매니저

## 아키텍처 패턴 및 확장

### 현재 구현: Orchestrator + Tools 패턴 (PoC)

현재 구현은 **Orchestrator + Tools** 패턴을 사용합니다. 이는 개념 증명(PoC)으로는 적합하지만, 실제 프로덕션 환경에서는 제한사항이 있습니다.

### 🎯 **프로덕션 추천: Graph + Hierarchical Hybrid 패턴**

실제 이커머스 고객 지원에서는 복잡한 조건부 분기, 에스컬레이션, 여러 에이전트 간 협력이 필요합니다.

**왜 Graph + Hierarchical이 더 나은가?**
👉 자세한 분석은 [RECOMMENDED_PATTERN.md](./RECOMMENDED_PATTERN.md) 참고

**주요 이점**:
- ✅ 조건부 워크플로우 (배송 상태에 따른 다른 처리)
- ✅ 에스컬레이션 (관리자 승인 필요한 경우)
- ✅ 복잡한 비즈니스 로직 표현
- ✅ 에이전트 간 상태 공유 및 협력

### 📚 아키텍처 문서

- **[RECOMMENDED_PATTERN.md](./RECOMMENDED_PATTERN.md)** ⭐ - 추천 패턴 및 구현 가이드
- **[ARCHITECTURE_PATTERNS.md](./ARCHITECTURE_PATTERNS.md)** - 모든 패턴 종합 설명

**지원되는 패턴**:
- 🔄 **Agent-to-Agent (A2A)**: 에이전트 간 직접 통신
- 🐝 **Swarm**: 병렬 처리 및 협력
- 📊 **Graph-Based**: 조건부 워크플로우 ⭐⭐⭐
- 🏢 **Hierarchical**: 계층적 의사결정 ⭐⭐⭐
- 📋 **Workflow**: 순차적 프로세스
- 🎯 **Hybrid**: 여러 패턴 조합 ⭐⭐⭐
