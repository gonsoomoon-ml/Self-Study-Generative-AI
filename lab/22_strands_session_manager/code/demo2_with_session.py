"""
데모 2: 세션 관리가 있는 에이전트 (FileSessionManager)
FileSessionManager를 사용하여 대화 내용을 로컬 디스크에 저장하고 복원하는 방법을 보여줍니다.

핵심 개념:
- session_id: 사용자/세션별 고유 식별자
- storage_dir: 세션 데이터를 저장할 디렉토리
- 앱 재시작 후에도 대화 내용이 유지됨

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo2_with_session.py
"""
import os
import shutil
from pathlib import Path
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
from utils import print_header, print_system, print_success, print_separator, chat, Colors


# ----------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------
SESSIONS_DIR = Path("./sessions")  # 세션 데이터 저장 디렉토리
SESSION_ID_ALICE = "user-alice"    # 사용자 Alice의 세션 ID
SESSION_ID_BOB = "user-bob"        # 사용자 Bob의 세션 ID


# ----------------------------------------------------------------------
# 헬퍼 함수
# ----------------------------------------------------------------------
def print_session_storage():
    """세션 저장소 디렉토리 구조를 출력합니다."""
    print(f"\n{Colors.BOLD}[세션 저장소]{Colors.RESET}")
    if not SESSIONS_DIR.exists():
        print("  (비어있음)")
        return

    for root, _, files in os.walk(SESSIONS_DIR):
        level = root.replace(str(SESSIONS_DIR), "").count(os.sep)
        indent = "  " * (level + 1)
        folder_name = os.path.basename(root)
        if level == 0:
            print(f"  {SESSIONS_DIR}/")
        else:
            print(f"{indent}{folder_name}/")

        sub_indent = "  " * (level + 2)
        for file in files:
            print(f"{sub_indent}{file}")


# ----------------------------------------------------------------------
# 에이전트 팩토리
# ----------------------------------------------------------------------
def create_session_manager(session_id: str):
    """주어진 세션 ID에 대한 FileSessionManager를 생성합니다.

    Args:
        session_id: 사용자/세션별 고유 식별자

    Returns:
        FileSessionManager: 로컬 파일 기반 세션 관리자
    """
    return FileSessionManager(
        session_id=session_id,      # 세션 식별자 (필수)
        storage_dir=str(SESSIONS_DIR)  # 저장 디렉토리 (선택, 기본값: 임시 디렉토리)
    )


def create_agent(session_manager):
    """세션 관리자를 사용하는 에이전트를 생성합니다.

    Args:
        session_manager: 대화 내용을 저장/복원할 세션 관리자

    Returns:
        Agent: 세션 관리 기능이 있는 에이전트
    """
    return Agent(
        system_prompt="당신은 친절한 한국어 도우미입니다. 간결하게 응답하세요.",
        session_manager=session_manager,  # 세션 관리자 연결
        callback_handler=None  # 스트리밍 출력 비활성화
    )


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 2: 세션 관리가 있는 에이전트")

    # ------------------------------------------------------------------
    # 초기 설정: 이전 세션 정리
    # ------------------------------------------------------------------
    if SESSIONS_DIR.exists():
        shutil.rmtree(SESSIONS_DIR)
    SESSIONS_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # 단계 1: 사용자 Alice가 앱에 접속
    # ------------------------------------------------------------------
    print_system("단계 1: 사용자 Alice가 앱에 접속...")

    # Alice용 세션 관리자와 에이전트 생성
    session_manager_alice = create_session_manager(SESSION_ID_ALICE)
    agent_alice = create_agent(session_manager_alice)

    print(f"모델 ID: {agent_alice.model.config.get('model_id', 'unknown')}")
    print(f"세션 ID: {SESSION_ID_ALICE}")
    print(f"세션 관리자 객체 ID: {id(session_manager_alice)}")
    print(f"저장 위치: {SESSIONS_DIR}")

    # Alice와 대화
    chat(agent_alice, "안녕하세요! 저는 김영희입니다. Python과 머신러닝을 좋아해요.")
    chat(agent_alice, "현재 추천 시스템 프로젝트를 진행 중입니다.")

    print_session_storage()

    # ------------------------------------------------------------------
    # 단계 2: 사용자 Bob이 앱에 접속 (다른 세션)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 사용자 Bob이 앱에 접속...")
    print_separator()

    # Bob용 세션 관리자와 에이전트 생성 (다른 session_id)
    session_manager_bob = create_session_manager(SESSION_ID_BOB)
    agent_bob = create_agent(session_manager_bob)

    print(f"세션 ID: {SESSION_ID_BOB}")
    print(f"세션 관리자 객체 ID: {id(session_manager_bob)} (다른 객체)")

    # Bob과 대화
    chat(agent_bob, "안녕하세요! 저는 이민수입니다. DevOps 엔지니어로 일하고 있어요.")
    chat(agent_bob, "제 이름이 뭐죠?")

    print_session_storage()

    # ------------------------------------------------------------------
    # 단계 3: Alice가 재접속 (앱 재시작 후)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 3: Alice가 앱 재시작 후 재접속...")
    print_system("새로운 세션 관리자를 같은 session_id로 생성...")
    print_separator()

    # 실제 앱 재시작 시에는 이전 객체들이 모두 사라짐
    # 새로운 세션 관리자가 디스크에서 기존 데이터를 로드함
    restored_session_manager_alice = create_session_manager(SESSION_ID_ALICE)
    restored_agent_alice = create_agent(restored_session_manager_alice)

    print(f"세션 ID: {SESSION_ID_ALICE}")
    print(f"세션 관리자 객체 ID: {id(restored_session_manager_alice)} (다른 객체!)")

    # 이전 대화 내용이 복원되었는지 확인
    chat(restored_agent_alice, "제 이름이 뭐고 어떤 프로젝트를 진행 중이라고 했죠?")

    # ------------------------------------------------------------------
    # 단계 4: Bob이 재접속 (앱 재시작 후)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 4: Bob이 앱 재시작 후 재접속...")
    print_separator()

    restored_session_manager_bob = create_session_manager(SESSION_ID_BOB)
    restored_agent_bob = create_agent(restored_session_manager_bob)

    print(f"세션 ID: {SESSION_ID_BOB}")
    print(f"세션 관리자 객체 ID: {id(restored_session_manager_bob)} (다른 객체!)")

    # Bob의 이전 대화도 복원되었는지 확인
    chat(restored_agent_bob, "제 이름이 뭐고 무슨 일을 한다고 했죠?")

    print_session_storage()

    print_success("성공: 두 사용자의 세션이 격리되고 올바르게 복원되었습니다!")
    print("=" * 60)
    print("""
핵심 포인트:
1. session_id가 같으면 = 같은 세션 데이터에 접근
2. 세션 관리자 객체가 달라도 session_id가 같으면 같은 세션
3. 대화 내용은 디스크에 저장되어 앱 재시작 후에도 유지됨
4. 다른 사용자는 다른 session_id로 완전히 격리됨
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
