# Deep Insight - 프로덕션 배포 가이드

> **Bedrock AgentCore Multi-Agent System**을 프로덕션 AWS 환경에 배포하기 위한 CloudFormation 기반 완전한 가이드

---

## 🎯 개요

이 디렉토리는 Deep Insight Multi-Agent System을 프로덕션 AWS 환경에 배포하기 위한 **Phase 1 인프라**를 CloudFormation Nested Stacks로 구현한 것입니다.

**주요 특징**:
- ✅ **Infrastructure as Code**: CloudFormation으로 재현 가능한 인프라
- ✅ **Nested Stacks 아키텍처**: 모듈화된 5개의 독립적인 스택
- ✅ **VPC Private 모드**: Bedrock AgentCore VPC Endpoint 지원
- ✅ **Multi-AZ 배포**: 고가용성 (us-east-1a, us-east-1b)
- ✅ **자동화 스크립트**: S3 업로드 + Deploy & Verify 스크립트 제공
- ✅ **자동 검증**: 15개 리소스 자동 확인
- ✅ **보안 Best Practices**: Private Subnets, Security Groups, IAM 최소 권한

**현재 상태**:
- ✅ **Phase 1 완료**: VPC 인프라 (CloudFormation + Nested Stacks)
- ✅ **Phase 2 완료**: Fargate Runtime (CloudFormation + Docker, Three-Stage 배포)
- 🚀 **Phase 3 준비**: AgentCore Runtime 배포 (CloudFormation 기반)
- ⏳ **Phase 4 준비 중**: Testing

---

## 📁 폴더 구조

```
production_deployment/
│
├── 📚 README.md                                  # 이 파일 (메인 가이드)
├── 📖 DEPLOYMENT_WORKFLOW.md                     # 두 계정 배포 워크플로우
├── 📖 STEP_BY_STEP_GUIDE.md                      # Phase 1 단계별 가이드
├── 📖 CLOUDFORMATION_GUIDE.md                    # CloudFormation 상세 가이드
│
├── cloudformation/                               # ☁️ CloudFormation 템플릿
│   ├── phase1-main.yaml                          # ✅ Parent Stack (Orchestrator)
│   ├── phase2-fargate.yaml                       # ✅ Fargate Runtime (ECR, ECS, Task Definition)
│   ├── nested/                                   # 📦 Phase 1 Nested Stacks
│   │   ├── network.yaml                          # ✅ VPC, Subnets, NAT Gateway, Routes (304줄)
│   │   ├── security-groups.yaml                  # ✅ 4 Security Groups + 15 Rules (263줄)
│   │   ├── vpc-endpoints.yaml                    # ✅ 6 VPC Endpoints (Bedrock, ECR, Logs, S3) (179줄)
│   │   ├── alb.yaml                              # ✅ ALB, Target Group, Listener (121줄)
│   │   └── iam.yaml                              # ✅ Task Role, Execution Role (127줄)
│   └── parameters/
│       ├── phase1-prod-params.json               # ✅ Phase 1 파라미터
│       └── phase2-prod-params.json               # ✅ Phase 2 파라미터 (템플릿)
│
├── scripts/                                      # 🔧 자동화 스크립트
│   ├── phase1/
│   │   ├── deploy.sh                             # ✅ Phase 1 배포
│   │   ├── verify.sh                             # ✅ Phase 1 검증
│   │   ├── monitor.sh                            # ✅ 배포 모니터링
│   │   └── cleanup.sh                            # ✅ 리소스 정리
│   └── phase2/
│       ├── deploy.sh                             # ✅ Phase 2 배포 (Docker 빌드 + ECR 푸시)
│       ├── verify.sh                             # ✅ Phase 2 검증
│       └── cleanup.sh                            # ✅ 리소스 정리
│
├── docs/                                         # 📚 상세 가이드
│   ├── 00_OVERVIEW.md                            # 전체 아키텍처 및 개요
│   ├── 02_FARGATE_RUNTIME.md                     # Phase 2 (예정)
│   ├── 03_AGENTCORE_RUNTIME.md                   # Phase 3 (예정)
│   └── 04_TESTING.md                             # Phase 4 (예정)
│
└── .env                                          # (배포 시 자동 생성) 리소스 ID 저장
```

