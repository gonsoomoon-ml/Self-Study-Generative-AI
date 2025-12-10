# Strands Agent 세션 관리: FileSessionManager, AgentCore Memory, LangGraph 비교.

## 요약

### 한눈에 보는 세션 관리 방식 비교

| 항목 | Strands (File) | Strands (AgentCore) | LangGraph |
|------|----------------|---------------------|-----------|
| **세션 식별자** | `session_id` | `session_id` + `actor_id` | `thread_id` |
| **저장 위치** | 로컬 디스크 (JSON) | AWS 클라우드 (관리형) | 메모리/DB (선택) |
| **영속성 레이어** | `FileSessionManager` | `AgentCoreMemorySessionManager` | `Checkpointer` |
| **확장성** | 단일 서버 | 분산, 확장 가능 | DB 선택에 따름 |
| **장기 메모리** | 없음 | 있음 (LTM 전략) | Store (크로스 스레드) |
| **설정 복잡도** | 간단 | AWS 설정 필요 | 간단~중간 |
| **비용** | 무료 | AWS 요금 | DB 비용 (선택적) |

### 핵심 코드 패턴

**1. Strands + FileSessionManager (로컬)**
```python
from strands import Agent
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(session_id="user-123", storage_dir="./sessions")
agent = Agent(session_manager=session_manager)
agent("안녕하세요!")  # 자동으로 디스크에 저장
```

**2. Strands + AgentCore Memory (AWS)**
```python
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig

config = AgentCoreMemoryConfig(memory_id="my-memory", session_id="session-123", actor_id="actor-123")
session_manager = AgentCoreMemorySessionManager(agentcore_memory_config=config, region_name="us-east-1")
agent = Agent(session_manager=session_manager)
```

**3. LangGraph + Checkpointer**
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
graph.invoke(input, {"configurable": {"thread_id": "user-123"}})
```

### 빠른 선택 가이드

| 상황 | 권장 방식 |
|------|----------|
| 로컬 개발/테스트 | Strands + FileSessionManager |
| AWS 프로덕션 배포 | Strands + AgentCore Memory |
| 서버리스/Lambda | Strands + AgentCore Memory |
| 복잡한 그래프 워크플로우 | LangGraph + Checkpointer |
| 기존 PostgreSQL/MongoDB 활용 | LangGraph + 해당 Saver |

---

## 개요

### 세션 관리란?

세션 관리는 AI 에이전트와의 **대화 내용과 상태를 저장/복원**하는 기능입니다.

### 왜 필요한가?

세션 관리 없이 에이전트를 사용하면:
- 앱 재시작 시 이전 대화 내용을 **모두 잊어버림**
- 사용자 정보, 선호도 등이 **유지되지 않음**
- 매번 처음부터 대화를 시작해야 함

→ `demo1_no_session.py`에서 이 문제를 직접 확인할 수 있습니다.

### 이 문서에서 다루는 내용

1. **FileSessionManager**: 로컬 파일 기반 세션 저장
2. **AgentCoreMemorySessionManager**: AWS 클라우드 기반 세션 저장
3. **agent.state**: 커스텀 애플리케이션 상태 저장
4. **LangGraph 비교**: Checkpointer와의 비교

---

## 빠른 시작

### 사전 준비

- Python 3.11+
- uv (Python 패키지 관리자)
- AWS 자격 증명 (AgentCore Memory 사용 시)

### 설치 방법

```bash
cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
cd setup
uv sync
cd ..
```

### 가장 간단한 예제

```python
from strands import Agent
from strands.session.file_session_manager import FileSessionManager

# 세션 관리자 생성
session_manager = FileSessionManager(
    session_id="user-alice",      # 사용자별 고유 ID
    storage_dir="./sessions"       # 저장 디렉토리
)

# 에이전트 생성
agent = Agent(session_manager=session_manager)

# 대화 (자동으로 저장됨)
agent("안녕하세요! 저는 김철수입니다.")
agent("제 이름이 뭐였죠?")  # "김철수"를 기억함

