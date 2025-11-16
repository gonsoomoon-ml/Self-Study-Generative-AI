# Sandbox Refactoring Plan: Multi-Backend Code Execution Support

**Date**: 2025-11-16
**Status**: Analysis Complete - Ready for Implementation
**Author**: Claude Code Analysis
**Objective**: Refactor tightly-coupled Fargate sandbox to support multiple execution backends (Fargate, Local, E2B)

---

## Executive Summary

Your codebase has a **clean dual-tool pattern** (Fargate vs Local) but is **100% hardcoded to Fargate** at the runtime level. The good news: you already have parallel implementations that can be leveraged. The challenge: **3 critical coupling points** need abstraction.

### Key Findings

- **Current State**: Runtime cannot function without Fargate
- **Architecture Strength**: Parallel tool implementations already exist
- **Refactoring Scope**: ~725 lines of new code, ~50 lines modified
- **Estimated Effort**: 13-15 hours
- **Risk Level**: Low-Medium (backward compatibility maintained)

---

## Table of Contents

1. [Current Architecture Issues](#current-architecture-issues)
2. [Refactoring Strategy](#refactoring-strategy)
3. [Migration Path](#migration-path)
4. [File Structure](#file-structure-after-refactoring)
5. [Testing Strategy](#testing-strategy)
6. [Risks & Mitigations](#risks--mitigations)
7. [Next Steps](#next-steps-recommended)

---

## Current Architecture Issues

### Critical Coupling Points

| **Location** | **File** | **Lines** | **Impact** |
|--------------|----------|-----------|------------|
| **Runtime Lifecycle** | `agentcore_runtime.py` | 108, 194-211, 346-367 | **BLOCKER** - Cannot run without Fargate |
| **Graph Tool Selection** | `src/graph/nodes.py` | 9 | **HIGH** - Hardcoded Fargate tool imports |
| **Agent Tool Injection** | `coder_agent_fargate_tool.py` | 11, 84-95 | **MEDIUM** - Session creation + tool passing |

### Detailed Coupling Analysis

#### 1. Runtime → Fargate Hardcoded Coupling

**File**: `agentcore_runtime.py`

```python
# Line 108: Direct import of Fargate coordinator
from src.tools.global_fargate_coordinator import get_global_session

# Line 194-211: Fargate session setup (REQUIRED for runtime)
def _setup_fargate_context(request_id: str) -> None:
    fargate_manager = get_global_session()
    fargate_manager.set_request_context(request_id)

# Line 346-367: Fargate cleanup (REQUIRED for runtime)
def _cleanup_request_session(request_id: str) -> None:
    fargate_manager = get_global_session()
    fargate_manager.cleanup_session(request_id)

# Lines 399, 437: Called in every request workflow
_setup_fargate_context(request_id)  # Line 399
_cleanup_request_session(request_id)  # Line 437
```

**Impact**: Runtime cannot function without Fargate. No local execution mode exists.

#### 2. Graph Nodes → Fargate Tools Hardcoded Coupling

**File**: `src/graph/nodes.py`

```python
# Line 9: Hardcoded import of Fargate-enabled tools
from src.tools import (
    coder_agent_fargate_tool,      # ← Fargate version
    reporter_agent_fargate_tool,   # ← Fargate version
    tracker_agent_tool,             # ← Local version
    validator_agent_fargate_tool    # ← Fargate version
)
```

**Impact**: Graph always uses Fargate tools. No environment-based selection.

#### 3. Agent Tools → Sandbox Tool Injection

**File**: `src/tools/coder_agent_fargate_tool.py`

```python
# Line 11: Import Fargate execution tools
from src.tools import fargate_python_tool, fargate_bash_tool

# Line 84-95: Fargate session creation (REQUIRED before agent execution)
from src.tools.global_fargate_coordinator import get_global_session
fargate_manager = get_global_session()

if csv_file_path and os.path.exists(csv_file_path):
    fargate_manager.ensure_session_with_data(csv_file_path)
else:
    fargate_manager.ensure_session()

# Lines 99-113: Agent creation with Fargate tools
coder_agent = strands_utils.get_agent(
    agent_name="coder-fargate",
    tools=[fargate_python_tool, fargate_bash_tool],  # ← Fargate tools injected
    streaming=True
)
```

**Local Equivalent**: `src/tools/coder_agent_tool.py` has **NO session creation** step.

### What Exists (Good News)

You **already have** parallel tool implementations:

```
Fargate Tools                      Local Tools
├─ fargate_python_tool.py      →  python_repl_tool.py
├─ fargate_bash_tool.py        →  bash_tool.py
├─ coder_agent_fargate_tool.py →  coder_agent_tool.py
├─ validator_agent_fargate_tool.py → validator_agent_tool.py
└─ reporter_agent_fargate_tool.py  → (local version missing)
```

**Key Difference**:
- **Fargate tools**: Require `ensure_session()` + use `global_fargate_coordinator`
- **Local tools**: Stateless `subprocess.run()` calls

### Tool Comparison: Fargate vs Local

#### Python Execution Tools

| Feature | `fargate_python_tool.py` | `python_repl_tool.py` |
|---------|--------------------------|------------------------|
| **Lines** | 194 lines | 125 lines |
| **Execution** | `session_manager.execute_code()` | `subprocess.run()` |
| **Isolation** | AWS Fargate container | Local subprocess |
| **Session** | Requires `get_global_session()` | No session (stateless) |
| **Timeout** | Configurable via session manager | 600s hardcoded |
| **State** | Persistent across calls (same container) | Stateless (new subprocess) |
| **Dependencies** | Global coordinator | Python `subprocess` module |

**Fargate Tool Flow**:
```python
session_manager = get_global_session()  # Singleton coordinator
result = session_manager.execute_code(code, "Python execution")  # HTTP → ALB → Container
```

**Local Tool Flow**:
```python
result = subprocess.run([sys.executable, "-c", command], ...)  # Direct subprocess
```

---

## Refactoring Strategy

### Phase 1: Create Sandbox Abstraction Layer ⭐ (Foundation)

**Goal**: Abstract the coordinator interface so runtime doesn't depend on Fargate

#### 1.1 Create Abstract Base Class

**New File**: `src/sandbox/base.py` (~100 lines)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class SandboxCoordinator(ABC):
    """
    Abstract interface for code execution sandbox management.

    This interface defines the contract that all sandbox implementations
    must follow. It handles the complete lifecycle of sandbox sessions:
    - Request context management
    - Session creation and data loading
    - Code execution
    - Resource cleanup

    Implementations:
    - FargateCoordinator: AWS Fargate containers with ALB routing
    - LocalCoordinator: Local subprocess execution (stateless)
    - E2BCoordinator: E2B cloud sandboxes
    """

    @abstractmethod
    def set_request_context(self, request_id: str) -> None:
        """
        Set the current request context for tracking.

        Associates subsequent operations with a specific request ID for
        logging, tracing, and resource cleanup.

        Args:
            request_id: Unique identifier for the current request
        """
        pass

    @abstractmethod
    def ensure_session(self) -> bool:
        """
        Create or verify a basic sandbox session.

        Ensures a sandbox environment is available for code execution.
        For stateful backends (Fargate, E2B), this creates containers.
        For stateless backends (Local), this may be a no-op.

        Returns:
            bool: True if session is ready, False on failure
        """
        pass

    @abstractmethod
    def ensure_session_with_data(self, csv_path: str) -> bool:
        """
        Create session with pre-loaded data file.

        Creates a sandbox session and uploads/mounts the specified
        CSV file for immediate access by code execution.

        Args:
            csv_path: Local path to CSV file to load into sandbox

        Returns:
            bool: True if session created and data loaded, False on failure
        """
        pass

    @abstractmethod
    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Execute code in the sandbox.

        Runs arbitrary code in the isolated sandbox environment and
        returns the execution result.

        Args:
            code: Code string to execute
            description: Human-readable description for logging

        Returns:
            dict: Execution result with keys:
                - success (bool): Whether execution succeeded
                - output (str): Standard output from execution
                - error (str): Error message if failed
        """
        pass

    @abstractmethod
    def cleanup_session(self, request_id: str) -> None:
        """
        Clean up resources for a completed request.

        Terminates sandbox environments, closes connections, and
        releases resources associated with the request.

        Args:
            request_id: Request identifier to clean up
        """
        pass
```

#### 1.2 Refactor Fargate Coordinator

**Action**: Rename and refactor existing code

**From**: `src/tools/global_fargate_coordinator.py` (990 lines)
**To**: `src/sandbox/fargate_coordinator.py` (990 lines + ~20 lines for class inheritance)

```python
"""
AWS Fargate implementation of sandbox coordinator.

This coordinator manages code execution in AWS Fargate containers
with ALB-based session routing and cookie-based stickiness.

Architecture:
    1. Creates ECS Fargate tasks on-demand
    2. Registers containers to ALB target group
    3. Acquires sticky session cookies for routing
    4. Executes code via HTTP POST to ALB
    5. Cleans up containers and deregisters from ALB

Components:
    - FargateCoordinator: High-level session manager (singleton)
    - SessionBasedFargateManager: Container lifecycle controller
    - Cookie acquisition: Subprocess-based isolation
"""

from src.sandbox.base import SandboxCoordinator
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class FargateCoordinator(SandboxCoordinator):
    """AWS Fargate implementation of sandbox coordinator."""

    # Move all GlobalFargateSessionManager code here
    # Inherit from SandboxCoordinator and implement all abstract methods
    # Keep exact same implementation logic

    def __init__(self):
        """Initialize Fargate coordinator with AWS clients."""
        # Existing GlobalFargateSessionManager.__init__ code
        pass

    def set_request_context(self, request_id: str) -> None:
        """Set request context for Fargate session tracking."""
        # Existing implementation
        pass

    def ensure_session(self) -> bool:
        """Create Fargate container session."""
        # Existing implementation
        pass

    def ensure_session_with_data(self, csv_path: str) -> bool:
        """Create Fargate session with S3 data upload."""
        # Existing implementation
        pass

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """Execute code via ALB → Fargate container."""
        # Existing implementation
        pass

    def cleanup_session(self, request_id: str) -> None:
        """Stop Fargate task and deregister from ALB."""
        # Existing implementation
        pass

# Keep all helper classes and functions
class SessionBasedFargateManager:
    # Existing implementation (unchanged)
    pass

# Singleton accessor (backward compatibility)
_fargate_instance: Optional[FargateCoordinator] = None

def get_global_session() -> FargateCoordinator:
    """Get singleton Fargate coordinator (legacy function)."""
    global _fargate_instance
    if _fargate_instance is None:
        _fargate_instance = FargateCoordinator()
    return _fargate_instance
```

**Changes**:
- Add `from src.sandbox.base import SandboxCoordinator`
- Change `class GlobalFargateSessionManager` → `class FargateCoordinator(SandboxCoordinator)`
- Keep all existing methods (they already match the interface)
- No logic changes required

#### 1.3 Create Local Coordinator

**New File**: `src/sandbox/local_coordinator.py` (~150 lines)

```python
"""
Local subprocess implementation of sandbox coordinator.

This coordinator executes code in local Python/Bash subprocesses
without persistent sessions or isolation. Suitable for development
and testing without AWS infrastructure.

Characteristics:
    - Stateless: Each code execution creates a new subprocess
    - No session management: ensure_session() is a no-op
    - No cleanup needed: Processes auto-terminate after execution
    - Direct filesystem access: CSV files read from local disk
"""

from src.sandbox.base import SandboxCoordinator
from typing import Dict, Any
import subprocess
import sys
import logging

logger = logging.getLogger(__name__)

class LocalCoordinator(SandboxCoordinator):
    """Local subprocess implementation (no session management)."""

    def __init__(self):
        """Initialize local coordinator (stateless)."""
        self.request_id = None
        self.csv_path = None
        logger.info("🖥️  Initialized LocalCoordinator (subprocess execution)")

    def set_request_context(self, request_id: str) -> None:
        """
        Set request context (no-op for local mode).

        Local mode is stateless, but we store the request ID for logging.
        """
        self.request_id = request_id
        logger.info(f"📋 Local coordinator: Request context set to {request_id}")

    def ensure_session(self) -> bool:
        """
        Ensure session is ready (always ready for local mode).

        Local mode doesn't require session setup - subprocesses are
        created on-demand for each execution.

        Returns:
            bool: Always True (local execution always available)
        """
        logger.info("✅ Local coordinator: Session ready (stateless mode)")
        return True

    def ensure_session_with_data(self, csv_path: str) -> bool:
        """
        Prepare session with data file (verify file exists).

        For local mode, this verifies the CSV file exists on the
        local filesystem. No upload needed since subprocess can
        access files directly.

        Args:
            csv_path: Path to CSV file

        Returns:
            bool: True if file exists, False otherwise
        """
        import os
        if not os.path.exists(csv_path):
            logger.error(f"❌ Local coordinator: CSV file not found: {csv_path}")
            return False

        self.csv_path = csv_path
        logger.info(f"✅ Local coordinator: CSV file verified: {csv_path}")
        return True

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Execute Python code in local subprocess.

        Creates a new Python subprocess for each execution. The code
        runs in the same Python version as the runtime.

        Args:
            code: Python code to execute
            description: Human-readable description for logging

        Returns:
            dict: Execution result with keys:
                - success (bool): Whether execution succeeded
                - output (str): Combined stdout/stderr
                - error (str): Error message if failed
        """
        logger.info(f"🐍 Local coordinator: Executing code ({description})")

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes (same as python_repl_tool)
            )

            output = result.stdout if result.returncode == 0 else result.stderr
            success = result.returncode == 0

            if success:
                logger.info("✅ Local coordinator: Code executed successfully")
            else:
                logger.warning(f"⚠️  Local coordinator: Code failed with code {result.returncode}")

            return {
                "success": success,
                "output": output,
                "error": "" if success else result.stderr
            }

        except subprocess.TimeoutExpired:
            logger.error("❌ Local coordinator: Code execution timeout (600s)")
            return {
                "success": False,
                "output": "",
                "error": "Code execution timeout after 600 seconds"
            }
        except Exception as e:
            logger.error(f"❌ Local coordinator: Code execution failed: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def cleanup_session(self, request_id: str) -> None:
        """
        Clean up resources (no-op for local mode).

        Local mode uses ephemeral subprocesses that auto-terminate,
        so no cleanup is needed.
        """
        logger.info(f"🧹 Local coordinator: Cleanup complete for {request_id} (no resources to clean)")
        self.request_id = None
        self.csv_path = None
```

#### 1.4 Create E2B Coordinator (Stub)

**New File**: `src/sandbox/e2b_coordinator.py` (~200 lines estimated)

```python
"""
E2B (Third-party) sandbox implementation of coordinator.

This coordinator manages code execution in E2B cloud sandboxes.
E2B provides isolated containerized environments with file system,
package management, and long-running sessions.

Architecture:
    1. Create E2B sandbox on ensure_session()
    2. Upload files via E2B file system API
    3. Execute code via E2B process API
    4. Clean up sandbox on request completion

Status: STUB IMPLEMENTATION - Requires E2B SDK integration

Dependencies:
    pip install e2b
"""

from src.sandbox.base import SandboxCoordinator
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class E2BCoordinator(SandboxCoordinator):
    """
    E2B sandbox implementation.

    TODO: Implement E2B integration
    - Install e2b SDK: pip install e2b
    - Configure E2B API key
    - Implement sandbox lifecycle
    """

    def __init__(self):
        """Initialize E2B coordinator."""
        self.sessions = {}  # request_id → e2b_sandbox
        self.current_request_id = None
        logger.warning("⚠️  E2BCoordinator: STUB IMPLEMENTATION - Not functional yet")

        # TODO: Initialize E2B client
        # from e2b import Sandbox
        # self.e2b_client = Sandbox(api_key=os.getenv("E2B_API_KEY"))

    def set_request_context(self, request_id: str) -> None:
        """Set request context for E2B session tracking."""
        self.current_request_id = request_id
        logger.info(f"📋 E2B coordinator: Request context set to {request_id}")

    def ensure_session(self) -> bool:
        """
        Create E2B sandbox session.

        TODO: Implement
        - Create E2B sandbox
        - Store sandbox reference in self.sessions
        - Configure environment (install packages, set working directory)

        Returns:
            bool: True if sandbox created successfully
        """
        logger.error("❌ E2B coordinator: ensure_session() not implemented")
        return False

        # TODO: Implement
        # try:
        #     sandbox = Sandbox.create()
        #     self.sessions[self.current_request_id] = sandbox
        #     logger.info(f"✅ E2B sandbox created: {sandbox.id}")
        #     return True
        # except Exception as e:
        #     logger.error(f"❌ E2B sandbox creation failed: {e}")
        #     return False

    def ensure_session_with_data(self, csv_path: str) -> bool:
        """
        Create E2B session with uploaded CSV file.

        TODO: Implement
        - Create sandbox
        - Upload CSV file to sandbox filesystem
        - Verify file uploaded successfully

        Args:
            csv_path: Local path to CSV file

        Returns:
            bool: True if session created and file uploaded
        """
        logger.error("❌ E2B coordinator: ensure_session_with_data() not implemented")
        return False

        # TODO: Implement
        # if not self.ensure_session():
        #     return False
        #
        # try:
        #     sandbox = self.sessions[self.current_request_id]
        #     with open(csv_path, 'rb') as f:
        #         sandbox.filesystem.write('data.csv', f.read())
        #     logger.info(f"✅ Uploaded {csv_path} to E2B sandbox")
        #     return True
        # except Exception as e:
        #     logger.error(f"❌ File upload failed: {e}")
        #     return False

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Execute code in E2B sandbox.

        TODO: Implement
        - Get sandbox for current request
        - Execute code via sandbox.process API
        - Capture stdout/stderr
        - Return formatted result

        Args:
            code: Code to execute
            description: Human-readable description

        Returns:
            dict: Execution result
        """
        logger.error("❌ E2B coordinator: execute_code() not implemented")
        return {
            "success": False,
            "output": "",
            "error": "E2B coordinator not implemented"
        }

        # TODO: Implement
        # try:
        #     sandbox = self.sessions.get(self.current_request_id)
        #     if not sandbox:
        #         return {"success": False, "output": "", "error": "No active session"}
        #
        #     process = sandbox.process.start_and_wait(code)
        #     return {
        #         "success": process.exit_code == 0,
        #         "output": process.stdout,
        #         "error": process.stderr if process.exit_code != 0 else ""
        #     }
        # except Exception as e:
        #     logger.error(f"❌ Code execution failed: {e}")
        #     return {"success": False, "output": "", "error": str(e)}

    def cleanup_session(self, request_id: str) -> None:
        """
        Clean up E2B sandbox.

        TODO: Implement
        - Get sandbox for request
        - Kill sandbox
        - Remove from sessions dict
        """
        logger.warning(f"⚠️  E2B coordinator: cleanup_session() not implemented for {request_id}")

        # TODO: Implement
        # try:
        #     sandbox = self.sessions.pop(request_id, None)
        #     if sandbox:
        #         sandbox.kill()
        #         logger.info(f"✅ E2B sandbox cleaned up: {sandbox.id}")
        # except Exception as e:
        #     logger.error(f"❌ Cleanup failed: {e}")
```

---

### Phase 2: Factory Pattern for Sandbox Selection ⭐

#### 2.1 Create Sandbox Factory

**New File**: `src/sandbox/factory.py` (~80 lines)

```python
"""
Sandbox coordinator factory with singleton pattern.

This module provides the central factory for creating and accessing
sandbox coordinators. It implements a singleton pattern to ensure
only one coordinator instance exists per runtime process.

Configuration:
    Set SANDBOX_MODE environment variable to select backend:
    - "fargate" (default): AWS Fargate containers
    - "local": Local subprocess execution
    - "e2b": E2B cloud sandboxes

Usage:
    from src.sandbox.factory import get_sandbox_coordinator

    coordinator = get_sandbox_coordinator()  # Uses SANDBOX_MODE env var
    coordinator = get_sandbox_coordinator(mode="local")  # Override
"""

import os
from typing import Optional
from src.sandbox.base import SandboxCoordinator
from src.sandbox.fargate_coordinator import FargateCoordinator
from src.sandbox.local_coordinator import LocalCoordinator
from src.sandbox.e2b_coordinator import E2BCoordinator
import logging

logger = logging.getLogger(__name__)

# Singleton instance cache
_coordinator_instance: Optional[SandboxCoordinator] = None

def get_sandbox_coordinator(mode: str = None) -> SandboxCoordinator:
    """
    Get sandbox coordinator based on configuration.

    Returns a singleton instance of the configured sandbox coordinator.
    The coordinator type is determined by the SANDBOX_MODE environment
    variable or the mode parameter (parameter takes precedence).

    Args:
        mode: Override mode (fargate|local|e2b).
              If None, reads from SANDBOX_MODE env var.
              Default: "fargate"

    Returns:
        Configured sandbox coordinator instance (singleton)

    Raises:
        ValueError: If unknown sandbox mode specified

    Examples:
        # Use environment variable
        os.environ["SANDBOX_MODE"] = "local"
        coordinator = get_sandbox_coordinator()  # Returns LocalCoordinator

        # Override with parameter
        coordinator = get_sandbox_coordinator(mode="e2b")  # Returns E2BCoordinator
    """
    global _coordinator_instance

    # Return existing instance if already created
    if _coordinator_instance is not None:
        logger.debug(f"Returning existing {_coordinator_instance.__class__.__name__}")
        return _coordinator_instance

    # Read from environment if not specified
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.info(f"🔧 Initializing sandbox coordinator: mode={mode}")

    # Create coordinator based on mode
    if mode == "fargate":
        _coordinator_instance = FargateCoordinator()
        logger.info("✅ FargateCoordinator initialized (AWS Fargate containers)")
    elif mode == "local":
        _coordinator_instance = LocalCoordinator()
        logger.info("✅ LocalCoordinator initialized (local subprocess execution)")
    elif mode == "e2b":
        _coordinator_instance = E2BCoordinator()
        logger.info("✅ E2BCoordinator initialized (E2B cloud sandboxes)")
    else:
        raise ValueError(
            f"Unknown sandbox mode: '{mode}'. "
            f"Valid options: fargate, local, e2b. "
            f"Set SANDBOX_MODE environment variable or pass mode parameter."
        )

    return _coordinator_instance

def reset_coordinator() -> None:
    """
    Reset the singleton coordinator instance.

    This is primarily used for testing to allow switching between
    different coordinator modes within the same process.

    Warning:
        This will abandon any active sessions. Only use this during
        testing or at process shutdown.
    """
    global _coordinator_instance
    if _coordinator_instance:
        logger.warning(f"⚠️  Resetting coordinator: {_coordinator_instance.__class__.__name__}")
    _coordinator_instance = None

# Backward compatibility alias
def get_global_session() -> SandboxCoordinator:
    """
    Get sandbox coordinator (legacy function name).

    This function provides backward compatibility for code that
    previously used get_global_session() to access the Fargate
    coordinator.

    Deprecated:
        Use get_sandbox_coordinator() instead.

    Returns:
        Sandbox coordinator instance (singleton)
    """
    return get_sandbox_coordinator()
```

#### 2.2 Create Sandbox Package Init

**New File**: `src/sandbox/__init__.py` (~15 lines)

```python
"""
Sandbox coordinator package.

This package provides abstract interfaces and concrete implementations
for code execution sandboxes.

Public API:
    - get_sandbox_coordinator(): Get configured coordinator (singleton)
    - SandboxCoordinator: Abstract base class for coordinators

Implementations:
    - FargateCoordinator: AWS Fargate containers
    - LocalCoordinator: Local subprocess execution
    - E2BCoordinator: E2B cloud sandboxes
"""

from src.sandbox.factory import get_sandbox_coordinator, get_global_session
from src.sandbox.base import SandboxCoordinator

__all__ = [
    "get_sandbox_coordinator",
    "get_global_session",  # Backward compatibility
    "SandboxCoordinator"
]
```

#### 2.3 Update Environment Configuration

**Modified File**: `.env.example` (add after line 35)

```bash
# ============================================================
# Sandbox Configuration
# ============================================================
# Code execution sandbox backend selection
# Options:
#   - fargate (default): AWS Fargate containers with ALB routing
#   - local: Local subprocess execution (development/testing)
#   - e2b: E2B cloud sandboxes (third-party, requires API key)
SANDBOX_MODE=fargate

# E2B Configuration (only needed if SANDBOX_MODE=e2b)
# E2B_API_KEY=your_e2b_api_key_here

# ============================================================
# Bedrock Model Configuration
# ============================================================
```

---

### Phase 3: Dynamic Tool Selection ⭐

#### 3.1 Create Tool Factory

**New File**: `src/tools/tool_factory.py` (~200 lines)

```python
"""
Dynamic tool selection based on sandbox mode.

This module provides factory functions for selecting the appropriate
execution tools based on the configured sandbox backend.

Each sandbox mode has its own set of tools:
    - Fargate: fargate_python_tool, fargate_bash_tool
    - Local: python_repl_tool, bash_tool
    - E2B: e2b_python_tool, e2b_bash_tool (when implemented)

Configuration:
    Set SANDBOX_MODE environment variable (fargate|local|e2b)

Usage:
    from src.tools.tool_factory import get_python_tool, get_bash_tool

    python_tool = get_python_tool()  # Returns tool based on SANDBOX_MODE
    bash_tool = get_bash_tool()
"""

import os
from typing import Any
import logging

logger = logging.getLogger(__name__)

def get_python_tool(sandbox_mode: str = None) -> Any:
    """
    Get Python execution tool based on sandbox mode.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        Python tool function for the selected sandbox

    Raises:
        ValueError: If unknown sandbox mode specified
    """
    mode = sandbox_mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.debug(f"Loading Python tool for mode: {mode}")

    if mode == "fargate":
        from src.tools.fargate_python_tool import fargate_python_tool
        logger.debug("✅ Loaded fargate_python_tool")
        return fargate_python_tool
    elif mode == "local":
        from src.tools.python_repl_tool import python_repl_tool
        logger.debug("✅ Loaded python_repl_tool")
        return python_repl_tool
    elif mode == "e2b":
        # TODO: Implement E2B Python tool
        logger.error("❌ E2B Python tool not implemented yet")
        raise NotImplementedError("E2B Python tool not implemented")
    else:
        raise ValueError(f"Unknown sandbox mode: '{mode}'")

def get_bash_tool(sandbox_mode: str = None) -> Any:
    """
    Get Bash execution tool based on sandbox mode.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        Bash tool function for the selected sandbox

    Raises:
        ValueError: If unknown sandbox mode specified
    """
    mode = sandbox_mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.debug(f"Loading Bash tool for mode: {mode}")

    if mode == "fargate":
        from src.tools.fargate_bash_tool import fargate_bash_tool
        logger.debug("✅ Loaded fargate_bash_tool")
        return fargate_bash_tool
    elif mode == "local":
        from src.tools.bash_tool import bash_tool
        logger.debug("✅ Loaded bash_tool")
        return bash_tool
    elif mode == "e2b":
        # TODO: Implement E2B Bash tool
        logger.error("❌ E2B Bash tool not implemented yet")
        raise NotImplementedError("E2B Bash tool not implemented")
    else:
        raise ValueError(f"Unknown sandbox mode: '{mode}'")

def get_coder_agent_tool(sandbox_mode: str = None) -> Any:
    """
    Get coder agent tool based on sandbox mode.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        Coder agent tool function for the selected sandbox

    Raises:
        ValueError: If unknown sandbox mode specified
    """
    mode = sandbox_mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.debug(f"Loading Coder Agent tool for mode: {mode}")

    if mode == "fargate":
        from src.tools.coder_agent_fargate_tool import coder_agent_fargate_tool
        logger.debug("✅ Loaded coder_agent_fargate_tool")
        return coder_agent_fargate_tool
    elif mode == "local":
        from src.tools.coder_agent_tool import coder_agent_tool
        logger.debug("✅ Loaded coder_agent_tool")
        return coder_agent_tool
    elif mode == "e2b":
        # TODO: Implement E2B Coder Agent tool
        logger.error("❌ E2B Coder Agent tool not implemented yet")
        raise NotImplementedError("E2B Coder Agent tool not implemented")
    else:
        raise ValueError(f"Unknown sandbox mode: '{mode}'")

def get_validator_agent_tool(sandbox_mode: str = None) -> Any:
    """
    Get validator agent tool based on sandbox mode.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        Validator agent tool function for the selected sandbox

    Raises:
        ValueError: If unknown sandbox mode specified
    """
    mode = sandbox_mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.debug(f"Loading Validator Agent tool for mode: {mode}")

    if mode == "fargate":
        from src.tools.validator_agent_fargate_tool import validator_agent_fargate_tool
        logger.debug("✅ Loaded validator_agent_fargate_tool")
        return validator_agent_fargate_tool
    elif mode == "local":
        from src.tools.validator_agent_tool import validator_agent_tool
        logger.debug("✅ Loaded validator_agent_tool")
        return validator_agent_tool
    elif mode == "e2b":
        # TODO: Implement E2B Validator Agent tool
        logger.error("❌ E2B Validator Agent tool not implemented yet")
        raise NotImplementedError("E2B Validator Agent tool not implemented")
    else:
        raise ValueError(f"Unknown sandbox mode: '{mode}'")

def get_reporter_agent_tool(sandbox_mode: str = None) -> Any:
    """
    Get reporter agent tool based on sandbox mode.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        Reporter agent tool function for the selected sandbox

    Raises:
        ValueError: If unknown sandbox mode specified
    """
    mode = sandbox_mode or os.getenv("SANDBOX_MODE", "fargate")
    mode = mode.lower().strip()

    logger.debug(f"Loading Reporter Agent tool for mode: {mode}")

    if mode == "fargate":
        from src.tools.reporter_agent_fargate_tool import reporter_agent_fargate_tool
        logger.debug("✅ Loaded reporter_agent_fargate_tool")
        return reporter_agent_fargate_tool
    elif mode == "local":
        # TODO: Create reporter_agent_tool.py (local version)
        logger.error("❌ Local Reporter Agent tool not implemented yet")
        raise NotImplementedError("Local Reporter Agent tool not implemented")
    elif mode == "e2b":
        # TODO: Implement E2B Reporter Agent tool
        logger.error("❌ E2B Reporter Agent tool not implemented yet")
        raise NotImplementedError("E2B Reporter Agent tool not implemented")
    else:
        raise ValueError(f"Unknown sandbox mode: '{mode}'")

def get_all_agent_tools(sandbox_mode: str = None) -> dict:
    """
    Get all agent tools for the selected sandbox mode.

    Returns a dictionary of all available agent tools, making it
    easy to pass them to graph nodes or supervisor.

    Args:
        sandbox_mode: Override mode (fargate|local|e2b).
                     If None, reads from SANDBOX_MODE env var.

    Returns:
        dict: Agent tools with keys:
            - coder_agent
            - validator_agent
            - reporter_agent
            - tracker_agent (always local)
    """
    from src.tools import tracker_agent_tool  # Always local

    try:
        tools = {
            "coder_agent": get_coder_agent_tool(sandbox_mode),
            "validator_agent": get_validator_agent_tool(sandbox_mode),
            "tracker_agent": tracker_agent_tool,  # Tracker is always local
        }

        # Reporter may not be available in all modes
        try:
            tools["reporter_agent"] = get_reporter_agent_tool(sandbox_mode)
        except NotImplementedError:
            logger.warning("⚠️  Reporter agent tool not available for this mode")

        return tools

    except Exception as e:
        logger.error(f"❌ Failed to load agent tools: {e}")
        raise
```

#### 3.2 Update Graph Nodes

**Modified File**: `src/graph/nodes.py`

```diff
- # Line 9: OLD - Hardcoded Fargate tool imports
- from src.tools import coder_agent_fargate_tool, reporter_agent_fargate_tool, tracker_agent_tool, validator_agent_fargate_tool
+ # Line 9: NEW - Dynamic tool selection
+ from src.tools.tool_factory import get_all_agent_tools
+ from src.tools import tracker_agent_tool
+
+ # Load tools based on SANDBOX_MODE environment variable
+ _agent_tools = get_all_agent_tools()
+ coder_agent_tool = _agent_tools["coder_agent"]
+ validator_agent_tool = _agent_tools["validator_agent"]
+ reporter_agent_tool = _agent_tools.get("reporter_agent")  # May be None
+
+ # Build tools list (exclude None values)
+ _supervisor_tools = [coder_agent_tool, tracker_agent_tool, validator_agent_tool]
+ if reporter_agent_tool:
+     _supervisor_tools.append(reporter_agent_tool)
```

```diff
  # Line 213: OLD - Hardcoded tool list
- tools=[coder_agent_fargate_tool, reporter_agent_fargate_tool, tracker_agent_tool, validator_agent_fargate_tool],
+ # Line 213: NEW - Dynamic tool list
+ tools=_supervisor_tools,
```

---

### Phase 4: Update Runtime ⭐

**Modified File**: `agentcore_runtime.py`

```diff
- # Line 108: OLD - Import Fargate coordinator directly
- from src.tools.global_fargate_coordinator import get_global_session
+ # Line 108: NEW - Import sandbox factory
+ from src.sandbox.factory import get_sandbox_coordinator

- # Line 205: OLD - Get Fargate manager
- fargate_manager = get_global_session()
+ # Line 205: NEW - Get sandbox coordinator
+ sandbox_coordinator = get_sandbox_coordinator()

- # Line 206: OLD - Set Fargate context
- fargate_manager.set_request_context(request_id)
+ # Line 206: NEW - Set sandbox context
+ sandbox_coordinator.set_request_context(request_id)

- # Line 207: OLD - Fargate-specific log message
- print(f"✅ Fargate session context set for request: {request_id}", flush=True)
+ # Line 207: NEW - Generic log message
+ print(f"✅ Sandbox session context set for request: {request_id}", flush=True)

- # Line 358: OLD - Get Fargate manager for cleanup
- fargate_manager = get_global_session()
+ # Line 358: NEW - Get sandbox coordinator for cleanup
+ sandbox_coordinator = get_sandbox_coordinator()

- # Line 359: OLD - Fargate-specific log message
- print(f"\n🧹 Request {request_id} completed - cleaning up Fargate session...", flush=True)
+ # Line 359: NEW - Generic log message
+ print(f"\n🧹 Request {request_id} completed - cleaning up sandbox session...", flush=True)

- # Line 360: OLD - Cleanup Fargate session
- fargate_manager.cleanup_session(request_id)
+ # Line 360: NEW - Cleanup sandbox session
+ sandbox_coordinator.cleanup_session(request_id)

- # Line 361: OLD - Fargate-specific log message
- print(f"✅ Fargate session cleaned up for request {request_id}", flush=True)
+ # Line 361: NEW - Generic log message
+ print(f"✅ Sandbox session cleaned up for request {request_id}", flush=True)
```

**Optional**: Rename functions for clarity (not required)

```diff
- def _setup_fargate_context(request_id: str) -> None:
+ def _setup_sandbox_context(request_id: str) -> None:
      """
-     Set up Fargate session context for request.
+     Set up sandbox session context for request.

-     Initializes the Fargate session manager with the request ID for tracking
+     Initializes the sandbox coordinator with the request ID for tracking
      and managing container lifecycle during execution.
```

---

## Migration Path

### Recommended Order (Minimize Risk)

| Phase | Files Changed | Risk | Testing Required |
|-------|---------------|------|------------------|
| **1A** | Create `src/sandbox/` directory + `base.py` | **LOW** | Unit test abstract class |
| **1B** | Move Fargate code → `fargate_coordinator.py` | **LOW** | Import test |
| **2A** | Create `factory.py` + `__init__.py` | **LOW** | Factory selection test |
| **2B** | Update `.env.example` (add SANDBOX_MODE) | **LOW** | Config validation |
| **3A** | Test factory with Fargate mode | **MEDIUM** | End-to-end Fargate test |
| **4A** | Update `agentcore_runtime.py` | **MEDIUM** | Runtime integration test |
| **4B** | Test runtime with Fargate mode | **HIGH** | Full workflow test |
| **5A** | Create `tool_factory.py` | **LOW** | Tool selection test |
| **5B** | Update `src/graph/nodes.py` | **MEDIUM** | Graph execution test |
| **5C** | Test graph with Fargate tools | **HIGH** | End-to-end agent test |
| **6A** | Implement `LocalCoordinator` | **LOW** | Local mode unit test |
| **6B** | Test local mode end-to-end | **MEDIUM** | Full workflow (local) |
| **7A** | Implement `E2BCoordinator` (stub) | **LOW** | E2B mode validation |
| **7B** | Test E2B mode (when ready) | **MEDIUM** | Full workflow (E2B) |

### Step-by-Step Migration

#### Phase 1: Foundation (2-3 hours)

```bash
# 1. Create directory structure
mkdir -p src/sandbox
touch src/sandbox/__init__.py
touch src/sandbox/base.py
touch src/sandbox/factory.py

# 2. Write abstract base class
# Edit src/sandbox/base.py (copy from Phase 1.1 above)

# 3. Move Fargate coordinator
cp src/tools/global_fargate_coordinator.py src/sandbox/fargate_coordinator.py
# Edit src/sandbox/fargate_coordinator.py:
#   - Add: from src.sandbox.base import SandboxCoordinator
#   - Change: class GlobalFargateSessionManager → class FargateCoordinator(SandboxCoordinator)

# 4. Create factory
# Edit src/sandbox/factory.py (copy from Phase 2.1 above)

# 5. Update package init
# Edit src/sandbox/__init__.py (copy from Phase 2.2 above)

# 6. Test imports
python3 -c "from src.sandbox import get_sandbox_coordinator; print(get_sandbox_coordinator())"
# Should print: FargateCoordinator instance
```

#### Phase 2: Runtime Integration (1-2 hours)

```bash
# 1. Update runtime imports
# Edit agentcore_runtime.py (see Phase 4 changes)

# 2. Test runtime (should work identically to before)
SANDBOX_MODE=fargate python3 agentcore_runtime.py

# 3. Run end-to-end test
python3 02_invoke_agentcore_runtime_vpc.py
# Expected: Identical behavior to current production
```

#### Phase 3: Tool Selection (2-3 hours)

```bash
# 1. Create tool factory
touch src/tools/tool_factory.py
# Edit src/tools/tool_factory.py (copy from Phase 3.1 above)

# 2. Update graph nodes
# Edit src/graph/nodes.py (see Phase 3.2 changes)

# 3. Test tool loading
python3 -c "from src.tools.tool_factory import get_all_agent_tools; print(get_all_agent_tools())"

# 4. Run end-to-end test
python3 02_invoke_agentcore_runtime_vpc.py
# Expected: Identical behavior, but using dynamic tool selection
```

#### Phase 4: Local Mode (2-3 hours)

```bash
# 1. Create local coordinator
touch src/sandbox/local_coordinator.py
# Edit src/sandbox/local_coordinator.py (copy from Phase 1.3 above)

# 2. Update .env
echo "SANDBOX_MODE=local" >> .env

# 3. Test local mode
SANDBOX_MODE=local python3 -c "from src.sandbox import get_sandbox_coordinator; c = get_sandbox_coordinator(); print(c.ensure_session())"

# 4. Run end-to-end test (local mode)
SANDBOX_MODE=local python3 02_invoke_agentcore_runtime_vpc.py
# Expected: Works without AWS (using local subprocess)
```

#### Phase 5: E2B Stub (1-2 hours)

```bash
# 1. Create E2B coordinator stub
touch src/sandbox/e2b_coordinator.py
# Edit src/sandbox/e2b_coordinator.py (copy from Phase 1.4 above)

# 2. Test E2B mode (should fail gracefully)
SANDBOX_MODE=e2b python3 -c "from src.sandbox import get_sandbox_coordinator; get_sandbox_coordinator()"
# Expected: E2BCoordinator instance (but methods not implemented)

# 3. Implement E2B integration (future work)
# - Install E2B SDK: pip install e2b
# - Implement methods in E2BCoordinator
# - Test E2B end-to-end
```

---

## File Structure (After Refactoring)

```
/home/ubuntu/Self-Study-Generative-AI/lab/20_deep_insight/
├── agentcore_runtime.py                     # ✏️  MODIFIED - Uses sandbox factory
├── .env.example                              # ✏️  MODIFIED - Adds SANDBOX_MODE
├── src/
│   ├── sandbox/                              # 🆕 NEW DIRECTORY
│   │   ├── __init__.py                       # 🆕 Exports get_sandbox_coordinator
│   │   ├── base.py                           # 🆕 Abstract base class (~100 lines)
│   │   ├── factory.py                        # 🆕 Singleton factory (~80 lines)
│   │   ├── fargate_coordinator.py            # 🆕 Moved from global_fargate_coordinator (~1000 lines)
│   │   ├── local_coordinator.py              # 🆕 Local subprocess (~150 lines)
│   │   └── e2b_coordinator.py                # 🆕 E2B integration stub (~200 lines)
│   ├── tools/
│   │   ├── tool_factory.py                   # 🆕 Dynamic tool selection (~200 lines)
│   │   ├── global_fargate_coordinator.py     # ⚠️  DEPRECATED (backward compat wrapper)
│   │   ├── fargate_python_tool.py            # ✅ UNCHANGED
│   │   ├── fargate_bash_tool.py              # ✅ UNCHANGED
│   │   ├── python_repl_tool.py               # ✅ UNCHANGED
│   │   ├── bash_tool.py                      # ✅ UNCHANGED
│   │   ├── coder_agent_fargate_tool.py       # ✅ UNCHANGED
│   │   ├── coder_agent_tool.py               # ✅ UNCHANGED
│   │   ├── validator_agent_fargate_tool.py   # ✅ UNCHANGED
│   │   ├── validator_agent_tool.py           # ✅ UNCHANGED
│   │   ├── reporter_agent_fargate_tool.py    # ✅ UNCHANGED
│   │   └── tracker_agent_tool.py             # ✅ UNCHANGED
│   └── graph/
│       └── nodes.py                          # ✏️  MODIFIED - Uses tool factory
```

**Legend**:
- 🆕 **NEW**: New file created
- ✏️  **MODIFIED**: Existing file modified
- ✅ **UNCHANGED**: Existing file (no changes)
- ⚠️  **DEPRECATED**: Legacy file (for backward compatibility)

---

## Backward Compatibility Strategy

### Maintain Existing Behavior

1. **Default to Fargate**: `SANDBOX_MODE=fargate` by default in `.env.example`
2. **Import Alias**: `get_global_session()` → `get_sandbox_coordinator()`
3. **No Breaking Changes**: Fargate mode works exactly as before
4. **Gradual Migration**: Old imports still work during transition

### Deprecation Wrapper

**File**: `src/tools/global_fargate_coordinator.py` (deprecated)

```python
"""
DEPRECATED: This module is deprecated. Use src.sandbox.factory instead.

This file provides backward compatibility for code that imports
from global_fargate_coordinator. New code should use:

    from src.sandbox import get_sandbox_coordinator
"""

import warnings
from src.sandbox.factory import get_sandbox_coordinator as _get_coordinator

def get_global_session():
    """
    DEPRECATED: Use get_sandbox_coordinator() instead.

    This function provides backward compatibility for existing code.
    It will be removed in a future version.
    """
    warnings.warn(
        "get_global_session() is deprecated. "
        "Use 'from src.sandbox import get_sandbox_coordinator' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_coordinator()

# Re-export for compatibility (will be removed in future)
GlobalFargateSessionManager = None  # Placeholder (use FargateCoordinator instead)

# Show deprecation notice on import
warnings.warn(
    "Module 'src.tools.global_fargate_coordinator' is deprecated. "
    "Import from 'src.sandbox.factory' instead.",
    DeprecationWarning,
    stacklevel=2
)
```

---

## Testing Strategy

### Phase 1: Unit Tests

Create test files for each new component:

```bash
tests/
├── sandbox/
│   ├── test_base.py              # Test abstract interface
│   ├── test_factory.py           # Test factory selection
│   ├── test_fargate_coordinator.py  # Test Fargate coordinator
│   └── test_local_coordinator.py    # Test local coordinator
└── tools/
    └── test_tool_factory.py      # Test tool selection
```

**Example Test**: `tests/sandbox/test_factory.py`

```python
import os
import pytest
from src.sandbox.factory import get_sandbox_coordinator, reset_coordinator
from src.sandbox.fargate_coordinator import FargateCoordinator
from src.sandbox.local_coordinator import LocalCoordinator

def test_factory_fargate_mode(monkeypatch):
    """Test factory returns FargateCoordinator for fargate mode."""
    reset_coordinator()
    monkeypatch.setenv("SANDBOX_MODE", "fargate")
    coordinator = get_sandbox_coordinator()
    assert isinstance(coordinator, FargateCoordinator)

def test_factory_local_mode(monkeypatch):
    """Test factory returns LocalCoordinator for local mode."""
    reset_coordinator()
    monkeypatch.setenv("SANDBOX_MODE", "local")
    coordinator = get_sandbox_coordinator()
    assert isinstance(coordinator, LocalCoordinator)

def test_factory_singleton():
    """Test factory returns same instance on multiple calls."""
    reset_coordinator()
    coord1 = get_sandbox_coordinator()
    coord2 = get_sandbox_coordinator()
    assert coord1 is coord2

def test_factory_invalid_mode(monkeypatch):
    """Test factory raises error for invalid mode."""
    reset_coordinator()
    monkeypatch.setenv("SANDBOX_MODE", "invalid")
    with pytest.raises(ValueError, match="Unknown sandbox mode"):
        get_sandbox_coordinator()
```

**Run Tests**:

```bash
# Install pytest if needed
pip install pytest

# Run all tests
pytest tests/sandbox/ -v

# Run specific test
pytest tests/sandbox/test_factory.py::test_factory_fargate_mode -v
```

### Phase 2: Integration Tests

Test each mode end-to-end:

```bash
# Test Fargate mode (existing workflow)
SANDBOX_MODE=fargate python3 -m pytest tests/integration/test_fargate_workflow.py

# Test local mode
SANDBOX_MODE=local python3 -m pytest tests/integration/test_local_workflow.py

# Test E2B mode (when implemented)
SANDBOX_MODE=e2b python3 -m pytest tests/integration/test_e2b_workflow.py
```

### Phase 3: Manual Testing

**Test Fargate Mode** (should work identically to current production):

```bash
# 1. Set environment
export SANDBOX_MODE=fargate
# (or add to .env file)

# 2. Run runtime
python3 02_invoke_agentcore_runtime_vpc.py

# 3. Verify:
#    - Fargate containers created
#    - Code executed in containers
#    - Results returned correctly
#    - Containers cleaned up after completion
```

**Test Local Mode** (no AWS required):

```bash
# 1. Set environment
export SANDBOX_MODE=local

# 2. Run runtime
python3 02_invoke_agentcore_runtime_vpc.py

# 3. Verify:
#    - No AWS API calls
#    - Code executed locally
#    - Results returned correctly
#    - No cleanup required
```

### Phase 4: Regression Testing

Ensure Fargate mode still works after refactoring:

```bash
# Checklist:
- [ ] Fargate container creation
- [ ] ALB registration
- [ ] Cookie acquisition
- [ ] Code execution (Python)
- [ ] Code execution (Bash)
- [ ] CSV file upload to S3
- [ ] Container cleanup
- [ ] ALB deregistration
- [ ] Multi-agent workflow
- [ ] Error handling
- [ ] Logging and observability
```

**Automated Regression Test**:

```bash
# Run existing test suite with new code
SANDBOX_MODE=fargate pytest tests/ -v --tb=short

# Compare logs with previous version
# - Check CloudWatch logs for identical behavior
# - Verify no new errors or warnings
# - Confirm resource cleanup working
```

---

## Estimated Effort

| Task | Lines of Code | Complexity | Time Estimate |
|------|---------------|------------|---------------|
| Create abstract base | ~100 | LOW | 1 hour |
| Refactor Fargate coordinator | ~50 (rename/move) | LOW | 30 mins |
| Create local coordinator | ~150 | MEDIUM | 2 hours |
| Create factory pattern | ~80 | LOW | 1 hour |
| Create tool factory | ~200 | LOW | 1 hour |
| Update runtime | ~10 changes | LOW | 30 mins |
| Update graph nodes | ~15 changes | LOW | 30 mins |
| E2B coordinator (stub) | ~200 | MEDIUM | 3 hours |
| Unit tests | ~300 | MEDIUM | 2 hours |
| Integration tests | ~200 | HIGH | 2 hours |
| Testing & validation | N/A | HIGH | 4 hours |
| **TOTAL** | **~1,325 lines** | **MEDIUM** | **17-20 hours** |

### Time Breakdown by Phase

| Phase | Tasks | Time |
|-------|-------|------|
| **Phase 1: Abstraction** | Base class + Fargate refactor | 1.5 hours |
| **Phase 2: Factory** | Factory + package init + env | 1.5 hours |
| **Phase 3: Runtime** | Update runtime + test | 2 hours |
| **Phase 4: Tool Selection** | Tool factory + update nodes | 2 hours |
| **Phase 5: Local Mode** | Local coordinator + test | 3 hours |
| **Phase 6: E2B Stub** | E2B coordinator stub | 3 hours |
| **Phase 7: Testing** | Unit + integration + regression | 4 hours |
| **TOTAL** | All phases | **17 hours** |

---

## Risks & Mitigations

### High-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Breaking Fargate mode** | **HIGH** | **LOW** | Keep exact same logic, just move to new class. Test thoroughly before deployment. |
| **Import errors after refactoring** | **MEDIUM** | **MEDIUM** | Use `__init__.py` exports + backward compat aliases. Test imports before changing runtime. |
| **Session state bugs** | **MEDIUM** | **LOW** | Singleton pattern ensures one coordinator per runtime. Add logging to verify state. |
| **Tool selection failure** | **MEDIUM** | **LOW** | Factory raises clear error for unknown modes. Default to fargate for safety. |
| **Production deployment failure** | **HIGH** | **LOW** | Test on dev environment first. Use feature flag to enable new code gradually. |

### Mitigation Strategies

#### 1. Incremental Rollout

```bash
# Week 1: Dev environment only
SANDBOX_MODE=fargate python3 agentcore_runtime.py  # Test on dev

# Week 2: Production canary (10% traffic)
# Deploy with SANDBOX_MODE=fargate (identical to current behavior)

# Week 3: Production full rollout
# After 1 week of successful canary, deploy to all production runtimes

# Week 4: Enable local mode for development
SANDBOX_MODE=local  # For local testing without AWS
```

#### 2. Rollback Plan

```bash
# If production issues occur:

# Option 1: Revert to previous code
git revert <commit-hash>

# Option 2: Disable new factory (use old import)
# Emergency patch: Restore global_fargate_coordinator.py as primary

# Option 3: Force Fargate mode
export SANDBOX_MODE=fargate  # Override any local config
```

#### 3. Monitoring & Alerts

**Add monitoring for**:
- Factory mode selection (log which coordinator is used)
- Session creation success rate
- Code execution errors
- Cleanup failures

**CloudWatch Metrics**:
```python
# In factory.py
logger.info(f"🔧 Initialized sandbox coordinator: mode={mode}")

# In coordinators
logger.info(f"✅ {self.__class__.__name__}: Session created")
logger.error(f"❌ {self.__class__.__name__}: Session creation failed")
```

---

## Key Design Decisions

### 1. Why Singleton Factory?

**Decision**: Use singleton pattern for coordinator

**Rationale**:
- **Single coordinator per runtime**: Avoid multiple session managers competing
- **State sharing**: Request context shared across all tool calls
- **Resource efficiency**: One HTTP client, one session pool, one AWS client pool
- **Simplified testing**: Easy to reset coordinator between tests

**Alternative Considered**: Per-request coordinator instances

**Rejected Because**: Would create multiple HTTP clients and session pools, breaking Fargate's cookie-based routing

---

### 2. Why Keep Parallel Tool Files?

**Decision**: Maintain separate `*_fargate_tool.py` and `*_tool.py` files

**Rationale**:
- **Clean separation**: Each tool is self-contained and testable
- **No conditionals in tools**: Tools don't check `SANDBOX_MODE` (single responsibility)
- **Easy testing**: Test each tool variant independently
- **Future-proof**: Add E2B without touching Fargate code
- **Clear intent**: File name indicates sandbox backend

**Alternative Considered**: Single tool file with `if SANDBOX_MODE == "fargate"`

**Rejected Because**:
- Violates single responsibility principle
- Hard to test (need to mock env vars)
- Difficult to maintain (lots of conditional logic)

---

### 3. Why Abstract at Coordinator Level (Not Tool Level)?

**Decision**: Abstract the lifecycle manager (coordinator), not individual tools

**Rationale**:
- **Fargate tools** need complex session management (cookies, ALB, cleanup)
- **Local tools** are stateless (no session concept)
- **E2B tools** will need different session semantics (API keys, sandbox IDs)
- **Coordinator** abstracts the lifecycle, tools stay simple
- **Single responsibility**: Coordinator = lifecycle, Tool = execution

**Alternative Considered**: Abstract base class for tools (e.g., `PythonExecutionTool`)

**Rejected Because**:
- Too granular (6+ tool classes to abstract)
- Different tools have different interfaces (Python vs Bash vs Agent)
- Coordinator already manages the state, tools just delegate

---

### 4. Why Default to Fargate Mode?

**Decision**: `SANDBOX_MODE=fargate` is the default

**Rationale**:
- **Backward compatibility**: Existing deployments work without changes
- **Production-ready**: Fargate mode is battle-tested
- **Safe fallback**: If env var not set, use known-good mode
- **Explicit opt-in**: Local/E2B modes require explicit configuration

**Alternative Considered**: No default (require explicit mode)

**Rejected Because**: Would break existing deployments without env var

---

## Next Steps (Recommended)

### Immediate Actions (Week 1)

**If you want to proceed, I suggest this order**:

1. **Create `src/sandbox/` directory structure** (5 mins)
   ```bash
   mkdir -p src/sandbox
   touch src/sandbox/__init__.py
   ```

2. **Write `base.py` abstract class** (30 mins)
   - Copy abstract class code from Phase 1.1
   - Add docstrings and type hints

3. **Move Fargate code → `fargate_coordinator.py`** (20 mins)
   - Copy `global_fargate_coordinator.py` → `fargate_coordinator.py`
   - Add inheritance from `SandboxCoordinator`
   - Test imports

4. **Create `factory.py` with backward compat** (1 hour)
   - Implement singleton factory
   - Add `get_global_session()` alias
   - Test mode selection

5. **Test Fargate mode** - Should work identically (30 mins)
   ```bash
   python3 -c "from src.sandbox import get_sandbox_coordinator; c = get_sandbox_coordinator(); print(c)"
   ```

6. **Update `agentcore_runtime.py`** (15 mins)
   - Change imports from `global_fargate_coordinator` → `sandbox.factory`
   - Test runtime

7. **Test again** (30 mins)
   ```bash
   python3 02_invoke_agentcore_runtime_vpc.py
   ```

8. **Create `tool_factory.py`** (1 hour)
   - Implement dynamic tool selection
   - Test tool loading

9. **Update `nodes.py`** (15 mins)
   - Use tool factory for agent tools
   - Test graph execution

10. **Full end-to-end test** (1 hour)
    ```bash
    python3 02_invoke_agentcore_runtime_vpc.py
    # Verify: Identical behavior to pre-refactoring
    ```

### Short-term Goals (Week 2-3)

11. **Implement `LocalCoordinator`** (2 hours)
    - Copy code from Phase 1.3
    - Test local subprocess execution

12. **Test local mode end-to-end** (1 hour)
    ```bash
    SANDBOX_MODE=local python3 02_invoke_agentcore_runtime_vpc.py
    ```

13. **Create E2B stub** (1 hour)
    - Basic coordinator structure
    - Stub methods with NotImplementedError

14. **Write unit tests** (2 hours)
    - Test factory selection
    - Test coordinator interfaces
    - Test tool selection

15. **Documentation** (1 hour)
    - Update README with SANDBOX_MODE
    - Add architecture diagram
    - Document mode selection

### Long-term Goals (Month 1+)

16. **Implement E2B integration** (8-10 hours)
    - Install E2B SDK
    - Implement coordinator methods
    - Create E2B tools
    - Test end-to-end

17. **Production deployment** (4 hours)
    - Deploy to dev environment
    - Canary rollout (10% traffic)
    - Monitor for 1 week
    - Full rollout

18. **Performance optimization** (variable)
    - Profile different modes
    - Optimize session creation
    - Add caching where appropriate

19. **Advanced features** (variable)
    - Multi-container sessions (parallel execution)
    - Session pooling (reduce startup time)
    - Hybrid mode (local + cloud)

---

## Appendix: Code Examples

### Example 1: Using Local Mode

```python
# .env
SANDBOX_MODE=local

# Your code (unchanged)
from src.sandbox import get_sandbox_coordinator

coordinator = get_sandbox_coordinator()  # Returns LocalCoordinator
coordinator.ensure_session()  # Always returns True (no setup needed)

result = coordinator.execute_code("""
import pandas as pd
df = pd.read_csv('data.csv')
print(df.describe())
""", "Data analysis")

print(result['output'])  # Prints statistics
```

### Example 2: Switching Modes at Runtime

```python
import os
from src.sandbox.factory import get_sandbox_coordinator, reset_coordinator

# Start with Fargate
os.environ["SANDBOX_MODE"] = "fargate"
coordinator = get_sandbox_coordinator()
print(coordinator.__class__.__name__)  # FargateCoordinator

# Switch to local (for testing)
reset_coordinator()  # Clear singleton
os.environ["SANDBOX_MODE"] = "local"
coordinator = get_sandbox_coordinator()
print(coordinator.__class__.__name__)  # LocalCoordinator
```

### Example 3: Custom Tool Selection

```python
from src.tools.tool_factory import get_python_tool, get_bash_tool

# Get tools for specific mode
python_tool = get_python_tool(sandbox_mode="local")
bash_tool = get_bash_tool(sandbox_mode="fargate")

# Use tools
python_tool(...)  # Runs locally
bash_tool(...)    # Runs in Fargate
```

---

## Questions & Answers

### Q1: Will this break my current production deployment?

**A**: No. The refactoring is designed for 100% backward compatibility. With `SANDBOX_MODE=fargate` (the default), the system behaves identically to the current implementation.

### Q2: Can I mix Fargate and local tools in the same runtime?

**A**: No. The sandbox mode is global per runtime process. All tools use the same coordinator. However, you can run multiple runtimes with different modes.

### Q3: What happens if I don't set SANDBOX_MODE?

**A**: The system defaults to `fargate` mode, maintaining current behavior.

### Q4: How do I test the refactoring without affecting production?

**A**:
1. Test on dev environment first
2. Use `SANDBOX_MODE=fargate` to ensure identical behavior
3. Run regression tests
4. Deploy to production with canary rollout (10% traffic)

### Q5: Can I roll back if something goes wrong?

**A**: Yes. The refactoring maintains backward compatibility. You can:
1. Revert the git commit
2. Set `SANDBOX_MODE=fargate` to force Fargate mode
3. Restore the old `global_fargate_coordinator.py` as primary

### Q6: When should I use local mode vs Fargate mode?

**A**:
- **Fargate mode**: Production, full isolation, concurrent jobs
- **Local mode**: Development, testing, no AWS costs
- **E2B mode**: Third-party hosting, managed infrastructure

### Q7: How much will this cost?

**A**: Same cost as current implementation. The refactoring doesn't change resource usage, just adds flexibility to choose backends.

---

## Conclusion

This refactoring provides a clean, maintainable architecture for supporting multiple code execution backends. The design prioritizes:

1. **Backward Compatibility**: Existing deployments work without changes
2. **Clean Separation**: Clear boundaries between coordinators and tools
3. **Easy Testing**: Each mode can be tested independently
4. **Future-Proof**: Easy to add new backends (E2B, others)
5. **Low Risk**: Incremental rollout with rollback capability

**Total effort**: 17-20 hours
**Risk level**: Low-Medium
**Impact**: High (enables local development, third-party backends)

**Next step**: Review this plan and decide whether to proceed with Phase 1 (foundation) or request modifications to the approach.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: Ready for Implementation
