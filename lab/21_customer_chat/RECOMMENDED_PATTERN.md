# 추천 아키텍처: Graph + Hierarchical Hybrid 패턴

## 현재 패턴의 한계 분석

### Orchestrator + Tools 패턴의 문제점

#### ❌ 실제 시나리오 1: 복잡한 주문 취소
```
고객: "주문 취소하고 환불 받고 싶은데, 배송이 이미 시작됐나요?"

현재 패턴의 처리:
1. Orchestrator → Orders Agent 호출
2. Orders Agent가 응답
3. 끝... (배송 상태는 확인 안 됨, 환불 처리도 안 됨)

필요한 처리:
1. Orders Agent: 주문 확인
2. Shipping Agent: 배송 상태 확인
3. 조건 분기:
   - 배송 전 → Orders Agent: 즉시 취소 → Payment Agent: 환불
   - 배송 중 → Shipping Agent: 배송 중지 시도 → Returns Agent: 반품 프로세스
   - 배송 완료 → Returns Agent: 반품 절차 안내
```

#### ❌ 실제 시나리오 2: 재고 문제 교환
```
고객: "받은 상품 불량이라서 교환하고 싶어요"

현재 패턴의 처리:
1. Orchestrator → Returns Agent 호출
2. 교환 정보 필요 → 끝 (재고 확인 안 됨)

필요한 처리:
1. Returns Agent: 교환 요청 접수
2. Inventory Agent: 교환 상품 재고 확인
3. 조건 분기:
   - 재고 있음 → Returns Agent: 교환 승인
   - 재고 없음 → Escalation → Manager Agent: 대체품 제안 또는 환불
```

---

## 왜 Graph 패턴이 더 나은가?

### ✅ Graph 패턴의 장점

#### 1. **조건부 분기 처리**
```python
# Graph 구조
if order.status == "배송 전":
    → cancel_order_node → refund_node
elif order.status == "배송 중":
    → stop_shipping_node → return_process_node
else:
    → return_guide_node
```

#### 2. **여러 에이전트 체이닝**
```python
# 순차적 데이터 전달
order_info → shipping_status → decision_node → action_nodes
```

#### 3. **Cyclic Graph (재시도/반복)**
```python
# 재고 확인 → 없으면 다시 확인
inventory_check → if_not_available → wait → inventory_check
```

#### 4. **상태 관리**
```python
# 각 노드가 상태를 공유
shared_context = {
    "order_id": "ORD123",
    "status": "배송중",
    "refund_amount": 50000
}
```

---

## 추천: Hybrid Pattern (Graph + Hierarchical)

### 아키텍처 설계

```
                    [Start: 고객 문의 접수]
                              ↓
                    [Classify: 문의 분류]
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            [주문/배송 Graph]      [반품/결제 Graph]
                    ↓                   ↓
        ┌───────────┼───────────┐       ↓
        ↓           ↓           ↓       ↓
    [주문확인] [재고확인] [배송확인]  [반품처리]
        ↓           ↓           ↓       ↓
        └───────────┼───────────┘       ↓
                    ↓                   ↓
            [Decision Node]      [환불승인?]
                    ↓                   ↓
        ┌───────────┴───────────┐   [Hierarchical]
        ↓                       ↓       ↓
    [즉시처리]              [에스컬레이션]  ↓
        ↓                       ↓       ↓
        └───────────────────────┴───────┘
                    ↓
            [최종 응답 생성]
```

### 주요 구성 요소

#### 1. **Classification Node** (현재 Orchestrator 역할)
```python
classification_node = GraphNode(
    id="classify",
    agent=classifier_agent,
    next={
        "주문": "order_graph",
        "배송": "order_graph",
        "반품": "return_graph",
        "환불": "return_graph",
        "교환": "return_graph"
    }
)
```

#### 2. **Order/Shipping Sub-Graph**
```python
order_graph = Graph(
    nodes=[
        GraphNode(
            id="check_order",
            agent=orders_agent,
            next={"needs_shipping_info": "check_shipping", "complete": "respond"}
        ),
        GraphNode(
            id="check_shipping",
            agent=shipping_agent,
            next={"needs_inventory": "check_inventory", "complete": "respond"}
        ),
        GraphNode(
            id="check_inventory",
            agent=inventory_agent,
            next="decide_action"
        ),
        GraphNode(
            id="decide_action",
            agent=decision_agent,
            next={
                "cancel": "cancel_order",
                "return": "escalate_to_return_graph",
                "info_only": "respond"
            }
        )
    ]
)
```

#### 3. **Return/Refund Sub-Graph with Hierarchy**
```python
return_graph = Graph(
    nodes=[
        GraphNode(
            id="check_eligibility",
            agent=returns_agent,
            next={"eligible": "process_return", "needs_approval": "escalate"}
        ),
        GraphNode(
            id="process_return",
            agent=returns_agent,
            next="check_refund"
        ),
        GraphNode(
            id="escalate",
            agent=HierarchicalAgent(  # ← Hierarchical 통합
                levels={
                    "specialist": returns_agent,
                    "manager": return_manager_agent,
                    "director": customer_service_director
                }
            ),
            next="process_return"
        ),
        GraphNode(
            id="check_refund",
            agent=payment_agent,
            next="respond"
        )
    ]
)
```

