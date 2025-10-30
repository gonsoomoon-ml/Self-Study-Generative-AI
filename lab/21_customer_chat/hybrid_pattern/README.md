# 그래프 + 계층적 하이브리드 패턴 구현

## 📋 개요

이 프로젝트는 **그래프(Graph) + 계층적(Hierarchical) 하이브리드 패턴**을 사용한 이커머스 고객 지원 시스템의 Proof of Concept입니다.

실제 프로덕션 환경에서 발생하는 복잡한 고객 지원 시나리오를 처리하기 위해 다음 두 패턴을 결합했습니다:

### 🔄 패턴 설명

#### 1️⃣ 그래프 기반 (Graph-Based)
- **조건부 워크플로우**: 고객 문의 유형에 따라 다른 처리 경로 선택
- **서브 그래프 라우팅**: 주문/배송 또는 반품/환불 서브 그래프로 분기
- **상태 기반 처리**: 주문 상태, 배송 상태에 따른 동적 처리
- **멀티 에이전트 협업**: 여러 전문 에이전트가 순차적으로 협력

#### 2️⃣ 계층적 (Hierarchical)
- **권한 레벨별 승인**: 환불 금액에 따른 승인 레벨 자동 결정
  - 일반 상담원: 50,000원 이하
  - 관리자: 50,000원 ~ 100,000원
  - 이사: 100,000원 이상
- **자동 에스컬레이션**: 권한 초과 시 자동으로 상위 레벨로 전달

#### 3️⃣ 하이브리드 (Hybrid)
두 패턴의 장점을 결합하여:
- ✅ 복잡한 비즈니스 로직을 명확하게 표현
- ✅ 조직의 승인 구조를 자연스럽게 반영
- ✅ 확장 가능하고 유지보수가 쉬운 구조

---

## 🏗️ 아키텍처

### 전체 시스템 구조

```
                    ┌─────────────────┐
                    │  고객 문의 시작   │
                    └────────┬────────┘
                             ↓
                    ┌────────────────┐
                    │ 분류 에이전트    │
                    │ (Classifier)    │
                    └────────┬────────┘
                             ↓
              ┌──────────────┴──────────────┐
              ↓                             ↓
    ┌─────────────────┐          ┌─────────────────┐
    │ 주문/배송 그래프  │          │  반품/환불 그래프 │
    │ (Order Graph)   │          │ (Return Graph)  │
    └─────────────────┘          └─────────────────┘
              ↓                             ↓
    ┌─────────────────┐          ┌─────────────────┐
    │  주문 에이전트    │          │  반품 에이전트    │
    │  배송 에이전트    │          │  결제 에이전트    │
    └─────────────────┘          └─────────────────┘
              ↓                             ↓
    ┌─────────────────────────────────────────────┐
    │          계층적 승인 시스템                   │
    │  일반 상담원 → 관리자 → 이사                  │
    └──────────────────┬──────────────────────────┘
                       ↓
              ┌────────────────┐
              │   최종 응답     │
              └────────────────┘
```

### 메인 그래프 (Main Graph)

```
execute_customer_support()
    ↓
    [단계 1] 분류 에이전트 호출
    ├─ 고객 문의 분석
    ├─ 카테고리 결정: 주문/배송/취소/반품/환불/교환
    └─ JSON 형식으로 결과 반환
    ↓
    [단계 2] 서브 그래프 라우팅
    ├─ 주문/배송/취소 → 주문_그래프
    └─ 반품/환불/교환 → 반품_그래프
    ↓
    [단계 3] 서브 그래프 실행
    ├─ 전문 에이전트 호출
    ├─ 도구(Tools) 사용
    └─ 승인 레벨 결정
    ↓
    [단계 4] 최종 응답 생성
    └─ 한글로 결과 반환
```

### 주문 그래프 (Order Graph)

```
execute_order_graph()
    ↓
    [단계 1] 주문 에이전트 호출
    ├─ check_order_status(): 주문 상태 확인
    ├─ get_order_details(): 주문 상세 정보
    └─ cancel_order(): 주문 취소 (조건부)
    ↓
    [단계 2] 배송 에이전트 호출 (배송 관련 문의인 경우)
    ├─ track_delivery(): 배송 추적
    ├─ get_shipping_status(): 배송 상태
    └─ request_shipping_stop(): 배송 중지 요청
    ↓
    [단계 3] 계층적 승인 확인
    ├─ 환불 금액 체크
    ├─ 60,000원 예시 → 관리자 레벨
    └─ 에스컬레이션 여부 결정
```

