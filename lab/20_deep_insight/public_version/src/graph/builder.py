
import asyncio
import time
from datetime import datetime
from strands.multiagent import GraphBuilder
from src.utils.strands_sdk_utils import FunctionNode
from src.utils.event_queue import has_events, get_event
from .nodes import (
    supervisor_node,
    coordinator_node,
    planner_node,
    should_handoff_to_planner,
)

# ============================================================
# COMMENTED OUT: Original StreamableGraph (No Progress Keep-Alive)
# ============================================================
# class StreamableGraph:
#     """Graph wrapper that adds streaming capability to Strands graphs."""
#
#     def __init__(self, graph):
#         self.graph = graph
#
#     async def invoke_async(self, task):
#         """Original non-streaming invoke method."""
#         return await self.graph.invoke_async(task)
#
#     async def _cleanup_workflow(self, workflow_task):
#         """Handle workflow completion and cleanup."""
#         if not workflow_task.done():
#             try:
#                 await asyncio.wait_for(workflow_task, timeout=1.0)
#             except asyncio.TimeoutError:
#                 workflow_task.cancel()
#                 try:
#                     await workflow_task
#                 except asyncio.CancelledError:
#                     pass
#
#     async def _yield_pending_events(self):
#         """Yield any pending events from queue."""
#         while has_events():
#             event = get_event()
#             if event:
#                 yield event
#
#     async def stream_async(self, task):
#         """Stream events from graph execution using background task + event queue pattern."""
#
#         # Step 1: Run graph backgound and put event into the global queue
#         async def run_workflow():
#             try:
#                 return await self.graph.invoke_async(task)
#             except Exception as e:
#                 print(f"Workflow error: {e}")
#                 raise
#
#         workflow_task = asyncio.create_task(run_workflow())
#
#         # Step 2: Consuming event in the global queue
#         try:
#             while not workflow_task.done():
#                 async for event in self._yield_pending_events():
#                     yield event
#                 await asyncio.sleep(0.005)
#         finally:
#             await self._cleanup_workflow(workflow_task)
#             async for event in self._yield_pending_events():
#                 yield event
#
#         yield {"type": "workflow_complete", "message": "All events processed through global queue"}

