"""
데모 1: 세션 관리 없는 에이전트
세션 관리자 없이 에이전트를 사용할 때 발생하는 메모리 손실 문제를 보여줍니다.

문제점:
- 앱 재시작 시 이전 대화 내용을 모두 잊어버림
- 사용자 정보, 선호도 등이 유지되지 않음

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo1_no_session.py
"""
from strands import Agent
from utils import print_header, print_system, print_error, print_separator, chat


# ----------------------------------------------------------------------
# 에이전트 팩토리
# ----------------------------------------------------------------------
def create_agent():
    """세션 관리자 없이 에이전트 생성.

    Returns:
        Agent: 세션 관리 기능이 없는 기본 에이전트
    """
    return Agent(
        system_prompt="당신은 친절한 한국어 도우미입니다. 간결하게 응답하세요.",
        callback_handler=None  # 스트리밍 출력 비활성화
    )


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 1: 세션 관리 없는 에이전트")

    # ------------------------------------------------------------------
    # 단계 1: 에이전트 생성 및 대화
    # ------------------------------------------------------------------
    print_system("단계 1: 에이전트 생성 및 대화 시작...")

    agent = create_agent()
    print(f"모델 ID: {agent.model.config.get('model_id', 'unknown')}")

    # 사용자 정보 전달
    chat(agent, "제 이름은 김철수이고, Python 프로그래밍을 좋아합니다.")

    # 에이전트가 정보를 기억하는지 확인
    chat(agent, "제 이름이 뭐고 무엇을 좋아한다고 했죠?")

    # ------------------------------------------------------------------
    # 단계 2: 앱 재시작 시뮬레이션 (새 에이전트 생성)
    # ------------------------------------------------------------------
    print_separator()
    print_system("단계 2: 앱 재시작 시뮬레이션 (새 에이전트 생성)...")
    print_separator()

    # 앱 재시작 = 새로운 에이전트 객체 생성
    # 이전 대화 내용은 메모리에만 있었으므로 사라짐
    agent_after_restart = create_agent()

    # 재시작 후 이전 정보 질문
    chat(agent_after_restart, "제 이름이 뭐였죠?")

    print_error("문제: 에이전트가 재시작 후 모든 것을 잊어버렸습니다!")
    print("=" * 60)
    print("""
해결책: SessionManager 사용
- FileSessionManager: 로컬 파일에 대화 저장
- S3SessionManager: AWS S3에 대화 저장
- AgentCoreMemorySessionManager: Bedrock AgentCore에 저장

다음 데모(demo2)에서 FileSessionManager 사용법을 확인하세요.
""")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
