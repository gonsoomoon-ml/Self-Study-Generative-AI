# 🏗️ CloudFormation 기반 배포 가이드

> **목표**: CloudFormation YAML로 인프라를 코드로 관리하고, 각 Phase를 Shell 스크립트로 실행

---

## 📋 전체 구조

```
production_deployment/
│
├── cloudformation/                    # CloudFormation 템플릿
│   ├── phase1-infrastructure.yaml     # VPC, Subnets, SG, VPC Endpoints, ALB, IAM
│   ├── phase2-fargate.yaml            # ECR Repository, ECS Cluster
│   └── parameters/                    # 환경별 파라미터
│       ├── phase1-prod-params.json
│       └── phase2-prod-params.json
│
├── scripts/                           # 배포 실행 스크립트
│   ├── phase1/
│   │   ├── deploy.sh                  # Phase 1 CloudFormation 배포
│   │   └── verify.sh                  # Phase 1 검증
│   │
│   ├── phase2/
│   │   ├── 1-deploy-infrastructure.sh # Phase 2 CloudFormation 배포 (ECR, ECS)
│   │   ├── 2-build-docker.sh          # Docker 이미지 빌드
│   │   ├── 3-push-to-ecr.sh           # ECR에 푸시
│   │   ├── 4-register-task.sh         # Task Definition 등록
│   │   ├── 5-run-test-task.sh         # 테스트 Task 실행
│   │   └── 6-verify.sh                # Phase 2 검증
│   │
│   ├── phase3/
│   │   ├── 1-prepare-source.sh        # Runtime 소스 준비
│   │   ├── 2-create-yaml.sh           # .bedrock_agentcore.yaml 생성
│   │   ├── 3-deploy-runtime.sh        # AgentCore Runtime 배포
│   │   └── 4-verify.sh                # Phase 3 검증
│   │
│   ├── phase4/
│   │   ├── 1-test-simple.sh           # 간단한 Job 테스트
│   │   ├── 2-test-complex.sh          # 복잡한 Job 테스트
│   │   └── 3-download-artifacts.sh    # Artifacts 다운로드
│   │
│   └── cleanup/
│       ├── cleanup-phase-4.sh
│       ├── cleanup-phase-3.sh
│       ├── cleanup-phase-2.sh         # CloudFormation 스택 삭제
│       └── cleanup-phase-1.sh         # CloudFormation 스택 삭제
│
├── fargate-runtime/                   # Fargate Docker 이미지
│   ├── Dockerfile
│   ├── dynamic_executor_v2.py
│   ├── session_fargate_manager.py
│   └── requirements.txt
│
└── .env.template                      # 환경 변수 템플릿
```

---

## 🎯 Phase별 상세 설명

### Phase 1: Infrastructure (CloudFormation)

**CloudFormation Stack**: `bedrock-manus-infrastructure-prod`

**포함 리소스**:
- ✅ VPC (10.0.0.0/16)
- ✅ Private Subnet (10.0.1.0/24, us-east-1a)
- ✅ Public Subnet (10.0.11.0/24, us-east-1a)
- ✅ Internet Gateway
- ✅ NAT Gateway
- ✅ Route Tables (Private, Public)
- ✅ Security Groups 4개 (AgentCore, ALB, Fargate, VPC Endpoint)
- ✅ VPC Endpoints 6개 (Bedrock AgentCore, ECR API, ECR Docker, Logs, S3)
- ✅ Internal ALB + Target Group
- ✅ IAM Roles (Task Execution Role, Task Role)

**배포 명령**:
```bash
./scripts/phase1/deploy.sh
```

**소요 시간**: 30-40분 (VPC Endpoints 생성 때문)

**Outputs** (다음 Phase에서 사용):
- VpcId
- PrivateSubnetId
- PublicSubnetId
- AgentCoreSecurityGroupId
- AlbSecurityGroupId
- FargateSecurityGroupId
- VpcEndpointSecurityGroupId
- AlbArn
- AlbDnsName
- TargetGroupArn
- TaskExecutionRoleArn
- TaskRoleArn

---

### Phase 2: Fargate Runtime (CloudFormation + Scripts)

#### 2.1 CloudFormation 부분

**CloudFormation Stack**: `bedrock-manus-fargate-prod`

**포함 리소스**:
- ✅ ECR Repository
- ✅ ECS Cluster

**배포 명령**:
```bash
./scripts/phase2/1-deploy-infrastructure.sh
```

**소요 시간**: 2분

**Outputs**:
- EcrRepositoryUri
- EcsClusterArn

#### 2.2 Script 부분 (CloudFormation으로 불가능)

다음은 Shell 스크립트로 실행:

