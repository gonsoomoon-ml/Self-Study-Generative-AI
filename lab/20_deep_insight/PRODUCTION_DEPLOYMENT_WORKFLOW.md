# Production Deployment Workflow

## 📋 Overview

This document describes how to deploy the AgentCore Runtime from **Development Account** to **Production Account**.

---

## 🔄 Deployment Workflow

### Development Account (준비)

#### 1. 코드 변경 및 테스트
```bash
# Make changes
vi src/prompts/coordinator.md

# Test locally
cd setup
uv sync
./patch_dockerignore_template.sh
cd ..
uv run 01_test_launch_with_latest_boto3.py
```

#### 2. Git 커밋 (중요 파일만)
```bash
git add setup/patch_dockerignore_template.sh
git add setup/README_PRODUCTION_SETUP.md
git add setup/pyproject.toml
git add src/prompts/*.md
git add src/utils/strands_sdk_utils.py
git add requirements.txt
git add .dockerignore

# ⚠️ 커밋하지 말 것:
# - setup/.venv/ (이미 .gitignore에 있음)
# - production_deployment/.env (계정별로 다름)
# - *.log, /tmp/*, artifacts/

git commit -m "feat: Fix coordinator.md inclusion in Docker builds

- Add patch script for dockerignore.template
- Update langchain import to langchain_core
- Add production setup documentation"

git push origin master
```

---

### Production Account (배포)

#### 1. 저장소 클론
```bash
git clone <repository-url>
cd 05_insight_extractor_strands_sdk_workshop_phase_2
```

#### 2. 의존성 설치 + 패치 적용
```bash
cd setup
uv sync
./patch_dockerignore_template.sh
```

**예상 출력**:
```
🔧 Patching dockerignore.template to include src/prompts/*.md files...
📄 Backup created: ...
✅ Patch applied successfully!
```

#### 3. 환경 설정 파일 생성
```bash
cd ../production_deployment

# Phase 1, 2 완료 후 .env 파일 업데이트
vi .env
```

**.env 예시**:
```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<PRODUCTION_ACCOUNT_ID>

VPC_ID=vpc-xxxxx
PRIVATE_SUBNET_ID=subnet-xxxxx
SG_AGENTCORE_ID=sg-xxxxx

TASK_EXECUTION_ROLE_ARN=arn:aws:iam::<ACCOUNT>:role/agentcore-xxx

ALB_DNS=internal-xxx.elb.amazonaws.com
```

#### 4. Runtime 배포
```bash
cd ..  # Back to project root
uv run 01_test_launch_with_latest_boto3.py
```

#### 5. 검증
```bash
# CloudWatch Logs 확인
aws logs tail /aws/bedrock-agentcore/runtimes/<RUNTIME_NAME> \
  --log-stream-name-prefix "2025/11/04/[runtime-logs]" \
  --follow

# coordinator.md 에러가 없는지 확인:
# ✅ "===== Coordinator started ====="
# ✅ "===== Coordinator completed ====="
# ❌ "FileNotFoundError: coordinator.md" (없어야 함)
```

#### 6. 테스트
```bash
uv run 03_invoke_agentcore_job_vpc.py
```

---

## 📦 Git에 포함해야 할 파일

### ✅ 커밋해야 하는 파일

**Setup Scripts**:
- `setup/patch_dockerignore_template.sh` ⭐ (핵심!)
- `setup/README_PRODUCTION_SETUP.md`
- `setup/pyproject.toml`

**Source Code**:
- `src/prompts/*.md` (coordinator.md, coder.md, etc.)
- `src/utils/strands_sdk_utils.py` (langchain import 수정)
- `src/graph/*.py`
- `src/tools/*.py`
- `agentcore_runtime.py`
- `requirements.txt`

**Docker**:
- `Dockerfile`
- `.dockerignore` (프로젝트 루트)

**Documentation**:
- `README.md`
- `PRODUCTION_DEPLOYMENT_WORKFLOW.md`
- `production_deployment/docs/*.md`

