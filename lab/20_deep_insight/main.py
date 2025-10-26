
"""
Entry point script for the Strands Agent Demo.
"""
import os
import sys
import shutil
import asyncio
import argparse
import atexit
import signal
import time
import subprocess
from dotenv import load_dotenv
from src.utils.strands_sdk_utils import strands_utils
from src.graph.builder import build_graph

# Load environment variables
load_dotenv()

# Observability
from opentelemetry import trace, context
from src.utils.agentcore_observability import set_session_context, add_span_event

# Import event queue for unified event processing
from src.utils.event_queue import clear_queue

# Import Fargate session manager for cleanup
from src.tools.global_fargate_coordinator import get_global_session 

def remove_artifact_folder(folder_path="./artifacts/"):
    """
    ./artifact/ 폴더가 존재하면 삭제하는 함수

    Args:
        folder_path (str): 삭제할 폴더 경로
    """
    if os.path.exists(folder_path):
        print(f"'{folder_path}' 폴더를 삭제합니다...")
        try:
            shutil.rmtree(folder_path)
            print(f"'{folder_path}' 폴더가 성공적으로 삭제되었습니다.")
        except Exception as e: print(f"오류 발생: {e}")
    else:
        print(f"'{folder_path}' 폴더가 존재하지 않습니다.")

def cleanup_fargate_session():
    """Enhanced Fargate session cleanup with guaranteed task termination"""
    try:
        # 1. 정상적인 세션 정리 시도
        fargate_manager = get_global_session()
        if fargate_manager and fargate_manager._session_manager and fargate_manager._session_manager.current_session:
            print("\n🧹 Starting final Fargate session cleanup...", flush=True)

            # 세션 완료 신호 전송 + S3 업로드 완료 대기
            print("📤 Initiating final S3 upload and waiting for completion...", flush=True)
            completion_result = fargate_manager._session_manager.complete_session(wait_for_s3=True)

            if completion_result and completion_result.get("status") == "success":
                print("✅ S3 upload confirmed - all Fargate artifacts uploaded", flush=True)
            else:
                print("⚠️ S3 upload status unclear, but proceeding with cleanup", flush=True)

        # 2. 강제로 모든 Fargate 태스크 정리 (fail-safe)
        print("🔍 Checking for any remaining Fargate tasks...", flush=True)
        try:
            result = subprocess.run([
                'aws', 'ecs', 'list-tasks',
                '--cluster', 'my-fargate-cluster',
                '--query', 'taskArns[*]',
                '--output', 'text'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                task_arns = result.stdout.strip().split('\t')
                task_ids = [arn.split('/')[-1] for arn in task_arns if arn.strip()]

                if task_ids:
                    print(f"🛑 Found {len(task_ids)} running tasks, terminating...", flush=True)
                    for task_id in task_ids:
                        subprocess.run([
                            'aws', 'ecs', 'stop-task',
                            '--cluster', 'my-fargate-cluster',
                            '--task', task_id
                        ], capture_output=True, timeout=20)
                        print(f"   • Stopped task: {task_id[:12]}...", flush=True)
                    print("✅ All orphaned Fargate tasks terminated", flush=True)
                else:
                    print("✅ No running Fargate tasks found", flush=True)
            else:
                print("ℹ️ Could not list Fargate tasks (cluster may not exist)", flush=True)

        except subprocess.TimeoutExpired:
            print("⚠️ Timeout while checking Fargate tasks", flush=True)
        except Exception as cleanup_error:
            print(f"⚠️ Error during task cleanup: {cleanup_error}", flush=True)

        print("✅ Fargate session cleanup completed", flush=True)
    except Exception as e:
        print(f"⚠️ Error during Fargate session cleanup: {e}", flush=True)

def signal_handler(signum, frame):
    """Enhanced signal handler with immediate cleanup"""
    print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...", flush=True)

    # 즉시 cleanup 실행 (atexit과 별도로)
    cleanup_fargate_session()

    # 짧은 대기 후 강제 종료
    time.sleep(2)
    print("🔚 Process terminating...", flush=True)
    sys.exit(0)

def _setup_execution():
    """Initialize execution environment"""
    remove_artifact_folder()
    clear_queue()

    # Register cleanup handlers
    atexit.register(cleanup_fargate_session)
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination

    print("\n=== Starting Queue-Only Event Stream ===")
    print("🔧 Fargate session cleanup handlers registered")


def _print_conversation_history():
    """Print final conversation history"""
    print("\n=== Conversation History ===")
    from src.graph.nodes import _global_node_states
    shared_state = _global_node_states.get('shared', {})
    history = shared_state.get('history', [])

    if history:
        for hist_item in history:
            print(f"[{hist_item['agent']}] {hist_item['message']}")
    else:
        print("No conversation history found")

async def graph_streaming_execution(payload):
    """Execute full graph streaming workflow using new graph.stream_async method"""

    _setup_execution()

    # Get user query from payload
    user_query = payload.get("user_query", "")
    context_token = set_session_context("default")

    try:
        # Get tracer for main application
        tracer = trace.get_tracer(
            instrumenting_module_name=os.getenv("TRACER_MODULE_NAME", "insight_extractor_agent"),
            instrumenting_library_version=os.getenv("TRACER_LIBRARY_VERSION", "1.0.0")
        )
        with tracer.start_as_current_span("insight_extractor_session") as span:   
            
            # Build graph and use stream_async method
            graph = build_graph()
            
            #########################
            ## modification START  ##
            #########################

            # Stream events from graph execution
            graph_input = {
                "request": user_query,
                "request_prompt": f"Here is a user request: <user_request>{user_query}</user_request>"
            }

            # CSV 파일 경로가 있으면 추가
            csv_file_path = payload.get("csv_file_path")
            if csv_file_path:
                graph_input["csv_file_path"] = csv_file_path

            async for event in graph.stream_async(graph_input):
                yield event

            #########################
            ## modification END    ##
            #########################
            
            _print_conversation_history()
            print("=== Queue-Only Event Stream Complete ===")

            # Add Event
            add_span_event(span, "user_query", {"user-query": str(user_query)}) 

    finally:
        context.detach(context_token)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Strands Agent Demo')
    parser.add_argument('--user_query', type=str, help='User query for the agent')

    args, unknown = parser.parse_known_args()


    #########################
    ## modification START  ##
    #########################

    # Use argparse values if provided, otherwise use predefined values
    if args.user_query:
        payload = {
            "user_query": args.user_query,
            "csv_file_path": "./data/test-dynamic-data.csv"  # 동적 CSV 파일 경로 (테스트용)
        }
    else:
        # Simple test version:
        payload = {
            "user_query": "'./data/Dat-fresh-food-claude.csv'를 읽어서 총 매출액 계산하고 간단한 차트 하나만 그려서 pdf로 저장해줘",
            "csv_file_path": "./data/Dat-fresh-food-claude.csv"  # 동적 CSV 파일 경로
        }

    #########################
    ## modification END    ##
    #########################

    remove_artifact_folder()

    # Use full graph streaming execution for real-time streaming with graph structure
    async def run_streaming():
        async for event in graph_streaming_execution(payload):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())

