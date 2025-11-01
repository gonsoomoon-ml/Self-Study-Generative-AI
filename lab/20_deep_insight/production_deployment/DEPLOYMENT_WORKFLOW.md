# 🔄 두 계정 배포 워크플로우 가이드

> **목표**: Development 계정에서 파일 생성 → Git 푸시 → Production 계정에서 다운로드 및 배포

---

## 📋 목차

1. [개요](#개요)
2. [Phase A: Development 계정 작업](#phase-a-development-계정-작업)
3. [Phase B: Git Repository 작업](#phase-b-git-repository-작업)
4. [Phase C: Production 계정 작업](#phase-c-production-계정-작업)
5. [트러블슈팅](#트러블슈팅)

---

## 🎯 개요

### 워크플로우 흐름

```
┌─────────────────────────────────────────────────────────────┐
│ 🔧 Development 계정                                          │
│ /home/ubuntu/.../production_deployment/                     │
│                                                              │
│ 1. 스크립트 생성 및 수정                                       │
│    - setup/vpc 스크립트를 Single-AZ로 변환                    │
│    - CloudFormation 템플릿 준비                               │
│    - 파라미터 파일 생성                                        │
│                                                              │
│ 2. 로컬 테스트 (선택)                                         │
│    - 개발 계정에서 스크립트 실행 테스트                         │
│    - 검증 후 리소스 정리                                       │
│                                                              │
│ 3. Git에 커밋 및 푸시                                         │
│    git add .                                                │
│    git commit -m "Add production deployment scripts"       │
│    git push origin master                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Git Push
                 ▼
         ┌──────────────┐
         │  📦 Git Repo │
         │  (GitHub)    │
         └──────┬───────┘
                 │
                 │ Git Clone/Pull
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 🚀 Production 계정 (새로운 AWS 계정)                          │
│                                                              │
│ 1. Git Repository Clone                                     │
│    git clone https://github.com/...                         │
│                                                              │
│ 2. AWS 환경 설정                                              │
│    aws configure (새 계정 자격증명)                           │
│                                                              │
│ 3. 배포 스크립트 실행                                         │
│    cd production_deployment                                 │
│    ./scripts/deploy-all.sh                                  │
│                                                              │
│ 4. 테스트 및 검증                                             │
│    ./scripts/test-deployment.sh                             │
└─────────────────────────────────────────────────────────────┘
```

### 각 계정의 역할

| 계정 | 역할 | 주요 작업 |
|------|------|----------|
| **Development** | 개발 및 준비 | - 스크립트 작성<br>- 템플릿 생성<br>- 문서 작성<br>- Git 관리 |
| **Production** | 테스트 및 운영 | - Git clone<br>- 스크립트 실행<br>- 인프라 배포<br>- 실제 서비스 운영 |

---

## Phase A: Development 계정 작업

> **위치**: 현재 폴더 (`production_deployment/`)
> **목표**: 배포에 필요한 모든 파일을 준비하고 Git에 푸시

### A1. 기존 스크립트 확인

현재 `setup/vpc/` 폴더에 이미 VPC 설정 스크립트가 있습니다:

```bash
cd /home/ubuntu/aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2

# 기존 스크립트 확인
ls -la setup/vpc/1_setup/    # new_vpc.sh, test_vpc.sh
ls -la setup/vpc/2_test/     # connectivity.py, private_connectivity.py
ls -la setup/vpc/3_cleanup/  # cleanup 스크립트들
```

**문제점**: 현재 스크립트는 **Multi-AZ (us-east-1a + us-east-1c)** 구성입니다.
**해결책**: **Single-AZ (us-east-1a)** 로 수정해야 합니다.

### A2. 스크립트를 Single-AZ로 수정

#### A2.1 인프라 배포 스크립트 생성

`production_deployment/scripts/deploy-infrastructure.sh` 생성:
- `setup/vpc/1_setup/new_vpc.sh`를 기반으로 수정
- Subnet 4개 → 2개로 변경 (Private 1개, Public 1개)
- us-east-1a만 사용

#### A2.2 Fargate Runtime 배포 스크립트 생성

`production_deployment/scripts/deploy-fargate-runtime.sh` 생성:
- Docker 이미지 빌드
- ECR에 푸시
- ECS Task Definition 등록
- Test Task 실행

#### A2.3 AgentCore Runtime 배포 스크립트 생성

`production_deployment/scripts/deploy-agentcore-runtime.sh` 생성:
- `.bedrock_agentcore.yaml` 생성 (VPC 모드)
- Runtime 배포
- ENI 확인

#### A2.4 통합 배포 스크립트 생성

`production_deployment/scripts/deploy-all.sh` 생성:
- 전체 Phase를 순차 실행
- 각 단계 완료 확인
- 오류 시 중단

#### A2.5 정리 스크립트 생성

`production_deployment/scripts/cleanup-all.sh` 생성:
- 모든 리소스를 역순으로 삭제

### A3. 파라미터 파일 생성

#### A3.1 Production 환경 파라미터

`production_deployment/parameters/prod-params.json`:

```json
{
  "Environment": "prod",
  "ProjectName": "bedrock-manus",
  "Region": "us-east-1",
  "AvailabilityZone": "us-east-1a",

  "VpcCidr": "10.0.0.0/16",
  "PrivateSubnetCidr": "10.0.1.0/24",
  "PublicSubnetCidr": "10.0.11.0/24",

  "ClusterName": "bedrock-manus-cluster",
  "AlbName": "bedrock-manus-alb",
  "TargetGroupName": "bedrock-manus-tg",

  "EcrRepositoryName": "bedrock-manus-fargate-runtime",
  "TaskDefinitionName": "bedrock-manus-task",

  "S3BucketName": "bedrock-logs-prod-REPLACE_WITH_ACCOUNT_ID"
}
```

**⚠️ 중요**: `REPLACE_WITH_ACCOUNT_ID`는 스크립트가 자동으로 치환합니다.

#### A3.2 환경 변수 템플릿

`production_deployment/.env.template`:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=

# Project Configuration
PROJECT_NAME=bedrock-manus
ENVIRONMENT=prod

# VPC Configuration (populated after Phase 1)
VPC_ID=
PRIVATE_SUBNET_ID=
PUBLIC_SUBNET_ID=
SG_AGENTCORE_ID=
SG_ALB_ID=
SG_FARGATE_ID=
SG_VPCE_ID=

# ALB Configuration (populated after Phase 1)
ALB_ARN=
ALB_DNS=
TARGET_GROUP_ARN=

# ECS Configuration (populated after Phase 2)
CLUSTER_ARN=
ECR_REPOSITORY_URI=
TASK_DEFINITION_ARN=

# AgentCore Runtime (populated after Phase 3)
RUNTIME_ID=
RUNTIME_ARN=
```

### A4. Git Repository 준비

#### A4.1 .gitignore 확인

`production_deployment/.gitignore`:

```
# Environment files
.env
deployment.env
*.env.local

# AWS credentials
.aws/
credentials

# Python
__pycache__/
*.pyc
.ipynb_checkpoints/

# Logs
*.log
logs/

# Temporary files
temp/
tmp/
artifacts/

# Runtime outputs
agentcore-runtime/

# Mac
.DS_Store
```

#### A4.2 README 확인

현재 `production_deployment/README.md`가 이미 존재합니다.
- 추가로 `DEPLOYMENT_WORKFLOW.md` (이 파일) 생성

### A5. 개발 계정에서 테스트 (선택 사항)

배포 전 개발 계정에서 스크립트를 테스트할 수 있습니다:

```bash
cd production_deployment

# 1. 인프라 배포 테스트
./scripts/deploy-infrastructure.sh

# 2. 리소스 확인
aws cloudformation describe-stacks --stack-name bedrock-manus-infrastructure-dev

# 3. 정리
./scripts/cleanup-all.sh
```

**⚠️ 주의**: 테스트 후 반드시 리소스를 정리하세요 (비용 발생).

### A6. Git에 커밋 및 푸시

```bash
cd production_deployment

# 변경 사항 확인
git status

# 모든 파일 추가
git add .

# 커밋
git commit -m "Add production deployment scripts and guides

- Single-AZ infrastructure scripts
- Fargate runtime deployment
- AgentCore runtime setup
- Complete deployment workflow guide
- Cleanup scripts
"

# 푸시 (master 브랜치)
git push origin master
```

**✅ Development 계정 작업 완료!**

---

## Phase B: Git Repository 작업

### B1. Repository 확인

GitHub에서 다음을 확인하세요:

1. **파일 업로드 확인**:
   - `production_deployment/scripts/*.sh`
   - `production_deployment/parameters/*.json`
   - `production_deployment/docs/*.md`
   - `production_deployment/DEPLOYMENT_WORKFLOW.md`

2. **README 확인**:
   - `production_deployment/README.md`가 제대로 표시되는지

3. **Repository URL 복사**:
   ```
   https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr
   ```

---

## Phase C: Production 계정 작업

> **위치**: 새로운 AWS 계정의 EC2 또는 로컬 환경
> **목표**: Git에서 코드 다운로드 후 전체 인프라 배포

### C1. 사전 준비

#### C1.1 AWS CLI 설정

```bash
# AWS CLI 버전 확인
aws --version  # v2.0 이상 필요

# Production 계정 자격증명 설정
aws configure

# 입력:
# AWS Access Key ID: [Production 계정 Access Key]
# AWS Secret Access Key: [Production 계정 Secret Key]
# Default region name: us-east-1
# Default output format: json

# 확인
aws sts get-caller-identity
```

**예상 출력**:
```json
{
  "UserId": "AIDAXXXXXXXXX",
  "Account": "123456789012",  # Production 계정 ID
  "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

#### C1.2 필수 도구 설치

```bash
# Docker 설치 확인 (Fargate 이미지 빌드용)
docker --version

# Python 3.12+ 확인
python3 --version

# bedrock_agentcore toolkit 설치
pip install bedrock_agentcore_starter_toolkit
```

### C2. Git Repository Clone

```bash
# Repository Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git

# 프로젝트 디렉토리로 이동
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment

# 파일 확인
ls -la scripts/
ls -la parameters/
ls -la docs/
```

### C3. 환경 설정

#### C3.1 환경 변수 파일 생성

```bash
# .env.template를 .env로 복사
cp .env.template .env

# AWS Account ID 자동 입력
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/AWS_ACCOUNT_ID=/AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID/g" .env

# 확인
cat .env
```

#### C3.2 파라미터 파일 업데이트

```bash
# prod-params.json의 Account ID 자동 치환
sed -i "s/REPLACE_WITH_ACCOUNT_ID/$AWS_ACCOUNT_ID/g" parameters/prod-params.json

# 확인
cat parameters/prod-params.json
```

### C4. 전체 배포 실행

#### C4.1 통합 배포 스크립트 실행

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/*.sh

# 전체 배포 시작 (Phase 1 → 2 → 3)
./scripts/deploy-all.sh
```

**예상 소요 시간**: 약 60-90분
- Phase 1 (인프라): 30-40분
- Phase 2 (Fargate): 15-20분
- Phase 3 (AgentCore): 10-15분

#### C4.2 배포 과정 모니터링

배포 중 별도 터미널에서 모니터링:

```bash
# CloudFormation 스택 상태
watch -n 10 aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'Stacks[0].StackStatus' \
  --output text

# VPC Endpoints 상태
watch -n 10 aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State]' \
  --output table
```

### C5. 배포 후 검증

#### C5.1 인프라 확인

```bash
# 생성된 .env 파일 확인 (Phase 1 완료 후)
cat deployment.env

# VPC 확인
aws ec2 describe-vpcs \
  --filters "Name=tag:Project,Values=bedrock-manus" \
  --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Subnet 확인
aws ec2 describe-subnets \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Security Groups 확인
aws ec2 describe-security-groups \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'SecurityGroups[*].[GroupId,GroupName]' \
  --output table

# VPC Endpoints 확인 (모두 available이어야 함)
aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
  --output table

# ALB 확인
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `bedrock-manus`)].[LoadBalancerArn,DNSName,State.Code]' \
  --output table
```

#### C5.2 Fargate Runtime 확인

```bash
# ECR Repository 확인
aws ecr describe-repositories \
  --repository-names bedrock-manus-fargate-runtime

# Docker Image 확인
aws ecr describe-images \
  --repository-name bedrock-manus-fargate-runtime \
  --query 'imageDetails[*].[imageTags[0],imagePushedAt,imageSizeInBytes]' \
  --output table

# ECS Cluster 확인
aws ecs describe-clusters \
  --clusters bedrock-manus-cluster

# Task Definition 확인
aws ecs describe-task-definition \
  --task-definition bedrock-manus-task \
  --query 'taskDefinition.[family,revision,status]' \
  --output table
```

#### C5.3 AgentCore Runtime 확인

```bash
# Runtime 상태 확인
RUNTIME_ID=$(cat deployment.env | grep RUNTIME_ID | cut -d'=' -f2)

aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --query 'agentRuntime.[agentRuntimeId,status,networkMode]' \
  --output table

# ENI 확인 (VPC 연결 확인)
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*bedrock*" "Name=status,Values=in-use" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,PrivateIpAddress,SubnetId]' \
  --output table
```

### C6. 테스트 실행

#### C6.1 기본 연결 테스트

```bash
# 테스트 스크립트 실행
./scripts/test-deployment.sh
```

#### C6.2 AgentCore Job 실행

```bash
# 간단한 Job 실행 (총 매출액 계산)
python3 invoke_agentcore_job.py \
  --runtime-id $RUNTIME_ID \
  --prompt "CSV 파일을 분석하고 총 매출액을 계산해주세요."

# 복잡한 Job 실행 (PDF 보고서)
python3 invoke_agentcore_job.py \
  --runtime-id $RUNTIME_ID \
  --prompt "CSV 파일을 분석하고 카테고리별 매출 분석 PDF 보고서를 생성해주세요."
```

#### C6.3 CloudWatch Logs 확인

```bash
# Fargate Runtime 로그
aws logs tail /ecs/bedrock-manus-fargate-runtime --follow

# AgentCore Runtime 로그 (observability 설정 시)
aws logs tail /aws/bedrock-agentcore/runtimes/${RUNTIME_ID} --follow
```

### C7. 배포 완료 확인

다음 체크리스트를 모두 만족하면 배포 성공입니다:

- [ ] VPC Status: `available`
- [ ] Subnet 2개 생성: Private, Public
- [ ] Security Groups 4개 생성: AgentCore, ALB, Fargate, VPC Endpoint
- [ ] VPC Endpoints 6개 모두: `available`
- [ ] NAT Gateway Status: `available`
- [ ] ALB Status: `active`
- [ ] ECS Cluster Status: `ACTIVE`
- [ ] ECR Image 푸시 완료
- [ ] Task Definition 등록 완료
- [ ] AgentCore Runtime Status: `READY`
- [ ] ENI 생성 확인 (VPC 연결)
- [ ] 테스트 Job 실행 성공

**✅ Production 계정 배포 완료!**

---

## 🔧 트러블슈팅

### 문제 1: Git Clone 실패

**증상**:
```
fatal: repository not found
```

**해결**:
1. Repository URL 확인
2. Public repository인지 확인
3. Private repository면 Personal Access Token 필요

### 문제 2: AWS CLI 권한 부족

**증상**:
```
An error occurred (AccessDenied) when calling the CreateVpc operation
```

**해결**:
```bash
# IAM User에 필요한 권한 추가:
# - AdministratorAccess (전체 권한)
# 또는:
# - VPCFullAccess
# - EC2FullAccess
# - ECSFullAccess
# - ECRFullAccess
# - BedrockAgentCoreFullAccess
# - IAMFullAccess
# - S3FullAccess
# - CloudWatchLogsFullAccess
```

### 문제 3: Docker 이미지 빌드 실패

**증상**:
```
Cannot connect to the Docker daemon
```

**해결**:
```bash
# Docker 데몬 시작
sudo systemctl start docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 로그아웃 후 재로그인
```

### 문제 4: VPC Endpoint 생성 실패

**증상**:
```
Availability Zone not supported
```

**해결**:
```bash
# 지원되는 AZ ID 확인
aws ec2 describe-vpc-endpoint-services \
  --service-name com.amazonaws.us-east-1.bedrock-agentcore-control \
  --query 'ServiceDetails[0].AvailabilityZones' \
  --output table

# 스크립트의 AZ를 지원되는 AZ로 변경
```

### 문제 5: AgentCore Runtime 생성 실패

**증상**:
```
CREATE_FAILED or UPDATE_FAILED
```

**해결**:
1. Service-Linked Role 확인:
   ```bash
   aws iam get-role --role-name AWSServiceRoleForBedrockAgentCoreNetwork
   ```

2. VPC Endpoints 상태 확인:
   ```bash
   aws ec2 describe-vpc-endpoints --filters "Name=tag:Environment,Values=prod"
   ```

3. Security Group 규칙 확인

### 문제 6: Fargate Task 시작 실패

**증상**:
```
CannotPullContainerError
```

**해결**:
```bash
# ECR 로그인 재시도
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# NAT Gateway 확인 (Private Subnet에서 ECR 접근용)
aws ec2 describe-nat-gateways \
  --filter "Name=tag:Environment,Values=prod" \
  --query 'NatGateways[*].[NatGatewayId,State]' \
  --output table

# VPC Endpoints 확인 (ECR API, ECR Docker)
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.ecr.*" \
  --query 'VpcEndpoints[*].[ServiceName,State]' \
  --output table
```

---

## 📊 비용 관리

### 운영 비용 (월간)

| 리소스 | 비용 (USD/월) |
|--------|--------------|
| NAT Gateway | ~$32.40 |
| VPC Endpoints (5개) | ~$36.00 |
| ALB | ~$16.00 |
| Fargate (10시간/월) | ~$4.00 |
| S3 + Logs | ~$3.00 |
| **총합** | **~$91.40/월** |

### 리소스 정리

사용하지 않을 때는 리소스를 정리하세요:

```bash
cd production_deployment

# 모든 리소스 삭제
./scripts/cleanup-all.sh

# 확인
aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod
```

---

## 🎯 다음 단계

### Development 계정
1. ✅ 스크립트 생성 및 수정
2. ✅ Git에 푸시
3. 🔄 Production 계정 피드백 받아 개선

### Production 계정
1. ✅ Git Clone 및 배포
2. ✅ 운영 환경 설정
3. 🚀 실제 서비스 시작

---

**작성일**: 2025-11-01
**버전**: 1.0.0
**작성자**: Claude Code