### 반품 그래프 (Return Graph)

```
execute_return_graph()
    ↓
    [단계 1] 반품 에이전트 호출
    ├─ process_return(): 반품 요청 처리
    └─ process_exchange(): 교환 요청 처리
    ↓
    [단계 2] 결제 에이전트 호출 (환불 필요시)
    ├─ verify_payment_method(): 결제 수단 확인
    ├─ check_refund_status(): 환불 상태 조회
    └─ process_refund(): 환불 처리
    ↓
    [단계 3] 고액 환불 승인 체크
    ├─ 120,000원 예시 → 이사 레벨
    └─ 에스컬레이션 필요 여부
```

### 계층적 승인 시스템

```
승인 권한 구조:

┌─────────────────────────────────┐
│         이사 (Director)          │
│   • 모든 금액 환불 승인           │
│   • 긴급 환불 처리               │
│   • 모든 정책 예외 승인           │
│   • 최종 의사결정                │
└────────────┬────────────────────┘
             ↑ (환불 > 100,000원)
             │ (중대한 정책 예외)
┌────────────┴────────────────────┐
│       관리자 (Manager)           │
│   • 100,000원 이하 환불 승인     │
│   • 배송 강제 중지               │
│   • 일부 정책 예외               │
└────────────┬────────────────────┘
             ↑ (환불 > 50,000원)
             │ (배송 강제 중지)
┌────────────┴────────────────────┐
│     일반 상담원 (Specialist)     │
│   • 50,000원 이하 환불           │
│   • 일반 문의 처리               │
│   • 표준 프로세스 수행           │
└─────────────────────────────────┘
```

---

## 📁 폴더 구조

```
hybrid_pattern/
├── graphs/                          # 그래프 정의
│   ├── __init__.py
│   ├── main_graph.py               # 메인 그래프 (전체 시스템)
│   ├── order_graph.py              # 주문/배송 서브그래프
│   └── return_graph.py             # 반품/환불 서브그래프
│
├── agents/                          # 에이전트 정의 (Strands SDK)
│   ├── __init__.py
│   ├── classifier_agent.py         # 문의 분류 에이전트
│   ├── orders_agent.py             # 주문 에이전트
│   ├── shipping_agent.py           # 배송 에이전트
│   ├── returns_agent.py            # 반품 에이전트
│   ├── payment_agent.py            # 결제 에이전트
│   └── decision_agent.py           # 의사결정 에이전트 (미사용)
│
├── tools/                           # 도구 함수 (@tool 데코레이터)
│   ├── __init__.py
│   ├── order_tools.py              # 주문 관련 도구
│   │   ├── check_order_status()
│   │   ├── cancel_order()
│   │   └── get_order_details()
│   ├── shipping_tools.py           # 배송 관련 도구
│   │   ├── track_delivery()
│   │   ├── request_shipping_stop()
│   │   ├── get_shipping_status()
│   │   └── force_shipping_return()
│   └── payment_tools.py            # 결제 관련 도구
│       ├── process_refund()
│       ├── check_refund_status()
│       ├── emergency_refund()
│       └── verify_payment_method()
│
├── hierarchies/                     # 계층적 구조
│   ├── __init__.py
│   └── approval_hierarchy.py       # 승인 계층 정의
│       ├── specialist_agent        # 일반 상담원
│       ├── manager_agent           # 관리자
│       ├── director_agent          # 이사
│       └── determine_escalation_level()
│
├── main.py                          # 실행 및 테스트 스크립트
├── README.md                        # 이 파일
└── 한글_출력_확인.md                 # 한글 출력 확인 문서
```

---

## 🔧 기술 스택

- **Python 3.11+**
- **Strands SDK**: AWS Bedrock Agent SDK for 에이전트 및 도구 정의
- **AWS Bedrock**: Claude Sonnet 4.5 모델
- **asyncio**: 비동기 처리

### 주요 컴포넌트

#### 1. 에이전트 (Agents)
```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

agent = Agent(
    model=model,
    tools=[tool1, tool2],
    system_prompt="당신은 전문 상담원입니다..."
)
```

#### 2. 도구 (Tools)
```python
from strands import tool

@tool
def check_order_status(order_id: str) -> dict:
    """주문 상태를 확인합니다"""
    return {
        "order_id": order_id,
        "status": "배송 중",
        "can_cancel": False
    }
```