### ❌ 커밋하지 말아야 할 파일

**Virtual Environment**:
- `setup/.venv/` (gitignore에 포함)
- `setup/uv.lock` (선택적)

**Credentials & Logs**:
- `production_deployment/.env` ⚠️ (계정별로 다름!)
- `.env.development`
- `*.log`
- `/tmp/*`
- `artifacts/`

**AWS 리소스 정보**:
- `backup/`
- `temp/`

---

## 🔐 보안 고려사항

### 1. .env 파일 관리
- **절대 Git에 커밋하지 말 것!**
- 각 환경(dev, staging, prod)마다 별도 .env 사용
- 템플릿만 제공: `.env.example`

**예시 .env.example**:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<YOUR_ACCOUNT_ID>

# VPC Configuration
VPC_ID=vpc-<YOUR_VPC_ID>
PRIVATE_SUBNET_ID=subnet-<YOUR_SUBNET_ID>
SG_AGENTCORE_ID=sg-<YOUR_SG_ID>

# IAM Role
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::<ACCOUNT>:role/<ROLE_NAME>

# ALB Configuration
ALB_DNS=internal-<YOUR_ALB>.elb.amazonaws.com
```

### 2. 민감 정보 스캔
배포 전에 확인:
```bash
# Secrets 스캔
git secrets --scan
# 또는
gitleaks detect
```

---

## 🆘 문제 해결

### 문제 1: coordinator.md FileNotFoundError

**증상**:
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/src/prompts/coordinator.md'
```

**원인**: Patch script를 실행하지 않음

**해결**:
```bash
cd setup
./patch_dockerignore_template.sh

# 검증
grep "!src/prompts/\*.md" .venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template

# Runtime 재배포
cd ..
uv run 01_test_launch_with_latest_boto3.py
```

### 문제 2: langchain Import Error

**증상**:
```
ModuleNotFoundError: No module named 'langchain.callbacks'
```

**원인**: langchain 0.3.x import 경로 변경

**해결**: 이미 수정됨
- `src/utils/strands_sdk_utils.py`: `from langchain_core.callbacks import ...`
- `requirements.txt`: `langchain-core>=0.3.27` 포함

### 문제 3: Patch Script 실패

**증상**:
```
❌ Error: Template file not found
```

**원인**: `uv sync` 미실행

**해결**:
```bash
cd setup
uv sync               # Dependencies 먼저 설치
./patch_dockerignore_template.sh
```

---

## 📊 체크리스트

프로덕션 배포 전 확인:

### Development Account
- [ ] 모든 변경사항 테스트 완료
- [ ] Git 커밋 (민감 정보 제외)
- [ ] Git push
- [ ] Tag 생성 (선택적): `git tag -a v1.0.0 -m "Production ready"`

### Production Account
- [ ] Git clone 완료
- [ ] `uv sync` 실행
- [ ] `patch_dockerignore_template.sh` 실행 ⭐
- [ ] Patch 검증 완료
- [ ] `.env` 파일 생성 (production 값)
- [ ] Phase 1-2 인프라 배포 완료
- [ ] Runtime 배포 성공
- [ ] CloudWatch Logs 확인 (coordinator 정상)
- [ ] End-to-end 테스트 완료

---

## 🎯 자동화 개선 (향후)

### Option 1: Makefile
```makefile
.PHONY: setup deploy test

setup:
	cd setup && uv sync && ./patch_dockerignore_template.sh

deploy:
	uv run 01_test_launch_with_latest_boto3.py

test:
	uv run 03_invoke_agentcore_job_vpc.py
```

### Option 2: CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    tags:
      - 'v*'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup dependencies
        run: |
          cd setup
          pip install uv
          uv sync
          ./patch_dockerignore_template.sh
      - name: Deploy Runtime
        env:
          AWS_REGION: ${{ secrets.AWS_REGION }}
          AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
        run: uv run 01_test_launch_with_latest_boto3.py
```

---

**Last Updated**: 2025-11-04
**Version**: 1.0.0