### Nested Stacks 구조

```
phase1-main.yaml (Parent Stack)
├── NetworkStack           # VPC, 4 Subnets, NAT, Routes
├── SecurityGroupsStack    # 4 Security Groups + 15 Rules
├── VPCEndpointsStack      # Bedrock, ECR, Logs, S3 Endpoints
├── ALBStack               # Internal ALB + Target Group
└── IAMStack               # Task Role + Execution Role
```

---

## 🚀 빠른 시작 (5분)

### 1단계: 사전 요구사항

```bash
# AWS CLI 확인 (v2.0 이상)
aws --version

# AWS 자격증명 설정
aws configure

# 계정 확인
aws sts get-caller-identity
```

### 2단계: Git Clone

```bash
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment
```

### 3단계: Phase 1 배포 (30-40분)

```bash
# 실행 권한 부여
chmod +x scripts/phase1/*.sh

# Phase 1 배포
./scripts/phase1/deploy.sh prod
```

### 4단계: 검증 (2-3분)

```bash
# 자동 검증 (15개 리소스 체크)
./scripts/phase1/verify.sh
```

**✅ 성공 시 출력**:
```
Total Checks:  15
Passed:        15

✓ All checks passed!
```

### 5단계: 환경 설정 (1분) - 선택사항

CloudFormation 배포 후, **프로젝트 루트**에 `.env` 파일을 자동으로 생성할 수 있습니다:

```bash
# 자동 생성 (권장) - 프로젝트 루트에 .env 생성
cd production_deployment/scripts
./setup_env.sh prod
```

**수동 설정**:
```bash
# 프로젝트 루트로 이동
cd /path/to/05_insight_extractor_strands_sdk_workshop_phase_2

# 템플릿 복사
cp production_deployment/.env.example .env

# .env 파일 편집 (CloudFormation outputs 값 입력)
vi .env
```

**주요 환경 변수**:
- `OTEL_*`: OpenTelemetry 설정 (per-invocation 로그 스트림)
- `AWS_REGION`, `AWS_ACCOUNT_ID`: AWS 계정 정보
- `VPC_ID`, `PRIVATE_SUBNET_*_ID`: Phase 1 네트워크 리소스
- `ECS_CLUSTER_NAME`, `ECR_REPOSITORY_URI`: Phase 2 Fargate 리소스
- `FARGATE_SUBNET_IDS`, `FARGATE_SECURITY_GROUP_IDS`: Fargate 네트워크 설정
- `RUNTIME_ARN`: Phase 3에서 생성됨

---

## 🔧 Environment Setup

### Quick Start (Automated)

`setup_env.sh` 스크립트는 CloudFormation Stack Outputs에서 자동으로 `.env` 파일을 생성합니다:

```bash
cd production_deployment/scripts
./setup_env.sh prod
```

**스크립트 기능**:
- ✅ AWS 계정 ID 및 리전 자동 감지
- ✅ Phase 1 CloudFormation Stack Outputs 읽기 (15개 변수)
- ✅ Phase 2 CloudFormation Stack Outputs 읽기 (7개 변수, 배포된 경우)
- ✅ OTEL 설정 자동 추가 (6개 변수)
- ✅ 기존 `RUNTIME_ARN` 보존 (이미 생성된 경우)
- ✅ `.env` 파일을 **프로젝트 루트**에 생성

