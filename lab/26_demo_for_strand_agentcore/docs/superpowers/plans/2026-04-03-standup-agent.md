# 스탠드업 에이전트 구현 계획

> **에이전트 실행자 참고:** 필수 서브스킬: superpowers:subagent-driven-development (권장) 또는 superpowers:executing-plans 를 사용하여 태스크 단위로 구현하세요. 각 단계는 체크박스 (`- [ ]`) 형식으로 진행 상황을 추적합니다.

**목표:** Strands AgentSkills 개인화와 AgentCore Runtime 호스팅을 시연하는 "내 스탠드업 작성해줘" 데모 에이전트 구축

**아키텍처:** 단일 `agent.py`가 `BedrockAgentCoreApp`으로 Strands 에이전트를 감쌉니다. `skills/<DEV_NAME>/`에서 개발자별 `SKILL.md`를 로드하고, `http_request` 커뮤니티 툴을 통해 GitHub API를 자율적으로 호출합니다. Alex와 Maria 두 개의 스킬 파일로 "동일한 코드 / 다른 출력" 개인화를 시연합니다.

**기술 스택:** `strands-agents`, `strands-agents-tools`, `bedrock-agentcore`, Python 3.11

---

## 파일 구조

```
lab/26_demo_for_strand_agentcore/
  agent.py                      # 메인 에이전트 — BedrockAgentCoreApp 엔트리포인트
  setup/
    pyproject.toml              # Python 의존성 패키지 (uv)
    create_env.sh               # 환경 설정 스크립트
  .bedrock_agentcore.yaml       # AgentCore Runtime 배포 설정 (배포 전 AWS 값 입력 필요)
  skills/
    alex/
      SKILL.md                  # Alex의 스탠드업 형식과 우선순위
    maria/
      SKILL.md                  # Maria의 스탠드업 형식과 우선순위
  tests/
    test_agent.py               # 단위 테스트: 스킬 로딩 + 에이전트 초기화 검증
```

---

## Task 1: 프로젝트 설정

**파일:**
- 생성: `lab/26_demo_for_strand_agentcore/setup/pyproject.toml`
- 생성: `lab/26_demo_for_strand_agentcore/setup/create_env.sh`

- [ ] **Step 1: 환경 설정 스크립트 실행**

```bash
cd lab/26_demo_for_strand_agentcore/setup
./create_env.sh
```

- [ ] **Step 2: 의존성 설치 확인**

```bash
cd lab/26_demo_for_strand_agentcore/setup
uv run python -c "from strands import Agent, AgentSkills; from strands_tools import http_request; from bedrock_agentcore.runtime import BedrockAgentCoreApp; print('OK')"
```
기대 출력: `OK`

- [ ] **Step 3: 커밋**

```bash
git add lab/26_demo_for_strand_agentcore/setup/
git commit -m "feat: add standup agent project setup"
```

---

## Task 2: 스킬 파일 생성

**파일:**
- 생성: `lab/26_demo_for_strand_agentcore/skills/alex/SKILL.md`
- 생성: `lab/26_demo_for_strand_agentcore/skills/maria/SKILL.md`

- [ ] **Step 1: Alex 스킬 파일 생성**

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

- [ ] **Step 2: Maria 스킬 파일 생성**

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

- [ ] **Step 3: 커밋**

```bash
git add lab/26_demo_for_strand_agentcore/skills/
git commit -m "feat: add alex and maria standup skill files"
```

---

## Task 3: 에이전트 코드 작성

**파일:**
- 생성: `lab/26_demo_for_strand_agentcore/agent.py`

- [ ] **Step 1: agent.py 작성**

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

- [ ] **Step 2: 임포트 오류 없이 실행되는지 확인**

```bash
cd lab/26_demo_for_strand_agentcore
python -c "import agent; print('Import OK')"
```
기대 출력: `Import OK`

- [ ] **Step 3: 커밋**

```bash
git add lab/26_demo_for_strand_agentcore/agent.py
git commit -m "feat: add standup agent with BedrockAgentCoreApp entrypoint"
```

---

## Task 4: 테스트 작성

**파일:**
- 생성: `lab/26_demo_for_strand_agentcore/tests/test_agent.py`

- [ ] **Step 1: 스킬 로딩 테스트 작성**

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

- [ ] **Step 2: 테스트 실행**

