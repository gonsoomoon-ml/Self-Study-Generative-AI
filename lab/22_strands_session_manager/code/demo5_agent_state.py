"""
데모 5: agent.state를 사용한 커스텀 애플리케이션 상태 저장 (FileSessionManager)
대화 내역 외에 커스텀 데이터(사용자 설정, 방문 횟수 등)를 저장하는 방법을 보여줍니다.

agent.state 사용 사례:
- 사용자 설정 (테마, 언어, 알림)
- 방문 횟수, 사용 통계
- 장바구니, 폼 데이터
- 애플리케이션별 컨텍스트
- 사용자별 기능 플래그

주의사항:
- agent.state는 dict처럼 직접 할당 불가 (agent.state["key"] = value ❌)
- set()/get() 메서드 사용 필수

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo5_agent_state.py
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
SESSIONS_DIR = Path("./sessions")  # 세션 저장 디렉토리
SESSION_ID = "user-alice-state"    # 세션 ID


# ----------------------------------------------------------------------
# 헬퍼 함수
# ----------------------------------------------------------------------
def print_state(agent, title: str = "현재 상태"):
    """에이전트의 커스텀 상태를 출력합니다.

    Args:
        agent: Strands Agent 인스턴스
        title: 출력 제목
    """
    print(f"\n{Colors.BOLD}[{title}]{Colors.RESET}")
    # agent.state.get() - 키 없이 호출하면 전체 데이터 dict 반환
    state_data = agent.state.get()
    if not state_data:
        print("  (비어있음)")
        return
    for key, value in state_data.items():
        print(f"  {key}: {value}")


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
        session_id: 세션 식별자

    Returns:
        FileSessionManager: 로컬 파일 기반 세션 관리자
    """
    return FileSessionManager(
        session_id=session_id,
        storage_dir=str(SESSIONS_DIR)
    )


def create_agent(session_manager):
    """세션 관리자를 사용하는 에이전트를 생성합니다.

    Args:
        session_manager: 세션 관리자 인스턴스

    Returns:
        Agent: 세션 관리 기능이 있는 에이전트
    """
    return Agent(
        system_prompt="당신은 친절한 한국어 도우미입니다. 간결하게 응답하세요.",
        session_manager=session_manager,
        callback_handler=None  # 스트리밍 출력 비활성화
    )


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 5: agent.state를 사용한 커스텀 상태 저장")

    # ------------------------------------------------------------------
    # 초기 설정: 이전 세션 정리
    # ------------------------------------------------------------------
    if SESSIONS_DIR.exists():
        shutil.rmtree(SESSIONS_DIR)
    SESSIONS_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # 단계 1: 에이전트 생성 및 커스텀 상태 저장
    # ------------------------------------------------------------------
    print_system("단계 1: 에이전트 생성 및 커스텀 상태 저장...")

    session_manager = create_session_manager(SESSION_ID)
    agent = create_agent(session_manager)

    print(f"모델 ID: {agent.model.config.get('model_id', 'unknown')}")
    print(f"세션 ID: {SESSION_ID}")

    # 커스텀 애플리케이션 상태 저장 - set() 메서드 사용
    # 주의: agent.state["key"] = value 형식은 지원되지 않음!
    agent.state.set("user_preferences", {
        "theme": "dark",        # 테마 설정
        "language": "ko",       # 언어 설정
        "notifications": True   # 알림 설정
    })
    agent.state.set("visit_count", 1)  # 방문 횟수
    agent.state.set("last_topic", "세션 관리")  # 마지막 주제
    agent.state.set("favorite_languages", ["Python", "TypeScript"])  # 선호 언어

    print_state(agent, "저장된 상태")

    # 에이전트 호출 시 자동으로 디스크에 저장됨
    chat(agent, "안녕하세요! 저는 다크 모드와 한국어를 선호합니다.")

    print_session_storage()

    # ------------------------------------------------------------------
    # 단계 2: 앱 재시작 시뮬레이션 및 상태 복원 확인
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 앱 재시작 시뮬레이션...")
    print_system("디스크에서 커스텀 상태가 복원되는지 확인...")
    print_separator()

    restored_session_manager = create_session_manager(SESSION_ID)
    restored_agent = create_agent(restored_session_manager)

    print(f"세션 ID: {SESSION_ID} (복원됨)")
    print_state(restored_agent, "복원된 상태")

    # 상태 값 검증
    prefs = restored_agent.state.get("user_preferences") or {}
    print(f"\n검증 결과:")
    print(f"  테마: {prefs.get('theme')} {'✓' if prefs.get('theme') == 'dark' else '✗'}")
    print(f"  언어: {prefs.get('language')} {'✓' if prefs.get('language') == 'ko' else '✗'}")
    print(f"  방문 횟수: {restored_agent.state.get('visit_count')} {'✓' if restored_agent.state.get('visit_count') == 1 else '✗'}")

    # ------------------------------------------------------------------
    # 단계 3: 상태 업데이트 (방문 횟수 증가)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 3: 상태 업데이트 (방문 횟수 증가)...")
    print_separator()

    old_count = restored_agent.state.get("visit_count") or 0
    restored_agent.state.set("visit_count", old_count + 1)
    restored_agent.state.set("last_topic", "agent.state 지속성")

    print(f"visit_count: {old_count} -> {restored_agent.state.get('visit_count')}")
    print(f"last_topic: '세션 관리' -> '{restored_agent.state.get('last_topic')}'")

    # 저장 트리거
    chat(restored_agent, "제가 선호하는 언어가 뭐라고 했죠?")

    # ------------------------------------------------------------------
    # 단계 4: 다시 재시작하여 업데이트된 상태 확인
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 4: 다시 재시작하여 업데이트된 상태 확인...")
    print_separator()

    final_session_manager = create_session_manager(SESSION_ID)
    final_agent = create_agent(final_session_manager)

    print_state(final_agent, "최종 복원 상태")

    # 업데이트된 값 검증
    print(f"\n검증 결과:")
    print(f"  visit_count: {final_agent.state.get('visit_count')} {'✓' if final_agent.state.get('visit_count') == 2 else '✗'}")
    print(f"  last_topic: {final_agent.state.get('last_topic')} {'✓' if final_agent.state.get('last_topic') == 'agent.state 지속성' else '✗'}")

    print_success("성공: 커스텀 상태가 재시작 후에도 유지됩니다!")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 요약: agent.state vs 대화 히스토리
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("요약: agent.state vs 대화 히스토리")
    print("=" * 60)
    print("""
| 항목       | 대화 히스토리 (messages)   | agent.state              |
|------------|---------------------------|--------------------------|
| 저장 내용  | 메시지 (user/assistant)    | 커스텀 데이터 (dict)      |
| 자동 저장  | 예 (agent 호출 시)         | 예 (agent 호출 시)        |
| 용도       | 대화 맥락 유지              | 앱 상태 저장              |
| 예시       | "제 이름은 김철수입니다"    | {"theme": "dark"}         |

agent.state 사용법:
  # 저장 - set() 메서드 사용 (직접 할당 불가!)
  agent.state.set("key", value)

  # 조회 - get() 메서드 사용
  value = agent.state.get("key")       # 특정 키
  all_data = agent.state.get()          # 전체 데이터

  # 기본값 처리 (get()에 기본값 파라미터 없음)
  value = agent.state.get("key") or default_value
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