# 앱 재시작 후에도 같은 session_id로 복원 가능
```

---

## 데모 파일 안내

### 실행 방법

```bash
cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
uv run python code/demo1_no_session.py
```

### 데모 목록

| 파일 | 설명 | 핵심 개념 |
|------|------|----------|
| `demo1_no_session.py` | 세션 없는 에이전트 | 문제점 확인 (메모리 손실) |
| `demo2_with_session.py` | FileSessionManager 사용 | session_id, 다중 사용자 격리 |
| `demo3_agentcore_memory.py` | AgentCore Memory 사용 | AWS 클라우드 저장, actor_id |
| `demo4_langgraph_session.py` | LangGraph Checkpointer | thread_id, 비교 분석 |
| `demo5_agent_state.py` | agent.state (File) | 커스텀 상태 저장 |
| `demo6_agentcore_state.py` | agent.state (AgentCore) | 클라우드 상태 저장 |
| `demo7_cleanup.py` | 정리 도구 | 로컬 세션, AgentCore Memory 삭제 |

### 권장 학습 순서

1. **demo1** → 문제 이해
2. **demo2** → 기본 해결책 (FileSessionManager)
3. **demo5** → agent.state 사용법
4. **demo3** → 프로덕션 환경 (AgentCore)
5. **demo4** → LangGraph 비교
6. **demo6** → AgentCore + agent.state
7. **demo7** → 정리

---

## FileSessionManager 동작 방식

### 디렉토리 구조

```
SESSIONS_DIR (하나의 저장 위치)
├── session_user-alice/      ← session_id="user-alice"
├── session_user-bob/        ← session_id="user-bob"
├── session_user-carol/      ← session_id="user-carol"
└── ...
```

### 사용 패턴

```python
# 앱 전체에서 공유하는 하나의 저장 위치
SESSIONS_DIR = "./sessions"

# 사용자 "alice"가 접속할 때:
session_manager_alice = FileSessionManager(
    session_id="user-alice",      # 사용자별 고유 ID
    storage_dir=SESSIONS_DIR       # 모든 사용자가 같은 위치 사용
)
agent_alice = Agent(session_manager=session_manager_alice)

# 사용자 "bob"이 접속할 때:
session_manager_bob = FileSessionManager(
    session_id="user-bob",         # 다른 session_id
    storage_dir=SESSIONS_DIR       # 같은 저장 위치
)
agent_bob = Agent(session_manager=session_manager_bob)
```

### 핵심 포인트

| 항목 | 설명 |
|------|------|
| `SESSIONS_DIR` | 앱 전체에서 공유하는 하나의 저장 위치 |
| `session_id` | 사용자/연결별 고유 식별자 |
| Session Manager 객체 | 각 사용자마다 별도의 객체 생성 |
| Agent 객체 | 각 사용자마다 별도의 객체 생성 |
| 세션 격리 | `session_id`로 구분 (객체가 아님) |

### 동작 흐름

```
1. 사용자 접속
   └── session_id 생성 (예: "user-alice")

2. FileSessionManager 생성
   └── session_id + SESSIONS_DIR 조합으로 저장 경로 결정

3. Agent 생성
   └── session_manager를 주입받아 사용

4. 대화 진행
   └── 메시지가 자동으로 디스크에 저장됨

5. 앱 재시작 또는 재접속
   └── 같은 session_id로 새 객체 생성
   └── 기존 대화 내역이 디스크에서 자동 로드됨
```

### 중요한 점

- **Session Manager 객체**는 사용자마다 새로 생성됩니다
- **하지만** 같은 `session_id`를 사용하면 같은 세션 데이터에 접근합니다
- 세션 데이터는 **디스크(파일)**에 저장되므로, 앱이 재시작되어도 유지됩니다
- 객체가 달라도 `session_id`가 같으면 = 같은 세션

### 저장 구조

```
sessions/
└── session_user-alice/
    ├── session.json
    └── agents/
        └── agent_default/
            ├── agent.json          ← agent.state 저장 위치
            └── messages/
                ├── message_0.json
                └── message_1.json
