# 🔄 두 계정 배포 워크플로우 가이드 (CloudFormation)

> **목표**: Development 계정에서 CloudFormation 템플릿 준비 → Git 푸시 → Production 계정에서 다운로드 및 배포

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
│ 1. CloudFormation 템플릿 준비                                 │
│    ✅ phase1-infrastructure.yaml (완료)                       │
│    ⏳ phase2, 3, 4 (Phase 1 완료 후 작업)                     │
│                                                              │
│ 2. 배포 스크립트 준비                                         │
│    ✅ scripts/phase1/deploy.sh (완료)                        │
│    ✅ scripts/phase1/verify.sh (완료)                        │
│    ⏳ phase2, 3, 4 scripts (Phase 1 완료 후 작업)            │
│                                                              │
│ 3. Git에 커밋 및 푸시                                         │
│    git add .                                                │
│    git commit -m "Add Phase 1 CloudFormation deployment"   │
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
│ 3. Phase 1 배포 (CloudFormation)                            │
│    cd production_deployment                                 │
│    ./scripts/phase1/deploy.sh                               │
│                                                              │
│ 4. Phase 1 검증                                              │
│    ./scripts/phase1/verify.sh                               │
│                                                              │
│ 5. Phase 2, 3, 4 배포 (Phase 1 완료 후)                      │
│    ⏳ 향후 진행                                               │
└─────────────────────────────────────────────────────────────┘
```

### 각 계정의 역할

| 계정 | 역할 | 주요 작업 |
|------|------|----------|
| **Development** | 개발 및 준비 | - CloudFormation 템플릿 작성<br>- 배포 스크립트 생성<br>- 문서 작성<br>- Git 관리 |
| **Production** | 테스트 및 운영 | - Git clone<br>- CloudFormation 배포<br>- 인프라 검증<br>- 실제 서비스 운영 |

---

## Phase A: Development 계정 작업

> **위치**: 현재 폴더 (`production_deployment/`)
> **목표**: CloudFormation 템플릿과 배포 스크립트를 준비하고 Git에 푸시

### A1. 현재 완료된 Phase 1 리소스 확인

**✅ 이미 준비된 파일들**:

```bash
cd production_deployment

# CloudFormation 템플릿
ls -l cloudformation/phase1-infrastructure.yaml

# Parameters 파일
ls -l cloudformation/parameters/phase1-prod-params.json

# 배포 스크립트
ls -l scripts/phase1/deploy.sh
ls -l scripts/phase1/verify.sh
```

**Phase 1 구조** (Single-AZ: us-east-1a):
- ✅ VPC (10.0.0.0/16)
- ✅ Private Subnet (10.0.1.0/24)
- ✅ Public Subnet (10.0.11.0/24)
- ✅ Internet Gateway + NAT Gateway
- ✅ Security Groups 4개 (AgentCore, ALB, Fargate, VPC Endpoint)
- ✅ VPC Endpoints 6개 (Bedrock AgentCore, ECR API, ECR Docker, Logs, S3)
- ✅ Internal ALB + Target Group
- ✅ IAM Roles (Task Execution, Task Role)

### A2. Phase 2, 3, 4 리소스 준비 (Phase 1 완료 후 작업)

**⏳ 향후 작업 예정**:

Phase 1이 Production 계정에서 성공적으로 배포되고 검증된 후에 다음 Phase들을 준비합니다:

#### Phase 2: Fargate Runtime (계획)
- `cloudformation/phase2-fargate.yaml` (ECR, ECS Cluster)
- `scripts/phase2/1-deploy-infrastructure.sh` (CloudFormation)
- `scripts/phase2/2-build-docker.sh` (Docker 빌드)
- `scripts/phase2/3-push-to-ecr.sh` (ECR 푸시)
- `scripts/phase2/4-register-task.sh` (Task Definition)
- `scripts/phase2/5-verify.sh` (검증)

#### Phase 3: AgentCore Runtime (계획)
- `scripts/phase3/1-prepare-source.sh` (소스 준비)
- `scripts/phase3/2-create-yaml.sh` (.bedrock_agentcore.yaml 생성)
- `scripts/phase3/3-deploy-runtime.sh` (Runtime 배포)
- `scripts/phase3/4-verify.sh` (검증)

#### Phase 4: Testing (계획)
- `scripts/phase4/1-test-simple.sh` (간단한 Job)
- `scripts/phase4/2-test-complex.sh` (복잡한 Job)
- `scripts/phase4/3-download-artifacts.sh` (결과물 다운로드)

### A3. 로컬 테스트 (선택 사항)

개발 계정에서 Phase 1 CloudFormation 배포를 테스트할 수 있습니다:

```bash
cd production_deployment

