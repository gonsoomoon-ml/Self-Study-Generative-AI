"""
데모 3: AWS Bedrock AgentCore Memory를 사용한 세션 관리
AgentCoreMemorySessionManager를 사용하여 AWS 클라우드에 대화를 저장합니다.

FileSessionManager vs AgentCore Memory:
- FileSessionManager: 로컬 디스크 저장 (개발/테스트용)
- AgentCore Memory: AWS 클라우드 저장 (프로덕션용)

AgentCore Memory 특징:
- 단기 메모리 (STM): 대화 지속성
- 장기 메모리 (LTM): 사용자 선호도, 팩트, 요약 자동 추출
- 분산/확장 가능한 아키텍처

사전 준비:
    1. AWS 자격 증명 설정
    2. 설치: pip install 'bedrock-agentcore[strands-agents]'
    3. Bedrock AgentCore 접근 권한

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo3_agentcore_memory.py
"""
import time
from strands import Agent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from utils import print_header, print_system, print_success, print_separator, print_error, chat


# ----------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------
AWS_REGION = "us-east-1"
MEMORY_NAME = "strands_session_demo"  # 메모리 리소스 이름 (언더스코어 사용, 하이픈 불가)
SESSION_ID_ALICE = "session-alice"    # Alice의 세션 ID
SESSION_ID_BOB = "session-bob"        # Bob의 세션 ID
ACTOR_ID_ALICE = "actor-alice"        # Alice의 액터 ID
ACTOR_ID_BOB = "actor-bob"            # Bob의 액터 ID


# ----------------------------------------------------------------------
# 헬퍼 함수
# ----------------------------------------------------------------------
def create_or_get_memory(client: MemoryClient, name: str) -> str:
    """메모리 리소스를 생성하거나 기존 것을 가져옵니다.

    Args:
        client: AgentCore 메모리 클라이언트
        name: 메모리 리소스 이름

    Returns:
        str: 메모리 ID
    """
    # 기존 메모리 확인
    try:
        memories = client.list_memories()
        # list 또는 dict 응답 형식 모두 처리
        memory_list = memories if isinstance(memories, list) else memories.get("memories", [])
        for memory in memory_list:
            # 메모리 ID는 이름으로 시작함 (예: "strands_session_demo-Qpy1hz77A2")
            memory_id = memory.get("memoryId") or memory.get("memory_id") or memory.get("id")
            if memory_id and memory_id.startswith(name):
                status = memory.get("status", "UNKNOWN")
                if status == "ACTIVE":
                    print(f"기존 메모리 사용: {memory_id} (상태: {status})")
                    return memory_id
                else:
                    print(f"메모리 {memory_id} 발견, 상태: {status}, 대기 중...")
                    return wait_for_memory_active(client, memory_id)
    except Exception as e:
        print(f"참고: 메모리 목록 조회 실패: {e}")

    # 새 메모리 생성
    response = client.create_memory(
        name=name,
        description="Strands 세션 관리 데모용 메모리"
    )
    memory_id = response.get("memoryId") or response.get("memory_id")
    print(f"새 메모리 생성됨: {memory_id}")

    # 메모리가 활성화될 때까지 대기
    return wait_for_memory_active(client, memory_id)


def wait_for_memory_active(client: MemoryClient, memory_id: str, max_wait: int = 60) -> str:
    """메모리가 활성화될 때까지 대기합니다.

    Args:
        client: AgentCore 메모리 클라이언트
        memory_id: 메모리 ID
        max_wait: 최대 대기 시간 (초)

    Returns:
        str: 활성화된 메모리 ID

    Raises:
        Exception: 메모리 활성화 실패 시
    """
    print(f"메모리 활성화 대기 중...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            memory = client.get_memory(memoryId=memory_id)
            status = memory.get("status", "UNKNOWN")
            print(f"  메모리 상태: {status}")

            if status == "ACTIVE":
                print(f"메모리가 활성화되었습니다!")
                return memory_id
            elif status in ["FAILED", "DELETED"]:
                raise Exception(f"메모리 실패: {status}")
        except Exception as e:
            if "ACTIVE" not in str(e):
                print(f"  상태 확인 중: {e}")

        time.sleep(3)

    raise Exception(f"메모리가 {max_wait}초 내에 활성화되지 않았습니다")


# ----------------------------------------------------------------------
# 에이전트 팩토리
# ----------------------------------------------------------------------
def create_session_manager(memory_id: str, session_id: str, actor_id: str):
    """AgentCore 메모리 세션 관리자를 생성합니다.

    Args:
        memory_id: AgentCore 메모리 리소스 ID
        session_id: 세션 식별자
        actor_id: 액터(사용자) 식별자

    Returns:
        AgentCoreMemorySessionManager: AWS 클라우드 기반 세션 관리자
    """
    config = AgentCoreMemoryConfig(
        memory_id=memory_id,    # 메모리 리소스 ID
        session_id=session_id,  # 세션 식별자
        actor_id=actor_id       # 액터 식별자 (대화 메시지 구분용)
    )
    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=AWS_REGION
    )


