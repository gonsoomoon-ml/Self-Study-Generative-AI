# 🔧 단계별 배포 가이드

> **목표**: 각 단계를 순서대로 하나씩 실행하여 인프라 배포

---

## 📋 전체 스크립트 구조

```
production_deployment/scripts/
│
├── 📁 phase1_infrastructure/          # Phase 1: 인프라 배포 (30-40분)
│   ├── 1-1-deploy-vpc.sh              # VPC, Subnets, IGW, NAT (10분)
│   ├── 1-2-deploy-security-groups.sh  # Security Groups 4개 (2분)
│   ├── 1-3-deploy-vpc-endpoints.sh    # VPC Endpoints 6개 (15분)
│   ├── 1-4-deploy-alb.sh              # ALB + Target Group (5분)
│   ├── 1-5-deploy-iam-roles.sh        # IAM Roles (2분)
│   └── 1-6-verify.sh                  # ✅ Phase 1 검증
│
├── 📁 phase2_fargate/                 # Phase 2: Fargate Runtime (15-20분)
│   ├── 2-1-create-ecr-repository.sh   # ECR Repository 생성 (1분)
│   ├── 2-2-build-docker-image.sh      # Docker 이미지 빌드 (5분)
│   ├── 2-3-push-to-ecr.sh             # ECR에 푸시 (3분)
│   ├── 2-4-register-task-definition.sh # Task Definition 등록 (1분)
│   ├── 2-5-create-ecs-cluster.sh      # ECS Cluster 생성 (1분)
│   ├── 2-6-test-fargate-task.sh       # 테스트 Task 실행 (2분)
│   └── 2-7-verify.sh                  # ✅ Phase 2 검증
│
├── 📁 phase3_agentcore/               # Phase 3: AgentCore Runtime (10-15분)
│   ├── 3-1-prepare-runtime-source.sh  # 소스 코드 준비 (1분)
│   ├── 3-2-create-bedrock-yaml.sh     # .bedrock_agentcore.yaml 생성 (1분)
│   ├── 3-3-deploy-runtime.sh          # Runtime 배포 (5분)
│   ├── 3-4-wait-for-eni.sh            # ENI 생성 대기 (2분)
│   └── 3-5-verify.sh                  # ✅ Phase 3 검증
│
├── 📁 phase4_testing/                 # Phase 4: 테스트 (10-30분)
│   ├── 4-1-test-connectivity.sh       # 네트워크 연결 테스트 (2분)
│   ├── 4-2-test-simple-job.sh         # 간단한 Job (5분)
│   ├── 4-3-test-complex-job.sh        # 복잡한 Job (15분)
│   └── 4-4-download-artifacts.sh      # Artifacts 다운로드 (2분)
│
└── 📁 cleanup/                        # 리소스 정리
    ├── cleanup-phase-4.sh             # Phase 4 정리
    ├── cleanup-phase-3.sh             # Phase 3 정리 (Runtime 삭제)
    ├── cleanup-phase-2.sh             # Phase 2 정리 (ECR, ECS)
    └── cleanup-phase-1.sh             # Phase 1 정리 (VPC 전체)
```

---

## 🚀 Production 계정 배포 절차

### 사전 준비

```bash
# 1. Git Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment

# 2. AWS 설정 확인
aws configure
aws sts get-caller-identity

# 3. 실행 권한 부여
chmod +x scripts/phase*/*.sh
chmod +x scripts/cleanup/*.sh

# 4. 환경 변수 파일 생성
cp .env.template .env

# 5. AWS Account ID 자동 입력
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/AWS_ACCOUNT_ID=/AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID/g" .env
```

---

## Phase 1: 인프라 배포 (30-40분)

### 1-1. VPC 생성 (10분)

```bash
./scripts/phase1_infrastructure/1-1-deploy-vpc.sh
```

**생성되는 리소스**:
- ✅ VPC (10.0.0.0/16)
- ✅ Private Subnet (10.0.1.0/24, us-east-1a)
- ✅ Public Subnet (10.0.11.0/24, us-east-1a)
- ✅ Internet Gateway
- ✅ NAT Gateway (Public Subnet에 생성)
- ✅ Route Tables (Private용, Public용)

**검증**:
```bash
# VPC ID 확인
grep VPC_ID .env

# Subnet 확인
aws ec2 describe-subnets --filters "Name=tag:Environment,Values=prod" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

**예상 결과**:
```
.env 파일에 다음 값들이 추가됨:
VPC_ID=vpc-xxxxx
PRIVATE_SUBNET_ID=subnet-xxxxx
PUBLIC_SUBNET_ID=subnet-xxxxx
NAT_GATEWAY_ID=nat-xxxxx
IGW_ID=igw-xxxxx
```

---

### 1-2. Security Groups 생성 (2분)

```bash
./scripts/phase1_infrastructure/1-2-deploy-security-groups.sh
```

**생성되는 리소스**:
- ✅ AgentCore Security Group (VPC Endpoint 통신)
- ✅ ALB Security Group (Port 80)
- ✅ Fargate Security Group (Port 8080)
- ✅ VPC Endpoint Security Group (Port 443)

**검증**:
```bash
# Security Groups 확인
aws ec2 describe-security-groups \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'SecurityGroups[*].[GroupId,GroupName]' \
  --output table