```

---

## agent.state: 커스텀 애플리케이션 상태 저장

### 개요

`agent.state`는 대화 내역(messages) 외에 **커스텀 애플리케이션 데이터**를 저장하는 기능입니다.

| 항목 | Conversation History | agent.state |
|------|---------------------|-------------|
| 저장 내용 | 메시지 (user/assistant) | 커스텀 데이터 (dict) |
| 자동 저장 | 예 (agent 호출 시) | 예 (agent 호출 시) |
| 용도 | 대화 맥락 유지 | 앱 상태 저장 |
| 예시 | "내 이름은 Alice야" | {"theme": "dark"} |

### 사용법

```python
from strands import Agent
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(session_id="user-alice", storage_dir="./sessions")
agent = Agent(session_manager=session_manager)

# 상태 저장 - set() 메서드 사용 (직접 할당 불가)
agent.state.set("user_preferences", {"theme": "dark", "language": "ko"})
agent.state.set("visit_count", 1)
agent.state.set("favorite_languages", ["Python", "TypeScript"])

# 상태 조회 - get() 메서드 사용
prefs = agent.state.get("user_preferences")  # {"theme": "dark", "language": "ko"}
count = agent.state.get("visit_count")        # 1
all_data = agent.state.get()                  # 전체 데이터 dict 반환

# agent 호출 시 자동으로 디스크에 저장됨
agent("Hello!")
```

### 주의사항

```python
# ❌ 잘못된 사용법 - 직접 할당 불가
agent.state["key"] = value  # TypeError 발생!

# ✅ 올바른 사용법 - set() 메서드 사용
agent.state.set("key", value)

# ❌ get()에 기본값 파라미터 없음
agent.state.get("key", default_value)  # TypeError 발생!

# ✅ or 연산자로 기본값 처리
value = agent.state.get("key") or default_value
```

### 저장 위치

`agent.state`는 `agent.json` 파일에 저장됩니다:

```
sessions/
└── session_user-alice/
    ├── session.json
    └── agents/
        └── agent_default/
            ├── agent.json          ← agent.state 저장 위치
            └── messages/
                └── message_0.json
```

**agent.json 내용 예시:**
```json
{
    "agent_id": "default",
    "state": {
        "user_preferences": {
            "theme": "dark",
            "language": "ko"
        },
        "visit_count": 2,
        "favorite_languages": ["Python", "TypeScript"]
    },
    "conversation_manager_state": {
        "__name__": "SlidingWindowConversationManager",
        "removed_message_count": 0
    },
    "created_at": "2025-12-07T08:44:17.910403+00:00",
    "updated_at": "2025-12-07T08:44:20.725523+00:00"
}
```

### 활용 사례

- 사용자 설정 (테마, 언어, 알림)
- 방문 횟수, 사용 통계
- 장바구니, 폼 데이터
- 애플리케이션별 컨텍스트
- 사용자별 기능 플래그

### agent.state 저장 위치 비교: FileSessionManager vs AgentCore Memory

| 항목 | FileSessionManager | AgentCore Memory |
|------|-------------------|------------------|
| **저장 위치** | 로컬 디스크 (`agent.json`) | AWS 클라우드 (이벤트) |
| **식별자** | 파일 경로 | `actorId: agent_default` |
| **저장 방식** | JSON 파일 덮어쓰기 | 불변(immutable) 이벤트 추가 |
| **히스토리** | 없음 (덮어쓰기) | 있음 (이벤트 히스토리) |

#### AgentCore Memory에서 agent.state 저장 방식

AgentCore Memory는 **불변(immutable) 이벤트** 기반으로 동작합니다:

```
agent.state 업데이트 시:
┌─────────────────────────────────────────────────────────────┐
│ Event 0 (최신) ← read_agent()가 가져오는 이벤트            │
│   eventId: 0000001765098154244#64a69027                     │
│   actorId: agent_default                                    │
│   state: { visit_count: 2, last_topic: "updated" }          │
├─────────────────────────────────────────────────────────────┤
│ Event 1 (이전)                                              │
│   eventId: 0000001765098153244#d3b5cded                     │
│   state: { visit_count: 1, last_topic: "original" }         │
├─────────────────────────────────────────────────────────────┤
│ Event 2 (더 이전)                                           │
│   ...                                                       │
└─────────────────────────────────────────────────────────────┘
```

**이벤트 데이터 구조:**
```json
{
  "agent_id": "default",
  "state": {
    "user_preferences": {
      "theme": "dark",
      "language": "ko"
    },
    "visit_count": 2,
    "last_topic": "agent.state with AgentCore",
    "favorite_languages": ["Python", "TypeScript"]
  },
  "conversation_manager_state": {
    "__name__": "SlidingWindowConversationManager",
    "removed_message_count": 0
  },
  "created_at": "2025-12-07T09:00:05.082220+00:00",
  "updated_at": "2025-12-07T09:02:31.064758+00:00"
}
```

**AgentCore Memory 이벤트 조회:**
```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")
events = client.list_events(
    memory_id="my-memory-id",
    actor_id="agent_default",      # Agent 이벤트는 'agent_' 프리픽스 사용
    session_id="session-alice",
    max_results=5
)