**Expected Output**:
```
============================================
Environment Setup - Auto-generate .env
Environment: prod
============================================

✓ Detected AWS Account: 738490718699
✓ Detected AWS Region: us-east-1
✓ Phase 1 stack status: CREATE_COMPLETE
✓ Phase 2 stack status: CREATE_COMPLETE
✓ Reading Phase 1 CloudFormation outputs...
✓ Phase 1: 15 variables
✓ Reading Phase 2 CloudFormation outputs...
✓ Phase 2: 7 variables
✓ Generated .env at: /path/to/project-root/.env

============================================
Summary
============================================
✓ Total variables: 35
  - OTEL: 6 variables
  - AWS Config: 4 variables
  - Phase 1: 15 variables
  - Phase 2: 7 variables
  - S3 Bucket: 1 variable
  - Runtime: 3 variables (empty, to be populated)

✓ Environment setup complete!

Next steps:
  1. Deploy Phase 3: cd production_deployment && python 01_create_agentcore_runtime.py
  2. Test Runtime: cd production_deployment && python 03_invoke_agentcore_job_vpc.py
```

### Manual Setup

`.env.example` 템플릿을 복사하여 수동으로 설정할 수도 있습니다:

```bash
cp .env.example .env
vi .env
```

**필수 값 확인** (CloudFormation Outputs에서):
```bash
# Phase 1 Outputs 확인
aws cloudformation describe-stacks \
  --stack-name deep-insight-infrastructure-prod \
  --query 'Stacks[0].Outputs' \
  --output json

# Phase 2 Outputs 확인
aws cloudformation describe-stacks \
  --stack-name deep-insight-fargate-prod \
  --query 'Stacks[0].Outputs' \
  --output json
```

**주요 섹션**:
1. **OTEL Configuration** (6 variables): Per-invocation 로그 스트림 활성화
2. **AWS Configuration** (4 variables): 계정 ID, 리전, Bedrock 모델
3. **Phase 1 Infrastructure** (15 variables): VPC, Subnets, Security Groups, ALB, IAM Roles
4. **Phase 2 Fargate Runtime** (7 variables): ECR, ECS Cluster, Task Definition
5. **Phase 3 Runtime** (3 variables): Runtime ARN (배포 후 자동 입력)

---

## 📖 상세 가이드

### 빠른 참조

| 목적 | 문서 | 소요 시간 |
|------|------|-----------|
| **빠르게 시작** | [PHASE1_QUICKSTART.md](./PHASE1_QUICKSTART.md) | 5분 읽기 |
| **단계별 배포** | [STEP_BY_STEP_GUIDE.md](./STEP_BY_STEP_GUIDE.md) | 10분 읽기 |
| **두 계정 워크플로우** | [DEPLOYMENT_WORKFLOW.md](./DEPLOYMENT_WORKFLOW.md) | 15분 읽기 |
| **CloudFormation 상세** | [CLOUDFORMATION_GUIDE.md](./CLOUDFORMATION_GUIDE.md) | 20분 읽기 |

### Phase별 가이드

#### ✅ Phase 1: 인프라 배포 (완료)
→ **[STEP_BY_STEP_GUIDE.md](./STEP_BY_STEP_GUIDE.md)**

**생성 리소스** (30-40분):
- VPC (10.0.0.0/16)
- Private Subnet (10.0.1.0/24, us-east-1a)
- Public Subnet (10.0.11.0/24, us-east-1a)
- NAT Gateway + Internet Gateway
- Security Groups 4개 (AgentCore, ALB, Fargate, VPC Endpoint)
- VPC Endpoints 6개 (Bedrock AgentCore x2, ECR API, ECR Docker, CloudWatch Logs, S3 Gateway)
- Internal ALB + Target Group
- IAM Roles (Task Execution, Task Role)

**배포 방법**:
```bash
./scripts/phase1/deploy.sh prod
./scripts/phase1/verify.sh
```

#### ✅ Phase 2: Fargate Runtime (완료)
→ **[02_FARGATE_RUNTIME.md](./docs/02_FARGATE_RUNTIME.md)**

**생성 리소스** (10-15분):
- ECR Repository (이미지 스캔, AES256 암호화, DeletionPolicy: Retain)
- Docker 이미지 (Python 3.12 + 한글 폰트 + 필수 패키지)
- ECS Cluster (Container Insights 활성화)
- ECS Task Definition (2 vCPU, 4GB RAM)
- CloudWatch Log Group (7일 보관)