```

**예상 결과**:
```
.env 파일에 추가:
SG_AGENTCORE_ID=sg-xxxxx
SG_ALB_ID=sg-xxxxx
SG_FARGATE_ID=sg-xxxxx
SG_VPCE_ID=sg-xxxxx
```

---

### 1-3. VPC Endpoints 생성 (15분)

```bash
./scripts/phase1_infrastructure/1-3-deploy-vpc-endpoints.sh
```

**생성되는 리소스**:
- ✅ Bedrock AgentCore Control Endpoint (Interface)
- ✅ Bedrock AgentCore Gateway Endpoint (Interface)
- ✅ ECR API Endpoint (Interface)
- ✅ ECR Docker Endpoint (Interface)
- ✅ CloudWatch Logs Endpoint (Interface)
- ✅ S3 Gateway Endpoint (Gateway)

**⏰ 대기 시간**: VPC Endpoints가 `available` 상태가 될 때까지 약 10-15분 소요

**검증**:
```bash
# VPC Endpoints 상태 확인 (모두 available이어야 함)
aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
  --output table

# 스크립트가 자동으로 대기하며 상태 체크
```

**예상 결과**:
```
모든 VPC Endpoints가 "available" 상태
.env 파일에 Endpoint ID들 추가
```

---

### 1-4. ALB 생성 (5분)

```bash
./scripts/phase1_infrastructure/1-4-deploy-alb.sh
```

**생성되는 리소스**:
- ✅ Internal Application Load Balancer (Private Subnet)
- ✅ Target Group (Port 8080, IP target type)

**검증**:
```bash
# ALB 상태 확인
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `bedrock-manus`)].[DNSName,State.Code]' \
  --output table
```

**예상 결과**:
```
.env 파일에 추가:
ALB_ARN=arn:aws:elasticloadbalancing:...
ALB_DNS=bedrock-manus-alb-xxxxx.us-east-1.elb.amazonaws.com
TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:...
```

---

### 1-5. IAM Roles 생성 (2분)

```bash
./scripts/phase1_infrastructure/1-5-deploy-iam-roles.sh
```

**생성되는 리소스**:
- ✅ Fargate Task Execution Role (ECR, CloudWatch 접근)
- ✅ Fargate Task Role (S3, Bedrock 접근)

**검증**:
```bash
# IAM Roles 확인
aws iam list-roles --query 'Roles[?contains(RoleName, `bedrock-manus`)].[RoleName,Arn]' \
  --output table
```

**예상 결과**:
```
.env 파일에 추가:
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::...
TASK_ROLE_ARN=arn:aws:iam::...
```

---

### 1-6. Phase 1 검증 (1분)

```bash
./scripts/phase1_infrastructure/1-6-verify.sh
```

**체크리스트**:
- [ ] VPC ID 존재
- [ ] Subnets 2개 존재 (Private, Public)
- [ ] NAT Gateway: `available`
- [ ] Security Groups 4개 존재
- [ ] VPC Endpoints 6개 모두: `available`
- [ ] ALB: `active`
- [ ] IAM Roles 2개 존재

**✅ Phase 1 완료!**

---

## Phase 2: Fargate Runtime 배포 (15-20분)

### 2-1. ECR Repository 생성 (1분)

```bash
./scripts/phase2_fargate/2-1-create-ecr-repository.sh
```

**생성되는 리소스**:
- ✅ ECR Repository: `bedrock-manus-fargate-runtime`

**검증**:
```bash
aws ecr describe-repositories \
  --repository-names bedrock-manus-fargate-runtime
```

**예상 결과**:
```
.env 파일에 추가:
ECR_REPOSITORY_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/bedrock-manus-fargate-runtime
```

---

### 2-2. Docker 이미지 빌드 (5분)

```bash
./scripts/phase2_fargate/2-2-build-docker-image.sh
```

**작업 내용**:
- ✅ `fargate-runtime/Dockerfile` 사용
- ✅ Python 3.12 + 필수 패키지 설치
- ✅ 한글 폰트 설치 (Noto Sans KR)
- ✅ Flask 서버 포함

**검증**:
```bash
# Docker 이미지 확인
docker images | grep bedrock-manus-fargate-runtime
```

**예상 결과**:
```
bedrock-manus-fargate-runtime   latest   xxxxx   5 minutes ago   ~500MB
```

---

### 2-3. ECR에 푸시 (3분)

```bash
./scripts/phase2_fargate/2-3-push-to-ecr.sh
```

**작업 내용**:
- ✅ ECR 로그인
- ✅ Docker 이미지 태깅
- ✅ ECR에 푸시

**검증**:
```bash
# ECR 이미지 확인
aws ecr describe-images \
  --repository-name bedrock-manus-fargate-runtime \
  --query 'imageDetails[*].[imageTags[0],imagePushedAt,imageSizeInBytes]' \
  --output table
