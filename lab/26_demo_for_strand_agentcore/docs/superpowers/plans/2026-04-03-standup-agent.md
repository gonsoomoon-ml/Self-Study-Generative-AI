# Standup Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a "Write My Standup" demo agent that showcases Strands AgentSkills personalization and AgentCore Runtime hosting.

**Architecture:** A single `agent.py` wraps a Strands agent with `BedrockAgentCoreApp`. It loads a developer-specific `SKILL.md` from `skills/<DEV_NAME>/` and calls GitHub API autonomously via the `http_request` community tool. Two skill files (alex, maria) demonstrate same-code / different-output personalization.

**Tech Stack:** `strands-agents`, `strands-agents-tools`, `bedrock-agentcore`, Python 3.11

---

## File Map

```
lab/26_demo_for_strand_agentcore/
  agent.py                      # Main agent — BedrockAgentCoreApp entrypoint
  requirements.txt              # Python dependencies
  .bedrock_agentcore.yaml       # AgentCore Runtime deployment config (fill AWS values before deploy)
  skills/
    alex/
      SKILL.md                  # Alex's standup format and priorities
    maria/
      SKILL.md                  # Maria's standup format and priorities
  tests/
    test_agent.py               # Unit tests: skill loading + agent instantiation + mocked output
```

---

## Task 1: Project Setup

**Files:**
- Create: `lab/26_demo_for_strand_agentcore/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
bedrock-agentcore>=0.1.0
pytest>=8.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd lab/26_demo_for_strand_agentcore
pip install -r requirements.txt
```

Expected: No errors. Verify with:
```bash
python -c "from strands import Agent, AgentSkills; from strands_tools import http_request; from bedrock_agentcore.runtime import BedrockAgentCoreApp; print('OK')"
```
Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add lab/26_demo_for_strand_agentcore/requirements.txt
git commit -m "feat: add standup agent project setup"
```

---

## Task 2: Skill Files

**Files:**
- Create: `lab/26_demo_for_strand_agentcore/skills/alex/SKILL.md`
- Create: `lab/26_demo_for_strand_agentcore/skills/maria/SKILL.md`

- [ ] **Step 1: Create Alex's skill file**

`skills/alex/SKILL.md`:
```markdown
---
name: alex-standup
description: Alex의 스탠드업 형식과 선호도
---
Format: 3 bullets max. Yesterday / Today / Blockers.
Alex's team lead cares most about blockers — always lead with those if any exist.
Skip routine commits. Only mention PRs and code reviews.
Keep each bullet under 15 words.
```

- [ ] **Step 2: Create Maria's skill file**

`skills/maria/SKILL.md`:
```markdown
---
name: maria-standup
description: Maria의 스탠드업 형식과 선호도
---
Format: numbered list. What I shipped / What I'm building / What I need.
Maria's team uses a "What I need" format — always include this even if empty (write "nothing blocked").
Include PR links when mentioning pull requests.
Maria's lead wants detail — 2 sentences per item is fine.
```

- [ ] **Step 3: Commit**

```bash
git add lab/26_demo_for_strand_agentcore/skills/
git commit -m "feat: add alex and maria standup skill files"
```

---

## Task 3: Agent Code

**Files:**
- Create: `lab/26_demo_for_strand_agentcore/agent.py`

- [ ] **Step 1: Write agent.py**

```python
import os
from strands import Agent, AgentSkills
from strands_tools import http_request
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel

app = BedrockAgentCoreApp()

dev_name = os.environ.get("DEV_NAME", "alex")

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

agent = Agent(
    model=model,
    system_prompt=(
        f"You are a daily standup assistant for {dev_name}. "
        f"GITHUB_TOKEN is available in the environment — use it as a Bearer token "
        f"when calling https://api.github.com endpoints."
    ),
    tools=[http_request],
    plugins=[AgentSkills(skills=f"./skills/{dev_name}/")],
)


@app.entrypoint
def standup_agent(payload):
    user_input = payload.get("prompt", "Write my standup for today")
    response = agent(user_input)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 2: Verify the file runs without import errors**

```bash
cd lab/26_demo_for_strand_agentcore
python -c "import agent; print('Import OK')"
```
Expected output: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add lab/26_demo_for_strand_agentcore/agent.py
git commit -m "feat: add standup agent with BedrockAgentCoreApp entrypoint"
```

---

## Task 4: Tests

**Files:**
- Create: `lab/26_demo_for_strand_agentcore/tests/test_agent.py`

- [ ] **Step 1: Write failing test for skill loading**

`tests/test_agent.py`:
```python
import os
import pytest
from unittest.mock import patch, MagicMock
from strands import AgentSkills, Skill

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")


def test_alex_skill_loads():
    plugin = AgentSkills(skills=os.path.join(SKILLS_DIR, "alex"))
    skills = plugin.get_available_skills()
    assert len(skills) == 1
    assert skills[0].name == "alex-standup"


def test_maria_skill_loads():
    plugin = AgentSkills(skills=os.path.join(SKILLS_DIR, "maria"))
    skills = plugin.get_available_skills()
    assert len(skills) == 1
    assert skills[0].name == "maria-standup"


def test_alex_and_maria_have_different_instructions():
    alex_plugin = AgentSkills(skills=os.path.join(SKILLS_DIR, "alex"))
    maria_plugin = AgentSkills(skills=os.path.join(SKILLS_DIR, "maria"))
    alex_instructions = alex_plugin.get_available_skills()[0].instructions
    maria_instructions = maria_plugin.get_available_skills()[0].instructions
    assert alex_instructions != maria_instructions
