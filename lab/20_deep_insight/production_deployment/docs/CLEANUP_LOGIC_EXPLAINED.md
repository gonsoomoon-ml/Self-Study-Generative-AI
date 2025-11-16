# Duplicate Cleanup Logic - Explained

## 🔍 The Problem: Two Cleanup Systems Doing Similar Things

### System 1: Per-Request Cleanup (Primary) ✅
**File**: `agentcore_runtime.py:405-426` + `global_fargate_coordinator.py:322-380`

```python
# agentcore_runtime.py (lines 494-496)
try:
    # ... handle request ...
    async for event in graph.stream_async(graph_input):
        yield event
finally:
    # ✅ CLEANUP AFTER EACH REQUEST
    _cleanup_request_session(request_id)  # <-- Per-request cleanup

# What it does:
def _cleanup_request_session(request_id: str):
    fargate_manager = get_global_session()
    fargate_manager.cleanup_session(request_id)
    # ↓
    # Calls global_fargate_coordinator.cleanup_session()
```

**Detailed Steps** (in `global_fargate_coordinator.py:322-380`):
```python
def cleanup_session(self, request_id):
    # 1. Complete session with S3 upload
    self._session_manager.complete_session()

    # 2. Release container IP
    del self._used_container_ips[container_ip]

    # 3. Deregister from ALB
    self._deregister_from_alb(container_ip)

    # 4. Clean up dictionaries
    del self._sessions[request_id]
    del self._http_clients[request_id]
    del self._session_creation_failures[request_id]

    # 5. Mark as cleaned up
    self._cleaned_up_requests.add(request_id)
```

---

### System 2: Process-Level Cleanup (Fail-Safe) 🛡️
**File**: `agentcore_runtime.py:136-203`

```python
# agentcore_runtime.py (line 501)
if __name__ == "__main__":
    # ✅ REGISTER CLEANUP FOR PROCESS EXIT
    atexit.register(cleanup_fargate_session)  # <-- Process-level cleanup
    app.run()

# What it does:
def cleanup_fargate_session():
    # 1. Graceful session cleanup
    if fargate_manager.current_session:
        fargate_manager.complete_session(wait_for_s3=True)  # S3 upload

    # 2. Force cleanup ALL tasks (fail-safe)
    # List all running tasks in cluster
    result = subprocess.run(['aws', 'ecs', 'list-tasks', '--cluster', ECS_CLUSTER_NAME])
    task_arns = result.stdout.strip().split('\t')

    # Stop ALL tasks
    for task_id in task_arns:
        subprocess.run(['aws', 'ecs', 'stop-task', '--cluster', ECS_CLUSTER_NAME, '--task', task_id])
```

---

## 🔄 The Duplication Problem

Both systems do **similar cleanup operations** but at different times:

| Operation | Per-Request (System 1) | Process-Exit (System 2) |
|-----------|------------------------|------------------------|
| **S3 Upload** | ✅ `complete_session()` | ✅ `complete_session(wait_for_s3=True)` |
| **ALB Deregister** | ✅ `_deregister_from_alb()` | ❌ Not done |
| **Container Stop** | ✅ Via ALB deregister | ✅ `aws ecs stop-task` (force) |
| **IP Release** | ✅ `del _used_container_ips` | ❌ Not done |
| **Dict Cleanup** | ✅ Multiple `del` operations | ❌ Not done |

### Issues:
1. **Code Duplication**: Same S3 upload logic in 2 places
2. **Different Approaches**: One uses Python API, other uses AWS CLI
3. **Maintenance Burden**: Bug fixes need to be applied twice
4. **Inconsistent Behavior**: System 1 is graceful, System 2 is forceful

---

## 📋 When to Use Each System

### Use Per-Request Cleanup (System 1) When:

✅ **Normal Request Completion**
- Request processed successfully
- User got their response
- Need to free resources for next request

✅ **Request Fails/Errors**
- Exception during processing
- User cancels request
- Timeout occurs

✅ **Multiple Concurrent Requests**
- Each request has its own session
- Need to cleanup specific request without affecting others

**Example Scenarios**:
```python
# Scenario 1: Successful request
User: "Analyze sales.csv"
→ Process completes ✅
→ Per-request cleanup runs
→ Container cleaned, ready for next request

# Scenario 2: Failed request
User: "Analyze missing.csv"
→ File not found ❌
→ finally block runs
→ Per-request cleanup runs anyway (guaranteed)

# Scenario 3: Multiple concurrent requests
Request A: Processing... (session 1)
Request B: Processing... (session 2)
→ Request A completes → Cleanup session 1 only
→ Request B still running → Session 2 untouched
```

---

### Use Process-Level Cleanup (System 2) When:

✅ **Python Process Exits**
- Runtime container shutting down
- AgentCore runtime being replaced
- System restart/redeployment

✅ **Fail-Safe Recovery**
- Per-request cleanup failed
- Orphaned containers exist
- Zombie resources need cleanup

✅ **Development/Debugging**
- Ctrl+C to stop runtime
- Testing/development mode
- Manual runtime termination

**Example Scenarios**:
```python
# Scenario 1: Container shutdown
AWS ECS: "Stopping container..."
→ Python receives SIGTERM
→ atexit handlers run
→ Process-level cleanup runs
→ ALL tasks stopped (even if per-request cleanup failed)

# Scenario 2: Orphaned resources
Request cleanup failed due to network error
→ Container IP not released
→ ALB target still registered
→ Process exit triggers fail-safe
→ Force stops ALL tasks (cleans up orphans)

# Scenario 3: Development
Developer: Ctrl+C (terminate runtime)
→ atexit handler runs
→ All running tasks stopped
→ Clean slate for next run
```

