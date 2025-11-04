# Deep Insight: Multi-Agent Data Analysis System

> AWS Bedrock AgentCore Runtime으로 구현한 자동화된 데이터 분석 시스템

---

## 🎯 Overview

CSV 데이터를 분석하여 인사이트를 추출하고 PDF 보고서를 자동 생성하는 Multi-Agent 시스템입니다.

**주요 기능**:
- 📊 데이터 분석 및 계산 (Coder Agent)
- ✅ 결과 검증 및 인용 생성 (Validator Agent)
- 📄 PDF 보고서 자동 생성 (Reporter Agent)
- 🔒 VPC Private 모드 지원

**Architecture**:
- AgentCore Runtime (VPC Private)
- Fargate Containers (Dynamic execution)
- Multi-Agent Workflow (Coordinator)
- Strands SDK Integration

---

## 🚀 Quick Start

### Production Deployment (프로덕션 배포)

프로덕션 계정에 전체 시스템을 배포하려면:

```bash
cd production_deployment
./scripts/phase1/deploy.sh prod  # VPC, ALB, IAM (30-40분)
./scripts/phase2/deploy.sh prod  # ECR, Docker, ECS (15-20분)
```

Phase 3 (AgentCore Runtime):
```bash
cd setup
./create-uv-env.sh deep-insight  # 완전 환경 구성 (UV, 폰트, 시스템 패키지)
./patch_dockerignore_template.sh

cd ..
python3 01_create_agentcore_runtime.py  # Runtime 배포 (10-15분)
```

**📚 상세 가이드**: [`production_deployment/README.md`](production_deployment/README.md)

**🎯 Phase 3 빠른 시작**: [`production_deployment/PHASE3_QUICKSTART.md`](production_deployment/PHASE3_QUICKSTART.md)

---

## 📁 Project Structure

```
.
├── production_deployment/       # 🏗️ CloudFormation 배포 (Phase 1-3)
│   ├── README.md                # 메인 배포 가이드 ⭐
│   ├── PHASE3_QUICKSTART.md     # Phase 3 빠른 시작
│   ├── CHANGELOG.md             # 버전 히스토리
│   ├── cloudformation/          # CloudFormation 템플릿
│   ├── scripts/                 # 배포/검증 스크립트
│   └── docs/                    # 상세 가이드
│
├── src/                         # 🤖 Agent 소스 코드
│   ├── graph/                   # LangGraph workflow
│   ├── tools/                   # Fargate tools
│   ├── prompts/                 # Agent prompts
│   └── utils/                   # Utilities
│
├── setup/                       # 🔧 환경 설정
│   ├── pyproject.toml           # Python 의존성 (uv)
│   └── patch_dockerignore_template.sh  # coordinator.md 포함
│
├── 01_create_agentcore_runtime.py  # Phase 3: Runtime 생성
├── 02_agentcore_runtime.py         # Runtime 엔트리포인트
├── 03_invoke_agentcore_job_vpc.py  # Runtime 테스트
│
├── DEV_ACCOUNT_GUIDE.md         # 개발 계정 가이드
└── README.md                    # 이 파일
```

---

## 📚 Documentation

### 배포 가이드
- **[production_deployment/README.md](production_deployment/README.md)** - 전체 배포 가이드 (Phase 1-3)
- **[production_deployment/PHASE3_QUICKSTART.md](production_deployment/PHASE3_QUICKSTART.md)** - Phase 3 빠른 시작
- **[production_deployment/DEPLOYMENT_WORKFLOW.md](production_deployment/DEPLOYMENT_WORKFLOW.md)** - 두 계정 워크플로우
- **[production_deployment/CHANGELOG.md](production_deployment/CHANGELOG.md)** - 버전 히스토리

### 기술 문서
- **[production_deployment/docs/00_OVERVIEW.md](production_deployment/docs/00_OVERVIEW.md)** - 아키텍처 개요

### 개발자 가이드
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - 기여 가이드
- **[docs_archive/DEV_ACCOUNT_GUIDE.md](docs_archive/DEV_ACCOUNT_GUIDE.md)** - 개발 계정 가이드

### 상세 가이드 (Archive)
- **[production_deployment/docs/archive/](production_deployment/docs/archive/)** - Phase별 상세 가이드
  - CloudFormation 상세
  - Fargate Runtime 가이드
  - AgentCore Runtime 가이드
  - Testing 가이드

---

## 🔑 Key Features

### Phase 1: Infrastructure (완료 ✅)
- VPC (10.0.0.0/16) + Multi-AZ Subnets
- Internal ALB + Security Groups
- VPC Endpoints (6개) - Private 통신
- IAM Roles (Task Role, Execution Role)

### Phase 2: Fargate Runtime (완료 ✅)
- ECR Repository (DeletionPolicy: Retain)
- Docker Image (Python 3.12 + 한글 폰트)
- ECS Cluster (Container Insights)
- Task Definition (2 vCPU, 4GB RAM)

### Phase 3: AgentCore Runtime (완료 ✅)
- Native `Runtime.launch()` 사용
- VPC Private 모드
- coordinator.md 자동 포함
- boto3 1.40.65 + toolkit 0.1.28

---

## 💡 Getting Started (개발)

### Prerequisites
```bash
# Python 3.12+ (Required - project uses >=3.12)
python3 --version

# uv 설치 (create-uv-env.sh will auto-install if missing)
curl -LsSf https://astral.sh/uv/install.sh | sh

# AWS CLI 설정
aws configure
```

### Development Setup
```bash
# 1. Clone repository
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2

# 2. Setup environment (complete setup)
cd setup
./create-uv-env.sh deep-insight  # Full setup: UV, fonts, system packages
./patch_dockerignore_template.sh

# 3. Configure .env
cd ../production_deployment
cp .env.example .env
vi .env  # Phase 1/2 출력값으로 업데이트

# 4. Deploy Runtime
cd ..
python3 01_create_agentcore_runtime.py

# 5. Test
python3 03_invoke_agentcore_job_vpc.py
```

**개발 가이드**: [DEV_ACCOUNT_GUIDE.md](DEV_ACCOUNT_GUIDE.md)

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AWS Bedrock (User)                                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  AgentCore Runtime (VPC Private)                        │
│  - Coordinator (LangGraph)                              │
│  - Multi-Agent Workflow                                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Internal ALB (Private)                                 │
│  - Target Group (Fargate)                               │
│  - Health Check                                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Fargate Containers (Private Subnet)                    │
│  - Python Code Execution                                │
│  - Dynamic Scaling                                      │
│  - Session Management                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr/issues)
- **Documentation**: [production_deployment/README.md](production_deployment/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📝 License

MIT License - See [LICENSE](LICENSE)

---

**Last Updated**: 2025-11-04
**Version**: 3.0.0 (Phase 3 완료)
**Status**: ✅ Production Ready