```

- [ ] **Step 2: Run tests to verify they fail (before agent code exists)**

```bash
cd lab/26_demo_for_strand_agentcore
pytest tests/test_agent.py -v
```
Expected: Tests run. If skill files from Task 2 are already created, these should PASS at this point — that is expected since skills are data, not code.

- [ ] **Step 3: Run all tests to confirm green**

```bash
pytest tests/test_agent.py -v
```
Expected output:
```
tests/test_agent.py::test_alex_skill_loads PASSED
tests/test_agent.py::test_maria_skill_loads PASSED
tests/test_agent.py::test_alex_and_maria_have_different_instructions PASSED
3 passed
```

- [ ] **Step 4: Commit**

```bash
git add lab/26_demo_for_strand_agentcore/tests/
git commit -m "test: verify skill files load correctly for alex and maria"
```

---

## Task 5: Local Demo Run

> **Pre-requisite:** A GitHub Personal Access Token with `repo` and `read:user` scopes.

- [ ] **Step 1: Set environment variables**

```bash
export GITHUB_TOKEN=your_github_pat_here
export DEV_NAME=alex
```

- [ ] **Step 2: Run agent as Alex**

```bash
cd lab/26_demo_for_strand_agentcore
python -c "
import os
os.environ['DEV_NAME'] = 'alex'
from agent import agent
response = agent('Write my standup for today')
print(response)
"
```
Expected: Terminal prints Alex's standup in bullet format (Yesterday / Today / Blockers), referencing actual GitHub PRs.

- [ ] **Step 3: Run agent as Maria**

```bash
python -c "
import os
os.environ['DEV_NAME'] = 'maria'
# Re-create agent with Maria's skill
from strands import Agent, AgentSkills
from strands_tools import http_request
from strands.models import BedrockModel

model = BedrockModel(model_id='us.anthropic.claude-sonnet-4-20250514-v1:0')
agent = Agent(
    model=model,
    system_prompt='You are a daily standup assistant for maria. Use GITHUB_TOKEN env var as Bearer token for https://api.github.com endpoints.',
    tools=[http_request],
    plugins=[AgentSkills(skills='./skills/maria/')],
)
response = agent('Write my standup for today')
print(response)
"
```
Expected: Terminal prints Maria's standup in numbered list format (What I shipped / What I'm building / What I need), with PR links.

**Demo talking point at this step:** Same 15 lines of agent code — completely different output because the Skill file changed.

---

## Task 6: AgentCore Runtime Deployment Config

**Files:**
- Create: `lab/26_demo_for_strand_agentcore/.bedrock_agentcore.yaml`

> **Pre-requisite:** AWS account, IAM role for AgentCore, ECR repository. Reference the existing config at `lab/17_bedrock_agent_core/01-tutorials/01-AgentCore-runtime/01-hosting-agent/01-strands-with-bedrock-model/.bedrock_agentcore.yaml` for exact field values.

- [ ] **Step 1: Create .bedrock_agentcore.yaml**

```yaml
default_agent: standup_agent
agents:
  standup_agent:
    name: standup_agent
    entrypoint: agent.py          # relative path from this yaml file
    platform: linux/arm64
    container_runtime: docker
    aws:
      execution_role: arn:aws:iam::ACCOUNT_ID:role/agentcore-standup-role   # replace
      execution_role_auto_create: false
      account: 'ACCOUNT_ID'       # replace
      region: us-east-1
      ecr_repository: ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-standup_agent  # replace
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: HTTP
      observability:
        enabled: true
```

- [ ] **Step 2: Launch to AgentCore Runtime**

```bash
cd lab/26_demo_for_strand_agentcore
bedrock-agentcore launch --agent standup_agent
```
Expected: Docker image built, pushed to ECR, agent deployed. Output includes `agent_arn`.

- [ ] **Step 3: Invoke the deployed agent via chat**

```bash
bedrock-agentcore invoke --agent standup_agent \
  --payload '{"prompt": "Write my standup for today"}' \
  --env DEV_NAME=alex GITHUB_TOKEN=$GITHUB_TOKEN
```
Expected: Same standup output as local run, now served from AgentCore Runtime.

- [ ] **Step 4: Commit**

```bash
git add lab/26_demo_for_strand_agentcore/.bedrock_agentcore.yaml
git commit -m "feat: add AgentCore Runtime deployment config for standup agent"
```

---

## Demo Script (5분)

| 시간 | 발표자가 할 것 |
|---|---|
| 0:00–1:00 | `agent.py` 화면 공유 — "15줄이 전부입니다" |
| 1:00–2:00 | `skills/alex/SKILL.md` 열기 — "이 마크다운 파일이 Alex의 에이전트를 정의합니다" |
| 2:00–3:00 | Alex로 로컬 실행 → 스탠드업 출력 |
| 3:00–3:30 | `skills/maria/SKILL.md` 열기 — "Maria의 파일은 다릅니다" |
| 3:30–4:00 | Maria로 실행 → 다른 형식으로 출력 — "코드는 바꾸지 않았습니다" |
| 4:00–5:00 | `bedrock-agentcore invoke` 실행 → 동일한 결과 — "이제 팀 서비스입니다" |
