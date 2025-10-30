# 멀티 에이전트 아키텍처 패턴

## 현재 구현: Orchestrator + Tools 패턴

### 개요
현재 구현은 **Agents as Tools** 패턴을 사용합니다:
- **Orchestrator Agent**: 고객 문의를 분석하고 적절한 서브 에이전트로 라우팅
- **Sub-Agents as Tools**: 각 서브 에이전트가 도구(tool)로 정의되어 orchestrator가 호출

### 장점
✅ **단순성**: 이해하고 구현하기 쉬움
✅ **중앙 집중식 제어**: 모든 라우팅 로직이 orchestrator에 집중
✅ **명확한 책임 분리**: 각 서브 에이전트가 특정 도메인 담당
✅ **확장 용이**: 새로운 서브 에이전트를 도구로 추가 가능

### 제한사항
⚠️ **순차적 처리**: Orchestrator가 한 번에 하나의 서브 에이전트만 호출
⚠️ **복잡한 워크플로우 제한**: 에이전트 간 직접 통신 불가
⚠️ **단일 실패 지점**: Orchestrator 실패 시 전체 시스템 영향

### 현재 구조
```python
# orchestrator_agent.py
@tool
def route_to_orders_agent(query: str) -> str:
    """고객 문의를 주문 및 배송 상담원에게 전달"""
    return handle_order_query(query)

orchestrator = Agent(
    model=model,
    tools=[route_to_orders_agent, route_to_returns_agent],
    system_prompt="문의를 분석하여 적절한 상담원에게 전달..."
)
```

---

## Strands Agents SDK 지원 패턴

Strands Agents SDK는 다양한 멀티 에이전트 패턴을 지원합니다:

### 1️⃣ Agent-to-Agent (A2A) 패턴

**개념**: 에이전트들이 직접 통신하며 협력

```
고객 문의
    ↓
Orders Agent ←→ Inventory Agent ←→ Shipping Agent
    ↓
Returns Agent ←→ Payment Agent
```

**적합한 경우**:
- 에이전트 간 양방향 통신이 필요한 경우
- 동적인 협력이 필요한 경우
- 에이전트가 다른 에이전트의 상태를 조회해야 하는 경우

**예시 시나리오**:
```
고객: "주문 취소하고 환불 받고 싶어요"
→ Orders Agent가 주문 취소 처리
→ Shipping Agent에게 배송 중지 요청
→ Payment Agent에게 환불 요청
→ 각 에이전트가 실시간으로 상태를 공유
```

**구현 예시**:
```python
from strands import Agent, A2AProtocol

# A2A 프로토콜을 사용한 에이전트 정의
orders_agent = Agent(
    model=model,
    tools=[check_order, cancel_order],
    a2a_enabled=True,  # A2A 통신 활성화
    peer_agents=[shipping_agent, payment_agent]
)

# 다른 에이전트에게 메시지 전송
await orders_agent.send_to_peer(
    agent_id="shipping_agent",
    message="주문 ORD123 배송 중지 필요"
)
```

---

### 2️⃣ Swarm 패턴

**개념**: 여러 에이전트가 협력하여 복잡한 작업 수행

```
                 Coordinator
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
   Agent 1       Agent 2       Agent 3
   (주문조회)     (배송추적)     (재고확인)
        ↓             ↓             ↓
                  결과 통합
```

**적합한 경우**:
- 병렬 처리가 필요한 경우
- 여러 소스에서 정보를 동시에 수집해야 하는 경우
- 독립적인 작업들을 조율해야 하는 경우

**예시 시나리오**:
```
고객: "제 주문 3건 모두 어디에 있나요?"
→ Swarm Coordinator가 3개의 Agent를 동시에 배치
→ 각 Agent가 병렬로 주문 상태 조회
→ 결과를 통합하여 하나의 응답 생성
```

**구현 예시**:
```python
from strands import Agent, Swarm

# Swarm 정의
customer_support_swarm = Swarm(
    agents=[
        orders_agent,
        shipping_agent,
        inventory_agent
    ],
    coordinator=coordinator_agent,
    strategy="parallel"  # 병렬 실행
)

# Swarm 실행
results = await customer_support_swarm.run(
    task="주문 ORD123, ORD456, ORD789 상태 확인"
)
```