```

---

### 2-4. Task Definition 등록 (1분)

```bash
./scripts/phase2_fargate/2-4-register-task-definition.sh
```

**생성되는 리소스**:
- ✅ ECS Task Definition (Fargate, 1 vCPU, 2GB RAM)

**검증**:
```bash
aws ecs describe-task-definition \
  --task-definition bedrock-manus-task \
  --query 'taskDefinition.[family,revision,status]' \
  --output table
```

**예상 결과**:
```
.env 파일에 추가:
TASK_DEFINITION_ARN=arn:aws:ecs:us-east-1:...:task-definition/bedrock-manus-task:1
```

---

### 2-5. ECS Cluster 생성 (1분)

```bash
./scripts/phase2_fargate/2-5-create-ecs-cluster.sh
```

**생성되는 리소스**:
- ✅ ECS Cluster: `bedrock-manus-cluster`

**검증**:
```bash
aws ecs describe-clusters --clusters bedrock-manus-cluster
```

**예상 결과**:
```
.env 파일에 추가:
CLUSTER_ARN=arn:aws:ecs:us-east-1:...:cluster/bedrock-manus-cluster
```

---

### 2-6. 테스트 Task 실행 (2분)

```bash
./scripts/phase2_fargate/2-6-test-fargate-task.sh
```

**작업 내용**:
- ✅ Fargate Task 1개 실행
- ✅ ALB에 자동 등록 (60초 대기)
- ✅ Health Check 통과 확인

**검증**:
```bash
# Task 상태 확인
aws ecs list-tasks --cluster bedrock-manus-cluster --desired-status RUNNING

# ALB Target Health 확인
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN
```

**예상 결과**:
```
Task Status: RUNNING
Target Health: healthy
```

---

### 2-7. Phase 2 검증 (1분)

```bash
./scripts/phase2_fargate/2-7-verify.sh
```

**체크리스트**:
- [ ] ECR Repository 존재
- [ ] Docker Image 푸시 완료
- [ ] Task Definition 등록 완료
- [ ] ECS Cluster 생성 완료
- [ ] Test Task: `RUNNING`
- [ ] ALB Target Health: `healthy`

**✅ Phase 2 완료!**

---

## Phase 3: AgentCore Runtime 배포 (10-15분)

### 3-1. Runtime 소스 준비 (1분)

```bash
./scripts/phase3_agentcore/3-1-prepare-runtime-source.sh
```

**작업 내용**:
- ✅ `agentcore-runtime/` 디렉토리 생성
- ✅ 필수 파일 복사:
  - `agentcore_runtime.py`
  - `src/` 전체
  - `requirements.txt`
  - `data/` 폴더
  - `.bedrock_agentcore.yaml` (템플릿)

**검증**:
```bash
ls -la agentcore-runtime/
```

---

### 3-2. Bedrock YAML 생성 (1분)

```bash
./scripts/phase3_agentcore/3-2-create-bedrock-yaml.sh
```

**작업 내용**:
- ✅ `.bedrock_agentcore.yaml` 파일 생성
- ✅ VPC 모드 설정:
  ```yaml
  networkConfiguration:
    networkMode: VPC
    networkModeConfig:
      securityGroups:
        - sg-xxxxx  # Phase 1에서 생성한 AgentCore SG
      subnets:
        - subnet-xxxxx  # Private Subnet
  ```

**검증**:
```bash
cat agentcore-runtime/.bedrock_agentcore.yaml
```

---

### 3-3. Runtime 배포 (5분)

```bash
./scripts/phase3_agentcore/3-3-deploy-runtime.sh
```

**작업 내용**:
- ✅ `bedrock_agentcore launch` 실행
- ✅ VPC Private 모드로 배포
- ✅ Runtime ID 저장

**검증**:
```bash
# Runtime 상태 확인
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --query 'agentRuntime.[agentRuntimeId,status,networkMode]' \
  --output table
```

**예상 결과**:
```
Status: READY
Network Mode: VPC
.env 파일에 추가:
RUNTIME_ID=bedrock_manus_runtime-xxxxx
RUNTIME_ARN=arn:aws:bedrock-agentcore:...
```

---

### 3-4. ENI 생성 대기 (2분)

```bash
./scripts/phase3_agentcore/3-4-wait-for-eni.sh
```

**작업 내용**:
- ✅ ENI (Elastic Network Interface) 생성 확인
- ✅ ENI가 Private Subnet에 attach되었는지 확인

**검증**:
```bash
# ENI 확인
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*bedrock*" "Name=status,Values=in-use" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,PrivateIpAddress,SubnetId]' \
  --output table