# 1. Phase 1 배포 테스트 (dev 환경)
./scripts/phase1/deploy.sh dev

# 2. CloudFormation 스택 확인
aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-dev \
  --region us-east-1

# 3. 검증
./scripts/phase1/verify.sh

# 4. 정리 (비용 절감)
aws cloudformation delete-stack \
  --stack-name bedrock-manus-infrastructure-dev \
  --region us-east-1
```

**⚠️ 주의**:
- 테스트 후 반드시 리소스를 정리하세요 (NAT Gateway ~$32/월)
- VPC Endpoints 삭제 시간: 약 5-10분

### A4. Git Repository 준비

#### A4.1 .gitignore 확인

production_deployment 폴더에 `.gitignore` 파일이 있는지 확인:

```bash
# .gitignore 생성 (없는 경우)
cat > production_deployment/.gitignore <<'EOF'
# Environment files
.env
*.env.local

# CloudFormation temporary files
cloudformation/parameters/.*.json

# Logs
*.log
logs/

# Temporary files
temp/
tmp/
artifacts/

# Mac
.DS_Store
EOF
```

**✅ Git에 포함되는 파일**:
- `cloudformation/phase1-infrastructure.yaml`
- `cloudformation/parameters/phase1-prod-params.json` (ACCOUNT_ID 플레이스홀더 포함)
- `scripts/phase1/deploy.sh`
- `scripts/phase1/verify.sh`
- `docs/*.md` (가이드 문서)
- `README.md`, `STATUS.md`, `DEPLOYMENT_WORKFLOW.md`

**❌ Git에서 제외되는 파일**:
- `.env` (생성된 환경 변수)
- `cloudformation/parameters/.phase1-*-params-temp.json` (임시 파일)

### A5. Git에 커밋 및 푸시

```bash
cd production_deployment

# 변경 사항 확인
git status

# Phase 1 관련 파일들 추가
git add cloudformation/phase1-infrastructure.yaml
git add cloudformation/parameters/phase1-prod-params.json
git add scripts/phase1/
git add docs/
git add README.md DEPLOYMENT_WORKFLOW.md STEP_BY_STEP_GUIDE.md CLOUDFORMATION_GUIDE.md

# 커밋
git commit -m "Add Phase 1 CloudFormation deployment

- CloudFormation template for VPC infrastructure (Single-AZ)
- Deploy and verify scripts
- Phase 1 deployment guide
- Parameter files for production environment
"

# 푸시 (master 브랜치)
git push origin master
```

**✅ Development 계정 Phase 1 작업 완료!**

**다음 단계**:
1. ✅ Phase 1 CloudFormation 템플릿 및 스크립트 Git에 푸시
2. ⏳ Production 계정에서 Phase 1 배포 및 검증
3. ⏳ 검증 완료 후 Phase 2, 3, 4 준비

---

## Phase B: Git Repository 작업

### B1. Repository 확인

GitHub에서 다음을 확인하세요:

1. **파일 업로드 확인**:
   - `production_deployment/cloudformation/phase1-infrastructure.yaml`
   - `production_deployment/cloudformation/parameters/phase1-prod-params.json`
   - `production_deployment/scripts/phase1/deploy.sh`
   - `production_deployment/scripts/phase1/verify.sh`
   - `production_deployment/docs/*.md`
   - `production_deployment/README.md`

2. **README 확인**:
   - `production_deployment/README.md`가 제대로 표시되는지

3. **Repository URL 복사**:
   ```
   https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr
   ```

---

## Phase C: Production 계정 작업

> **위치**: 새로운 AWS 계정의 EC2 또는 로컬 환경
> **목표**: Git에서 코드 다운로드 후 Phase 1 인프라 배포

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

#### C1.2 필수 IAM 권한 확인

다음 권한이 필요합니다:
- ✅ EC2FullAccess (VPC, Subnets, Security Groups, VPC Endpoints)
- ✅ ElasticLoadBalancingFullAccess (ALB, Target Group)
- ✅ IAMFullAccess (IAM Roles 생성)
- ✅ CloudFormationFullAccess (스택 관리)

### C2. Git Repository Clone

```bash
# Repository Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git

# 프로젝트 디렉토리로 이동
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment

# Phase 1 파일 확인
ls -la cloudformation/phase1-infrastructure.yaml
ls -la cloudformation/parameters/phase1-prod-params.json
ls -la scripts/phase1/deploy.sh
ls -la scripts/phase1/verify.sh
```

### C3. Phase 1 인프라 배포 (CloudFormation)

#### C3.1 배포 스크립트 실행

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/phase1/*.sh

# Phase 1 배포 시작 (Production 환경)
./scripts/phase1/deploy.sh prod
```

**배포 과정**:
1. ✅ 사전 체크 (AWS CLI, 자격증명)
2. ✅ CloudFormation 템플릿 검증
3. ✅ Account ID를 Parameter 파일에 자동 주입
4. ✅ CloudFormation 스택 배포 시작
5. ⏳ **대기 시간: 30-40분**
6. ✅ 스택 출력값을 `.env` 파일에 저장

**예상 소요 시간**: 30-40분
- VPC, Subnets: 2-3분
- NAT Gateway: 5-7분
- VPC Endpoints: 15-20분 (6개)
- ALB: 3-5분
- Security Groups, IAM: 1-2분

#### C3.2 배포 모니터링 (별도 터미널)

배포 중 별도 터미널에서 진행 상황 확인:

```bash
# CloudFormation 스택 상태
watch -n 10 "aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus' \
  --output text"

# VPC Endpoints 상태 (6개 모두 available 되어야 함)
watch -n 10 "aws ec2 describe-vpc-endpoints \
  --filters 'Name=tag:Environment,Values=prod' \
  --region us-east-1 \
  --query 'VpcEndpoints[*].[ServiceName,State]' \
  --output table"
```

### C4. Phase 1 검증

#### C4.1 자동 검증 스크립트 실행

```bash
# Phase 1 검증 스크립트 실행
./scripts/phase1/verify.sh
```

**검증 항목** (총 15개 체크):
1. ✅ VPC 생성 확인
2. ✅ Private Subnet 생성 확인
3. ✅ Public Subnet 생성 확인
4. ✅ NAT Gateway available 확인
5. ✅ Internet Gateway attached 확인
6. ✅ Security Group 4개 확인 (AgentCore, ALB, Fargate, VPC Endpoint)
7. ✅ VPC Endpoints 6개 확인 (모두 available 상태)
8. ✅ ALB State: active 확인
9. ✅ Target Group Health Check 활성화 확인
10. ✅ Sticky Sessions 활성화 확인
11. ✅ Task Execution Role 생성 확인
12. ✅ Task Role 생성 확인

**예상 출력**:
```
============================================
Phase 1: Infrastructure Verification
============================================

1. Checking VPC and Network Resources...

  VPC exists                                      ✓ OK
  Private Subnet exists                           ✓ OK
  Public Subnet exists                            ✓ OK
  NAT Gateway available                           ✓ OK
  Internet Gateway attached                       ✓ OK

2. Checking Security Groups...

  AgentCore Security Group                        ✓ OK
  ALB Security Group                              ✓ OK
  Fargate Security Group                          ✓ OK
  VPC Endpoint Security Group                     ✓ OK

3. Checking VPC Endpoints...

  VPC Endpoints count (expected 6)                ✓ OK (6)
  VPC Endpoint (bedrock-agentcore-control)        ✓ available
  VPC Endpoint (bedrock-agentcore)                ✓ available
  VPC Endpoint (ecr.api)                          ✓ available
  VPC Endpoint (ecr.dkr)                          ✓ available
  VPC Endpoint (logs)                             ✓ available
  VPC Endpoint (s3)                               ✓ available

4. Checking Application Load Balancer...

  ALB State                                       ✓ active
  Target Group Health Check                       ✓ Enabled
  Sticky Sessions                                 ✓ Enabled

5. Checking IAM Roles...

  Task Execution Role                             ✓ OK
  Task Role                                       ✓ OK

============================================
Verification Summary
============================================

Total Checks:  15
Passed:        15

============================================
✓ All checks passed!
============================================

Next Steps:
  1. Proceed to Phase 2: (Phase 1 완료 후 진행)
```

#### C4.2 생성된 리소스 확인 (.env 파일)

```bash
# .env 파일 확인 (모든 리소스 ID가 자동으로 저장됨)
cat .env
```

**예상 내용**:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Project Configuration
PROJECT_NAME=bedrock-manus
ENVIRONMENT=prod

# VPC Configuration
VPC_ID=vpc-xxxxxxxxxxxxx
PRIVATE_SUBNET_ID=subnet-xxxxxxxxxxxxx
PUBLIC_SUBNET_ID=subnet-xxxxxxxxxxxxx
SG_AGENTCORE_ID=sg-xxxxxxxxxxxxx
SG_ALB_ID=sg-xxxxxxxxxxxxx
SG_FARGATE_ID=sg-xxxxxxxxxxxxx
SG_VPCE_ID=sg-xxxxxxxxxxxxx
AVAILABILITY_ZONE=us-east-1a

# ALB Configuration
ALB_ARN=arn:aws:elasticloadbalancing:...
ALB_DNS=bedrock-manus-alb-prod-xxxxx.us-east-1.elb.amazonaws.com
TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:...

# IAM Roles
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::123456789012:role/bedrock-manus-task-execution-role-prod
TASK_ROLE_ARN=arn:aws:iam::123456789012:role/bedrock-manus-task-role-prod
```

### C5. Phase 1 배포 완료!

**✅ Phase 1 체크리스트**:
- [x] VPC Status: `available`
- [x] Subnet 2개 생성: Private, Public (us-east-1a)
- [x] Security Groups 4개 생성: AgentCore, ALB, Fargate, VPC Endpoint
- [x] VPC Endpoints 6개 모두: `available`
- [x] NAT Gateway Status: `available`
- [x] ALB Status: `active`
- [x] IAM Roles 2개 생성: Task Execution Role, Task Role
- [x] `.env` 파일에 모든 리소스 ID 저장 완료

**🎉 Phase 1 Infrastructure 배포 성공!**

### C6. 다음 단계

**⏳ Phase 2, 3, 4는 Phase 1 완료 후 진행 예정**:

1. **Phase 2: Fargate Runtime**
   - ECR Repository 생성
   - Docker 이미지 빌드 및 푸시
   - ECS Cluster 생성
   - Task Definition 등록

2. **Phase 3: AgentCore Runtime**
   - `.bedrock_agentcore.yaml` 생성 (VPC 모드)
   - Runtime 배포
   - ENI 생성 확인

3. **Phase 4: Testing**
   - 네트워크 연결 테스트
   - AgentCore Job 실행
   - PDF 보고서 생성 테스트

**현재 상태**: ✅ Phase 1 완료, Phase 2-4 준비 중

---

## 🔧 트러블슈팅 (Phase 1 CloudFormation)

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
An error occurred (AccessDenied) when calling the CreateStack operation
```

**해결**:
```bash
# IAM User에 필요한 권한 추가 (최소 권한):
# - EC2FullAccess
# - ElasticLoadBalancingFullAccess
# - IAMFullAccess (IAM Role 생성용)
# - CloudFormationFullAccess

# 또는 간편하게:
# - AdministratorAccess (개발/테스트 환경)
```

**IAM 권한 확인**:
```bash
# 현재 사용자 확인
aws sts get-caller-identity

# 사용자의 정책 확인
aws iam list-attached-user-policies --user-name YOUR_USERNAME
```

### 문제 3: CloudFormation 템플릿 검증 실패

**증상**:
```bash
./scripts/phase1/deploy.sh
# Error: Template validation failed
```

**해결**:
```bash
# 수동으로 템플릿 검증
aws cloudformation validate-template \
  --template-body file://cloudformation/phase1-infrastructure.yaml \
  --region us-east-1

# YAML 문법 오류 확인
yamllint cloudformation/phase1-infrastructure.yaml
```

### 문제 4: VPC Endpoint 생성 실패 (AZ 지원 문제)

**증상**:
```
The requested Availability Zone is not supported for this service
```

**원인**: Bedrock AgentCore VPC Endpoint는 특정 AZ만 지원

**해결**:
```bash
# 지원되는 AZ ID 확인
aws ec2 describe-vpc-endpoint-services \
  --service-names com.amazonaws.us-east-1.bedrock-agentcore-control \
  --region us-east-1 \
  --query 'ServiceDetails[0].AvailabilityZones' \
  --output table

# 결과 예시:
# +----------+
# | use1-az2 |
# | use1-az4 |
# | use1-az6 |
# +----------+

# AvailabilityZone 파라미터를 지원되는 AZ로 변경
# cloudformation/parameters/phase1-prod-params.json:
# "AvailabilityZone": "us-east-1a"  # use1-az2 (지원됨)
```

**현재 AZ ID 확인**:
```bash
aws ec2 describe-availability-zones \
  --region us-east-1 \
  --query 'AvailabilityZones[*].[ZoneName,ZoneId]' \
  --output table

# 결과:
# us-east-1a → use1-az2 ✅ (지원됨)
# us-east-1b → use1-az4 ✅ (지원됨)
# us-east-1c → use1-az6 ✅ (지원됨)
```

### 문제 5: CloudFormation 스택 배포 중 실패

**증상**:
```
Stack bedrock-manus-infrastructure-prod is in CREATE_FAILED state
```

**해결**:
```bash
# 스택 이벤트 확인 (실패 원인 파악)
aws cloudformation describe-stack-events \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1 \
  --max-items 50 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[ResourceType,ResourceStatusReason]' \
  --output table

# 스택 삭제 후 재시도
aws cloudformation delete-stack \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1

# 삭제 완료 대기 (약 5-10분)
aws cloudformation wait stack-delete-complete \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1

# 재배포
./scripts/phase1/deploy.sh prod
```

### 문제 6: NAT Gateway 생성 실패 (EIP Limit)

**증상**:
```
The maximum number of addresses has been reached
```

**해결**:
```bash
# 현재 EIP 사용량 확인
aws ec2 describe-addresses --region us-east-1

# 사용하지 않는 EIP 릴리스
aws ec2 release-address --allocation-id eipalloc-xxxxx --region us-east-1

# 또는 Service Quotas에서 EIP 한도 증가 요청
aws service-quotas request-service-quota-increase \
  --service-code vpc \
  --quota-code L-0263D0A3 \
  --desired-value 10 \
  --region us-east-1
```

### 문제 7: 스택 업데이트 시 "No updates are to be performed"

**증상**:
```
No changes to deploy. Stack bedrock-manus-infrastructure-prod is up to date.
```

**원인**: CloudFormation 템플릿 또는 파라미터가 변경되지 않음

**해결**: 정상 동작입니다. 변경사항이 없으면 업데이트가 스킵됩니다.

### 문제 8: Verification 스크립트 실패

**증상**:
```bash
./scripts/phase1/verify.sh
# VPC Endpoints count (expected 6) ⚠ WARNING (5)
```

**해결**:
```bash
# VPC Endpoint 상태 확인
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$(cat .env | grep VPC_ID | cut -d'=' -f2)" \
  --region us-east-1 \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
  --output table

# pending 상태면 5-10분 대기 후 재확인
# failed 상태면 스택 이벤트 확인
```

---

## 📊 비용 관리 (Phase 1)

### Phase 1 운영 비용 (월간, 24/7 실행 시)

| 리소스 | 수량 | 비용 (USD/월) | 비고 |
|--------|------|--------------|------|
| **NAT Gateway** | 1 | ~$32.40 | $0.045/시간 |
| **VPC Endpoints (Interface)** | 5 | ~$36.00 | $0.01/시간/endpoint |
| **VPC Endpoint (Gateway)** | 1 | $0 | S3 Gateway는 무료 |
| **ALB** | 1 | ~$16.00 | $0.0225/시간 |
| **Elastic IP** | 1 | $0 | NAT Gateway에 연결 시 무료 |
| **S3 Storage** | 1 | ~$1.00 | 최소 사용 가정 |
| **CloudWatch Logs** | - | ~$1.00 | 최소 로그 가정 |
| **총합 (Phase 1)** | - | **~$86.40/월** | - |

**⚠️ 비용 절감 팁**:
- **개발/테스트 환경**: 사용 후 스택 삭제 (CloudFormation 한 번에 정리)
- **NAT Gateway 대안**: VPC Endpoints만 사용 (ECR, S3 접근 가능)
- **ALB 대안**: 개발 환경에서는 Public IP 사용 고려

### 리소스 정리 (CloudFormation 스택 삭제)

사용하지 않을 때는 CloudFormation 스택을 삭제하여 모든 리소스를 한 번에 정리:

```bash
cd production_deployment

# Phase 1 스택 삭제
aws cloudformation delete-stack \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1

# 삭제 진행 상황 모니터링
aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus' \
  --output text

# 또는 삭제 완료 대기 (블로킹)
aws cloudformation wait stack-delete-complete \
  --stack-name bedrock-manus-infrastructure-prod \
  --region us-east-1
```

**예상 삭제 시간**: 10-15분
- VPC Endpoints 삭제: 5-10분
- NAT Gateway 삭제: 2-3분
- 기타 리소스: 1-2분

**⚠️ 주의사항**:
- CloudFormation 스택 삭제 시 모든 리소스가 삭제됩니다
- `.env` 파일은 삭제되지 않으므로 수동 삭제 필요
- 재배포 시 `.env` 파일이 자동으로 다시 생성됩니다

---

## 🎯 다음 단계

### Development 계정 (현재)
1. ✅ Phase 1 CloudFormation 템플릿 생성
2. ✅ Deploy/Verify 스크립트 생성
3. ✅ 문서 작성 (DEPLOYMENT_WORKFLOW.md)
4. ⏳ Git에 푸시 (준비 완료)
5. ⏳ Production 계정 배포 후 Phase 2, 3, 4 준비

### Production 계정 (다음)
1. ⏳ Git Clone
2. ⏳ Phase 1 배포 (`./scripts/phase1/deploy.sh prod`)
3. ⏳ Phase 1 검증 (`./scripts/phase1/verify.sh`)
4. ⏳ 검증 완료 후 Development 계정에 피드백
5. ⏳ Phase 2, 3, 4 진행 (Development 계정에서 준비 후)

### 전체 로드맵
- **현재**: Phase 1 CloudFormation 완료
- **다음**: Production 계정 Phase 1 배포
- **향후**: Phase 2 (Fargate), Phase 3 (AgentCore), Phase 4 (Testing)

---

## 📝 요약

**이 문서의 목적**:
- Development 계정에서 Phase 1 CloudFormation 템플릿과 스크립트를 준비
- Git을 통해 Production 계정으로 전달
- Production 계정에서 Phase 1 인프라 배포 및 검증

**주요 장점**:
- ✅ **Infrastructure as Code**: CloudFormation으로 재현 가능한 인프라
- ✅ **자동화**: 스크립트 한 번 실행으로 전체 배포
- ✅ **검증**: 자동 검증 스크립트로 모든 리소스 확인
- ✅ **Git 기반**: 버전 관리 및 협업 용이
- ✅ **비용 투명성**: 예상 비용 명시 및 정리 스크립트 제공

**완료 시점**:
- Phase 1 배포: 30-40분
- Phase 1 검증: 2-3분
- 총 소요 시간: 35-45분

---

**작성일**: 2025-11-02
**버전**: 2.0.0 (CloudFormation 기반)
**작성자**: Claude Code
**변경 이력**:
- v1.0.0 (2025-11-01): Shell 스크립트 기반 초기 버전
- v2.0.0 (2025-11-02): CloudFormation 기반으로 전환 (Phase 1 완료)
