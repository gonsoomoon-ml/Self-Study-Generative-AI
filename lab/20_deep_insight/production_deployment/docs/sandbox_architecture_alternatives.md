# Alternative Architectural Approaches for Sandbox Refactoring

**Date**: 2025-11-16
**Status**: Analysis & Comparison
**Context**: Beyond the factory method - exploring alternative design patterns

---

## Table of Contents

1. [Pattern Comparison Matrix](#pattern-comparison-matrix)
2. [Alternative 1: Dependency Injection Container](#alternative-1-dependency-injection-container)
3. [Alternative 2: Plugin Architecture](#alternative-2-plugin-architecture)
4. [Alternative 3: Context Manager Pattern](#alternative-3-context-manager-pattern)
5. [Alternative 4: Configuration-Driven Architecture](#alternative-4-configuration-driven-architecture)
6. [Alternative 5: Middleware Pipeline Pattern](#alternative-5-middleware-pipeline-pattern)
7. [Alternative 6: Protocol-Based (Duck Typing)](#alternative-6-protocol-based-duck-typing)
8. [Alternative 7: Hybrid Approach](#alternative-7-hybrid-approach-recommended)
9. [Decision Matrix](#decision-matrix)
10. [Recommendation](#recommendation)

---

## Pattern Comparison Matrix

| Pattern | Complexity | Flexibility | Testability | Extensibility | Python-Native | Best For |
|---------|------------|-------------|-------------|---------------|---------------|----------|
| **Factory (Current Plan)** | Low | Medium | High | Medium | ✅ | Simple mode selection |
| **DI Container** | High | High | Very High | High | ⚠️ (needs library) | Large codebases, testing |
| **Plugin Architecture** | Medium | Very High | High | Very High | ✅ | Third-party extensions |
| **Context Manager** | Low | Low | High | Low | ✅ | Resource lifecycle |
| **Config-Driven** | Medium | Medium | Medium | High | ✅ | Runtime flexibility |
| **Middleware Pipeline** | Medium | High | High | Very High | ✅ | Composable behaviors |
| **Protocol-Based** | Low | High | High | High | ✅ | Python 3.8+ |
| **Hybrid** | Medium | Very High | Very High | Very High | ✅ | Production systems |

---

## Alternative 1: Dependency Injection Container

### Concept

Use a DI container to manage all dependencies, inverting control from manual instantiation to declarative registration.

### Architecture

```
┌─────────────────────────────────────────────┐
│         DI Container (Registry)              │
│  ┌────────────────────────────────────┐    │
│  │ "sandbox" → FargateCoordinator     │    │
│  │ "python_tool" → fargate_python_tool│    │
│  │ "bash_tool" → fargate_bash_tool    │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                    ↓
          Runtime requests dependencies
                    ↓
        Container resolves and injects
```

### Implementation

**File**: `src/sandbox/di_container.py` (~200 lines)

```python
"""
Dependency Injection container for sandbox management.

This provides a central registry for all sandbox-related dependencies,
enabling loose coupling and easy testing.

Benefits:
    - Explicit dependency declaration
    - Easy mocking for tests (inject fake implementations)
    - Lifecycle management (singletons, transient, scoped)
    - Runtime reconfiguration without code changes

Dependencies:
    pip install dependency-injector  # Optional (can build custom)
"""

from typing import Dict, Any, Callable, Optional, Type
import os
import logging

logger = logging.getLogger(__name__)

class DIContainer:
    """
    Simple dependency injection container.

    Supports:
    - Singleton instances (shared across application)
    - Factory functions (create new instance each time)
    - Value injection (constants, config)
    """

    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._values: Dict[str, Any] = {}

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance (shared)."""
        self._singletons[name] = instance
        logger.debug(f"✅ Registered singleton: {name}")

    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function (creates new instance each time)."""
        self._factories[name] = factory
        logger.debug(f"✅ Registered factory: {name}")

    def register_value(self, name: str, value: Any) -> None:
        """Register a constant value."""
        self._values[name] = value
        logger.debug(f"✅ Registered value: {name}")

    def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name.

        Resolution order:
        1. Singletons (if already created)
        2. Factories (create new instance)
        3. Values (return constant)
        4. Raise error if not found
        """
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]

        # Check factories (create and cache singleton)
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance  # Cache as singleton
            return instance

        # Check values
        if name in self._values:
            return self._values[name]

        raise KeyError(f"Dependency not found: {name}")

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._singletons.clear()
        self._factories.clear()
        self._values.clear()
        logger.info("🧹 DI container cleared")

# Global container instance
_container = DIContainer()

def get_container() -> DIContainer:
    """Get the global DI container."""
    return _container

# Configuration-based registration
def configure_container(mode: str = None) -> None:
    """
    Configure DI container based on sandbox mode.

    Args:
        mode: Sandbox mode (fargate|local|e2b)
    """
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")
    container = get_container()
    container.clear()

    logger.info(f"🔧 Configuring DI container for mode: {mode}")

    # Register sandbox coordinator
    if mode == "fargate":
        from src.sandbox.fargate_coordinator import FargateCoordinator
        container.register_factory("sandbox_coordinator", FargateCoordinator)

        # Register Fargate tools
        from src.tools.fargate_python_tool import fargate_python_tool
        from src.tools.fargate_bash_tool import fargate_bash_tool
        container.register_value("python_tool", fargate_python_tool)
        container.register_value("bash_tool", fargate_bash_tool)

    elif mode == "local":
        from src.sandbox.local_coordinator import LocalCoordinator
        container.register_factory("sandbox_coordinator", LocalCoordinator)

        # Register local tools
        from src.tools.python_repl_tool import python_repl_tool
        from src.tools.bash_tool import bash_tool
        container.register_value("python_tool", python_repl_tool)
        container.register_value("bash_tool", bash_tool)

    elif mode == "e2b":
        from src.sandbox.e2b_coordinator import E2BCoordinator
        container.register_factory("sandbox_coordinator", E2BCoordinator)

        # E2B tools (when implemented)
        # container.register_value("python_tool", e2b_python_tool)
        # container.register_value("bash_tool", e2b_bash_tool)

    else:
        raise ValueError(f"Unknown sandbox mode: {mode}")

    # Always register tracker (local only)
    from src.tools.tracker_agent_tool import tracker_agent_tool
    container.register_value("tracker_tool", tracker_agent_tool)

    logger.info(f"✅ DI container configured for {mode} mode")
```

### Usage in Runtime

**Modified File**: `agentcore_runtime.py`

```python
from src.sandbox.di_container import configure_container, get_container

# At startup (line ~110)
configure_container()  # Reads SANDBOX_MODE from environment

# In functions (line ~205)
def _setup_sandbox_context(request_id: str) -> None:
    container = get_container()
    coordinator = container.resolve("sandbox_coordinator")
    coordinator.set_request_context(request_id)
```

### Usage in Tests

```python
import pytest
from src.sandbox.di_container import get_container, configure_container

@pytest.fixture
def mock_sandbox():
    """Inject a mock sandbox for testing."""
    container = get_container()
    container.clear()

    # Inject mock coordinator
    mock_coordinator = MagicMock()
    container.register_singleton("sandbox_coordinator", mock_coordinator)

    yield mock_coordinator

    container.clear()

def test_runtime_with_mock_sandbox(mock_sandbox):
    """Test runtime with mocked sandbox."""
    # Runtime will use the mock, no real AWS calls
    runtime.execute(...)
    mock_sandbox.ensure_session.assert_called_once()
```

### Pros

✅ **Excellent testability** - Easy to inject mocks
✅ **Explicit dependencies** - Clear what each component needs
✅ **Flexible lifecycles** - Singleton, transient, scoped
✅ **Runtime reconfiguration** - Change dependencies without restart
✅ **Separation of concerns** - Construction vs usage

### Cons

❌ **Higher complexity** - Needs container management
❌ **Learning curve** - Team needs to understand DI pattern
❌ **Magic strings** - `resolve("sandbox_coordinator")` prone to typos
❌ **Indirection** - Harder to trace dependency graph
❌ **Overkill for small projects** - More suitable for large codebases

---

## Alternative 2: Plugin Architecture

### Concept

Discover and load sandbox implementations dynamically from a plugin directory. Supports third-party sandboxes without code changes.

### Architecture

```
plugins/
├── fargate/
│   ├── __init__.py
│   ├── coordinator.py
│   └── tools.py
├── local/
│   ├── __init__.py
│   ├── coordinator.py
│   └── tools.py
└── e2b/
    ├── __init__.py
    ├── coordinator.py
    └── tools.py

Plugin Loader scans directory → Registers plugins → Runtime selects plugin
```

### Implementation

**File**: `src/sandbox/plugin_loader.py` (~250 lines)

```python
"""
Dynamic plugin loader for sandbox backends.

This module enables dynamic discovery and loading of sandbox implementations
from a plugin directory. Supports:
    - Built-in plugins (Fargate, Local)
    - Third-party plugins (E2B, custom)
    - Hot reloading (reload plugins without restart)

Plugin Structure:
    plugins/<name>/
        __init__.py          # Plugin metadata
        coordinator.py       # SandboxCoordinator implementation
        tools.py            # Tool implementations

Plugin Metadata (__init__.py):
    PLUGIN_NAME = "fargate"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "AWS Fargate sandbox"
    COORDINATOR_CLASS = "FargateCoordinator"
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Type, Optional
import logging

logger = logging.getLogger(__name__)

class PluginMetadata:
    """Plugin metadata and configuration."""

    def __init__(self, name: str, path: Path, module: Any):
        self.name = name
        self.path = path
        self.module = module

        # Extract metadata from module
        self.version = getattr(module, "PLUGIN_VERSION", "unknown")
        self.description = getattr(module, "PLUGIN_DESCRIPTION", "")
        self.coordinator_class_name = getattr(module, "COORDINATOR_CLASS", None)

    def get_coordinator_class(self) -> Type:
        """Get the coordinator class from plugin."""
        if not self.coordinator_class_name:
            raise ValueError(f"Plugin {self.name} missing COORDINATOR_CLASS")

        # Import coordinator module
        coordinator_module = importlib.import_module(
            f"{self.module.__name__}.coordinator"
        )

        # Get class by name
        coordinator_class = getattr(coordinator_module, self.coordinator_class_name)
        return coordinator_class

class PluginLoader:
    """
    Load and manage sandbox plugins.

    Plugins are loaded from the plugins directory and registered
    for use by the runtime.
    """

    def __init__(self, plugin_dir: str = None):
        """
        Initialize plugin loader.

        Args:
            plugin_dir: Directory containing plugins (default: ./plugins)
        """
        self.plugin_dir = Path(plugin_dir or os.getenv("PLUGIN_DIR", "./plugins"))
        self.plugins: Dict[str, PluginMetadata] = {}

        logger.info(f"🔌 Plugin loader initialized: {self.plugin_dir}")

    def discover_plugins(self) -> List[str]:
        """
        Discover all plugins in the plugin directory.

        Returns:
            List of plugin names found
        """
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {self.plugin_dir}")
            return []

        plugin_names = []
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                plugin_names.append(item.name)

        logger.info(f"📦 Discovered {len(plugin_names)} plugins: {plugin_names}")
        return plugin_names

    def load_plugin(self, name: str) -> PluginMetadata:
        """
        Load a plugin by name.

        Args:
            name: Plugin name (directory name)

        Returns:
            Plugin metadata
        """
        plugin_path = self.plugin_dir / name

        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin not found: {name}")

        # Add plugin directory to path
        plugin_parent = str(self.plugin_dir.absolute())
        if plugin_parent not in sys.path:
            sys.path.insert(0, plugin_parent)

        # Import plugin module
        try:
            module = importlib.import_module(name)
            metadata = PluginMetadata(name, plugin_path, module)

            logger.info(
                f"✅ Loaded plugin: {name} v{metadata.version} - {metadata.description}"
            )

            self.plugins[name] = metadata
            return metadata

        except Exception as e:
            logger.error(f"❌ Failed to load plugin {name}: {e}")
            raise

    def load_all_plugins(self) -> None:
        """Load all discovered plugins."""
        plugin_names = self.discover_plugins()

        for name in plugin_names:
            try:
                self.load_plugin(name)
            except Exception as e:
                logger.warning(f"⚠️  Skipping plugin {name}: {e}")

    def get_plugin(self, name: str) -> Optional[PluginMetadata]:
        """Get loaded plugin by name."""
        return self.plugins.get(name)

    def get_coordinator_class(self, plugin_name: str) -> Type:
        """
        Get coordinator class from plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            Coordinator class
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin not loaded: {plugin_name}")

        return plugin.get_coordinator_class()

    def create_coordinator(self, plugin_name: str):
        """
        Create coordinator instance from plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            Coordinator instance
        """
        coordinator_class = self.get_coordinator_class(plugin_name)
        return coordinator_class()

# Global plugin loader
_plugin_loader: Optional[PluginLoader] = None

def get_plugin_loader() -> PluginLoader:
    """Get the global plugin loader (singleton)."""
    global _plugin_loader

    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
        _plugin_loader.load_all_plugins()

    return _plugin_loader

def get_coordinator_for_mode(mode: str = None):
    """
    Get coordinator for specified mode using plugin system.

    Args:
        mode: Sandbox mode (plugin name)

    Returns:
        Coordinator instance
    """
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")

    loader = get_plugin_loader()
    coordinator = loader.create_coordinator(mode)

    logger.info(f"🚀 Created coordinator from plugin: {mode}")
    return coordinator
```

### Plugin Structure

**Directory**: `plugins/fargate/__init__.py`

```python
"""
AWS Fargate sandbox plugin.

This plugin provides AWS Fargate-based code execution with
ALB routing and session management.
"""

PLUGIN_NAME = "fargate"
PLUGIN_VERSION = "2.0.0"
PLUGIN_DESCRIPTION = "AWS Fargate containers with ALB routing"
COORDINATOR_CLASS = "FargateCoordinator"

# Optional: Plugin-specific configuration
DEFAULT_CONFIG = {
    "timeout": 180,
    "max_sessions": 10,
    "cleanup_on_exit": True
}
```

**Directory**: `plugins/fargate/coordinator.py`

```python
from src.sandbox.base import SandboxCoordinator

class FargateCoordinator(SandboxCoordinator):
    """AWS Fargate implementation (moved from src/sandbox/)."""
    # All existing Fargate code here
    pass
```

**Directory**: `plugins/local/__init__.py`

```python
"""Local subprocess sandbox plugin."""

PLUGIN_NAME = "local"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Local subprocess execution"
COORDINATOR_CLASS = "LocalCoordinator"
```

### Usage

```python
from src.sandbox.plugin_loader import get_coordinator_for_mode

# Automatically loads plugin based on SANDBOX_MODE
coordinator = get_coordinator_for_mode()

# Or specify explicitly
coordinator = get_coordinator_for_mode(mode="fargate")
```

### Pros

✅ **Highly extensible** - Add new backends without code changes
✅ **Third-party support** - Anyone can create plugins
✅ **Hot reloading** - Reload plugins without restart
✅ **Version management** - Each plugin has version metadata
✅ **Isolation** - Plugins don't affect each other
✅ **Discovery** - Auto-discover available plugins

### Cons

❌ **Complexity** - Plugin loader adds overhead
❌ **Import path issues** - sys.path manipulation can be fragile
❌ **Dependency conflicts** - Plugins may have conflicting dependencies
❌ **Security risk** - Loading arbitrary code from plugins directory
❌ **Harder debugging** - Dynamic imports harder to trace

---

## Alternative 3: Context Manager Pattern

### Concept

Use Python's context manager protocol (`with` statements) to manage sandbox lifecycle. Natural resource management with automatic cleanup.

### Implementation

**File**: `src/sandbox/context_managers.py` (~150 lines)

```python
"""
Context manager-based sandbox lifecycle management.

This provides a Pythonic way to manage sandbox resources using
the 'with' statement, ensuring automatic cleanup even on errors.

Usage:
    with FargateSandbox(request_id="abc") as sandbox:
        result = sandbox.execute_code("print('hello')")
        # Sandbox automatically cleaned up on exit
"""

from contextlib import contextmanager
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

class SandboxContext:
    """
    Context manager for sandbox lifecycle.

    Automatically handles:
    - Session setup on __enter__
    - Code execution during context
    - Cleanup on __exit__ (even on exceptions)
    """

    def __init__(self, coordinator, request_id: str, csv_path: str = None):
        """
        Initialize sandbox context.

        Args:
            coordinator: Sandbox coordinator instance
            request_id: Request identifier
            csv_path: Optional CSV file path
        """
        self.coordinator = coordinator
        self.request_id = request_id
        self.csv_path = csv_path
        self._session_created = False

    def __enter__(self):
        """
        Enter context (setup sandbox).

        Returns:
            Self (for use in 'as' clause)
        """
        logger.info(f"🔓 Entering sandbox context: {self.request_id}")

        # Set request context
        self.coordinator.set_request_context(self.request_id)

        # Create session (with or without data)
        if self.csv_path:
            success = self.coordinator.ensure_session_with_data(self.csv_path)
        else:
            success = self.coordinator.ensure_session()

        if not success:
            raise RuntimeError("Failed to create sandbox session")

        self._session_created = True
        logger.info(f"✅ Sandbox session ready: {self.request_id}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context (cleanup sandbox).

        Called automatically even if exception occurs in context body.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)

        Returns:
            False (propagate exceptions)
        """
        if self._session_created:
            logger.info(f"🔒 Exiting sandbox context: {self.request_id}")

            try:
                self.coordinator.cleanup_session(self.request_id)
                logger.info(f"✅ Sandbox cleaned up: {self.request_id}")
            except Exception as cleanup_error:
                logger.error(f"❌ Cleanup failed: {cleanup_error}")
                # Don't suppress original exception

        # Return False to propagate exceptions from context body
        return False

    def execute_code(self, code: str, description: str = ""):
        """
        Execute code in sandbox (convenience method).

        Args:
            code: Code to execute
            description: Description for logging

        Returns:
            Execution result
        """
        return self.coordinator.execute_code(code, description)

# Convenience factory functions
def fargate_sandbox(request_id: str, csv_path: str = None) -> SandboxContext:
    """Create Fargate sandbox context."""
    from src.sandbox.fargate_coordinator import FargateCoordinator
    coordinator = FargateCoordinator()
    return SandboxContext(coordinator, request_id, csv_path)

def local_sandbox(request_id: str, csv_path: str = None) -> SandboxContext:
    """Create local sandbox context."""
    from src.sandbox.local_coordinator import LocalCoordinator
    coordinator = LocalCoordinator()
    return SandboxContext(coordinator, request_id, csv_path)

# Generic factory based on environment
def sandbox_context(request_id: str, csv_path: str = None, mode: str = None) -> SandboxContext:
    """
    Create sandbox context based on mode.

    Args:
        request_id: Request identifier
        csv_path: Optional CSV file path
        mode: Sandbox mode (fargate|local|e2b)

    Returns:
        Sandbox context manager
    """
    import os
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")

    if mode == "fargate":
        return fargate_sandbox(request_id, csv_path)
    elif mode == "local":
        return local_sandbox(request_id, csv_path)
    else:
        raise ValueError(f"Unknown sandbox mode: {mode}")
```

### Usage in Runtime

**Modified File**: `agentcore_runtime.py`

```python
from src.sandbox.context_managers import sandbox_context

@app.entrypoint
async def agentcore_streaming_execution(payload, context):
    request_id = _generate_request_id()
    user_query = _extract_user_query(payload)
    csv_path = _extract_csv_path_from_prompt(user_query)

    # Use context manager for automatic cleanup
    with sandbox_context(request_id, csv_path) as sandbox:
        # Build and execute graph
        graph = build_graph()
        graph_input = _build_graph_input(user_query, payload)

        async for event in graph.stream_async(graph_input):
            yield event

    # Sandbox automatically cleaned up here (even on errors)
```

### Pros

✅ **Pythonic** - Natural resource management with `with` statements
✅ **Automatic cleanup** - Guaranteed cleanup even on exceptions
✅ **Clear scope** - Sandbox lifetime is visually scoped
✅ **Simple** - Easy to understand and use
✅ **Composable** - Can nest contexts

### Cons

❌ **Limited to lifecycle** - Only handles setup/teardown, not selection
❌ **Needs factory** - Still need separate mechanism to choose mode
❌ **Nesting complexity** - Multiple contexts can be confusing
❌ **Not for singletons** - Creates new coordinator each time

---

## Alternative 4: Configuration-Driven Architecture

### Concept

Define sandbox configurations in YAML/JSON files. Change sandboxes without code changes.

### Implementation

**File**: `config/sandboxes.yaml`

```yaml
# Sandbox configuration file
# This defines all available sandbox backends and their settings

default_mode: fargate

sandboxes:
  fargate:
    enabled: true
    coordinator:
      module: src.sandbox.fargate_coordinator
      class: FargateCoordinator
    tools:
      python:
        module: src.tools.fargate_python_tool
        function: fargate_python_tool
      bash:
        module: src.tools.fargate_bash_tool
        function: fargate_bash_tool
    config:
      timeout: 180
      max_sessions: 10
      cleanup_on_exit: true
      alb_dns: ${ALB_DNS}  # Environment variable substitution
      ecs_cluster: ${ECS_CLUSTER_NAME}

  local:
    enabled: true
    coordinator:
      module: src.sandbox.local_coordinator
      class: LocalCoordinator
    tools:
      python:
        module: src.tools.python_repl_tool
        function: python_repl_tool
      bash:
        module: src.tools.bash_tool
        function: bash_tool
    config:
      timeout: 600
      working_directory: ./workspace

  e2b:
    enabled: false  # Not yet implemented
    coordinator:
      module: src.sandbox.e2b_coordinator
      class: E2BCoordinator
    tools:
      python:
        module: src.tools.e2b_python_tool
        function: e2b_python_tool
      bash:
        module: src.tools.e2b_bash_tool
        function: e2b_bash_tool
    config:
      api_key: ${E2B_API_KEY}
      timeout: 300

# Agent tool mappings
agents:
  coder:
    tools: [python, bash]
    sandbox_required: true

  validator:
    tools: [python, bash]
    sandbox_required: true

  reporter:
    tools: [python]
    sandbox_required: true

  tracker:
    tools: []
    sandbox_required: false  # Always local
```

**File**: `src/sandbox/config_loader.py` (~300 lines)

```python
"""
Configuration-driven sandbox loader.

This module loads sandbox configurations from YAML files and
dynamically creates coordinators and tools based on config.

Benefits:
    - No code changes for new sandboxes
    - Environment-specific configs (dev.yaml, prod.yaml)
    - Easy to version control configs
    - Validates config against schema
"""

import os
import yaml
import importlib
from typing import Dict, Any, Type, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SandboxConfig:
    """Parsed sandbox configuration."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.enabled = config.get("enabled", True)

        # Coordinator config
        coord_config = config.get("coordinator", {})
        self.coordinator_module = coord_config.get("module")
        self.coordinator_class = coord_config.get("class")

        # Tools config
        self.tools = config.get("tools", {})

        # Runtime config
        self.runtime_config = self._resolve_env_vars(config.get("config", {}))

    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve environment variable references in config.

        Replaces ${VAR_NAME} with os.getenv("VAR_NAME")
        """
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved[key] = os.getenv(env_var, value)
            else:
                resolved[key] = value
        return resolved

    def create_coordinator(self) -> Any:
        """Create coordinator instance from config."""
        if not self.enabled:
            raise RuntimeError(f"Sandbox {self.name} is disabled in config")

        # Import module
        module = importlib.import_module(self.coordinator_module)

        # Get class
        coordinator_class = getattr(module, self.coordinator_class)

        # Create instance (pass runtime config if constructor accepts it)
        try:
            coordinator = coordinator_class(**self.runtime_config)
        except TypeError:
            # Constructor doesn't accept config, create without args
            coordinator = coordinator_class()

        logger.info(f"✅ Created coordinator: {self.name} ({self.coordinator_class})")
        return coordinator

    def get_tool(self, tool_name: str) -> Callable:
        """Get tool function from config."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not defined for sandbox {self.name}")

        tool_config = self.tools[tool_name]
        module = importlib.import_module(tool_config["module"])
        tool_func = getattr(module, tool_config["function"])

        return tool_func

class ConfigLoader:
    """Load and manage sandbox configurations."""

    def __init__(self, config_file: str = None):
        """
        Initialize config loader.

        Args:
            config_file: Path to YAML config (default: config/sandboxes.yaml)
        """
        self.config_file = Path(config_file or "config/sandboxes.yaml")
        self.config: Dict[str, Any] = {}
        self.sandboxes: Dict[str, SandboxConfig] = {}

        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        # Parse sandbox configs
        sandbox_configs = self.config.get("sandboxes", {})
        for name, config in sandbox_configs.items():
            self.sandboxes[name] = SandboxConfig(name, config)

        logger.info(f"📄 Loaded config: {len(self.sandboxes)} sandboxes")

    def get_default_mode(self) -> str:
        """Get default sandbox mode from config."""
        return self.config.get("default_mode", "fargate")

    def get_sandbox_config(self, name: str) -> SandboxConfig:
        """Get sandbox configuration by name."""
        if name not in self.sandboxes:
            raise ValueError(f"Sandbox not found in config: {name}")
        return self.sandboxes[name]

    def create_coordinator(self, mode: str = None):
        """
        Create coordinator from config.

        Args:
            mode: Sandbox mode (uses default if not specified)

        Returns:
            Coordinator instance
        """
        mode = mode or os.getenv("SANDBOX_MODE") or self.get_default_mode()
        sandbox_config = self.get_sandbox_config(mode)
        return sandbox_config.create_coordinator()

    def get_tools_for_agent(self, agent_name: str, mode: str = None):
        """
        Get tools for specified agent.

        Args:
            agent_name: Agent name (coder, validator, etc.)
            mode: Sandbox mode

        Returns:
            List of tool functions
        """
        mode = mode or os.getenv("SANDBOX_MODE") or self.get_default_mode()

        # Get agent config
        agent_config = self.config.get("agents", {}).get(agent_name)
        if not agent_config:
            raise ValueError(f"Agent not found in config: {agent_name}")

        # Get sandbox config
        sandbox_config = self.get_sandbox_config(mode)

        # Get tools for agent
        tool_names = agent_config.get("tools", [])
        tools = [sandbox_config.get_tool(name) for name in tool_names]

        return tools

# Global config loader
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get global config loader (singleton)."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader
```

### Usage

```python
from src.sandbox.config_loader import get_config_loader

# Load coordinator from config
loader = get_config_loader()
coordinator = loader.create_coordinator()  # Uses SANDBOX_MODE or default

# Get tools for agent
coder_tools = loader.get_tools_for_agent("coder")
```

### Pros

✅ **Zero code changes** - New sandboxes via config only
✅ **Environment-specific** - dev.yaml, prod.yaml configs
✅ **Validation** - Can validate config against schema
✅ **Centralized** - All sandbox settings in one place
✅ **Version control** - Easy to track config changes
✅ **Documentation** - Config is self-documenting

### Cons

❌ **YAML complexity** - Large configs hard to maintain
❌ **Error handling** - Config errors harder to debug than code errors
❌ **Type safety** - No compile-time validation
❌ **Performance** - YAML parsing on every startup
❌ **Dependency** - Requires PyYAML library

---

## Alternative 5: Middleware Pipeline Pattern

### Concept

Chain sandboxes as middleware layers. Each layer can enhance, monitor, or transform execution.

### Architecture

```
Request → [Auth] → [Logging] → [Caching] → [Fargate] → Response
           ↑         ↑           ↑           ↑
        Middleware layers (composable)
```

### Implementation

**File**: `src/sandbox/middleware.py` (~250 lines)

```python
"""
Middleware pipeline for sandbox execution.

This enables composable sandbox behaviors by chaining middleware layers.
Each layer can:
    - Enhance execution (add logging, metrics, caching)
    - Transform inputs/outputs
    - Short-circuit execution (cached results)
    - Handle errors (retry, fallback)

Usage:
    pipeline = SandboxPipeline(base_coordinator)
    pipeline.add_middleware(LoggingMiddleware())
    pipeline.add_middleware(CachingMiddleware())
    pipeline.add_middleware(RetryMiddleware(max_retries=3))

    result = pipeline.execute_code("print('hello')")
```

from typing import Dict, Any, Callable, List
from abc import ABC, abstractmethod
import logging
import time

logger = logging.getLogger(__name__)

class SandboxMiddleware(ABC):
    """
    Abstract middleware for sandbox execution.

    Each middleware wraps the next layer in the chain,
    allowing pre/post processing of execution.
    """

    def __init__(self):
        self.next_middleware: Callable = None

    def set_next(self, next_middleware: Callable) -> None:
        """Set the next middleware in the chain."""
        self.next_middleware = next_middleware

    @abstractmethod
    def execute(self, code: str, description: str, **kwargs) -> Dict[str, Any]:
        """
        Execute code with middleware processing.

        Must call self.next_middleware() to continue the chain.
        """
        pass

class LoggingMiddleware(SandboxMiddleware):
    """Log execution requests and results."""

    def execute(self, code: str, description: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"📝 Executing: {description}")
        logger.debug(f"Code: {code[:100]}...")

        start_time = time.time()
        result = self.next_middleware(code, description, **kwargs)
        duration = time.time() - start_time

        logger.info(f"✅ Completed in {duration:.2f}s")
        return result

class CachingMiddleware(SandboxMiddleware):
    """Cache execution results by code hash."""

    def __init__(self, max_cache_size: int = 100):
        super().__init__()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_cache_size = max_cache_size

    def execute(self, code: str, description: str, **kwargs) -> Dict[str, Any]:
        # Generate cache key (simple hash of code)
        import hashlib
        cache_key = hashlib.md5(code.encode()).hexdigest()

        # Check cache
        if cache_key in self.cache:
            logger.info(f"💾 Cache hit: {description}")
            return self.cache[cache_key]

        # Execute and cache
        result = self.next_middleware(code, description, **kwargs)

        # Evict oldest if cache full
        if len(self.cache) >= self.max_cache_size:
            self.cache.pop(next(iter(self.cache)))

        self.cache[cache_key] = result
        logger.info(f"💾 Cached result: {description}")

        return result

class RetryMiddleware(SandboxMiddleware):
    """Retry failed executions with exponential backoff."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        super().__init__()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def execute(self, code: str, description: str, **kwargs) -> Dict[str, Any]:
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.next_middleware(code, description, **kwargs)

                if result.get("success", False):
                    if attempt > 0:
                        logger.info(f"✅ Retry succeeded on attempt {attempt + 1}")
                    return result
                else:
                    # Execution failed, retry
                    last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)

            # Sleep before retry (exponential backoff)
            if attempt < self.max_retries:
                sleep_time = self.backoff_factor ** attempt
                logger.warning(
                    f"⚠️  Attempt {attempt + 1} failed: {last_error}. "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)

        # All retries failed
        logger.error(f"❌ All {self.max_retries + 1} attempts failed")
        return {
            "success": False,
            "output": "",
            "error": f"Failed after {self.max_retries + 1} attempts: {last_error}"
        }

class MetricsMiddleware(SandboxMiddleware):
    """Collect execution metrics (duration, success rate, etc.)."""

    def __init__(self):
        super().__init__()
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_duration": 0.0
        }

    def execute(self, code: str, description: str, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        result = self.next_middleware(code, description, **kwargs)
        duration = time.time() - start_time

        # Update metrics
        self.metrics["total_executions"] += 1
        self.metrics["total_duration"] += duration

        if result.get("success", False):
            self.metrics["successful_executions"] += 1
        else:
            self.metrics["failed_executions"] += 1

        return result

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if self.metrics["total_executions"] > 0:
            avg_duration = self.metrics["total_duration"] / self.metrics["total_executions"]
            success_rate = self.metrics["successful_executions"] / self.metrics["total_executions"]
        else:
            avg_duration = 0.0
            success_rate = 0.0

        return {
            **self.metrics,
            "average_duration": avg_duration,
            "success_rate": success_rate
        }

class SandboxPipeline:
    """
    Composable middleware pipeline for sandbox execution.

    Chains middleware layers to build complex execution behaviors.
    """

    def __init__(self, base_coordinator):
        """
        Initialize pipeline with base coordinator.

        Args:
            base_coordinator: Underlying sandbox coordinator
        """
        self.base_coordinator = base_coordinator
        self.middlewares: List[SandboxMiddleware] = []

    def add_middleware(self, middleware: SandboxMiddleware) -> 'SandboxPipeline':
        """
        Add middleware to the pipeline.

        Middlewares are executed in the order they were added.

        Args:
            middleware: Middleware instance to add

        Returns:
            Self (for method chaining)
        """
        self.middlewares.append(middleware)
        return self

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Execute code through the middleware pipeline.

        Args:
            code: Code to execute
            description: Description for logging

        Returns:
            Execution result
        """
        # Build middleware chain
        # Last middleware calls the base coordinator
        def base_execution(code, description, **kwargs):
            return self.base_coordinator.execute_code(code, description)

        # Chain middlewares in reverse order
        next_layer = base_execution
        for middleware in reversed(self.middlewares):
            middleware.set_next(next_layer)
            next_layer = middleware.execute

        # Execute through pipeline
        return next_layer(code, description)

    # Delegate other coordinator methods to base
    def set_request_context(self, request_id: str) -> None:
        return self.base_coordinator.set_request_context(request_id)

    def ensure_session(self) -> bool:
        return self.base_coordinator.ensure_session()

    def ensure_session_with_data(self, csv_path: str) -> bool:
        return self.base_coordinator.ensure_session_with_data(csv_path)

    def cleanup_session(self, request_id: str) -> None:
        return self.base_coordinator.cleanup_session(request_id)
```

### Usage

```python
from src.sandbox.fargate_coordinator import FargateCoordinator
from src.sandbox.middleware import (
    SandboxPipeline,
    LoggingMiddleware,
    CachingMiddleware,
    RetryMiddleware,
    MetricsMiddleware
)

# Create base coordinator
base = FargateCoordinator()

# Build pipeline with middleware
pipeline = SandboxPipeline(base)
pipeline.add_middleware(LoggingMiddleware())
pipeline.add_middleware(CachingMiddleware(max_cache_size=50))
pipeline.add_middleware(RetryMiddleware(max_retries=3))
metrics = MetricsMiddleware()
pipeline.add_middleware(metrics)

# Use pipeline like a coordinator
pipeline.ensure_session()
result = pipeline.execute_code("print('hello')")

# Get metrics
print(metrics.get_metrics())
# {"total_executions": 1, "success_rate": 1.0, "average_duration": 2.5}
```

### Pros

✅ **Highly composable** - Mix and match behaviors
✅ **Reusable middleware** - Write once, use anywhere
✅ **Testable** - Test each middleware independently
✅ **Flexible** - Add/remove layers at runtime
✅ **Separation of concerns** - Each middleware has single responsibility

### Cons

❌ **Complexity** - Pipeline building adds overhead
❌ **Performance** - Multiple layers add latency
❌ **Debugging** - Harder to trace through multiple layers
❌ **Order matters** - Middleware order affects behavior

---

## Alternative 6: Protocol-Based (Duck Typing)

### Concept

Use Python 3.8+ `Protocol` (structural subtyping) instead of abstract base classes. More Pythonic, no inheritance required.

### Implementation

**File**: `src/sandbox/protocols.py` (~100 lines)

```python
"""
Protocol-based sandbox interface (PEP 544).

This uses Python's typing.Protocol for structural subtyping,
allowing any class that implements the required methods to be
used as a sandbox coordinator without explicit inheritance.

Benefits over ABC:
    - No inheritance required (duck typing)
    - More Pythonic (matches Python's philosophy)
    - Easier to adapt existing classes
    - Better for third-party integration

Requirements:
    Python 3.8+ (typing.Protocol)
"""

from typing import Protocol, Dict, Any, runtime_checkable

@runtime_checkable
class SandboxCoordinator(Protocol):
    """
    Protocol for sandbox coordinators.

    Any class implementing these methods can be used as a coordinator,
    without explicitly inheriting from this class.

    This is structural subtyping (like Go interfaces or TypeScript).
    """

    def set_request_context(self, request_id: str) -> None:
        """Set the current request context for tracking."""
        ...

    def ensure_session(self) -> bool:
        """Create or verify a basic sandbox session."""
        ...

    def ensure_session_with_data(self, csv_path: str) -> bool:
        """Create session with pre-loaded data file."""
        ...

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """Execute code in the sandbox."""
        ...

    def cleanup_session(self, request_id: str) -> None:
        """Clean up resources for a completed request."""
        ...

# Type alias for convenience
Coordinator = SandboxCoordinator

def is_valid_coordinator(obj: Any) -> bool:
    """
    Check if an object implements the SandboxCoordinator protocol.

    Args:
        obj: Object to check

    Returns:
        True if object has all required methods
    """
    return isinstance(obj, SandboxCoordinator)
```

### Coordinator Implementation (No Inheritance!)

```python
# No "class FargateCoordinator(SandboxCoordinator)" needed!
# Just implement the methods

class FargateCoordinator:
    """AWS Fargate implementation - no inheritance required."""

    def set_request_context(self, request_id: str) -> None:
        # Implementation
        pass

    def ensure_session(self) -> bool:
        # Implementation
        pass

    def ensure_session_with_data(self, csv_path: str) -> bool:
        # Implementation
        pass

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        # Implementation
        pass

    def cleanup_session(self, request_id: str) -> None:
        # Implementation
        pass

# This automatically satisfies the Protocol!
from src.sandbox.protocols import is_valid_coordinator

coordinator = FargateCoordinator()
assert is_valid_coordinator(coordinator)  # True!
```

### Usage with Type Checking

```python
from src.sandbox.protocols import SandboxCoordinator
from src.sandbox.fargate_coordinator import FargateCoordinator

def execute_with_coordinator(coordinator: SandboxCoordinator, code: str):
    """
    Type checker verifies coordinator has required methods.

    No runtime overhead - this is pure type checking.
    """
    coordinator.ensure_session()
    return coordinator.execute_code(code)

# Type checker ensures FargateCoordinator implements protocol
coordinator = FargateCoordinator()
result = execute_with_coordinator(coordinator, "print('hello')")
```

### Pros

✅ **No inheritance** - More Pythonic duck typing
✅ **Type safety** - Static type checkers (mypy) validate implementation
✅ **Flexibility** - Adapt any class without changing it
✅ **Third-party friendly** - External classes can conform without knowing about protocol
✅ **Zero runtime cost** - Protocols are compile-time only
✅ **Python 3.8+ native** - No external dependencies

### Cons

❌ **Python 3.8+ required** - Not available in older Python
❌ **No enforcement** - Forgot a method? Only caught by type checker, not at runtime
❌ **Type checker needed** - Need mypy/pyright to get full benefits
❌ **Less discoverable** - IDE autocomplete may not work as well

---

## Alternative 7: Hybrid Approach (Recommended)

### Concept

Combine the best aspects of multiple patterns:
- **Protocol** for interface definition (Pythonic)
- **Factory** for coordinator selection (simple)
- **Context Manager** for lifecycle (automatic cleanup)
- **Config** for tool selection (flexible)

### Architecture

```
┌──────────────────────────────────────────────────┐
│              Protocol Interface                   │
│     (Structural typing - no inheritance)         │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│            Factory + Context Manager              │
│  - Factory selects coordinator by mode           │
│  - Context manager handles lifecycle             │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│          Configuration-Driven Tools               │
│  - YAML defines tool mappings per mode           │
│  - Dynamic tool selection                        │
└──────────────────────────────────────────────────┘
```

### Implementation

**Step 1: Protocol Interface**

```python
# src/sandbox/protocols.py
from typing import Protocol, runtime_checkable, Dict, Any

@runtime_checkable
class SandboxCoordinator(Protocol):
    """Sandbox coordinator protocol (no inheritance required)."""

    def set_request_context(self, request_id: str) -> None: ...
    def ensure_session(self) -> bool: ...
    def ensure_session_with_data(self, csv_path: str) -> bool: ...
    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]: ...
    def cleanup_session(self, request_id: str) -> None: ...
```

**Step 2: Factory with Context Manager**

```python
# src/sandbox/factory.py
from contextlib import contextmanager
from src.sandbox.protocols import SandboxCoordinator
import os

_coordinator_cache = {}

def get_coordinator(mode: str = None) -> SandboxCoordinator:
    """Get coordinator (cached singleton)."""
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")

    if mode not in _coordinator_cache:
        if mode == "fargate":
            from src.sandbox.fargate_coordinator import FargateCoordinator
            _coordinator_cache[mode] = FargateCoordinator()
        elif mode == "local":
            from src.sandbox.local_coordinator import LocalCoordinator
            _coordinator_cache[mode] = LocalCoordinator()
        # ... etc

    return _coordinator_cache[mode]

@contextmanager
def sandbox_session(request_id: str, csv_path: str = None, mode: str = None):
    """
    Context manager for sandbox session with automatic cleanup.

    Usage:
        with sandbox_session("req-123", csv_path="data.csv") as coordinator:
            result = coordinator.execute_code("print('hello')")
        # Automatic cleanup here
    """
    coordinator = get_coordinator(mode)
    coordinator.set_request_context(request_id)

    # Setup
    if csv_path:
        success = coordinator.ensure_session_with_data(csv_path)
    else:
        success = coordinator.ensure_session()

    if not success:
        raise RuntimeError("Failed to create sandbox session")

    try:
        yield coordinator
    finally:
        # Cleanup (always runs, even on exceptions)
        coordinator.cleanup_session(request_id)
```

**Step 3: Configuration-Driven Tools**

```python
# config/tools.yaml
sandboxes:
  fargate:
    tools:
      python: src.tools.fargate_python_tool.fargate_python_tool
      bash: src.tools.fargate_bash_tool.fargate_bash_tool
  local:
    tools:
      python: src.tools.python_repl_tool.python_repl_tool
      bash: src.tools.bash_tool.bash_tool
```

```python
# src/tools/loader.py
import yaml
import importlib

def load_tools(mode: str = None):
    """Load tools from config."""
    mode = mode or os.getenv("SANDBOX_MODE", "fargate")

    with open("config/tools.yaml") as f:
        config = yaml.safe_load(f)

    tool_paths = config["sandboxes"][mode]["tools"]
    tools = {}

    for tool_name, module_path in tool_paths.items():
        module_name, func_name = module_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        tools[tool_name] = getattr(module, func_name)

    return tools
```

### Usage (Combined)

```python
from src.sandbox.factory import sandbox_session
from src.tools.loader import load_tools

# Load tools based on mode
tools = load_tools()  # Reads SANDBOX_MODE from env

# Use context manager for automatic lifecycle
with sandbox_session("req-123", csv_path="data.csv") as coordinator:
    # Execute code
    result = coordinator.execute_code("""
    import pandas as pd
    df = pd.read_csv('data.csv')
    print(df.describe())
    """)

    print(result["output"])

# Automatic cleanup happened here
```

### Pros

✅ **Best of all worlds** - Combines strengths of multiple patterns
✅ **Pythonic** - Protocol + context managers
✅ **Flexible** - Config for tools, factory for coordinators
✅ **Automatic cleanup** - Context manager guarantees resource cleanup
✅ **Type-safe** - Protocol provides type checking
✅ **Simple** - Easy factory for coordinator selection
✅ **Extensible** - Config-driven tool loading

### Cons

❌ **More moving parts** - Multiple patterns to understand
❌ **Initial complexity** - Takes time to set up
❌ **Config + code** - Configuration split from code

---

## Decision Matrix

### By Use Case

| Your Scenario | Best Pattern | Reason |
|---------------|--------------|---------|
| **Small project (<5 files)** | Factory only | Simple, low overhead |
| **Large codebase (>50 files)** | DI Container or Hybrid | Better dependency management |
| **Third-party plugins needed** | Plugin Architecture | Dynamic loading, extensibility |
| **Resource-intensive sandboxes** | Context Manager | Guaranteed cleanup |
| **Frequent config changes** | Config-Driven | No code deploys for config |
| **Python 3.8+ only** | Protocol-based | Most Pythonic |
| **Need composable behaviors** | Middleware Pipeline | Flexible layering |
| **Production system** | Hybrid (recommended) | Balanced approach |

### By Priority

**If you prioritize...**

| Priority | Pattern | Trade-off |
|----------|---------|-----------|
| **Simplicity** | Factory | Less flexible |
| **Testability** | DI Container | More complex |
| **Extensibility** | Plugin Architecture | Harder debugging |
| **Python idioms** | Protocol + Context Manager | Python 3.8+ only |
| **Flexibility** | Config-Driven | YAML dependency |
| **Composability** | Middleware Pipeline | Performance overhead |
| **Balance** | Hybrid | More moving parts |

---

## Recommendation

### For Your Specific Project

Based on your codebase analysis:
- **Size**: Medium (~20,000 lines)
- **Team**: Likely small (1-3 developers)
- **Use case**: Production AgentCore runtime
- **Requirements**: Support 3 backends (Fargate, Local, E2B)
- **Priority**: Reliability > Flexibility > Simplicity

### ⭐ Recommended: **Hybrid Approach**

**Rationale**:

1. **Protocol** for interface (Pythonic, type-safe)
2. **Factory** for coordinator selection (simple, proven)
3. **Context Manager** for lifecycle (automatic cleanup)
4. **Config** for tool mappings (flexible, no code changes)

**Implementation Priority**:

```
Week 1: Protocol + Factory (core pattern)
Week 2: Context Manager (lifecycle)
Week 3: Config for tools (flexibility)
Week 4: Testing & refinement
```

**Why NOT the others?**:

- ❌ **DI Container**: Overkill for this project size
- ❌ **Plugin Architecture**: Too complex, security concerns
- ❌ **Middleware**: Not needed (no layered behaviors required)
- ❌ **Config-only**: Still need factory for coordinator selection

---

## Next Steps

1. **Review this document** with your team
2. **Choose a pattern** (or use recommended hybrid)
3. **Create prototype** (1-2 days)
4. **Validate with small test** (Fargate mode)
5. **Iterate and expand** (add local, E2B)

Would you like me to implement the recommended hybrid approach, or would you prefer a different pattern?

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: Analysis Complete