---

### 3️⃣ Graph-Based 패턴

**개념**: 에이전트들이 그래프 구조로 연결되어 조건에 따라 흐름 제어

```
              [Start]
                 ↓
          [Classification]
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
   [주문/배송]         [반품/결제]
        ↓                 ↓
   [재고 확인?] ←YES→ [Inventory]
        ↓ NO
   [배송 추적?] ←YES→ [Shipping]
        ↓ NO
      [End]
```

**적합한 경우**:
- 복잡한 조건부 워크플로우
- 순환 참조가 필요한 경우 (Cyclic Graph)
- 상태 기반 의사결정이 필요한 경우

**예시 시나리오**:
```
고객: "반품하고 싶은데 교환도 가능한가요?"
→ Classification Agent: 반품/교환 문의로 분류
→ Returns Agent: 반품 가능 여부 확인
→ Inventory Agent: 교환 상품 재고 확인
→ Shipping Agent: 배송비 계산
→ Returns Agent: 최종 옵션 제시
```

**구현 예시**:
```python
from strands import Agent, Graph, GraphNode

# Graph 노드 정의
workflow = Graph(
    nodes=[
        GraphNode(
            id="classify",
            agent=classifier_agent,
            next={"주문": "orders", "반품": "returns"}
        ),
        GraphNode(
            id="orders",
            agent=orders_agent,
            next={"재고확인": "inventory", "완료": "end"}
        ),
        GraphNode(
            id="inventory",
            agent=inventory_agent,
            next={"주문": "orders"}  # Cyclic: 다시 주문으로
        ),
        GraphNode(id="end")
    ],
    start="classify"
)

# Graph 실행
result = await workflow.run(customer_query)
```

---

### 4️⃣ Hierarchical 패턴 (계층적)

**개념**: 에이전트들이 계층 구조로 조직됨

```
        [Senior Manager Agent]
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
  [Order Manager]   [Return Manager]
        ↓                 ↓
   ┌────┴────┐       ┌────┴────┐
   ↓         ↓       ↓         ↓
[Order]  [Shipping] [Return] [Payment]
```

**적합한 경우**:
- 복잡한 의사결정 계층이 필요한 경우
- 권한/역할이 명확한 경우
- 에스컬레이션이 필요한 경우

**예시 시나리오**:
```
고객: "주문 취소 안 되는데 환불은 가능한가요?"
→ Order Agent: 취소 불가 확인
→ Order Manager: 특별 케이스로 상위 에스컬레이션
→ Senior Manager: 정책 예외 승인
→ Payment Agent: 환불 처리
```

**구현 예시**:
```python
from strands import Agent, Hierarchy

# 계층 구조 정의
support_hierarchy = Hierarchy(
    levels={
        "senior": senior_manager_agent,
        "manager": [order_manager_agent, return_manager_agent],
        "specialist": [orders_agent, shipping_agent, returns_agent]
    },
    escalation_rules={
        "취소불가+환불요청": "senior",
        "재고부족": "manager"
    }
)

# 계층적 처리
result = await support_hierarchy.process(customer_query)
```

---

### 5️⃣ Workflow Orchestration 패턴

**개념**: 정의된 순서대로 에이전트들이 작업 수행

```
[Step 1: 주문확인]
        ↓
[Step 2: 재고확인]
        ↓
[Step 3: 배송정보]
        ↓
[Step 4: 최종응답]
```

**적합한 경우**:
- 명확한 순서가 있는 프로세스
- 각 단계의 출력이 다음 단계의 입력이 되는 경우
- 체크리스트 형태의 작업

**예시 시나리오**:
```
고객: "새 주문하고 싶어요"
→ Step 1: Product Agent - 상품 정보 확인
→ Step 2: Inventory Agent - 재고 확인
→ Step 3: Pricing Agent - 가격 계산
→ Step 4: Order Agent - 주문 생성
→ Step 5: Notification Agent - 확인 이메일 발송
```