#### 3. 그래프 (Graphs)
```python
async def execute_customer_support(query: str) -> dict:
    # 1. 분류
    classification = classify_query(query)

    # 2. 라우팅
    if classification['카테고리'] in ["주문", "배송", "취소"]:
        result = await execute_order_graph(query)
    else:
        result = await execute_return_graph(query)

    # 3. 응답
    return final_response
```

---

## 🚀 실행 방법

### 1. 테스트 실행

```bash
cd hybrid_pattern
uv run python main.py
```

### 2. 코드에서 사용

```python
import asyncio
from graphs.main_graph import execute_customer_support

async def main():
    # 고객 문의 처리
    result = await execute_customer_support("주문 취소하고 환불 받고 싶어요")

    # 결과 확인
    print(f"카테고리: {result['카테고리']}")
    print(f"상태: {result['상태']}")
    print(f"사용된 그래프: {result['사용된_그래프']}")
    print(f"메시지: {result['메시지']}")

asyncio.run(main())
```

### 3. 출력 예시

```
================================================================================
[메인 그래프] 고객 문의 처리 시작
문의: 주문 취소하고 환불 받고 싶어요
================================================================================

[단계 1] 분류 에이전트 호출
[분류 에이전트] 문의 분석 중...
[분류 에이전트] 분류 결과: 취소

[단계 2] 서브 그래프 라우팅
[단계 2] 라우팅 대상: 주문_그래프

[단계 3] 서브 그래프 실행 중...

============================================================
[주문 그래프] 실행 시작
============================================================

[단계 1] 주문 에이전트 호출
[도구] 주문 상태 확인 중 - 주문번호: ORD12345
[단계 1] 주문 에이전트 응답 완료

[단계 3] 에스컬레이션 필요: 관리자 레벨

============================================================
[주문 그래프] 처리 완료
============================================================

[단계 4] 최종 응답 생성

================================================================================
[메인 그래프] 처리 완료
================================================================================

결과:
  - 카테고리: 취소
  - 상태: 완료
  - 메시지: 고객 문의가 성공적으로 처리되었습니다.
  - 사용된 그래프: 주문_그래프
```

---

## 📊 테스트 케이스

프로젝트는 4가지 실제 시나리오를 테스트합니다:

### 테스트 1: 주문 취소 (배송 전)
- **문의**: "주문번호 ORD12345를 취소하고 환불 받고 싶어요"
- **분류**: 취소
- **그래프**: 주문_그래프
- **에이전트**: 주문 에이전트 → 관리자 승인
- **결과**: ✅ 성공

### 테스트 2: 주문 취소 (배송 중)
- **문의**: "배송 중인 주문을 취소하고 싶은데 가능한가요?"
- **분류**: 취소
- **그래프**: 주문_그래프
- **에이전트**: 주문 에이전트 → 배송 에이전트 → 관리자 승인
- **결과**: ✅ 성공

### 테스트 3: 반품 요청
- **문의**: "주문번호 ORD67890 상품이 불량이라서 반품하고 싶어요"
- **분류**: 반품
- **그래프**: 반품_그래프
- **에이전트**: 반품 에이전트
- **결과**: ✅ 성공

### 테스트 4: 고액 환불
- **문의**: "15만원 주문을 환불 받고 싶어요"
- **분류**: 환불
- **그래프**: 반품_그래프
- **에이전트**: 반품 에이전트 → 결제 에이전트 → 이사 승인
- **결과**: ✅ 성공 (120,000원 → 이사 레벨)

---

## ✨ 주요 특징

### 1. 완전한 한국어 지원
- ✅ 모든 로그 메시지가 한국어로 출력
- ✅ 에이전트 응답이 한국어로 제공
- ✅ 결과 데이터 키가 한국어 (카테고리, 상태, 메시지)

### 2. Strands SDK 실제 구현
- ✅ Agent, tool 데코레이터 사용
- ✅ BedrockModel을 통한 Claude 호출
- ✅ 실제 LLM 응답 생성

### 3. 간단한 Proof of Concept
- ✅ 복잡한 비즈니스 로직 없이 흐름 시연
- ✅ print() 로 프로세스 추적 가능
- ✅ 명확하고 이해하기 쉬운 코드

### 4. 확장 가능한 구조
- ✅ 새로운 에이전트 추가 용이
- ✅ 도구 함수 쉽게 확장 가능
- ✅ 승인 레벨 커스터마이징 가능

---

## 🎯 장점

### ✅ 복잡한 비즈니스 로직 처리
- 조건부 분기 (주문 상태, 배송 상태)
- 루프 및 재시도 로직 (재고 확인 등)
- 동적 에스컬레이션 (환불 금액 기반)