---

## ⚠️ Critical Differences

### Scope
- **Per-Request**: Cleans up ONE specific request/session
- **Process-Level**: Cleans up ALL sessions/tasks

### Method
- **Per-Request**: Uses Python SDK (boto3), graceful
- **Process-Level**: Uses AWS CLI, forceful

### S3 Upload
- **Per-Request**: Async, doesn't wait (faster)
- **Process-Level**: Sync, waits for completion (safer)

### Execution Guarantee
- **Per-Request**: Runs in `finally` block (guaranteed per request)
- **Process-Level**: Runs at process exit (guaranteed once)

---

## 🎯 Recommended Architecture

### Current (Duplicated)
```
┌─────────────────────┐
│  Per-Request        │
│  Cleanup            │
│  - S3 upload        │
│  - ALB deregister   │◄─── Duplicated logic
│  - IP release       │
│  - Dict cleanup     │
└─────────────────────┘

┌─────────────────────┐
│  Process-Level      │
│  Cleanup            │
│  - S3 upload        │◄─── Duplicated logic
│  - Force stop tasks │
└─────────────────────┘
```

### Improved (Unified)
```
┌─────────────────────────────────┐
│  Unified Cleanup Engine         │
│  (Single source of truth)       │
│                                 │
│  def cleanup_resources():       │
│    - S3 upload                  │◄─── Shared logic
│    - ALB deregister             │
│    - IP release                 │
│    - Dict cleanup               │
│    - Task stop (optional)       │
└─────────────────────────────────┘
         ▲                    ▲
         │                    │
    ┌────┴──────┐      ┌─────┴──────┐
    │ Per-Request│      │ Process-Level│
    │ (specific) │      │ (all tasks)  │
    └────────────┘      └──────────────┘
```

**Proposed Implementation**:
```python
class CleanupEngine:
    """Unified cleanup logic"""

    def cleanup(self, request_id=None, scope='single', force=False):
        """
        Unified cleanup method

        Args:
            request_id: Which request to cleanup (None = all)
            scope: 'single' | 'all'
            force: Force stop tasks even if cleanup fails
        """
        if scope == 'single' and request_id:
            # Per-request cleanup
            self._cleanup_single_request(request_id, force=False)
        elif scope == 'all':
            # Process-level cleanup
            self._cleanup_all_requests(force=True)

    def _cleanup_single_request(self, request_id, force):
        # Shared cleanup logic
        self._s3_upload(request_id)
        self._alb_deregister(request_id)
        self._release_ip(request_id)
        self._clear_state(request_id)
        if force:
            self._force_stop_task(request_id)

    def _cleanup_all_requests(self, force):
        # Cleanup all sessions
        for request_id in list(self._sessions.keys()):
            self._cleanup_single_request(request_id, force=force)

# Usage
# Per-request: cleanup_engine.cleanup(request_id, scope='single')
# Process exit: cleanup_engine.cleanup(scope='all', force=True)
```

---

## 📊 Decision Matrix

**Use Per-Request Cleanup When:**
- ✅ Request completes (success or failure)
- ✅ Need to cleanup specific session
- ✅ Other requests are still running
- ✅ Want graceful cleanup without forcing

**Use Process-Level Cleanup When:**
- ✅ Python process exits
- ✅ Need to cleanup ALL sessions
- ✅ Fail-safe is required (orphan cleanup)
- ✅ Force stop is acceptable

**Use Unified Cleanup Engine When:**
- ✅ Reducing code duplication
- ✅ Ensuring consistent behavior
- ✅ Easier maintenance and testing
- ✅ Single source of truth for cleanup logic

---

## 💡 Best Practices

### 1. Keep Fail-Safe (Process-Level)
```python
# ALWAYS keep this for safety
atexit.register(cleanup_fargate_session)
```

**Why**: Guarantees cleanup even if per-request cleanup fails

### 2. Make Per-Request Primary
```python
finally:
    _cleanup_request_session(request_id)  # Primary cleanup
```

**Why**: Faster, more granular, doesn't affect other requests

### 3. Extract Common Logic
```python
# Instead of duplicating S3 upload logic
def _upload_to_s3(session_id, wait=False):
    # Single implementation used by both
    pass
```

### 4. Add Idempotency
```python
def cleanup_session(self, request_id):
    # Safe to call multiple times
    if request_id in self._cleaned_up_requests:
        logger.info(f"Already cleaned up {request_id}")
        return  # Idempotent
```

### 5. Log Cleanup Context
```python
logger.info(f"Cleanup triggered by: {'per-request' if in_request else 'process-exit'}")
```

**Why**: Helps debug which cleanup system ran

---

## 🔧 Immediate Action Items

1. **Keep Both Systems** (for now)
   - Per-request cleanup: Primary path
   - Process-level cleanup: Fail-safe

2. **Extract Common Code**
   - Create `_upload_to_s3_shared()`
   - Create `_stop_task_shared()`

3. **Add Tracking**
   - Log which cleanup system runs
   - Track cleanup failures
   - Monitor orphaned resources

4. **Future Refactoring**
   - Implement unified cleanup engine
   - Consolidate duplicate logic
   - Improve test coverage