```bash
cd lab/26_demo_for_strand_agentcore/setup
uv run pytest ../tests/test_agent.py -v
```
참고: Task 2에서 스킬 파일을 이미 생성했다면 이 시점에서 PASS가 정상입니다. 스킬은 코드가 아닌 데이터이므로 별도 구현 없이 바로 검증 가능합니다.

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
uv run pytest ../tests/test_agent.py -v
```
기대 출력:
```
tests/test_agent.py::test_alex_skill_loads PASSED
tests/test_agent.py::test_maria_skill_loads PASSED
tests/test_agent.py::test_alex_and_maria_have_different_instructions PASSED
3 passed
```

- [ ] **Step 4: 커밋**

```bash
git add lab/26_demo_for_strand_agentcore/tests/
git commit -m "test: verify skill files load correctly for alex and maria"
```

---

## Task 5: 로컬 데모 실행

> **사전 조건:** `repo` 및 `read:user` 권한이 있는 GitHub Personal Access Token (PAT) 필요

- [ ] **Step 1: 환경 변수 설정**

```bash
export GITHUB_TOKEN=your_github_pat_here
export DEV_NAME=alex
```

- [ ] **Step 2: Alex로 에이전트 실행**

```bash
cd lab/26_demo_for_strand_agentcore/setup
uv run python -c "
import os
os.environ['DEV_NAME'] = 'alex'
import sys; sys.path.insert(0, '..')
from agent import agent
response = agent('Write my standup for today')
print(response)
"
```
기대 결과: 터미널에 Alex의 스탠드업이 불릿 형식(Yesterday / Today / Blockers)으로 출력되며, 실제 GitHub PR이 언급됩니다.

- [ ] **Step 3: Maria로 에이전트 실행**

```bash
python -c "
import os
os.environ['DEV_NAME'] = 'maria'
# DEV_NAME은 모듈 로드 시점에 읽히므로 Maria용 에이전트를 새로 생성합니다
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
기대 결과: 터미널에 Maria의 스탠드업이 번호 목록 형식(What I shipped / What I'm building / What I need)으로 출력되며, PR 링크가 포함됩니다.

**이 시점의 데모 핵심 멘트:** "에이전트 코드는 동일한 15줄입니다. 스킬 파일만 바꿨을 뿐인데 출력이 완전히 달라졌습니다."

---

## Task 6: AgentCore Runtime 배포 설정

**파일:**
- 생성: `lab/26_demo_for_strand_agentcore/.bedrock_agentcore.yaml`

> **사전 조건:** AWS 계정, AgentCore용 IAM 역할, ECR 리포지토리 필요. 참고 설정 파일: `lab/17_bedrock_agent_core/01-tutorials/01-AgentCore-runtime/01-hosting-agent/01-strands-with-bedrock-model/.bedrock_agentcore.yaml`

- [ ] **Step 1: .bedrock_agentcore.yaml 생성**

```yaml
default_agent: standup_agent
agents:
  standup_agent:
    name: standup_agent
    entrypoint: agent.py          # 이 yaml 파일 기준 상대 경로
    platform: linux/arm64
    container_runtime: docker
    aws:
      execution_role: arn:aws:iam::ACCOUNT_ID:role/agentcore-standup-role   # 교체 필요
      execution_role_auto_create: false
      account: 'ACCOUNT_ID'       # 교체 필요
      region: us-east-1
      ecr_repository: ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-standup_agent  # 교체 필요
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: HTTP
      observability:
        enabled: true
```

- [ ] **Step 2: AgentCore Runtime에 배포**

```bash
cd lab/26_demo_for_strand_agentcore
bedrock-agentcore launch --agent standup_agent
```
기대 결과: Docker 이미지 빌드 → ECR 푸시 → 에이전트 배포 완료. 출력에 `agent_arn` 포함.

- [ ] **Step 3: 배포된 에이전트를 채팅으로 호출**

```bash
bedrock-agentcore invoke --agent standup_agent \
  --payload '{"prompt": "Write my standup for today"}' \
  --env DEV_NAME=alex GITHUB_TOKEN=$GITHUB_TOKEN
```
기대 결과: 로컬 실행과 동일한 스탠드업 출력. 이제 AgentCore Runtime에서 서빙됩니다.

- [ ] **Step 4: 커밋**

```bash
git add lab/26_demo_for_strand_agentcore/.bedrock_agentcore.yaml
git commit -m "feat: add AgentCore Runtime deployment config for standup agent"
```

---

## 데모 스크립트 (5분)

| 시간 | 발표자가 할 것 |
|---|---|
| 0:00–1:00 | `agent.py` 화면 공유 — "15줄이 전부입니다" |
| 1:00–2:00 | `skills/alex/SKILL.md` 열기 — "이 마크다운 파일이 Alex의 에이전트를 정의합니다" |
| 2:00–3:00 | Alex로 로컬 실행 → 스탠드업 출력 |
| 3:00–3:30 | `skills/maria/SKILL.md` 열기 — "Maria의 파일은 다릅니다" |
| 3:30–4:00 | Maria로 실행 → 다른 형식으로 출력 — "코드는 바꾸지 않았습니다" |
| 4:00–5:00 | `bedrock-agentcore invoke` 실행 → 동일한 결과 — "이제 팀 서비스입니다" |