# events[0]이 가장 최신 상태 (agent.state 포함)
```

---

## 세션 관리 방식 상세 비교

### 1. Strands Agent + FileSessionManager

**특징:**
- 로컬 파일 시스템에 JSON 파일로 저장
- 개발/테스트 환경에 적합
- 단일 서버 배포에 적합

**코드 패턴:**
```python
from strands import Agent
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(
    session_id="user-alice",
    storage_dir="./sessions"
)
agent = Agent(session_manager=session_manager)
agent("안녕하세요!")  # 자동으로 디스크에 저장됨
```

### 2. Strands Agent + AgentCore Memory

**특징:**
- AWS Bedrock AgentCore에 저장
- 단기 메모리 (STM): 대화 지속성
- 장기 메모리 (LTM): 사용자 선호도, 팩트, 요약 자동 추출
- 프로덕션/서버리스 환경에 적합

**코드 패턴:**
```python
from strands import Agent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig

config = AgentCoreMemoryConfig(
    memory_id="my-memory-id",
    session_id="session-alice",
    actor_id="actor-alice"
)
session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=config,
    region_name="us-east-1"
)
agent = Agent(session_manager=session_manager)
agent("안녕하세요!")  # AWS 클라우드에 저장됨
```

**LTM 전략:**
- `summaryMemoryStrategy`: 세션 요약
- `userPreferenceMemoryStrategy`: 사용자 선호도 학습
- `semanticMemoryStrategy`: 팩트 추출

### 3. LangGraph + Checkpointer

**특징:**
- 그래프 상태를 체크포인트로 저장
- 다양한 백엔드 지원 (Memory, PostgreSQL, MongoDB, Redis)
- 그래프 기반 워크플로우에 적합

**코드 패턴:**
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# 체크포인터 생성
checkpointer = MemorySaver()  # 또는 PostgresSaver, MongoDBSaver

# 그래프 컴파일 시 체크포인터 연결
graph = builder.compile(checkpointer=checkpointer)

# 호출 시 thread_id로 세션 식별
graph.invoke(
    {"messages": [{"role": "user", "content": "안녕하세요!"}]},
    {"configurable": {"thread_id": "user-alice"}}
)
```

**상태 조회:**
```python
config = {"configurable": {"thread_id": "user-alice"}}
state = graph.get_state(config)       # 현재 상태
history = graph.get_state_history(config)  # 전체 히스토리
```

### Strands vs LangGraph 비교

| 항목 | Strands Agent | LangGraph |
|------|---------------|-----------|
| 세션 식별자 | `session_id` | `thread_id` |
| 지속성 레이어 | `SessionManager` | `Checkpointer` |
| 기본 제공 백엔드 | File, S3, AgentCore | Memory, Postgres, MongoDB |
| 상태 저장 | messages + agent.state | Graph state (TypedDict) |
| 멀티 에이전트 | Orchestrator만 | 그래프의 각 노드 |
| 커스텀 상태 | agent.state dict | Custom TypedDict 필드 |
| 장기 메모리 | AgentCore Memory (LTM) | Store (크로스 스레드) |