**배포 방법**:
```bash
./scripts/phase2/deploy.sh prod   # Three-Stage 자동 배포
./scripts/phase2/verify.sh        # 12개 항목 검증
```

**특징**:
- ✅ **완전한 IaC**: CloudFormation이 모든 리소스 관리
- ✅ **Three-Stage 배포**: ECR 생성 → Docker 빌드/푸시 → ECS 배포
- ✅ **재현 가능**: 어떤 계정에서도 동일하게 작동
- ✅ **데이터 보호**: ECR은 DeletionPolicy: Retain으로 보호

#### ✅ Phase 3: AgentCore Runtime (준비 완료)
→ **[03_AGENTCORE_RUNTIME.md](./docs/03_AGENTCORE_RUNTIME.md)**

**배포 작업** (10-15분):
- AgentCore Runtime 생성 (VPC 모드)
- Docker 이미지 빌드 (CodeBuild)
- ECR 푸시 및 Runtime 배포
- ENI 생성 및 상태 검증

**배포 방법**:
```bash
# 1. 프로젝트로 이동
cd /path/to/05_insight_extractor_strands_sdk_workshop_phase_2

# 2. uv 환경 설정
cd setup
uv sync
./patch_dockerignore_template.sh  # coordinator.md 포함 (필수!)

# 3. .env 파일 확인 (Phase 1/2에서 자동 생성됨)
cd ../production_deployment
cat .env  # VPC_ID, SUBNET_ID 등 Phase 1/2 출력값 확인

# 4. Runtime 배포
cd ..
python3 01_create_agentcore_runtime.py
```

**특징**:
- ✅ **Native launch() 메서드**: AWS CLI 우회 방식 불필요
- ✅ **VPC Private 모드**: VPC Endpoint 통한 안전한 통신
- ✅ **자동 CodeBuild Role**: Toolkit이 자동 생성/재사용
- ✅ **coordinator.md 포함**: Patch script로 프롬프트 파일 자동 포함

**현재 상태**: 프로덕션 배포 준비 완료 ✅

#### ⏳ Phase 4: 테스트 및 검증 (예정)
→ **[04_TESTING.md](./docs/04_TESTING.md)**

**예정 작업** (10-30분):
- 네트워크 연결 테스트
- 간단한 Job 실행 (총 매출액 계산)
- 복잡한 Job 실행 (PDF 보고서)
- 성능 검증 및 로그 확인

**현재 상태**: Phase 1 완료 후 진행 예정

---

## 🏗️ 아키텍처 (Phase 1)

### 네트워크 구조

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                            │
└──────────────────────┬──────────────────────────────────┘
                       │
                  ┌────▼─────┐
                  │   IGW    │
                  └────┬─────┘
                       │
         ┌─────────────▼─────────────┐
         │  VPC (10.0.0.0/16)        │
         │  us-east-1a (Single-AZ)   │
         │                            │
         │  ┌──────────────────────┐ │
         │  │ Public Subnet        │ │
         │  │ 10.0.11.0/24         │ │
         │  │                      │ │
         │  │  ┌─────────────┐    │ │
         │  │  │ NAT Gateway │    │ │
         │  │  └─────────────┘    │ │
         │  └──────────────────────┘ │
         │           │                │
         │  ┌────────▼─────────────┐ │
         │  │ Private Subnet       │ │
         │  │ 10.0.1.0/24          │ │
         │  │                      │ │
         │  │  ┌───────────────┐  │ │
         │  │  │ Internal ALB  │  │ │
         │  │  └───────────────┘  │ │
         │  │                      │ │
         │  │  ┌───────────────┐  │ │
         │  │  │ VPC Endpoints │  │ │
         │  │  │ (6개)          │  │ │
         │  │  └───────────────┘  │ │
         │  └──────────────────────┘ │
         └────────────────────────────┘
