# Agent Runtime Overview

Agent Runtime is a lightweight framework for building AI-powered applications with built-in observability and guardrails.

## Features

- **Plugin System**: Extend functionality using slash commands and custom skills
- **Prompt Caching**: Reduce latency and cost with automatic prompt caching
- **Hook Integration**: Trigger automated workflows on file changes
- **Fine-tuning Support**: Customize Post-Trained Models for domain-specific tasks

## Quick Start

```bash
npm install agent-runtime
export CLAUDE_CODE_USE_BEDROCK=1
```

```javascript
const { AgentRuntime } = require('agent-runtime');

const agent = new AgentRuntime({
  model: 'claude-sonnet-4-6',
  region: 'us-west-2'
});

agent.run('Translate this document to Korean');
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `claude-sonnet-4-6` | Model ID to use |
| `region` | string | `us-west-2` | AWS region |
| `enableGuardrails` | boolean | `true` | Enable content guardrails |
| `cacheEnabled` | boolean | `true` | Enable prompt caching |

## Architecture

The Agent Runtime connects to Amazon Bedrock for model inference. All plugin definitions (skills, commands, hooks) run locally on the client side. Only the model inference requests are sent to the Bedrock API endpoint.

> **Note**: Ensure your IAM role has `bedrock:InvokeModel` permission before deployment.

For more details, see the [API Documentation](https://example.com/docs) or contact the team on Slack at `#agent-runtime`.