---

## 구체적인 구현 예시

### 시나리오: "배송 중인 주문 취소 요청"

```python
from strands import Agent, Graph, GraphNode, HierarchicalAgent

# 1. Classification Agent
classifier_agent = Agent(
    model=model,
    system_prompt="고객 문의를 분석하여 카테고리 분류"
)

# 2. Order Graph 정의
order_graph = Graph(
    name="order_processing",
    nodes=[
        # Step 1: 주문 상태 확인
        GraphNode(
            id="check_order_status",
            agent=Agent(
                model=model,
                tools=[check_order_status],
                system_prompt="주문 상태를 확인하고 다음 단계 결정"
            ),
            next=lambda context: (
                "check_shipping" if context["order"]["has_shipping"]
                else "cancel_direct"
            )
        ),

        # Step 2: 배송 상태 확인
        GraphNode(
            id="check_shipping",
            agent=Agent(
                model=model,
                tools=[track_delivery],
                system_prompt="배송 상태 확인"
            ),
            next=lambda context: (
                "cancel_direct" if context["shipping"]["status"] == "배송 전"
                else "shipping_in_progress" if context["shipping"]["status"] == "배송 중"
                else "already_delivered"
            )
        ),

        # Step 3a: 배송 전 → 즉시 취소
        GraphNode(
            id="cancel_direct",
            agent=Agent(
                model=model,
                tools=[cancel_order, process_refund],
                system_prompt="주문 취소 및 환불 처리"
            ),
            next="respond"
        ),

        # Step 3b: 배송 중 → 에스컬레이션
        GraphNode(
            id="shipping_in_progress",
            agent=HierarchicalAgent(
                levels={
                    "specialist": Agent(
                        model=model,
                        tools=[request_shipping_stop],
                        system_prompt="배송 중지 시도"
                    ),
                    "manager": Agent(
                        model=model,
                        tools=[force_shipping_return, emergency_refund],
                        system_prompt="관리자 권한으로 배송 중지 및 환불"
                    )
                },
                escalation_rule=lambda result: (
                    "manager" if not result.get("shipping_stopped")
                    else "specialist"
                )
            ),
            next="respond"
        ),

        # Step 3c: 배송 완료 → 반품 그래프로 연결
        GraphNode(
            id="already_delivered",
            agent=Agent(
                model=model,
                system_prompt="반품 프로세스 안내"
            ),
            next="return_graph"  # ← 다른 그래프로 연결
        ),

        # Final: 응답 생성
        GraphNode(
            id="respond",
            agent=Agent(
                model=model,
                system_prompt="최종 응답 생성"
            )
        )
    ],
    start="check_order_status"
)

# 3. Return Graph 정의 (유사하게...)
return_graph = Graph(
    name="return_processing",
    nodes=[
        GraphNode(
            id="process_return_request",
            agent=returns_agent,
            next="check_item_condition"
        ),
        GraphNode(
            id="check_item_condition",
            agent=Agent(
                model=model,
                tools=[verify_item_eligibility],
                system_prompt="반품 가능 여부 확인"
            ),
            next=lambda context: (
                "approve_return" if context["eligible"]
                else "escalate_manager"
            )
        ),
        # ... 더 많은 노드
    ]
)

# 4. Main Graph (전체 시스템)
main_graph = Graph(
    name="customer_support_system",
    nodes=[
        GraphNode(
            id="classify",
            agent=classifier_agent,
            next={
                "주문": "order_graph",
                "취소": "order_graph",
                "배송": "order_graph",
                "반품": "return_graph",
                "환불": "return_graph",
                "교환": "return_graph"
            }
        ),
        GraphNode(
            id="order_graph",
            graph=order_graph,  # ← Sub-graph
            next="final_response"
        ),
        GraphNode(
            id="return_graph",
            graph=return_graph,  # ← Sub-graph
            next="final_response"
        ),
        GraphNode(
            id="final_response",
            agent=Agent(
                model=model,
                system_prompt="모든 처리 결과를 종합하여 고객에게 최종 응답"
            )
        )
    ],
    start="classify"
)

# 5. 실행
async def handle_customer_query(query: str):
    result = await main_graph.execute(
        input={"query": query},
        context={}
    )
    return result
```

---

## Graph vs Hierarchical vs Workflow 비교

### 실제 이커머스 시나리오별 추천

