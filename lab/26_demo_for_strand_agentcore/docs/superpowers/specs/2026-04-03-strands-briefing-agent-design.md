# Demo Design: "Write My Standup" Agent

**Date:** 2026-04-03
**Duration:** 5-minute live demo
**Audience:** Developers

---

## Concept

A personal standup-writing agent each developer deploys once and messages every morning.

**Core message:**
> "You write the agent in an afternoon. You deploy it once. Your whole team uses it."

---

## Capabilities Showcased

### Strands Agents SDK
| Feature | Role in demo |
|---|---|
| `http_request` community tool | Agent calls GitHub API autonomously — developer writes zero REST logic |
| `AgentSkills` + `SKILL.md` | Personalization per developer via plain markdown, no code changes |

### Amazon Bedrock AgentCore
| Feature | Role in demo |
|---|---|
| Runtime | Hosts the agent as a chat-invocable team service |

---

## 5-Minute Demo Flow

| Time | What audience sees |
|---|---|
| 0:00–1:00 | Agent code on screen — `Agent(tools=[http_request], plugins=[AgentSkills(...)])`. ~15 lines total |
| 1:00–2:00 | `alex/SKILL.md` — plain text defining Alex's standup format and priorities |
| 2:00–3:00 | Run locally → agent calls GitHub, standup appears in terminal |
| 3:00–3:30 | Show `maria/SKILL.md` — different format, different priorities |
| 3:30–4:00 | Run for Maria → same code, different output |
| 4:00–5:00 | Deploy to AgentCore Runtime — one command. Invoke via chat → same result, now a team service |

### "Aha" Moments
- **Min 2:** Agent figures out which GitHub endpoints to call by itself — no REST logic written by developer
- **Min 3:30:** Same 15 lines, completely different output — Skills did that
- **Min 4:30:** Local script → team service in one step

---

## Code Structure

### `agent.py`
```python
import os
from strands import Agent, AgentSkills
from strands_tools import http_request

agent = Agent(
    system_prompt="You are a developer assistant. Use GITHUB_TOKEN from env to call GitHub API.",
    tools=[http_request],
    plugins=[AgentSkills(skills=f"./skills/{os.environ['DEV_NAME']}/")]
)

agent("Write my standup for today")
```

### Skill Files
```
skills/
  alex/
    SKILL.md
  maria/
    SKILL.md
```

### `skills/alex/SKILL.md`
```markdown
---
name: alex-standup
description: Alex's standup format and preferences
---
Format: 3 bullets max. Yesterday / Today / Blockers.
Alex's team lead cares most about blockers — always lead with those if any exist.
Skip routine commits. Only mention PRs and reviews.
```

### Deploy
```bash
# AgentCore Runtime deployment — exact command to be verified from AgentCore docs
agentcore deploy agent.py
```

---

## What's Intentionally Excluded

- **GitHub MCP / AgentCore Gateway** — adds OAuth/infra complexity, kills the "simple" message
- **Slack output** — webhook setup distracts from agent code
- **Scheduled execution** — AgentCore Runtime is chat-invocable, not a cron job
- **Memory** — out of scope for 5-min demo
- **Multiple data sources** (Jira, Calendar) — one source keeps the demo focused

---

## Why This Use Case

Standup generation was chosen over a general "morning briefing" because:
- Developers do it every day and find it genuinely annoying
- GitHub API provides all needed data with just a personal access token
- Output is short, immediately verifiable, and relatable to any developer in the audience
- Skills personalization is natural: every team has a different standup format
