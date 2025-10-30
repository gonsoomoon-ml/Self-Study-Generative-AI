# Agent + Tools 패턴 구현

## 개요
이 폴더는 **Orchestrator + Tools** 패턴의 원본 구현을 포함합니다.

## 패턴 설명
- **Orchestrator Agent**: 고객 문의를 분석하고 적절한 서브 에이전트로 라우팅
- **Sub-Agents as Tools**: 각 서브 에이전트가 도구(tool)로 정의됨

## 파일 구조
```
agent_tool_pattern/
├── orchestrator_agent.py    # 메인 오케스트레이터
├── sub_agent_orders.py       # 주문/배송 서브 에이전트
├── sub_agent_returns.py      # 반품/결제 서브 에이전트
├── main.py                   # 테스트 스크립트
└── README.md                 # 이 파일
```

## 실행 방법
```bash
cd agent_tool_pattern
uv run python main.py
```

## 특징
✅ **장점**:
- 단순하고 이해하기 쉬움
- 빠른 프로토타이핑
- 중앙 집중식 제어

⚠️ **제한사항**:
- 순차적 처리만 가능
- 복잡한 조건부 로직 어려움
- 에이전트 간 직접 통신 불가

## 다음 단계
더 복잡한 시나리오를 위해서는 **Graph + Hierarchical Hybrid** 패턴을 권장합니다.
👉 `/hybrid` 폴더 참고