### ✅ 여러 에이전트 협력
- 분류 → 주문 → 배송 → 승인
- 각 에이전트가 전문 영역에 집중
- 명확한 책임 분리

### ✅ 확장성
- 새로운 서브 그래프 추가 (예: 상품 문의 그래프)
- 새로운 도구 함수 추가 (예: 재고 확인)
- 새로운 승인 레벨 추가 (예: VP 레벨)

### ✅ 관찰 가능성
- 각 노드의 실행을 추적 가능
- 로그를 통한 디버깅 용이
- 프로세스 흐름 시각화

### ✅ 유지보수성
- 각 컴포넌트가 독립적
- 테스트가 용이한 구조
- 명확한 인터페이스

---

## 🔄 워크플로우 예시

### 시나리오: 배송 중인 고액 주문 취소

```
1. 고객 문의
   "배송 중인 15만원 주문을 취소하고 싶어요"

2. 분류 에이전트
   → 카테고리: "취소"
   → 신뢰도: 0.95

3. 메인 그래프 라우팅
   → 취소 = 주문/배송/취소 → 주문_그래프 선택

4. 주문 그래프 실행
   [단계 1] 주문 에이전트
   → check_order_status() 호출
   → 상태: "배송 중" 확인
   → 일반 취소 불가 판단

   [단계 2] 배송 에이전트
   → "배송" 키워드 감지
   → request_shipping_stop() 호출
   → 배송 중지 어려움 → needs_escalation: true

   [단계 3] 승인 레벨 결정
   → refund_amount: 150,000원
   → 100,000원 초과 → 이사 레벨 필요

5. 최종 응답
   {
     "카테고리": "취소",
     "상태": "완료",
     "사용된_그래프": "주문_그래프",
     "승인_레벨": "이사",
     "메시지": "이사 승인이 필요한 고액 주문입니다."
   }
```

---

## 📝 구현 세부사항

### 분류 에이전트 로직

```python
def classify_query(query: str) -> dict:
    """
    고객 문의를 분석하여 카테고리를 결정합니다.

    카테고리:
    - 주문: 주문 확인, 주문 변경
    - 배송: 배송 추적, 배송 지연
    - 취소: 주문 취소 요청
    - 반품: 반품 요청, 반품 절차
    - 환불: 환불 상태, 환불 요청
    - 교환: 상품 교환

    Returns:
        {
            "category": "카테고리명",
            "confidence": 0.95,
            "reasoning": "분류 이유"
        }
    """
```

### 승인 레벨 결정 로직

```python
def determine_escalation_level(context: dict) -> str:
    """
    컨텍스트를 기반으로 필요한 승인 레벨을 결정합니다.

    Rules:
    - refund_amount > 100,000 → director
    - refund_amount > 50,000 → manager
    - shipping_force_stop → manager
    - policy_exception (high) → director
    - 기본값 → specialist

    Returns:
        "specialist" | "manager" | "director"
    """
```

---

## 🔮 향후 개선 사항

### 단기 (1-2주)
- [ ] 실제 데이터베이스 연동 (주문, 배송 정보)
- [ ] 에러 처리 및 재시도 로직 추가
- [ ] 로깅 시스템 개선 (구조화된 로그)

### 중기 (1-2개월)
- [ ] 실제 Strands Graph API 사용 (현재는 간단한 함수 호출)
- [ ] 승인 프로세스 실제 구현 (이메일, Slack 알림)
- [ ] 성능 최적화 (병렬 처리, 캐싱)

### 장기 (3-6개월)
- [ ] 더 많은 도메인 추가 (상품 문의, 계정 관리)
- [ ] A/B 테스트 프레임워크
- [ ] 실시간 모니터링 대시보드
- [ ] 고객 만족도 피드백 시스템

---

## 📚 참고 자료

- [Strands SDK 문서](https://github.com/aws-samples/bedrock-agentcore)
- [RECOMMENDED_PATTERN.md](../RECOMMENDED_PATTERN.md) - 상세한 구현 가이드
- [ARCHITECTURE_PATTERNS.md](../ARCHITECTURE_PATTERNS.md) - 패턴 비교 및 설명
- [한글_출력_확인.md](./한글_출력_확인.md) - 한글 출력 검증 문서

---

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

이 프로젝트는 교육 및 데모 목적으로 제작되었습니다.

---

## 👥 작성자

AWS Bedrock Agent Core 팀

**문의**: [GitHub Issues](https://github.com/aws-samples/bedrock-agentcore/issues)