**구현 예시**:
```python
from strands import Agent, Workflow

# 순차적 워크플로우 정의
order_workflow = Workflow(
    steps=[
        ("product_check", product_agent),
        ("inventory_check", inventory_agent),
        ("pricing", pricing_agent),
        ("order_creation", order_agent),
        ("notification", notification_agent)
    ]
)

# 워크플로우 실행
result = await order_workflow.execute(order_request)
```

---

## 향후 확장 권장 사항

### 🎯 단기 (1-3개월)

**1. A2A 패턴 추가**
- 주문 취소 시 배송/결제 에이전트 간 통신 필요
- 복잡한 고객 문의 처리 향상

```python
# 예시: 주문 취소 시나리오
orders_agent.send_to_peer("shipping_agent", "배송 중지")
orders_agent.send_to_peer("payment_agent", "환불 처리")
```

**2. 병렬 처리 (Swarm 부분 도입)**
- 여러 주문 동시 조회
- 대량 문의 처리

### 🚀 중기 (3-6개월)

**3. Graph-Based 패턴**
- 복잡한 반품/교환 프로세스
- 조건부 워크플로우 구현

**4. Session Management**
- 대화 컨텍스트 유지
- 이전 문의 이력 참조

### 🌟 장기 (6-12개월)

**5. Hierarchical + A2A 하이브리드**
- 복잡한 에스컬레이션
- VIP 고객 처리

**6. Self-Improving Agents**
- 고객 피드백 학습
- 성능 최적화

---

## 패턴 선택 가이드

| 시나리오 | 추천 패턴 | 이유 |
|---------|----------|------|
| 단순 문의 라우팅 | Orchestrator + Tools ⭐ (현재) | 간단하고 명확함 |
| 복잡한 취소/환불 | A2A | 여러 시스템 간 조율 필요 |
| 대량 주문 조회 | Swarm | 병렬 처리로 성능 향상 |
| 조건부 프로세스 | Graph | 복잡한 비즈니스 로직 |
| 권한 기반 처리 | Hierarchical | 에스컬레이션 필요 |
| 정형화된 프로세스 | Workflow | 단계별 검증 필요 |

---

## 하이브리드 패턴 예시

실제 프로덕션에서는 여러 패턴을 조합합니다:

```python
from strands import Agent, Graph, Swarm, A2AProtocol

# 하이브리드: Graph + Swarm + A2A
support_system = Graph(
    nodes=[
        GraphNode(
            id="classify",
            agent=orchestrator,  # 기존 orchestrator 재사용
        ),
        GraphNode(
            id="parallel_check",
            agent=Swarm(  # 병렬 처리
                agents=[orders_agent, shipping_agent, inventory_agent],
                strategy="parallel"
            ),
            next="consolidate"
        ),
        GraphNode(
            id="consolidate",
            agent=consolidator_agent,  # 결과 통합
            a2a_enabled=True  # 다른 에이전트와 통신 가능
        )
    ]
)
```

---

## 참고 자료

- **Strands Agents SDK 공식 문서**: https://strandsagents.com/latest/documentation/docs/
- **Multi-Agent 예시**: https://github.com/strands-agents/sdk-python
- **A2A Protocol**: Strands Agents 1.0 릴리즈 노트
- **AWS 블로그**: "Strands Agents SDK: A technical deep dive"

---

## 마이그레이션 로드맵

### Phase 1: 현재 → A2A (2-4주)
```
Orchestrator + Tools → Orchestrator + A2A-enabled Sub-Agents
```
- 기존 코드 90% 재사용
- Sub-agent 간 통신 추가

### Phase 2: A2A → Graph (4-8주)
```
Linear Routing → Conditional Graph
```
- 복잡한 워크플로우 지원
- 조건부 라우팅

### Phase 3: Graph → Hybrid (8-12주)
```
Single Pattern → Graph + Swarm + A2A
```
- 최적의 성능과 유연성
- 프로덕션 준비 완료
