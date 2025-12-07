"""
데모 7: 세션 및 메모리 정리
로컬 세션(FileSessionManager)과 AgentCore Memory 리소스를 정리합니다.

정리 대상:
1. 로컬 세션 파일 (./sessions 디렉토리)
2. AgentCore Memory 리소스 (AWS 클라우드)

주의:
- AgentCore Memory 삭제는 복구할 수 없습니다
- 삭제 전 확인 프롬프트가 표시됩니다

실행 방법:
    cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager
    uv run python code/demo7_cleanup.py
"""
import shutil
from pathlib import Path
from utils import print_header, print_system, print_success, print_error, Colors

# AgentCore 관련 import (실패해도 로컬 세션 정리는 가능)
try:
    from bedrock_agentcore.memory import MemoryClient
    AGENTCORE_AVAILABLE = True
except ImportError:
    AGENTCORE_AVAILABLE = False


# ----------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------
SESSIONS_DIR = Path("./sessions")
AWS_REGION = "us-east-1"


# ----------------------------------------------------------------------
# 로컬 세션 관리 함수
# ----------------------------------------------------------------------
def list_local_sessions():
    """로컬 세션 목록을 반환합니다.

    Returns:
        list: 세션 디렉토리 이름 목록
    """
    if not SESSIONS_DIR.exists():
        return []
    sessions = [d.name for d in SESSIONS_DIR.iterdir() if d.is_dir()]
    return sessions


def delete_local_session(session_id: str) -> bool:
    """특정 로컬 세션을 삭제합니다.

    Args:
        session_id: 세션 ID (session_ 접두사 포함/미포함 모두 가능)

    Returns:
        bool: 삭제 성공 여부
    """
    # session_xxx 형식과 xxx 형식 모두 처리
    if session_id.startswith("session_"):
        session_path = SESSIONS_DIR / session_id
    else:
        session_path = SESSIONS_DIR / f"session_{session_id}"

    if session_path.exists():
        shutil.rmtree(session_path)
        print(f"  삭제됨: {session_path.name}")
        return True
    else:
        print(f"  찾을 수 없음: {session_id}")
        return False


def delete_all_local_sessions() -> int:
    """모든 로컬 세션을 삭제합니다.

    Returns:
        int: 삭제된 세션 수
    """
    if SESSIONS_DIR.exists():
        count = len(list_local_sessions())
        shutil.rmtree(SESSIONS_DIR)
        SESSIONS_DIR.mkdir(exist_ok=True)
        print(f"  {count}개 세션 삭제됨")
        return count
    return 0


# ----------------------------------------------------------------------
# AgentCore Memory 관리 함수
# ----------------------------------------------------------------------
def list_agentcore_memories():
    """AgentCore Memory 목록을 반환합니다.

    Returns:
        list: 메모리 정보 목록 [{id, name, status}, ...]
    """
    if not AGENTCORE_AVAILABLE:
        return []

    try:
        client = MemoryClient(region_name=AWS_REGION)
        memories = client.list_memories()
        memory_list = memories if isinstance(memories, list) else memories.get("memories", [])

        result = []
        for memory in memory_list:
            memory_id = memory.get("memoryId") or memory.get("memory_id") or memory.get("id")
            status = memory.get("status", "UNKNOWN")
            # 이름은 ID에서 추출 (예: strands_session_demo-Qpy1hz77A2 -> strands_session_demo)
            name = memory_id.rsplit("-", 1)[0] if memory_id else "unknown"
            result.append({
                "id": memory_id,
                "name": name,
                "status": status
            })
        return result
    except Exception as e:
        print(f"  AgentCore Memory 조회 실패: {e}")
        return []


def delete_agentcore_memory(memory_id: str) -> bool:
    """특정 AgentCore Memory를 삭제합니다.

    Args:
        memory_id: 메모리 ID

    Returns:
        bool: 삭제 성공 여부
    """
    if not AGENTCORE_AVAILABLE:
        print("  AgentCore 모듈이 설치되지 않았습니다")
        return False

    try:
        client = MemoryClient(region_name=AWS_REGION)
        client.delete_memory(memory_id=memory_id)
        print(f"  삭제 요청됨: {memory_id}")
        print(f"  (삭제 완료까지 시간이 걸릴 수 있습니다)")
        return True
    except Exception as e:
        print(f"  삭제 실패: {e}")
        return False


