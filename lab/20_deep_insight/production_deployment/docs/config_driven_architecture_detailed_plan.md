# Configuration-Driven Sandbox Architecture: Detailed Implementation Plan

**Date**: 2025-11-16
**Status**: Detailed Planning
**Objective**: Implement a production-ready configuration-driven sandbox architecture

---

## Table of Contents

1. [Vision & Philosophy](#vision--philosophy)
2. [Configuration Schema Design](#configuration-schema-design)
3. [File Structure & Organization](#file-structure--organization)
4. [Component Loading Strategy](#component-loading-strategy)
5. [Validation & Error Handling](#validation--error-handling)
6. [Environment Management](#environment-management)
7. [Advanced Features](#advanced-features)
8. [Migration Path](#migration-path)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Testing Strategy](#testing-strategy)

---

## Vision & Philosophy

### Core Principle

**"Configuration is code, but safer"** - All sandbox behavior should be configurable without code changes, but with the same level of validation and type safety.

### Design Goals

| Goal | Rationale | Benefit |
|------|-----------|---------|
| **Zero-code deployment** | Change sandboxes without redeploying Python | Faster iterations |
| **Environment parity** | Same code, different configs (dev/prod) | Reduces bugs |
| **Self-documenting** | Config is the documentation | Easy onboarding |
| **Type-safe** | Schema validation catches errors early | Production safety |
| **Hot-reloadable** | Update config without restart (optional) | Zero downtime |
| **Composable** | Share config fragments across environments | DRY principle |

### What Should Be Configurable?

```
┌─────────────────────────────────────────────┐
│            Configuration Scope               │
├─────────────────────────────────────────────┤
│ ✅ Sandbox Selection (fargate/local/e2b)   │
│ ✅ Coordinator Settings (timeouts, limits)  │
│ ✅ Tool Mappings (python_tool → module)     │
│ ✅ Agent Configurations (tools per agent)   │
│ ✅ Network Settings (ALB DNS, VPC, etc.)    │
│ ✅ Observability (logging, metrics)         │
│ ✅ Feature Flags (enable experimental)      │
├─────────────────────────────────────────────┤
│ ❌ Business Logic (always in code)          │
│ ❌ Security Credentials (use env vars)      │
│ ❌ Graph Structure (too complex for YAML)   │
└─────────────────────────────────────────────┘
```

---

## Configuration Schema Design

### Hierarchical Schema

```
config/
├── base.yaml                 # Base configuration (shared)
├── environments/
│   ├── dev.yaml             # Development overrides
│   ├── prod.yaml            # Production overrides
│   └── local.yaml           # Local testing overrides
├── sandboxes/
│   ├── fargate.yaml         # Fargate-specific config
│   ├── local.yaml           # Local-specific config
│   └── e2b.yaml             # E2B-specific config
└── schemas/
    └── sandbox.schema.json  # JSON Schema for validation
```

### Master Configuration File

**File**: `config/base.yaml` (~200 lines)

```yaml
# ============================================================
# Deep Insight Sandbox Configuration (Base)
# ============================================================
#
# This is the master configuration file for sandbox backends.
# Environment-specific overrides are in config/environments/
#
# Configuration Precedence:
#   1. Environment variables (highest priority)
#   2. Environment-specific YAML (config/environments/{ENV}.yaml)
#   3. This base configuration (lowest priority)
#
# Variable Interpolation:
#   ${VAR_NAME}              - Required environment variable
#   ${VAR_NAME:default}      - Optional with default value
#   ${sandbox.timeout}       - Reference to another config value
#
# ============================================================

# Schema version (for migration compatibility)
schema_version: "2.0"

# Default sandbox mode (overridden by SANDBOX_MODE env var)
default_sandbox: fargate

# ============================================================
# Sandbox Definitions
# ============================================================
sandboxes:

  # ──────────────────────────────────────────────────────────
  # AWS Fargate Sandbox
  # ──────────────────────────────────────────────────────────
  fargate:
    enabled: true
    description: "AWS Fargate containers with ALB routing"

    # Coordinator implementation
    coordinator:
      module: src.sandbox.fargate_coordinator
      class: FargateCoordinator

      # Constructor parameters
      config:
        # ECS Configuration
        ecs_cluster_name: ${ECS_CLUSTER_NAME}
        task_definition_arn: ${TASK_DEFINITION_ARN}
        container_name: ${CONTAINER_NAME:fargate-runtime}

        # Network Configuration
        subnet_ids: ${FARGATE_SUBNET_IDS}  # Comma-separated
        security_group_ids: ${FARGATE_SECURITY_GROUP_IDS}  # Comma-separated
        assign_public_ip: ${FARGATE_ASSIGN_PUBLIC_IP:DISABLED}

        # ALB Configuration
        alb_dns: ${ALB_DNS}
        alb_target_group_arn: ${ALB_TARGET_GROUP_ARN}

        # S3 Configuration (for file uploads)
        s3_bucket_name: ${S3_BUCKET_NAME}

        # Execution Limits
        timeout_seconds: 180
        max_concurrent_sessions: 10
        max_code_size_bytes: 1048576  # 1MB

        # Session Management
        session_ttl_seconds: 3600  # 1 hour
        cleanup_on_exit: true
        enable_session_reuse: false

        # Health Check
        health_check_interval_seconds: 5
        health_check_max_retries: 12
        alb_wait_time_seconds: 60

        # Retry Configuration
        retry_on_failure: true
        max_retries: 3
        retry_backoff_factor: 2.0

    # Tool Implementations
    tools:
      python:
        module: src.tools.fargate_python_tool
        function: fargate_python_tool
        config:
          timeout: ${sandboxes.fargate.coordinator.config.timeout_seconds}

      bash:
        module: src.tools.fargate_bash_tool
        function: fargate_bash_tool
        config:
          timeout: ${sandboxes.fargate.coordinator.config.timeout_seconds}

    # Observability
    observability:
      logging:
        enabled: true
        level: INFO  # DEBUG, INFO, WARNING, ERROR
        log_code_execution: true  # Log code being executed (careful with PII)

      metrics:
        enabled: true
        namespace: DeepInsight/Fargate
        dimensions:
          Environment: ${AWS_ENV:dev}

      tracing:
        enabled: ${AGENT_OBSERVABILITY_ENABLED:true}
        sample_rate: 1.0  # 100% sampling

  # ──────────────────────────────────────────────────────────
  # Local Subprocess Sandbox
  # ──────────────────────────────────────────────────────────
  local:
    enabled: true
    description: "Local subprocess execution (development/testing)"

    coordinator:
      module: src.sandbox.local_coordinator
      class: LocalCoordinator

      config:
        # Execution Limits
        timeout_seconds: 600  # 10 minutes (longer for local dev)
        max_code_size_bytes: 5242880  # 5MB (more generous for local)

        # Working Directory
        working_directory: ./workspace
        create_working_directory: true
        cleanup_working_directory: false  # Keep files for inspection

        # Python Configuration
        python_executable: ${PYTHON_EXECUTABLE:python3}
        use_virtualenv: false
        virtualenv_path: null

        # Security (local dev - more permissive)
        allow_network_access: true
        allow_file_system_access: true
        restricted_imports: []  # Empty = no restrictions

    tools:
      python:
        module: src.tools.python_repl_tool
        function: python_repl_tool
        config:
          timeout: ${sandboxes.local.coordinator.config.timeout_seconds}

      bash:
        module: src.tools.bash_tool
        function: bash_tool
        config:
          timeout: ${sandboxes.local.coordinator.config.timeout_seconds}
          shell: /bin/bash

    observability:
      logging:
        enabled: true
        level: DEBUG  # More verbose for local dev
        log_code_execution: true

      metrics:
        enabled: false  # No metrics for local dev

      tracing:
        enabled: false  # No tracing for local dev

  # ──────────────────────────────────────────────────────────
  # E2B Cloud Sandbox
  # ──────────────────────────────────────────────────────────
  e2b:
    enabled: false  # Not yet implemented
    description: "E2B cloud sandboxes (third-party)"

    coordinator:
      module: src.sandbox.e2b_coordinator
      class: E2BCoordinator

      config:
        # E2B API Configuration
        api_key: ${E2B_API_KEY}
        api_endpoint: ${E2B_API_ENDPOINT:https://api.e2b.dev}

        # Sandbox Configuration
        template: python3  # E2B template name
        timeout_seconds: 300

        # Resource Limits
        cpu_count: 2
        memory_mb: 2048
        disk_mb: 10240

        # Session Management
        session_ttl_seconds: 3600
        cleanup_on_exit: true

    tools:
      python:
        module: src.tools.e2b_python_tool
        function: e2b_python_tool
        config:
          timeout: ${sandboxes.e2b.coordinator.config.timeout_seconds}

      bash:
        module: src.tools.e2b_bash_tool
        function: e2b_bash_tool
        config:
          timeout: ${sandboxes.e2b.coordinator.config.timeout_seconds}

    observability:
      logging:
        enabled: true
        level: INFO
        log_code_execution: true

      metrics:
        enabled: true
        namespace: DeepInsight/E2B

# ============================================================
# Agent Tool Configurations
# ============================================================
agents:

  # Coder Agent
  coder:
    description: "Python/Bash code execution agent"
    tools:
      - python
      - bash
    sandbox_required: true
    timeout_multiplier: 1.0  # Use sandbox default timeout

  # Validator Agent
  validator:
    description: "Result validation agent"
    tools:
      - python
      - bash
    sandbox_required: true
    timeout_multiplier: 0.5  # Validation is faster

  # Reporter Agent
  reporter:
    description: "Report generation agent"
    tools:
      - python
    sandbox_required: true
    timeout_multiplier: 2.0  # Reporting takes longer

  # Tracker Agent
  tracker:
    description: "Progress tracking agent (always local)"
    tools: []
    sandbox_required: false
    force_local: true  # Always runs locally, never in sandbox

# ============================================================
# Feature Flags
# ============================================================
features:

  # Session Management
  enable_session_pooling: false  # Experimental: Pre-create sessions
  enable_session_reuse: false    # Experimental: Reuse sessions across requests

  # Performance
  enable_code_caching: false     # Experimental: Cache code execution results
  enable_parallel_execution: false  # Experimental: Run multiple agents in parallel

  # Observability
  enable_detailed_tracing: ${AGENT_OBSERVABILITY_ENABLED:true}
  enable_performance_profiling: false

  # Security
  enable_code_sandboxing: true   # Always true for production
  enable_code_validation: true   # Validate code before execution

# ============================================================
# Global Settings
# ============================================================
global:

  # AWS Configuration
  aws_region: ${AWS_REGION:us-east-1}
  aws_account_id: ${AWS_ACCOUNT_ID}

  # Bedrock Configuration
  bedrock_model_id: ${BEDROCK_MODEL_ID:anthropic.claude-3-haiku-20240307-v1:0}

  # Runtime Configuration
  runtime_name: ${RUNTIME_NAME:deep_insight_runtime}
  runtime_version: "2.0"

  # Error Handling
  retry_on_transient_errors: true
  max_global_retries: 3

  # Rate Limiting
  max_requests_per_minute: 60
  max_concurrent_requests: 10

# ============================================================
# Validation Rules
# ============================================================
validation:

  # Coordinator Validation
  require_coordinator_module: true
  require_coordinator_class: true

  # Tool Validation
  require_tool_module: true
  require_tool_function: true

  # Configuration Validation
  require_timeout_config: true
  warn_on_long_timeout: 600  # Warn if timeout > 10 minutes

  # Environment Validation
  require_env_vars:
    fargate:
      - ECS_CLUSTER_NAME
      - TASK_DEFINITION_ARN
      - ALB_DNS
      - ALB_TARGET_GROUP_ARN
    local: []
    e2b:
      - E2B_API_KEY
```

### Environment-Specific Overrides

**File**: `config/environments/prod.yaml` (~50 lines)

```yaml
# ============================================================
# Production Environment Overrides
# ============================================================
#
# This file overrides base.yaml for production deployments.
# Only specify values that differ from base configuration.
#
# ============================================================

# Production uses Fargate exclusively
default_sandbox: fargate

sandboxes:
  fargate:
    coordinator:
      config:
        # Production: More aggressive timeouts
        timeout_seconds: 120  # 2 minutes (vs 3 in base)
        max_concurrent_sessions: 50  # Higher capacity

        # Production: No session reuse (security)
        enable_session_reuse: false

        # Production: Stricter health checks
        health_check_max_retries: 6  # Fail faster

    observability:
      logging:
        level: WARNING  # Less verbose
        log_code_execution: false  # Don't log code (PII concerns)

      metrics:
        enabled: true
        dimensions:
          Environment: prod

      tracing:
        sample_rate: 0.1  # 10% sampling (reduce costs)

  # Disable local and E2B in production
  local:
    enabled: false

  e2b:
    enabled: false

# Feature flags for production
features:
  enable_session_pooling: false  # Not ready for prod
  enable_code_caching: false
  enable_parallel_execution: false
  enable_detailed_tracing: false  # Reduce overhead
  enable_performance_profiling: false

# Production rate limits
global:
  max_requests_per_minute: 120  # Higher throughput
  max_concurrent_requests: 50
```

**File**: `config/environments/dev.yaml` (~30 lines)

```yaml
# ============================================================
# Development Environment Overrides
# ============================================================

# Dev can use any sandbox
default_sandbox: ${SANDBOX_MODE:fargate}

sandboxes:
  fargate:
    coordinator:
      config:
        # Dev: Longer timeouts for debugging
        timeout_seconds: 300
        max_concurrent_sessions: 5

    observability:
      logging:
        level: DEBUG  # Verbose logging
        log_code_execution: true

      tracing:
        sample_rate: 1.0  # 100% sampling

  local:
    enabled: true  # Allow local development

  e2b:
    enabled: true  # Allow testing E2B

# Feature flags for development
features:
  enable_session_pooling: true  # Test experimental features
  enable_code_caching: true
  enable_parallel_execution: true
  enable_detailed_tracing: true
  enable_performance_profiling: true

# Dev: Lower rate limits (prevent runaway costs)
global:
  max_requests_per_minute: 30
  max_concurrent_requests: 5
```

**File**: `config/environments/local.yaml` (~20 lines)

```yaml
# ============================================================
# Local Testing Environment (No AWS)
# ============================================================

# Force local mode
default_sandbox: local

sandboxes:
  # Disable cloud sandboxes for local testing
  fargate:
    enabled: false

  e2b:
    enabled: false

  # Only local is available
  local:
    enabled: true
    coordinator:
      config:
        timeout_seconds: 3600  # 1 hour for interactive debugging

    observability:
      logging:
        level: DEBUG

# No rate limits for local
global:
  max_requests_per_minute: 1000
  max_concurrent_requests: 100
```

---

## File Structure & Organization

### Recommended Structure

```
project_root/
├── config/
│   ├── base.yaml                      # Master configuration
│   ├── environments/
│   │   ├── dev.yaml                   # Development overrides
│   │   ├── prod.yaml                  # Production overrides
│   │   └── local.yaml                 # Local testing overrides
│   ├── sandboxes/                     # Sandbox-specific (alternative org)
│   │   ├── fargate.yaml
│   │   ├── local.yaml
│   │   └── e2b.yaml
│   ├── schemas/
│   │   ├── sandbox.schema.json        # JSON Schema for validation
│   │   └── agent.schema.json
│   └── README.md                      # Config documentation
├── src/
│   ├── config/                        # Configuration loading logic
│   │   ├── __init__.py
│   │   ├── loader.py                  # YAML loading + merging
│   │   ├── validator.py               # Schema validation
│   │   ├── interpolation.py           # Variable interpolation
│   │   └── cache.py                   # Config caching
│   └── sandbox/
│       ├── factory.py                 # Config-driven factory
│       └── ...
└── tests/
    └── config/
        ├── test_loader.py
        ├── test_validator.py
        └── fixtures/
            ├── valid_config.yaml
            └── invalid_config.yaml
```

### Alternative: Modular Organization

```
config/
├── _base.yaml                         # Shared base
├── sandboxes/
│   ├── fargate/
│   │   ├── coordinator.yaml           # Coordinator config
│   │   ├── tools.yaml                 # Tool mappings
│   │   └── observability.yaml         # Logging/metrics
│   ├── local/
│   │   └── ...
│   └── e2b/
│       └── ...
├── agents/
│   ├── coder.yaml
│   ├── validator.yaml
│   └── reporter.yaml
└── environments/
    ├── dev.yaml                       # Imports and overrides
    ├── prod.yaml
    └── local.yaml
```

**Pros**: Better organization for large configs
**Cons**: More complex loading logic (need to merge multiple files)

---

## Component Loading Strategy

### Configuration Loader Implementation

**File**: `src/config/loader.py` (~400 lines)

```python
"""
Configuration loader with environment merging and validation.

Features:
    - Load YAML configurations
    - Merge base + environment-specific configs
    - Interpolate environment variables
    - Validate against JSON Schema
    - Cache parsed configurations

Usage:
    from src.config.loader import ConfigLoader

    loader = ConfigLoader()
    config = loader.load()  # Loads base + environment

    # Access config
    sandbox_config = config.get_sandbox("fargate")
    timeout = sandbox_config["coordinator"]["config"]["timeout_seconds"]
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    Load and merge YAML configurations.

    Configuration precedence (highest to lowest):
        1. Environment variables
        2. Environment-specific YAML
        3. Base YAML
    """

    def __init__(
        self,
        base_config_path: str = "config/base.yaml",
        env_config_dir: str = "config/environments",
        environment: str = None
    ):
        """
        Initialize configuration loader.

        Args:
            base_config_path: Path to base configuration file
            env_config_dir: Directory containing environment-specific configs
            environment: Environment name (dev/prod/local).
                        Defaults to AWS_ENV or ENVIRONMENT env var.
        """
        self.base_config_path = Path(base_config_path)
        self.env_config_dir = Path(env_config_dir)

        # Determine environment
        self.environment = (
            environment
            or os.getenv("AWS_ENV")
            or os.getenv("ENVIRONMENT")
            or "dev"
        )

        self.env_config_path = self.env_config_dir / f"{self.environment}.yaml"

        # Cache
        self._config: Optional[Dict[str, Any]] = None
        self._load_time: Optional[float] = None

        logger.info(f"🔧 ConfigLoader initialized: environment={self.environment}")

    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration with caching.

        Args:
            force_reload: Force reload even if cached

        Returns:
            Merged configuration dictionary
        """
        if self._config is not None and not force_reload:
            logger.debug("Using cached configuration")
            return self._config

        logger.info("📄 Loading configuration files...")

        # 1. Load base config
        base_config = self._load_yaml(self.base_config_path)
        logger.info(f"✅ Loaded base config: {self.base_config_path}")

        # 2. Load environment-specific config (if exists)
        if self.env_config_path.exists():
            env_config = self._load_yaml(self.env_config_path)
            logger.info(f"✅ Loaded environment config: {self.env_config_path}")
        else:
            env_config = {}
            logger.warning(f"⚠️  Environment config not found: {self.env_config_path}")

        # 3. Merge configurations (env overrides base)
        merged_config = self._deep_merge(base_config, env_config)

        # 4. Interpolate variables
        interpolated_config = self._interpolate_variables(merged_config)

        # 5. Cache result
        self._config = interpolated_config
        import time
        self._load_time = time.time()

        logger.info("✅ Configuration loaded successfully")
        return self._config

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file with error handling."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Override values take precedence. Nested dictionaries are merged recursively.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def _interpolate_variables(self, config: Dict) -> Dict:
        """
        Interpolate variables in configuration.

        Supports:
            ${VAR_NAME}           - Required env var (error if missing)
            ${VAR_NAME:default}   - Optional env var with default
            ${config.path.to.value} - Reference to another config value

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with interpolated values
        """
        result = deepcopy(config)

        def interpolate_value(value: Any, context: Dict) -> Any:
            """Recursively interpolate a value."""
            if isinstance(value, str):
                # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

                def replacer(match):
                    var_name = match.group(1)
                    default_value = match.group(2)

                    # Check if it's a config reference (e.g., config.path.to.value)
                    if var_name.startswith("config."):
                        # Not implemented in this example (would need recursive lookup)
                        logger.warning(f"Config references not yet implemented: {var_name}")
                        return match.group(0)

                    # Check if it's a reference to another sandbox config
                    if "." in var_name and not var_name.startswith("config."):
                        # e.g., sandboxes.fargate.coordinator.config.timeout_seconds
                        try:
                            parts = var_name.split(".")
                            ref_value = context
                            for part in parts:
                                ref_value = ref_value[part]
                            return str(ref_value)
                        except (KeyError, TypeError):
                            if default_value is not None:
                                return default_value
                            raise ValueError(f"Config reference not found: {var_name}")

                    # Environment variable
                    env_value = os.getenv(var_name)

                    if env_value is not None:
                        return env_value
                    elif default_value is not None:
                        return default_value
                    else:
                        raise ValueError(
                            f"Required environment variable not set: {var_name}"
                        )

                return re.sub(pattern, replacer, value)

            elif isinstance(value, dict):
                return {k: interpolate_value(v, context) for k, v in value.items()}

            elif isinstance(value, list):
                return [interpolate_value(item, context) for item in value]

            else:
                return value

        return interpolate_value(result, result)

    def get_sandbox(self, sandbox_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific sandbox.

        Args:
            sandbox_name: Name of sandbox (fargate, local, e2b)

        Returns:
            Sandbox configuration dictionary

        Raises:
            ValueError: If sandbox not found or disabled
        """
        config = self.load()

        sandboxes = config.get("sandboxes", {})
        if sandbox_name not in sandboxes:
            raise ValueError(f"Sandbox not found in configuration: {sandbox_name}")

        sandbox_config = sandboxes[sandbox_name]

        if not sandbox_config.get("enabled", True):
            raise ValueError(f"Sandbox is disabled: {sandbox_name}")

        return sandbox_config

    def get_default_sandbox_name(self) -> str:
        """Get the default sandbox name."""
        config = self.load()

        # Check SANDBOX_MODE env var first
        sandbox_mode = os.getenv("SANDBOX_MODE")
        if sandbox_mode:
            return sandbox_mode

        # Fall back to config default
        return config.get("default_sandbox", "fargate")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.

        Args:
            agent_name: Name of agent (coder, validator, etc.)

        Returns:
            Agent configuration dictionary
        """
        config = self.load()

        agents = config.get("agents", {})
        if agent_name not in agents:
            raise ValueError(f"Agent not found in configuration: {agent_name}")

        return agents[agent_name]

    def get_feature_flag(self, feature_name: str, default: bool = False) -> bool:
        """
        Get feature flag value.

        Args:
            feature_name: Name of feature flag
            default: Default value if not found

        Returns:
            Feature flag value (bool)
        """
        config = self.load()
        features = config.get("features", {})
        return features.get(feature_name, default)

    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration settings."""
        config = self.load()
        return config.get("global", {})

# Singleton instance
_config_loader: Optional[ConfigLoader] = None

def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader (singleton)."""
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader()

    return _config_loader

def load_config() -> Dict[str, Any]:
    """Convenience function to load configuration."""
    return get_config_loader().load()
```

### Dynamic Component Creation

**File**: `src/config/component_factory.py` (~200 lines)

```python
"""
Component factory for creating coordinators and tools from configuration.

This module reads configuration and dynamically imports/instantiates
the specified classes and functions.
"""

import importlib
from typing import Any, Callable, Dict
import logging

from src.config.loader import get_config_loader

logger = logging.getLogger(__name__)

class ComponentFactory:
    """Factory for creating components from configuration."""

    def __init__(self):
        self.config_loader = get_config_loader()
        self._coordinator_cache: Dict[str, Any] = {}

    def create_coordinator(self, sandbox_name: str = None) -> Any:
        """
        Create sandbox coordinator from configuration.

        Args:
            sandbox_name: Name of sandbox (defaults to configured default)

        Returns:
            Coordinator instance
        """
        # Get sandbox name
        if sandbox_name is None:
            sandbox_name = self.config_loader.get_default_sandbox_name()

        # Check cache (coordinators are singletons)
        if sandbox_name in self._coordinator_cache:
            logger.debug(f"Using cached coordinator: {sandbox_name}")
            return self._coordinator_cache[sandbox_name]

        # Get sandbox config
        sandbox_config = self.config_loader.get_sandbox(sandbox_name)

        # Get coordinator specification
        coord_spec = sandbox_config.get("coordinator", {})
        module_name = coord_spec.get("module")
        class_name = coord_spec.get("class")

        if not module_name or not class_name:
            raise ValueError(
                f"Sandbox {sandbox_name} missing coordinator module or class"
            )

        # Import module and get class
        try:
            module = importlib.import_module(module_name)
            coordinator_class = getattr(module, class_name)
        except ImportError as e:
            raise ImportError(
                f"Failed to import coordinator module {module_name}: {e}"
            )
        except AttributeError as e:
            raise AttributeError(
                f"Coordinator class {class_name} not found in {module_name}: {e}"
            )

        # Get constructor config
        constructor_config = coord_spec.get("config", {})

        # Create instance
        try:
            coordinator = coordinator_class(**constructor_config)
            logger.info(
                f"✅ Created coordinator: {sandbox_name} "
                f"({module_name}.{class_name})"
            )
        except TypeError as e:
            # Constructor doesn't accept config, try without args
            logger.warning(
                f"Constructor doesn't accept config, creating without args: {e}"
            )
            coordinator = coordinator_class()

        # Cache and return
        self._coordinator_cache[sandbox_name] = coordinator
        return coordinator

    def get_tool(self, tool_name: str, sandbox_name: str = None) -> Callable:
        """
        Get tool function from configuration.

        Args:
            tool_name: Name of tool (python, bash, etc.)
            sandbox_name: Name of sandbox (defaults to configured default)

        Returns:
            Tool function
        """
        # Get sandbox name
        if sandbox_name is None:
            sandbox_name = self.config_loader.get_default_sandbox_name()

        # Get sandbox config
        sandbox_config = self.config_loader.get_sandbox(sandbox_name)

        # Get tool specification
        tools = sandbox_config.get("tools", {})
        if tool_name not in tools:
            raise ValueError(
                f"Tool {tool_name} not found in sandbox {sandbox_name}"
            )

        tool_spec = tools[tool_name]
        module_name = tool_spec.get("module")
        function_name = tool_spec.get("function")

        if not module_name or not function_name:
            raise ValueError(
                f"Tool {tool_name} missing module or function specification"
            )

        # Import module and get function
        try:
            module = importlib.import_module(module_name)
            tool_function = getattr(module, function_name)
        except ImportError as e:
            raise ImportError(
                f"Failed to import tool module {module_name}: {e}"
            )
        except AttributeError as e:
            raise AttributeError(
                f"Tool function {function_name} not found in {module_name}: {e}"
            )

        logger.debug(
            f"Loaded tool: {tool_name} ({module_name}.{function_name})"
        )

        return tool_function

    def get_tools_for_agent(self, agent_name: str, sandbox_name: str = None) -> list:
        """
        Get all tools for a specific agent.

        Args:
            agent_name: Name of agent (coder, validator, etc.)
            sandbox_name: Name of sandbox (defaults to configured default)

        Returns:
            List of tool functions
        """
        # Get agent config
        agent_config = self.config_loader.get_agent_config(agent_name)
        tool_names = agent_config.get("tools", [])

        # Get tool functions
        tools = []
        for tool_name in tool_names:
            tool_func = self.get_tool(tool_name, sandbox_name)
            tools.append(tool_func)

        logger.info(
            f"Loaded {len(tools)} tools for agent {agent_name}: {tool_names}"
        )

        return tools

    def clear_cache(self) -> None:
        """Clear cached coordinators (for testing)."""
        self._coordinator_cache.clear()
        logger.info("🧹 Cleared component cache")

# Singleton instance
_component_factory: Optional[ComponentFactory] = None

def get_component_factory() -> ComponentFactory:
    """Get the global component factory (singleton)."""
    global _component_factory

    if _component_factory is None:
        _component_factory = ComponentFactory()

    return _component_factory
```

---

## Validation & Error Handling

### JSON Schema for Validation

**File**: `config/schemas/sandbox.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Sandbox Configuration Schema",
  "type": "object",
  "required": ["schema_version", "sandboxes"],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+$",
      "description": "Configuration schema version (e.g., '2.0')"
    },
    "default_sandbox": {
      "type": "string",
      "enum": ["fargate", "local", "e2b"],
      "default": "fargate"
    },
    "sandboxes": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/sandbox"
      },
      "minProperties": 1
    },
    "agents": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/agent"
      }
    },
    "features": {
      "type": "object",
      "additionalProperties": {
        "type": "boolean"
      }
    },
    "global": {
      "type": "object"
    }
  },
  "definitions": {
    "sandbox": {
      "type": "object",
      "required": ["enabled", "coordinator", "tools"],
      "properties": {
        "enabled": {
          "type": "boolean"
        },
        "description": {
          "type": "string"
        },
        "coordinator": {
          "type": "object",
          "required": ["module", "class"],
          "properties": {
            "module": {
              "type": "string",
              "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*$"
            },
            "class": {
              "type": "string",
              "pattern": "^[A-Z][a-zA-Z0-9]*$"
            },
            "config": {
              "type": "object"
            }
          }
        },
        "tools": {
          "type": "object",
          "additionalProperties": {
            "$ref": "#/definitions/tool"
          }
        },
        "observability": {
          "type": "object"
        }
      }
    },
    "tool": {
      "type": "object",
      "required": ["module", "function"],
      "properties": {
        "module": {
          "type": "string",
          "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*$"
        },
        "function": {
          "type": "string",
          "pattern": "^[a-z_][a-z0-9_]*$"
        },
        "config": {
          "type": "object"
        }
      }
    },
    "agent": {
      "type": "object",
      "required": ["tools", "sandbox_required"],
      "properties": {
        "description": {
          "type": "string"
        },
        "tools": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "sandbox_required": {
          "type": "boolean"
        },
        "timeout_multiplier": {
          "type": "number",
          "minimum": 0.1,
          "maximum": 10.0
        }
      }
    }
  }
}
```

### Schema Validator

**File**: `src/config/validator.py` (~150 lines)

```python
"""
Configuration validator using JSON Schema.

Validates configuration against schema before use, providing
clear error messages for invalid configurations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import logging

try:
    import jsonschema
    from jsonschema import Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logging.warning("jsonschema not installed. Install with: pip install jsonschema")

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Validate configuration against JSON Schema."""

    def __init__(self, schema_path: str = "config/schemas/sandbox.schema.json"):
        """
        Initialize validator.

        Args:
            schema_path: Path to JSON Schema file
        """
        self.schema_path = Path(schema_path)
        self.schema: Optional[Dict] = None

        if JSONSCHEMA_AVAILABLE:
            self._load_schema()
        else:
            logger.warning("⚠️  Validator disabled (jsonschema not installed)")

    def _load_schema(self) -> None:
        """Load JSON Schema from file."""
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found: {self.schema_path}")
            return

        with open(self.schema_path, 'r') as f:
            self.schema = json.load(f)

        logger.info(f"✅ Loaded schema: {self.schema_path}")

    def validate(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not JSONSCHEMA_AVAILABLE or self.schema is None:
            # No validation possible
            return True, []

        validator = Draft7Validator(self.schema)
        errors = list(validator.iter_errors(config))

        if not errors:
            logger.info("✅ Configuration is valid")
            return True, []

        # Format error messages
        error_messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path)
            message = f"{path}: {error.message}"
            error_messages.append(message)
            logger.error(f"❌ Validation error: {message}")

        return False, error_messages

    def validate_or_raise(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration and raise exception if invalid.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        is_valid, errors = self.validate(config)

        if not is_valid:
            error_text = "\n".join(errors)
            raise ValueError(f"Invalid configuration:\n{error_text}")

# Convenience function
def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration (raises exception if invalid).

    Args:
        config: Configuration dictionary
    """
    validator = ConfigValidator()
    validator.validate_or_raise(config)
```

---

## Environment Management

### Environment Detection Strategy

```python
# Priority order for environment detection
def get_environment() -> str:
    """
    Detect current environment.

    Priority:
        1. ENVIRONMENT env var (explicit)
        2. AWS_ENV env var (AWS convention)
        3. Check if running in AWS (EC2/ECS metadata)
        4. Default to 'dev'
    """
    # Explicit environment variable
    if env := os.getenv("ENVIRONMENT"):
        return env

    # AWS environment variable
    if aws_env := os.getenv("AWS_ENV"):
        return aws_env

    # Check if running in AWS
    if is_running_in_aws():
        return "prod"  # Assume prod if in AWS

    # Default to dev
    return "dev"

def is_running_in_aws() -> bool:
    """Check if running in AWS (EC2/ECS)."""
    # Check ECS metadata
    if os.getenv("ECS_CONTAINER_METADATA_URI"):
        return True

    # Check EC2 metadata (with timeout)
    try:
        import urllib.request
        urllib.request.urlopen(
            "http://169.254.169.254/latest/meta-data/",
            timeout=1
        )
        return True
    except:
        return False
```

### Environment Variable Mapping

**File**: `.env.example` (updated)

```bash
# ============================================================
# Environment Selection
# ============================================================
# Which configuration to load from config/environments/
# Options: dev, prod, local
ENVIRONMENT=dev

# Alternative: AWS_ENV (AWS convention)
# AWS_ENV=prod

# ============================================================
# Sandbox Mode Override
# ============================================================
# Override default_sandbox from config
# Options: fargate, local, e2b
SANDBOX_MODE=fargate

# ============================================================
# AWS Configuration (required for fargate mode)
# ============================================================
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
ECS_CLUSTER_NAME=my-cluster
TASK_DEFINITION_ARN=arn:aws:ecs:...
CONTAINER_NAME=fargate-runtime
ALB_DNS=my-alb-123.us-east-1.elb.amazonaws.com
ALB_TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:...
FARGATE_SUBNET_IDS=subnet-123,subnet-456
FARGATE_SECURITY_GROUP_IDS=sg-123
S3_BUCKET_NAME=my-bucket

# ============================================================
# E2B Configuration (required for e2b mode)
# ============================================================
E2B_API_KEY=your_api_key_here

# ============================================================
# Model Configuration
# ============================================================
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# ============================================================
# Observability
# ============================================================
AGENT_OBSERVABILITY_ENABLED=true
```

---

## Advanced Features

### 1. Configuration Composition (Import/Extend)

**Syntax**:

```yaml
# config/environments/staging.yaml

# Import base prod config
_import: prod.yaml

# Override specific values
sandboxes:
  fargate:
    coordinator:
      config:
        max_concurrent_sessions: 20  # Lower than prod (50)
```

**Implementation** (`src/config/loader.py` addition):

```python
def _process_imports(self, config: Dict, config_dir: Path) -> Dict:
    """Process _import directives recursively."""
    if "_import" not in config:
        return config

    import_path = config_dir / config["_import"]
    imported_config = self._load_yaml(import_path)

    # Recursively process imports in imported config
    imported_config = self._process_imports(imported_config, config_dir)

    # Remove _import directive
    current_config = {k: v for k, v in config.items() if k != "_import"}

    # Merge: current overrides imported
    return self._deep_merge(imported_config, current_config)
```

### 2. Conditional Configuration

**Syntax**:

```yaml
sandboxes:
  fargate:
    coordinator:
      config:
        # Use different timeouts based on environment
        timeout_seconds:
          _if: ${ENVIRONMENT}
          prod: 120
          dev: 300
          _default: 180
```

### 3. Hot Reloading

**Implementation**:

```python
class ConfigLoader:
    def watch_for_changes(self, callback: Callable) -> None:
        """
        Watch configuration files for changes and reload.

        Uses file system watching (watchdog library).
        """
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class ConfigChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith('.yaml'):
                    logger.info(f"Config changed: {event.src_path}")
                    self.load(force_reload=True)
                    callback(self._config)

        observer = Observer()
        observer.schedule(ConfigChangeHandler(), str(self.base_config_path.parent))
        observer.start()
```

### 4. Configuration Versioning

**Migration Script**:

```python
# src/config/migrations.py

def migrate_v1_to_v2(config: Dict) -> Dict:
    """Migrate configuration from v1.0 to v2.0."""
    # v1.0 used 'timeout' instead of 'timeout_seconds'
    # ... migration logic
    return migrated_config

MIGRATIONS = {
    "1.0": migrate_v1_to_v2,
}

def migrate_config(config: Dict) -> Dict:
    """Apply migrations to reach current schema version."""
    current_version = config.get("schema_version", "1.0")

    for version, migration_func in MIGRATIONS.items():
        if current_version == version:
            config = migration_func(config)
            current_version = config["schema_version"]

    return config
```

---

## Migration Path

### Phase 1: Setup Infrastructure (Week 1)

**Day 1-2: Create Configuration Files**

```bash
# Create directory structure
mkdir -p config/environments config/schemas

# Create base configuration
cp config/base.yaml.example config/base.yaml

# Create environment-specific configs
touch config/environments/{dev,prod,local}.yaml

# Create JSON Schema
touch config/schemas/sandbox.schema.json
```

**Day 3-4: Implement Loader**

```bash
# Create config module
mkdir -p src/config
touch src/config/{__init__.py,loader.py,validator.py}

# Implement ConfigLoader (copy from above)
# Implement ConfigValidator (copy from above)

# Test loading
python3 -c "from src.config.loader import load_config; print(load_config())"
```

**Day 5: Implement Component Factory**

```bash
# Implement ComponentFactory
touch src/config/component_factory.py

# Test component creation
python3 -c "from src.config.component_factory import get_component_factory; f = get_component_factory(); print(f.create_coordinator('fargate'))"
```

### Phase 2: Migration (Week 2)

**Day 1: Update Runtime**

```python
# OLD (agentcore_runtime.py)
from src.tools.global_fargate_coordinator import get_global_session
coordinator = get_global_session()

# NEW
from src.config.component_factory import get_component_factory
factory = get_component_factory()
coordinator = factory.create_coordinator()  # Uses config!
```

**Day 2: Update Graph Nodes**

```python
# OLD (src/graph/nodes.py)
from src.tools import coder_agent_fargate_tool, ...

# NEW
from src.config.component_factory import get_component_factory
factory = get_component_factory()
coder_tools = factory.get_tools_for_agent("coder")
```

**Day 3-4: Test End-to-End**

```bash
# Test Fargate mode (should work identically)
ENVIRONMENT=dev python3 02_invoke_agentcore_runtime_vpc.py

# Test local mode (new capability!)
ENVIRONMENT=local python3 02_invoke_agentcore_runtime_vpc.py
```

**Day 5: Production Deployment**

```bash
# Deploy with prod config
ENVIRONMENT=prod python3 01_create_agentcore_runtime_vpc.py
```

### Phase 3: Advanced Features (Week 3-4)

- Configuration validation
- Hot reloading
- Configuration composition
- Metrics and monitoring

---

## Implementation Roadmap

### Sprint 1: Foundation (5 days)

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Design YAML schema | 4h | | |
| Create base.yaml | 3h | | |
| Create environment configs | 2h | | |
| Implement ConfigLoader | 6h | | |
| Implement variable interpolation | 4h | | |
| Unit tests for loader | 3h | | |
| **Total** | **22h** | | |

### Sprint 2: Component Factory (5 days)

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Design component factory API | 2h | | |
| Implement ComponentFactory | 8h | | |
| Create JSON Schema | 3h | | |
| Implement ConfigValidator | 4h | | |
| Integration tests | 4h | | |
| **Total** | **21h** | | |

### Sprint 3: Runtime Integration (5 days)

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Update agentcore_runtime.py | 3h | | |
| Update src/graph/nodes.py | 3h | | |
| Update agent tools | 4h | | |
| End-to-end testing (Fargate) | 4h | | |
| End-to-end testing (Local) | 4h | | |
| Documentation | 3h | | |
| **Total** | **21h** | | |

### Sprint 4: Production Deployment (5 days)

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Create prod.yaml | 2h | | |
| Validation testing | 4h | | |
| Canary deployment (10%) | 4h | | |
| Monitor for 24h | 2h | | |
| Full deployment (100%) | 2h | | |
| Post-deployment validation | 2h | | |
| **Total** | **16h** | | |

**Grand Total**: **80 hours** (4 weeks @ 20h/week)

---

## Testing Strategy

### Unit Tests

**File**: `tests/config/test_loader.py`

```python
import pytest
from src.config.loader import ConfigLoader

def test_load_base_config():
    """Test loading base configuration."""
    loader = ConfigLoader()
    config = loader.load()

    assert "sandboxes" in config
    assert "fargate" in config["sandboxes"]

def test_environment_override():
    """Test environment-specific overrides."""
    loader = ConfigLoader(environment="prod")
    config = loader.load()

    # Prod should have stricter timeout
    timeout = config["sandboxes"]["fargate"]["coordinator"]["config"]["timeout_seconds"]
    assert timeout == 120

def test_variable_interpolation():
    """Test environment variable interpolation."""
    import os
    os.environ["TEST_VAR"] = "test_value"

    loader = ConfigLoader()
    # ... test interpolation

def test_missing_required_env_var():
    """Test error on missing required env var."""
    loader = ConfigLoader()

    with pytest.raises(ValueError, match="Required environment variable"):
        loader.load()
```

### Integration Tests

**File**: `tests/integration/test_config_driven.py`

```python
def test_create_coordinator_from_config():
    """Test creating coordinator from configuration."""
    from src.config.component_factory import get_component_factory

    factory = get_component_factory()
    coordinator = factory.create_coordinator("fargate")

    assert coordinator is not None
    assert hasattr(coordinator, "ensure_session")

def test_get_tools_for_agent():
    """Test getting tools for agent from config."""
    from src.config.component_factory import get_component_factory

    factory = get_component_factory()
    tools = factory.get_tools_for_agent("coder")

    assert len(tools) == 2  # python and bash
```

### End-to-End Tests

```bash
# Test all environments
for env in dev prod local; do
    echo "Testing environment: $env"
    ENVIRONMENT=$env python3 02_invoke_agentcore_runtime_vpc.py
done

# Test all sandbox modes
for mode in fargate local; do
    echo "Testing sandbox: $mode"
    SANDBOX_MODE=$mode python3 02_invoke_agentcore_runtime_vpc.py
done
```

---

## Summary

### Benefits of Configuration-Driven Approach

✅ **Zero-code deployments** - Change sandboxes via config updates
✅ **Environment parity** - Same code, different configs (dev/prod/local)
✅ **Self-documenting** - Config files document available options
✅ **Type-safe** - JSON Schema validation catches errors early
✅ **Flexible** - Easy to add new sandboxes without code changes
✅ **Testable** - Easy to test different configurations

### Trade-offs

❌ **Initial complexity** - More setup than simple factory
❌ **YAML dependency** - Requires understanding YAML syntax
❌ **Validation overhead** - Schema validation adds startup time
❌ **Debugging** - Config errors harder to debug than code errors

### Recommended Next Steps

1. **Review this plan** with team
2. **Create proof-of-concept** (base.yaml + loader.py)
3. **Test with Fargate mode** (should work identically)
4. **Iterate** based on feedback
5. **Full implementation** (follow Sprint roadmap)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: Detailed Planning Complete
