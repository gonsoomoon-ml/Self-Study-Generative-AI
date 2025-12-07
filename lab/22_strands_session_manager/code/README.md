# Session Management Demo Code

Demo Python files for Tutorial 1: Introduction to Session Management.

## Setup

```bash
cd /home/ubuntu/Self-Study-Generative-AI/lab/22_strands_session_manager

# If not already set up, run:
cd setup && ./create_env.sh customer_chat 3.11 && cd ..
```

## Run Demos

Run demos in order to understand session management concepts:

```bash
# Demo 1: See the problem - agent forgets everything after restart
uv run python code/demo1_no_session.py

# Demo 2: See the solution - session manager preserves memory
uv run python code/demo2_with_session.py

# Demo 3: Inspect what's stored in session files (run after demo2)
uv run python code/demo3_inspect_storage.py

# Demo 4: Multiple users with isolated sessions
uv run python code/demo4_multiple_users.py

# Demo 5: Store custom data in agent.state
uv run python code/demo5_agent_state.py

# Demo 6: Clean up session data (interactive)
uv run python code/demo6_cleanup.py
```

## Demo Overview

| Demo | File | Concept |
|------|------|---------|
| 1 | `demo1_no_session.py` | Memory loss without sessions |
| 2 | `demo2_with_session.py` | Memory persistence with FileSessionManager |
| 3 | `demo3_inspect_storage.py` | View session file structure |
| 4 | `demo4_multiple_users.py` | Isolated sessions per user |
| 5 | `demo5_agent_state.py` | Custom state persistence |
| 6 | `demo6_cleanup.py` | Delete session data |

## Session Storage

Sessions are stored in `./sessions/` directory:

```
sessions/
├── session_user-alice-demo/
│   ├── session.json
│   └── agents/
│       └── agent_xxx/
│           ├── agent.json
│           └── messages/
├── session_user-bob/
├── session_user-carol/
└── ...
```