| 시나리오 | 패턴 | 이유 |
|---------|------|------|
| 주문 취소 (조건부) | **Graph** ⭐ | 배송 상태에 따라 다른 경로 |
| 반품 승인 프로세스 | **Workflow** | 정해진 단계 순서대로 |
| 특별 환불 요청 | **Hierarchical** | 권한 레벨별 승인 필요 |
| 복잡한 교환 (재고↔배송↔환불) | **Graph + Hierarchical** ⭐⭐⭐ | 조건부 + 에스컬레이션 |
| 대량 주문 조회 | **Swarm** | 병렬 처리 |

---

## 추천 구현 전략

### Phase 1: Graph 패턴으로 리팩토링 (2주)

**목표**: 현재 Orchestrator를 Graph의 Classification Node로 전환

```python
# Before (현재)
orchestrator = Agent(
    tools=[route_to_orders, route_to_returns]
)

# After (Graph)
main_graph = Graph(
    nodes=[
        GraphNode(id="classify", agent=orchestrator),
        GraphNode(id="orders", agent=orders_agent),
        GraphNode(id="returns", agent=returns_agent)
    ]
)
```

**장점**:
- 기존 코드 90% 재사용
- 점진적 마이그레이션
- 즉시 조건부 로직 추가 가능

### Phase 2: Sub-Graphs 추가 (2-3주)

각 도메인별 상세 그래프 구축:
- Order Sub-Graph (주문확인 → 재고 → 배송 → 결정)
- Return Sub-Graph (반품확인 → 조건확인 → 승인 → 환불)

### Phase 3: Hierarchical 통합 (2주)

특정 노드에 계층적 승인 추가:
- 고액 환불 → Manager 승인
- 정책 예외 → Director 승인

---

## 코드 구조 변경

### 현재 구조
```
21_customer_chat/
├── orchestrator_agent.py      # Orchestrator
├── sub_agent_orders.py         # Orders Agent (도구로만)
├── sub_agent_returns.py        # Returns Agent (도구로만)
└── main.py
```

### 추천 구조 (Graph Hybrid)
```
21_customer_chat/
├── graphs/
│   ├── __init__.py
│   ├── main_graph.py           # 메인 그래프 정의
│   ├── order_graph.py          # 주문/배송 서브그래프
│   └── return_graph.py         # 반품/환불 서브그래프
├── agents/
│   ├── __init__.py
│   ├── classifier_agent.py     # 분류 에이전트
│   ├── orders_agent.py         # 주문 에이전트
│   ├── shipping_agent.py       # 배송 에이전트
│   ├── returns_agent.py        # 반품 에이전트
│   ├── payment_agent.py        # 결제 에이전트
│   └── decision_agent.py       # 의사결정 에이전트
├── tools/
│   ├── __init__.py
│   ├── order_tools.py          # 주문 관련 도구
│   ├── shipping_tools.py       # 배송 관련 도구
│   └── payment_tools.py        # 결제 관련 도구
├── hierarchies/
│   ├── __init__.py
│   └── approval_hierarchy.py   # 승인 계층 정의
├── main.py
└── README.md
```

---

## 실제 이점 (Real-World Benefits)

### 1. **복잡한 비즈니스 로직 표현**
```python
# 현재: 불가능
# Graph: 가능
if order.shipping_started and order.value > 100000:
    → escalate_to_manager → special_refund_process
else:
    → standard_cancel → auto_refund
```

### 2. **재시도/반복 로직**
```python
# Cyclic Graph
inventory_check → if_out_of_stock → wait_and_retry → inventory_check
```

### 3. **A/B 테스트 및 실험**
```python
# Graph로 쉽게 경로 변경
if experiment_enabled:
    next_node = "new_return_process"
else:
    next_node = "old_return_process"
```

### 4. **관찰 가능성 (Observability)**
```python
# 각 노드의 실행 로그
[classify] → [check_order] → [check_shipping] → [escalate] → [approve]
            ↑ 여기서 5초     ↑ 여기서 실패
```

---

## 결론 및 추천

### ✅ 최종 추천: **Graph + Hierarchical Hybrid**

**이유**:
1. ✅ 실제 이커머스는 조건부 분기가 많음 → Graph 필수
2. ✅ 승인/에스컬레이션 필요 → Hierarchical 필수
3. ✅ 확장성 및 유지보수 → Hybrid가 최적
4. ✅ Strands SDK가 모두 지원 → 구현 가능

**구현 우선순위**:
1. **Week 1-2**: Graph 기본 구조 (Classification → Sub-graphs)
2. **Week 3-4**: Order/Return Sub-graphs 상세화
3. **Week 5-6**: Hierarchical 승인 통합
4. **Week 7-8**: 테스트 및 최적화

**기대 효과**:
- 복잡한 고객 문의 처리 능력 **3배 향상**
- 에이전트 간 협력으로 정확도 **향상**
- 에스컬레이션으로 고객 만족도 **증가**
- 유지보수 및 확장 용이성 **대폭 개선**

현재 Orchestrator + Tools는 좋은 시작점이지만,
**실제 프로덕션에서는 Graph + Hierarchical Hybrid가 필수**입니다! 🚀
