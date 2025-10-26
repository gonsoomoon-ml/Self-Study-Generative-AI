"""
AgentCore Runtime - Enhanced entry point for the Strands Agent Demo with AgentCore integration.
Based on main.py with AgentCore-specific enhancements.
"""
import os
import sys
import shutil
import asyncio
import atexit
import signal
import time
import subprocess
from dotenv import load_dotenv
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from src.utils.strands_sdk_utils import strands_utils
from src.graph.builder import build_graph

# Load environment variables
load_dotenv()

# Observability
from opentelemetry import trace
from opentelemetry import context as otel_context
from src.utils.agentcore_observability import set_session_context, add_span_event

# Import event queue for unified event processing
from src.utils.event_queue import clear_queue

# Import Fargate session manager for cleanup
from src.tools.global_fargate_coordinator import get_global_session

# Initialize AgentCore app
app = BedrockAgentCoreApp()

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
        except Exception as e:
            print(f"오류 발생: {e}")
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

    # ⚠️ cleanup_fargate_session은 프로세스 종료 시에만 실행되어야 함
    # 요청별 정리는 finally 블록에서 cleanup_session(request_id)로 처리
    # atexit는 최초 1회만 등록 (중복 방지)

    print("\n=== Starting AgentCore Runtime Event Stream ===")
    print("🔧 Request-level cleanup will be handled in finally block")

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

@app.entrypoint
async def agentcore_streaming_execution(payload, context):
    """
    Execute full graph streaming workflow through AgentCore Runtime
    Enhanced with Fargate session management and observability

    Args:
        payload: Request payload containing user query and configuration
        context: AgentCore runtime context for ping/health management
    """

    _setup_execution()

    # 고유 요청 ID 생성
    import uuid
    request_id = str(uuid.uuid4())
    print(f"\n{'='*60}")
    print(f"🆔 Request ID: {request_id}")
    print(f"{'='*60}\n", flush=True)

    # Fargate 세션 매니저에 요청 컨텍스트 설정
    try:
        fargate_manager = get_global_session()
        fargate_manager.set_request_context(request_id)
        print(f"✅ Fargate session context set for request: {request_id}", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to set Fargate session context: {e}", flush=True)

    # Get user query from payload - AgentCore uses 'prompt' key
    user_query = payload.get("prompt", "")

    # Fall back to 'user_query' for compatibility
    if not user_query:
        user_query = payload.get("user_query", "")

    # Use default query if none provided
    if not user_query:
        # user_query = "'./data/Dat-fresh-food-claude.csv'를 읽어서 총 매출액 계산하고 카테고리별 분석과 월별 추세 차트를 생성한 후 종합 PDF 보고서를 작성해줘"
        user_query = "'./data/Dat-fresh-food-claude.csv'를 읽어서 총 매출액 계산하고 간단한 차트 하나만 그려서 pdf로 해줘"

    context_token = set_session_context("agentcore-session")

    # Register async task to prevent 15-minute timeout during long-running streaming
    # AWS Official API: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html
    # ⚠️ REMOVED: app.add_async_task() causes 94-second early termination
    # Root cause: AgentCore expects first yield event quickly when async task is registered
    # Our Health Check takes 60-90s, causing initial response timeout
    # WITHOUT async task: Health Check completes successfully ✅
    # WITH async task: Connection terminates at 94s ❌
    # task_id = app.add_async_task(
    #     "streaming_workflow",
    #     {
    #         "request_id": request_id,
    #         "query": user_query,
    #         "runtime": "bedrock_manus_agentcore"
    #     }
    # )
    # print(f"🚀 Registered async task: {task_id} (auto HEALTHY_BUSY)", flush=True)

    try:
        # Get tracer for AgentCore application
        tracer = trace.get_tracer(
            instrumenting_module_name=os.getenv("TRACER_MODULE_NAME", "agentcore_insight_extractor"),
            instrumenting_library_version=os.getenv("TRACER_LIBRARY_VERSION", "2.0.0")
        )

        with tracer.start_as_current_span("agentcore_session") as span:

            # Build graph with AgentCore configuration
            graph = build_graph()

            # Prepare input for AgentCore-enhanced graph execution
            graph_input = {
                "request": user_query,
                "request_prompt": f"AgentCore Request: <user_request>{user_query}</user_request>",
                "agentcore_enabled": True,
                "runtime_source": "bedrock_manus_agentcore"
            }

            # CSV 파일 경로 추가 (payload에서 가져오거나 기본값 사용)
            csv_file_path = payload.get("csv_file_path", "./data/Dat-fresh-food-claude.csv")
            graph_input["csv_file_path"] = csv_file_path

            # AgentCore 메타데이터 추가
            agentcore_metadata = payload.get("agentcore_metadata", {
                "runtime": "agentcore",
                "version": "2.0",
                "fargate_enabled": True
            })
            graph_input["agentcore_metadata"] = agentcore_metadata

            print(f"🚀 Launching AgentCore Runtime with query: {user_query[:100]}...")

            event_count = 0

            # Stream events from graph execution
            async for event in graph.stream_async(graph_input):
                event_count += 1

                # Add AgentCore runtime metadata to each event
                event["event_id"] = event_count
                event["runtime_source"] = "bedrock_manus_agentcore"

                # Mark final event
                if event.get("type") == "workflow_complete":
                    event["total_events"] = event_count
                    event["message"] = "All events processed through AgentCore Runtime"

                yield event

            _print_conversation_history()
            print("=== AgentCore Runtime Event Stream Complete ===")

            # Add AgentCore Event
            add_span_event(span, "agentcore_query", {
                "user-query": str(user_query),
                "agentcore-enabled": True,
                "total-events": event_count
            })

    finally:
        # Complete async task to signal streaming finished
        # ⚠️ REMOVED: app.complete_async_task() (no task_id since app.add_async_task was removed)
        # print("🏁 Completing async task...", flush=True)
        # try:
        #     app.complete_async_task(task_id)
        #     print(f"✅ Async task completed: {task_id}", flush=True)
        # except Exception as task_error:
        #     print(f"⚠️ Error completing async task: {task_error}", flush=True)

        # 요청 종료 시 Fargate 세션 정리 (요청 ID 기반)
        try:
            fargate_manager = get_global_session()
            print(f"\n🧹 Request {request_id} completed - cleaning up Fargate session...", flush=True)
            fargate_manager.cleanup_session(request_id)
            print(f"✅ Fargate session cleaned up for request {request_id}", flush=True)
        except Exception as cleanup_error:
            print(f"⚠️ Failed to cleanup Fargate session for request {request_id}: {cleanup_error}", flush=True)

        otel_context.detach(context_token)

if __name__ == "__main__":
    # 프로세스 종료 시에만 실행되는 cleanup 등록 (1회만)
    atexit.register(cleanup_fargate_session)
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination

    # Run with AgentCore app.run()
    print("=" * 60)
    print("🤖 AgentCore Runtime v2.0 with async task management")
    print("=" * 60)
    app.run()