1. **Docker 빌드**:
   ```bash
   ./scripts/phase2/2-build-docker.sh
   ```
   - `fargate-runtime/Dockerfile` 빌드
   - 소요 시간: 5분

2. **ECR 푸시**:
   ```bash
   ./scripts/phase2/3-push-to-ecr.sh
   ```
   - ECR 로그인 → 태깅 → 푸시
   - 소요 시간: 3분

3. **Task Definition 등록**:
   ```bash
   ./scripts/phase2/4-register-task.sh
   ```
   - ECS Task Definition JSON 생성
   - `aws ecs register-task-definition` 실행
   - 소요 시간: 1분

4. **테스트 Task 실행**:
   ```bash
   ./scripts/phase2/5-run-test-task.sh
   ```
   - Fargate Task 1개 실행
   - ALB Target 등록 대기 (60초)
   - Health Check 확인
   - 소요 시간: 2분

5. **검증**:
   ```bash
   ./scripts/phase2/6-verify.sh
   ```

**전체 Phase 2 소요 시간**: 15-20분

---

### Phase 3: AgentCore Runtime (Scripts Only)

**이유**: Bedrock AgentCore는 CloudFormation 미지원, CLI 사용 필요

**스크립트**:

1. **소스 준비**:
   ```bash
   ./scripts/phase3/1-prepare-source.sh
   ```
   - `agentcore-runtime/` 디렉토리 생성
   - 필수 파일 복사
   - 소요 시간: 1분

2. **YAML 생성**:
   ```bash
   ./scripts/phase3/2-create-yaml.sh
   ```
   - `.bedrock_agentcore.yaml` 생성 (VPC 모드)
   - Phase 1의 Subnet, Security Group 사용
   - 소요 시간: 1분

3. **Runtime 배포**:
   ```bash
   ./scripts/phase3/3-deploy-runtime.sh
   ```
   - `bedrock_agentcore launch` 실행
   - ENI 생성 대기
   - 소요 시간: 10분

4. **검증**:
   ```bash
   ./scripts/phase3/4-verify.sh
   ```
   - Runtime Status 확인
   - ENI 확인
   - 소요 시간: 1분

**전체 Phase 3 소요 시간**: 10-15분

---

### Phase 4: Testing (Scripts Only)

1. **간단한 Job**:
   ```bash
   ./scripts/phase4/1-test-simple.sh
   ```
   - CSV 분석, 총 매출액 계산
   - 소요 시간: 5분

2. **복잡한 Job**:
   ```bash
   ./scripts/phase4/2-test-complex.sh
   ```
   - 카테고리별 분석, PDF 보고서 생성
   - 소요 시간: 15-20분

3. **Artifacts 다운로드**:
   ```bash
   ./scripts/phase4/3-download-artifacts.sh
   ```
   - S3에서 생성된 파일 다운로드
   - 소요 시간: 2분

**전체 Phase 4 소요 시간**: 20-30분

---

## 🚀 Production 계정 배포 순서

### 1. Git Clone 및 환경 설정

```bash
# Repository Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment

# AWS 설정
aws configure
aws sts get-caller-identity

# 환경 변수 설정
cp .env.template .env
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/AWS_ACCOUNT_ID=/AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID/g" .env

# 스크립트 실행 권한
chmod +x scripts/phase*/*.sh scripts/cleanup/*.sh
```

### 2. Phase 1: Infrastructure (30-40분)

```bash
# CloudFormation 스택 배포
./scripts/phase1/deploy.sh

# 배포 진행 상황 모니터링 (별도 터미널)
watch -n 10 aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'Stacks[0].StackStatus'

# 배포 완료 후 검증
./scripts/phase1/verify.sh
```

**완료 시 .env 파일에 자동으로 추가**:
- VPC_ID
- PRIVATE_SUBNET_ID
- PUBLIC_SUBNET_ID
- SG_AGENTCORE_ID, SG_ALB_ID, SG_FARGATE_ID, SG_VPCE_ID
- ALB_ARN, ALB_DNS, TARGET_GROUP_ARN
- TASK_EXECUTION_ROLE_ARN, TASK_ROLE_ARN

### 3. Phase 2: Fargate Runtime (15-20분)

```bash
# 2.1 CloudFormation 배포 (ECR, ECS Cluster)
./scripts/phase2/1-deploy-infrastructure.sh

# 2.2 Docker 빌드
./scripts/phase2/2-build-docker.sh

# 2.3 ECR 푸시
./scripts/phase2/3-push-to-ecr.sh

# 2.4 Task Definition 등록
./scripts/phase2/4-register-task.sh

# 2.5 테스트 Task 실행
./scripts/phase2/5-run-test-task.sh

# 2.6 검증
./scripts/phase2/6-verify.sh
```