# ============================================================
# NEW: StreamableGraph with Progress Keep-Alive (HTTP/2 Timeout Prevention)
# ============================================================
class StreamableGraph:
    """Graph wrapper that adds streaming capability with periodic progress keep-alive.

    Features:
    - Original event streaming via global queue
    - Periodic progress messages every 30 seconds to prevent HTTP/2 timeout
    - Handles both throttling retries and normal processing gaps
    """

    def __init__(self, graph):
        self.graph = graph

    async def invoke_async(self, task):
        """Original non-streaming invoke method."""
        return await self.graph.invoke_async(task)

    async def _cleanup_workflow(self, workflow_task):
        """Handle workflow completion and cleanup."""
        if not workflow_task.done():
            try:
                await asyncio.wait_for(workflow_task, timeout=1.0)
            except asyncio.TimeoutError:
                workflow_task.cancel()
                try:
                    await workflow_task
                except asyncio.CancelledError:
                    pass

    async def _yield_pending_events(self):
        """Yield any pending events from queue."""
        while has_events():
            event = get_event()
            if event:
                yield event

    async def stream_async(self, task):
        """Stream events from graph execution using background task + event queue pattern.

        Includes periodic progress keep-alive to prevent HTTP/2 SSE timeout (120s).
        Progress messages are sent every 30 seconds when no other events occur.
        """

        # Progress keep-alive setup
        streaming_active = {"value": True}
        last_event_time = {"value": time.time()}

        # Progress keep-alive background task
        async def progress_keepalive():
            """Send periodic progress messages to keep HTTP/2 connection alive.

            - Progress message: Every 30 seconds (for client display and keep-alive)

            This prevents HTTP/2 SSE timeout (120s) during long agent processing.

            Note: Dummy bash execution (every 90s) is currently disabled due to
            elapsed time calculation bugs. Progress messages alone provide sufficient
            keep-alive for typical workflows.
            """
            while streaming_active["value"]:
                await asyncio.sleep(30)  # Check every 30 seconds

                if not streaming_active["value"]:
                    break

                elapsed = int(time.time() - last_event_time["value"])

                # 1. Progress message: Every 30s (for client display)
                if elapsed >= 30:
                    from src.utils.event_queue import put_event
                    from src.utils.strands_sdk_utils import strands_utils

                    # Create progress event in Strands-compatible format (text chunk)
                    # Same pattern as retry event in process_streaming_response_yield()
                    progress_message = f"⏳ In Progress... ({elapsed}s elapsed since last event)"

                    strands_progress_event = {
                        "data": progress_message  # Strands text chunk format
                    }

                    # Convert to AgentCore event format
                    agentcore_event = await strands_utils._convert_to_agentcore_event(
                        strands_progress_event,
                        agent_name="workflow",  # Graph-level progress (not specific agent)
                        session_id="ABC",       # Dummy session_id (replaced by agentcore_runtime)
                        source="progress_keepalive"
                    )

                    if agentcore_event:
                        # Add internal marker to distinguish from real agent events
                        agentcore_event["_is_progress"] = True
                        put_event(agentcore_event)

                        # Log to CloudWatch for debugging and HTTP/2 keep-alive
                        print(f"⏳ {progress_message}", flush=True)

                    # Note: Don't update last_event_time here
                    # Progress messages don't reset the "idle" timer

                # 2. COMMENTED OUT: Dummy bash execution - Container connection keep-alive every 90s
                # Reason: Elapsed time calculation bug causes unreliable execution
                # Alternative: Progress messages (every 30s) provide sufficient keep-alive
                # if elapsed >= 90:
                #     from src.utils.event_queue import put_event
                #     from src.tools.fargate_bash_tool import handle_fargate_bash_tool
                #
                #     print(f"🔄 Executing dummy bash for HTTP/2 keep-alive (elapsed: {elapsed}s)", flush=True)
                #
                #     try:
                #         # Execute simple echo command (~0.1s execution time)
                #         # Note: handle_fargate_bash_tool is a sync function, but very fast
                #         result = handle_fargate_bash_tool(cmd="echo 'HTTP/2 keepalive'")
                #
                #         # Check if execution was successful (no error in result string)
                #         if result and "Command failed" not in result and "Error executing command" not in result:
                #             print(f"✅ Dummy bash executed - HTTP/2 timer reset", flush=True)
                #
                #             # IMPORTANT: Create event and send through HTTP/2 stream
                #             # This is what actually resets the HTTP/2 idle timer!
                #             dummy_bash_message = f"🔄 HTTP/2 keep-alive (bash executed)"
                #
                #             strands_dummy_event = {
                #                 "data": dummy_bash_message  # Strands text chunk format
                #             }
                #
                #             # Convert to AgentCore event format
                #             agentcore_event = await strands_utils._convert_to_agentcore_event(
                #                 strands_dummy_event,
                #                 agent_name="workflow",
                #                 session_id="ABC",
                #                 source="dummy_bash_keepalive"
                #             )
                #
                #             if agentcore_event:
                #                 # Mark as dummy bash event (not progress, not real agent event)
                #                 agentcore_event["_is_dummy_bash"] = True
                #                 put_event(agentcore_event)
                #
                #                 # Now HTTP/2 stream will send this event to client
                #                 # This sends actual data through the connection, resetting the timer!
                #                 print(f"✅ Dummy bash result queued for streaming - HTTP/2 timer will reset", flush=True)
                #
                #         else:
                #             print(f"⚠️ Dummy bash execution failed: {result}", flush=True)
                #
                #     except Exception as e:
                #         print(f"⚠️ Dummy bash execution failed: {e}", flush=True)
                #         # Don't crash the keep-alive task on error
                #         # Continue to next iteration

        # Step 1: Run graph background and put event into the global queue
        async def run_workflow():
            try:
                return await self.graph.invoke_async(task)
            except Exception as e:
                print(f"Workflow error: {e}")
                raise

        workflow_task = asyncio.create_task(run_workflow())

        # Start progress keep-alive background task
        progress_task = asyncio.create_task(progress_keepalive())

        # Step 2: Consuming event in the global queue
        try:
            while not workflow_task.done():
                async for event in self._yield_pending_events():
                    # Update last event time when real events arrive (not progress events)
                    # Check internal marker to distinguish progress from real agent events
                    if not event.get("_is_progress"):
                        last_event_time["value"] = time.time()
                    yield event
                await asyncio.sleep(0.005)
        finally:
            # Stop progress keep-alive
            streaming_active["value"] = False
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            await self._cleanup_workflow(workflow_task)
            async for event in self._yield_pending_events():
                yield event

        yield {"type": "workflow_complete", "message": "All events processed through global queue"}

def build_graph():
    """Build and return the agent workflow graph with streaming capability.

    Timeout settings:
    - execution_timeout: 1800s (30 min) - Total workflow execution timeout
    - max_node_executions: 50 - Prevent infinite loops in cyclic graphs

    Note: These timeouts are for the Strands graph itself, not for AgentCore initial response.
    Initial response timeout is handled by yielding events during Health Check.
    """
    builder = GraphBuilder()

    # Add nodes
    coordinator = FunctionNode(func=coordinator_node, name="coordinator")
    planner = FunctionNode(func=planner_node, name="planner")
    supervisor = FunctionNode(func=supervisor_node, name="supervisor")

    builder.add_node(coordinator, "coordinator")
    builder.add_node(planner, "planner")
    builder.add_node(supervisor, "supervisor")

    # Set entry point and edges
    builder.set_entry_point("coordinator")
    builder.add_edge("coordinator", "planner", condition=should_handoff_to_planner)
    builder.add_edge("planner", "supervisor")

    # Configure timeout settings (Strands SDK feature)
    # execution_timeout: Total execution timeout in seconds (default: 900s = 15 min)
    # Increase to 1800s (30 min) to accommodate long-running workflows with:
    # - Fargate container initialization (60-90s)
    # - CSV data processing
    # - Multiple chart generation
    # - PDF report creation
    builder.set_execution_timeout(1800.0)  # 30 minutes

    # max_node_executions: Prevent infinite loops (default: unlimited)
    # Set to 50 to prevent runaway execution in cyclic graph patterns
    builder.set_max_node_executions(50)

    # Return graph with streaming capability
    return StreamableGraph(builder.build())