```

### VPC Endpoints

| Service | Type | 목적 |
|---------|------|------|
| `bedrock-agentcore-control` | Interface | AgentCore Runtime 관리 |
| `bedrock-agentcore` | Interface | AgentCore Data Plane |
| `ecr.api` | Interface | ECR 이미지 메타데이터 |
| `ecr.dkr` | Interface | ECR 이미지 다운로드 |
| `logs` | Interface | CloudWatch Logs 전송 |
| `s3` | Gateway | S3 접근 (무료) |

---

## 📊 비용 (월간 예상)

### Phase 1: 인프라

| 리소스 | 수량 | 비용 (USD/월) | 비고 |
|--------|------|--------------|------|
| NAT Gateway | 1 | ~$32.40 | $0.045/시간 |
| VPC Endpoints (Interface) | 5 | ~$36.00 | $0.01/시간/endpoint |
| VPC Endpoint (Gateway) | 1 | $0 | S3 무료 |
| ALB | 1 | ~$16.00 | $0.0225/시간 |
| **Phase 1 총합** | - | **~$84.40/월** | 24/7 실행 시 |

### Phase 2: Fargate Runtime

| 리소스 | 수량 | 비용 (USD/월) | 비고 |
|--------|------|--------------|------|
| ECR Repository | 1 | ~$0.10 | 저장 용량에 따라 |
| ECS Cluster | 1 | $0 | 클러스터 자체는 무료 |
| Fargate Task | 변동 | ~$0.04/시간 | 실행 중일 때만 과금 |
| CloudWatch Logs | 1 | ~$0.50 | 로그 저장 및 ingestion |
| **Phase 2 총합** | - | **~$0.60/월** | Task 미실행 시 |

### 전체 비용

| Phase | 비용 (USD/월) |
|-------|--------------|
| Phase 1 (인프라) | ~$84.40 |
| Phase 2 (Runtime, Task 미실행) | ~$0.60 |
| **전체 총합 (Task 미실행)** | **~$85.00/월** |

**Fargate Task 실행 시 추가 비용**:
- 2 vCPU, 4GB RAM: $0.04/시간
- 24/7 실행 시: $29/월 추가
- On-demand 실행 권장 (필요할 때만)

**비용 절감 팁**:
- 개발/테스트 환경: 사용 후 스택 삭제
- NAT Gateway 대안: VPC Endpoints만 사용
- Fargate Task: On-demand 실행 (24/7 실행 불필요)
- 정리 명령어:
  ```bash
  ./scripts/phase2/cleanup.sh prod  # Phase 2 정리
  ./scripts/phase1/cleanup.sh prod  # Phase 1 정리
  ```

---

## 🔧 주요 명령어

### Phase 1: 인프라 배포

```bash
# 배포 (30-40분)
./scripts/phase1/deploy.sh prod

# 실시간 모니터링 (선택 사항)
./scripts/phase1/monitor.sh prod

# 검증 (23개 체크)
./scripts/phase1/verify.sh

# 수동 확인
cat .env
aws cloudformation describe-stacks --stack-name deep-insight-infrastructure-prod
```

### Phase 2: Fargate Runtime 배포

```bash
# Docker 설치 확인
docker --version

# 배포 (10-15분: Docker 빌드 + ECR 푸시 + CloudFormation)
./scripts/phase2/deploy.sh prod

# 검증 (12개 체크)
./scripts/phase2/verify.sh

# ECR 이미지 확인
aws ecr list-images \
  --repository-name deep-insight-fargate-runtime-prod \
  --region us-east-1
```

### Phase 3: AgentCore Runtime 배포

```bash
# Python/uv 설치 확인
python3 --version
uv --version

# 배포 (10-15분: setup + Docker 빌드 + Runtime 생성)
cd /path/to/05_insight_extractor_strands_sdk_workshop_phase_2

# 1. uv 환경 설정
cd setup
uv sync
./patch_dockerignore_template.sh  # coordinator.md 포함 (필수!)

# 2. .env 파일 확인 (Phase 1/2에서 자동 생성됨)
cd ../production_deployment
cat .env  # VPC_ID, SUBNET_ID 등 확인

# 3. Runtime 배포
cd ..
python3 01_create_agentcore_runtime.py