**완료 시 .env 파일에 추가**:
- ECR_REPOSITORY_URI
- ECS_CLUSTER_ARN
- TASK_DEFINITION_ARN

### 4. Phase 3: AgentCore Runtime (10-15분)

```bash
# 3.1 소스 준비
./scripts/phase3/1-prepare-source.sh

# 3.2 YAML 생성
./scripts/phase3/2-create-yaml.sh

# 3.3 Runtime 배포
./scripts/phase3/3-deploy-runtime.sh

# 3.4 검증
./scripts/phase3/4-verify.sh
```

**완료 시 .env 파일에 추가**:
- RUNTIME_ID
- RUNTIME_ARN

### 5. Phase 4: Testing (20-30분)

```bash
# 4.1 간단한 Job
./scripts/phase4/1-test-simple.sh

# 4.2 복잡한 Job
./scripts/phase4/2-test-complex.sh

# 4.3 Artifacts 다운로드
./scripts/phase4/3-download-artifacts.sh
```

**✅ 전체 배포 완료!**

**총 소요 시간**: 75-105분 (약 1.5-2시간)

---

## 🧹 리소스 정리

**⚠️ 역순으로 실행해야 합니다!**

```bash
# Phase 4 정리 (Artifacts)
./scripts/cleanup/cleanup-phase-4.sh

# Phase 3 정리 (AgentCore Runtime)
./scripts/cleanup/cleanup-phase-3.sh

# Phase 2 정리 (CloudFormation Stack 삭제)
./scripts/cleanup/cleanup-phase-2.sh

# Phase 1 정리 (CloudFormation Stack 삭제)
./scripts/cleanup/cleanup-phase-1.sh
```

**Phase 1 정리 소요 시간**: 15-20분 (VPC Endpoints 삭제 대기)

---

## 📊 CloudFormation의 장점

### 1. **재사용 가능**
```bash
# Dev 환경
./scripts/phase1/deploy.sh dev

# Staging 환경
./scripts/phase1/deploy.sh staging

# Production 환경
./scripts/phase1/deploy.sh prod
```

### 2. **롤백 용이**
```bash
# 문제 발생 시 자동 롤백
aws cloudformation delete-stack --stack-name bedrock-manus-infrastructure-prod
```

### 3. **변경 관리**
```bash
# Change Set으로 변경 사항 미리 확인
aws cloudformation create-change-set \
  --stack-name bedrock-manus-infrastructure-prod \
  --template-body file://cloudformation/phase1-infrastructure.yaml \
  --change-set-name update-vpc-cidr
```

### 4. **의존성 관리**
- CloudFormation이 자동으로 리소스 생성 순서 결정
- DependsOn으로 명시적 의존성 설정 가능

### 5. **Infrastructure as Code**
- Git으로 버전 관리
- 코드 리뷰 가능
- 히스토리 추적

---

## 🔍 트러블슈팅

### CloudFormation 스택 생성 실패

```bash
# 실패 이유 확인
aws cloudformation describe-stack-events \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]' \
  --output table

# 스택 삭제 후 재시도
aws cloudformation delete-stack --stack-name bedrock-manus-infrastructure-prod
./scripts/phase1/deploy.sh
```

### VPC Endpoints 생성 시간 초과

**원인**: VPC Endpoints는 생성에 10-15분 소요

**해결**:
- 스크립트가 자동으로 대기하도록 설계됨
- `WaitCondition`을 사용하여 모든 Endpoints가 `available`이 될 때까지 대기

### Docker 빌드 실패

```bash
# Docker 데몬 확인
sudo systemctl status docker

# 수동으로 빌드
cd fargate-runtime
docker build -t bedrock-manus-fargate-runtime:latest .
```

---

## 📝 파일 구조 요약

```
production_deployment/
├── cloudformation/
│   ├── phase1-infrastructure.yaml (약 800-1000줄)
│   ├── phase2-fargate.yaml (약 100줄)
│   └── parameters/
│       ├── phase1-prod-params.json
│       └── phase2-prod-params.json
│
├── scripts/ (총 18개 스크립트)
│   ├── phase1/ (2개)
│   ├── phase2/ (6개)
│   ├── phase3/ (4개)
│   ├── phase4/ (3개)
│   └── cleanup/ (4개)
│
├── fargate-runtime/ (Docker 이미지)
├── .env.template
├── CLOUDFORMATION_GUIDE.md (이 파일)
└── STATUS.md (자동 업데이트)
```

---

**작성일**: 2025-11-01
**버전**: 1.0.0
**다음 단계**: Phase 1 CloudFormation YAML 파일 생성
