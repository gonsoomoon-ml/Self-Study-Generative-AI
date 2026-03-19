# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code plugin** called `translate-toolkit` — a multilingual translation plugin built entirely with Markdown and JSON (no programming language code). It demonstrates the Claude Code plugin system for non-developers, with a local marketplace for distribution.

Primary language of README and docs: **Korean**. The plugin itself handles ko/ja translations.

## Architecture

The plugin has a **dual directory layout** — the same files exist in two locations:

- `translate-toolkit/` — the plugin source (development copy)
- `local-marketplace/plugins/translate-toolkit/` — the installable copy inside the local Git-based marketplace

**Keep both copies in sync** when making changes.

### Plugin Components (all Markdown/JSON, no code)

| Component | Location | Purpose |
|-----------|----------|---------|
| Commands | `commands/*.md` | User-invoked slash commands (`/translate`, `/translate-file`, `/glossary`) |
| Skills | `skills/translation-context/SKILL.md` | Auto-injected context for AI (style guides, glossary rules) |
| Agents | `agents/review-translator.md` | Sub-agent for translation quality review |
| Hooks | `hooks/hooks.json` + `hooks/check-translation.sh` | PostToolUse hook warns when source files change |
| Glossary | `glossary/terms.json` | Term mappings (en→ko, en→ja) |
| Metadata | `.claude-plugin/plugin.json` | Plugin name, version, author |

### Critical Layout Rule

`commands/`, `skills/`, `agents/`, `hooks/` **must be at the plugin root level**, not inside `.claude-plugin/`. The `.claude-plugin/` directory holds only `plugin.json` (and optionally duplicates for legacy reasons). The plugin loader discovers components from root-level directories.

## Plugin Installation Flow

```bash
# Register the local marketplace
claude plugin marketplace add /path/to/local-marketplace

# Install the plugin
claude plugin install translate-toolkit@local-plugins

# Validate structure before install
claude plugin validate /path/to/translate-toolkit
```

## Key Conventions

- **plugin.json**: `author` must be an object `{"name": "..."}`, never a string. Do not add `commands`/`skills`/`agents` fields — these are auto-discovered from directory structure.
- **hooks.json**: Uses event names as keys (`PostToolUse`, `PreToolUse`, `Stop`, `SessionStart`, `UserPromptSubmit`), not arrays at the top level. The `${CLAUDE_PLUGIN_ROOT}` variable resolves to the plugin root at runtime.
- **Glossary terms.json**: Array of `{"term", "translations": {"ko": ..., "ja": ...}}`. Always read before modifying; write back the complete file.
- **Translation output naming**: `<filename>.<locale>.md` (e.g., `README.ko.md`).

## Bedrock Integration

When used with Amazon Bedrock, set environment variables:
- `CLAUDE_CODE_USE_BEDROCK=1`
- `AWS_REGION`
- `ANTHROPIC_MODEL`