def create_agent(session_manager):
    """AgentCore Memory 세션 관리자를 사용하는 에이전트를 생성합니다.

    Args:
        session_manager: AgentCore 메모리 세션 관리자

    Returns:
        Agent: 클라우드 세션 관리 기능이 있는 에이전트
    """
    return Agent(
        system_prompt="당신은 친절한 한국어 도우미입니다. 간결하게 응답하세요.",
        # AgentCoreMemorySessionManager - 세션을 AWS Bedrock AgentCore에 저장
        session_manager=session_manager,
        callback_handler=None  # 스트리밍 출력 비활성화
    )


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 3: Bedrock AgentCore Memory 세션 관리")

    # ------------------------------------------------------------------
    # 초기 설정: AgentCore Memory 리소스 연결
    # ------------------------------------------------------------------
    print_system("설정: Bedrock AgentCore Memory 연결 중...")

    try:
        client = MemoryClient(region_name=AWS_REGION)
        memory_id = create_or_get_memory(client, MEMORY_NAME)
        print(f"메모리 ID: {memory_id}")
        print(f"리전: {AWS_REGION}")
    except Exception as e:
        print_error(f"AgentCore Memory 연결 실패: {e}")
        print("\n다음 사항을 확인하세요:")
        print("  1. AWS 자격 증명이 설정되어 있는지")
        print("  2. pip install 'bedrock-agentcore[strands-agents]' 설치 여부")
        print("  3. AWS 계정에서 Bedrock AgentCore 접근 권한")
        return

    # ------------------------------------------------------------------
    # 단계 1: 사용자 Alice 접속
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 1: 사용자 Alice 접속...")
    print_separator()

    session_manager_alice = create_session_manager(memory_id, SESSION_ID_ALICE, ACTOR_ID_ALICE)
    agent_alice = create_agent(session_manager_alice)

    print(f"모델 ID: {agent_alice.model.config.get('model_id', 'unknown')}")
    print(f"세션 ID: {SESSION_ID_ALICE}")
    print(f"액터 ID: {ACTOR_ID_ALICE}")

    chat(agent_alice, "안녕하세요! 저는 박지영입니다. 다크 모드와 Python을 선호해요.")
    chat(agent_alice, "현재 머신러닝 프로젝트를 진행 중입니다.")

    # ------------------------------------------------------------------
    # 단계 2: 사용자 Bob 접속 (다른 세션)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 사용자 Bob 접속 (다른 세션)...")
    print_separator()

    session_manager_bob = create_session_manager(memory_id, SESSION_ID_BOB, ACTOR_ID_BOB)
    agent_bob = create_agent(session_manager_bob)

    print(f"세션 ID: {SESSION_ID_BOB}")
    print(f"액터 ID: {ACTOR_ID_BOB}")

    chat(agent_bob, "안녕하세요! 저는 최준호입니다. 라이트 모드와 JavaScript를 좋아해요.")
    chat(agent_bob, "제 이름이 뭐죠?")

    # ------------------------------------------------------------------
    # 단계 3: Alice 재접속 (AgentCore Memory에서 세션 복원)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 3: Alice 재접속 (앱 재시작 후)...")
    print_system("Bedrock AgentCore Memory에서 세션 복원 중...")
    print_separator()

    # 새로운 세션 관리자 생성 - AgentCore Memory에서 데이터 로드
    restored_session_manager_alice = create_session_manager(memory_id, SESSION_ID_ALICE, ACTOR_ID_ALICE)
    restored_agent_alice = create_agent(restored_session_manager_alice)

    print(f"세션 ID: {SESSION_ID_ALICE} (복원됨)")

    chat(restored_agent_alice, "제 이름이 뭐고 어떤 프로젝트를 하고 있다고 했죠?")

    # ------------------------------------------------------------------
    # 단계 4: Bob 재접속 (세션 복원)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 4: Bob 재접속 (앱 재시작 후)...")
    print_separator()

    restored_session_manager_bob = create_session_manager(memory_id, SESSION_ID_BOB, ACTOR_ID_BOB)
    restored_agent_bob = create_agent(restored_session_manager_bob)

    print(f"세션 ID: {SESSION_ID_BOB} (복원됨)")

    chat(restored_agent_bob, "제 이름이 뭐고 무엇을 좋아한다고 했죠?")

    print_success("성공: 두 세션 모두 Bedrock AgentCore Memory에서 복원되었습니다!")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 비교: FileSessionManager vs AgentCore Memory
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("비교: FileSessionManager vs AgentCore Memory")
    print("=" * 60)
    print("""
| 항목               | FileSessionManager      | AgentCore Memory         |
|--------------------|-------------------------|--------------------------|
| 저장 위치          | 로컬 디스크 (JSON)      | AWS 클라우드 (관리형)    |
| 확장성             | 단일 서버               | 분산, 확장 가능          |
| 장기 메모리        | 없음                    | 있음 (LTM 전략)          |
| 사용자 선호도      | 수동 (agent.state)      | 자동 추출                |
| 세션 격리          | session_id로            | session_id + actor_id    |
| 설정 복잡도        | 간단                    | AWS 설정 필요            |
| 비용               | 무료                    | AWS 요금                 |

사용 시나리오:
- 개발/테스트: FileSessionManager
- 프로덕션: AgentCore Memory
- 서버리스/Lambda: AgentCore Memory
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