# ----------------------------------------------------------------------
# 메인 함수
# ----------------------------------------------------------------------
def main():
    print_header("데모 7: 세션 및 메모리 정리")

    while True:
        # ------------------------------------------------------------------
        # 메뉴 표시
        # ------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("정리 옵션:")
        print("=" * 60)
        print("  1. 로컬 세션 목록 보기")
        print("  2. 로컬 세션 삭제 (선택)")
        print("  3. 로컬 세션 전체 삭제")
        print("  -" * 30)
        if AGENTCORE_AVAILABLE:
            print("  4. AgentCore Memory 목록 보기")
            print("  5. AgentCore Memory 삭제 (선택)")
        else:
            print(f"  {Colors.SYSTEM}4. AgentCore Memory (사용 불가 - 모듈 미설치){Colors.RESET}")
            print(f"  {Colors.SYSTEM}5. AgentCore Memory (사용 불가 - 모듈 미설치){Colors.RESET}")
        print("  -" * 30)
        print("  0. 종료")

        choice = input("\n선택: ").strip()

        # ------------------------------------------------------------------
        # 1. 로컬 세션 목록
        # ------------------------------------------------------------------
        if choice == "1":
            print_system("로컬 세션 목록")
            sessions = list_local_sessions()
            if sessions:
                for i, session in enumerate(sessions, 1):
                    print(f"  {i}. {session}")
            else:
                print("  (세션 없음)")

        # ------------------------------------------------------------------
        # 2. 로컬 세션 삭제 (선택)
        # ------------------------------------------------------------------
        elif choice == "2":
            print_system("로컬 세션 삭제")
            sessions = list_local_sessions()
            if not sessions:
                print("  삭제할 세션이 없습니다")
                continue

            for i, session in enumerate(sessions, 1):
                print(f"  {i}. {session}")

            session_input = input("\n삭제할 세션 번호 또는 이름: ").strip()
            if not session_input:
                continue

            try:
                idx = int(session_input) - 1
                if 0 <= idx < len(sessions):
                    delete_local_session(sessions[idx])
                else:
                    print("  잘못된 번호")
            except ValueError:
                delete_local_session(session_input)

        # ------------------------------------------------------------------
        # 3. 로컬 세션 전체 삭제
        # ------------------------------------------------------------------
        elif choice == "3":
            print_system("로컬 세션 전체 삭제")
            sessions = list_local_sessions()
            if not sessions:
                print("  삭제할 세션이 없습니다")
                continue

            print(f"  현재 세션 수: {len(sessions)}")
            confirm = input("  정말 모든 세션을 삭제하시겠습니까? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_all_local_sessions()
                print_success("모든 로컬 세션이 삭제되었습니다")
            else:
                print("  취소됨")

        # ------------------------------------------------------------------
        # 4. AgentCore Memory 목록
        # ------------------------------------------------------------------
        elif choice == "4":
            if not AGENTCORE_AVAILABLE:
                print_error("AgentCore 모듈이 설치되지 않았습니다")
                print("  설치: pip install 'bedrock-agentcore[strands-agents]'")
                continue

            print_system("AgentCore Memory 목록")
            memories = list_agentcore_memories()
            if memories:
                for i, mem in enumerate(memories, 1):
                    status_color = Colors.SUCCESS if mem["status"] == "ACTIVE" else Colors.SYSTEM
                    print(f"  {i}. {mem['id']}")
                    print(f"     이름: {mem['name']}, 상태: {status_color}{mem['status']}{Colors.RESET}")
            else:
                print("  (메모리 없음)")

        # ------------------------------------------------------------------
        # 5. AgentCore Memory 삭제
        # ------------------------------------------------------------------
        elif choice == "5":
            if not AGENTCORE_AVAILABLE:
                print_error("AgentCore 모듈이 설치되지 않았습니다")
                print("  설치: pip install 'bedrock-agentcore[strands-agents]'")
                continue

            print_system("AgentCore Memory 삭제")
            memories = list_agentcore_memories()
            if not memories:
                print("  삭제할 메모리가 없습니다")
                continue

            for i, mem in enumerate(memories, 1):
                print(f"  {i}. {mem['id']} ({mem['status']})")

            mem_input = input("\n삭제할 메모리 번호: ").strip()
            if not mem_input:
                continue

            try:
                idx = int(mem_input) - 1
                if 0 <= idx < len(memories):
                    memory_id = memories[idx]["id"]
                    print(f"\n  선택된 메모리: {memory_id}")
                    print(f"  {Colors.ERROR}경고: 이 작업은 복구할 수 없습니다!{Colors.RESET}")
                    confirm = input("  정말 삭제하시겠습니까? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        delete_agentcore_memory(memory_id)
                    else:
                        print("  취소됨")
                else:
                    print("  잘못된 번호")
            except ValueError:
                print("  잘못된 입력")

        # ------------------------------------------------------------------
        # 0. 종료
        # ------------------------------------------------------------------
        elif choice == "0":
            print("\n정리 완료!")
            break

        else:
            print("  잘못된 선택")


# ----------------------------------------------------------------------
# 엔트리 포인트
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