```

**예상 결과**:
```
ENI ID: eni-xxxxx
Private IP: 10.0.1.xxx
Subnet: subnet-xxxxx (Private Subnet)
```

---

### 3-5. Phase 3 검증 (1분)

```bash
./scripts/phase3_agentcore/3-5-verify.sh
```

**체크리스트**:
- [ ] Runtime Status: `READY`
- [ ] Network Mode: `VPC`
- [ ] ENI 생성 확인
- [ ] ENI가 Private Subnet에 attach
- [ ] Security Group 연결 확인

**✅ Phase 3 완료!**

---

## Phase 4: 테스트 및 검증 (10-30분)

### 4-1. 네트워크 연결 테스트 (2분)

```bash
./scripts/phase4_testing/4-1-test-connectivity.sh
```

**테스트 내용**:
- ✅ Runtime → VPC Endpoint 연결
- ✅ Runtime → ALB 연결
- ✅ ALB → Fargate Container 연결

---

### 4-2. 간단한 Job 실행 (5분)

```bash
./scripts/phase4_testing/4-2-test-simple-job.sh
```

**테스트 내용**:
- ✅ CSV 파일 분석
- ✅ 총 매출액 계산
- ✅ 결과 반환 확인

**예상 소요 시간**: 2-5분

---

### 4-3. 복잡한 Job 실행 (15분)

```bash
./scripts/phase4_testing/4-3-test-complex-job.sh
```

**테스트 내용**:
- ✅ 카테고리별 매출 분석
- ✅ 차트 생성 (7개)
- ✅ PDF 보고서 생성
- ✅ S3 업로드 확인

**예상 소요 시간**: 15-20분

---

### 4-4. Artifacts 다운로드 (2분)

```bash
./scripts/phase4_testing/4-4-download-artifacts.sh
```

**작업 내용**:
- ✅ S3에서 생성된 파일 다운로드
- ✅ 로컬 `artifacts/` 폴더에 저장

**다운로드되는 파일**:
- `final_report.pdf`
- `final_report_with_citations.pdf`
- `citations.json`
- `*.png` (차트 파일들)

**✅ Phase 4 완료! 배포 성공!**

---

## 🧹 리소스 정리

### 역순으로 정리해야 합니다!

#### Phase 4 정리
```bash
./scripts/cleanup/cleanup-phase-4.sh
# - 테스트 artifacts 삭제
```

#### Phase 3 정리 (AgentCore Runtime)
```bash
./scripts/cleanup/cleanup-phase-3.sh
# - AgentCore Runtime 삭제
# - ENI 자동 삭제 대기
```

#### Phase 2 정리 (Fargate)
```bash
./scripts/cleanup/cleanup-phase-2.sh
# - Fargate Tasks 중지
# - ECS Cluster 삭제
# - Task Definition 삭제
# - ECR Repository 삭제 (이미지 포함)
```

#### Phase 1 정리 (인프라)
```bash
./scripts/cleanup/cleanup-phase-1.sh
# - ALB 삭제
# - VPC Endpoints 삭제 (5-10분 소요)
# - NAT Gateway 삭제
# - Internet Gateway 삭제
# - Subnets 삭제
# - VPC 삭제
# - IAM Roles 삭제
```

**⚠️ 주의**: Phase 1 정리는 15-20분 소요될 수 있습니다 (VPC Endpoints 삭제 대기).

---

## 📊 진행 상황 추적

각 Phase 완료 후 `STATUS.md` 파일이 자동 업데이트됩니다:

```bash
cat STATUS.md
```

**예시**:
```markdown
## Phase 1: Infrastructure
✅ 1-1: VPC Created (vpc-xxxxx)
✅ 1-2: Security Groups Created
✅ 1-3: VPC Endpoints Available
✅ 1-4: ALB Active
✅ 1-5: IAM Roles Created
✅ Phase 1 Verified

## Phase 2: Fargate Runtime
✅ 2-1: ECR Repository Created
✅ 2-2: Docker Image Built
✅ 2-3: Image Pushed to ECR
✅ 2-4: Task Definition Registered
✅ 2-5: ECS Cluster Created
✅ 2-6: Test Task Running
✅ Phase 2 Verified

...
```

---

## 🎯 다음 단계

1. **Development 계정**: 이제 실제 스크립트 파일들을 생성해야 합니다
2. **Git Push**: 모든 스크립트를 Git에 푸시
3. **Production 계정**: Git clone 후 단계별 실행

---

**작성일**: 2025-11-01
**버전**: 1.0.0