# 3. 검증
# CloudWatch Logs 확인
aws logs tail /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc --follow --region us-east-1

# 4. 테스트 (선택 사항)
python3 03_invoke_agentcore_job_vpc.py
```

**중요 참고사항**:
- ✅ **patch_dockerignore_template.sh 필수**: coordinator.md 파일 포함을 위해 반드시 실행
- ✅ **CodeBuild Role 자동 생성**: Toolkit이 첫 실행 시 자동으로 생성, 이후 재사용
- ✅ **VPC 모드**: Phase 1에서 생성한 VPC Endpoint 사용

### 정리

```bash
# Phase 2 정리
./scripts/phase2/cleanup.sh prod  # 또는 --force

# Phase 1 정리
./scripts/phase1/cleanup.sh prod  # 또는 --force

# 수동 정리 (CloudFormation)
aws cloudformation delete-stack \
  --stack-name deep-insight-fargate-prod \
  --region us-east-1

aws cloudformation delete-stack \
  --stack-name deep-insight-infrastructure-prod \
  --region us-east-1
```

---

## 🛟 트러블슈팅

### 일반적인 문제

1. **VPC Endpoint 생성 실패**:
   - AZ ID 확인 (use1-az2, use1-az4, use1-az6만 지원)
   - 해결: `cloudformation/parameters/phase1-prod-params.json`에서 AZ 변경

2. **CloudFormation 배포 실패**:
   - 스택 이벤트 확인:
     ```bash
     aws cloudformation describe-stack-events \
       --stack-name deep-insight-infrastructure-prod \
       --max-items 50
     ```

3. **권한 부족 에러**:
   - 필수 IAM 권한: EC2FullAccess, ElasticLoadBalancingFullAccess, IAMFullAccess, CloudFormationFullAccess

자세한 트러블슈팅은 [DEPLOYMENT_WORKFLOW.md - 트러블슈팅](./DEPLOYMENT_WORKFLOW.md#트러블슈팅) 참조

---

## 📝 다음 단계

### 현재 완료
- [x] Phase 1 CloudFormation 템플릿 생성 (Nested Stacks)
- [x] Phase 1 Deploy/Verify/Cleanup 스크립트 생성
- [x] Phase 2 CloudFormation 템플릿 생성 (Three-Stage)
- [x] Phase 2 Deploy/Verify/Cleanup 스크립트 생성
- [x] Phase 3 Python 배포 스크립트 생성 (01_create_agentcore_runtime.py)
- [x] Phase 3 coordinator.md 포함 패치 스크립트 (patch_dockerignore_template.sh)
- [x] boto3/toolkit 버전 업데이트 (requirements.txt, pyproject.toml)
- [x] 가이드 문서 작성 (Phase 1-3 완전 배포 가이드)

### 다음 작업 (Phase 4 - 테스트 및 검증)
- [ ] End-to-End 테스트 스크립트 작성
- [ ] 성능 벤치마크 테스트
- [ ] 모니터링 대시보드 구성
- [ ] Production 롤아웃 체크리스트 작성

---

## 📚 참고 자료

### 공식 문서
- [AWS Bedrock AgentCore 공식 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [VPC Endpoints for Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html)
- [CloudFormation 템플릿 레퍼런스](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html)

### 프로젝트 문서
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 작업 이력
- [docs/00_OVERVIEW.md](./docs/00_OVERVIEW.md) - 전체 아키텍처 개요

---

## 🤝 기여

이슈 및 개선 제안은 [GitHub Issues](https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr/issues)에 등록해 주세요.

---

**작성일**: 2025-11-02
**버전**: 2.0.0 (CloudFormation Phase 1)
**작성자**: Claude Code
**라이선스**: MIT

---

## 📞 지원

질문이나 이슈가 있으면:
1. [DEPLOYMENT_WORKFLOW.md - 트러블슈팅](./DEPLOYMENT_WORKFLOW.md#트러블슈팅) 확인
2. [GitHub Issues](https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr/issues) 등록
3. AWS Support 문의 (계정 관련 이슈)
