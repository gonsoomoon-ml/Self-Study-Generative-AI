# 🚀 Phase 1 단계별 배포 가이드 (CloudFormation)

> **목표**: Production 계정에서 Phase 1 인프라를 CloudFormation으로 배포

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [Git Repository Clone](#2-git-repository-clone)
3. [Phase 1 배포](#3-phase-1-배포)
4. [검증](#4-검증)
5. [다음 단계](#5-다음-단계)

---

## 1. 사전 준비

### 1.1 AWS CLI 설치 및 설정

```bash
# AWS CLI 버전 확인 (v2.0 이상 필요)
aws --version

# Production 계정 자격증명 설정
aws configure
```

**입력 정보**:
- AWS Access Key ID: `<Production 계정 Access Key>`
- AWS Secret Access Key: `<Production 계정 Secret Key>`
- Default region name: `us-east-1`
- Default output format: `json`

**확인**:
```bash
aws sts get-caller-identity
```

### 1.2 필수 IAM 권한 확인

다음 권한이 필요합니다:
- ✅ `EC2FullAccess`
- ✅ `ElasticLoadBalancingFullAccess`
- ✅ `IAMFullAccess`
- ✅ `CloudFormationFullAccess`

**권한 확인**:
```bash
# 현재 사용자의 정책 확인
aws iam list-attached-user-policies \
  --user-name $(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
```

---

## 2. Git Repository Clone

### 2.1 Repository Clone

```bash
# GitHub에서 Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git

# 프로젝트 디렉토리로 이동
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment
```

### 2.2 파일 확인

```bash
# Phase 1 관련 파일 확인
ls -l cloudformation/phase1-infrastructure.yaml
ls -l cloudformation/parameters/phase1-prod-params.json
ls -l scripts/phase1/deploy.sh
ls -l scripts/phase1/verify.sh
```

**예상 출력**:
```
-rw-r--r-- 1 user group 22K cloudformation/phase1-infrastructure.yaml
-rw-r--r-- 1 user group 588 cloudformation/parameters/phase1-prod-params.json
-rwxr-xr-x 1 user group 12K scripts/phase1/deploy.sh
-rwxr-xr-x 1 user group 8K  scripts/phase1/verify.sh
```

---

## 3. Phase 1 배포

### 3.1 배포 스크립트 실행 권한 부여

```bash
chmod +x scripts/phase1/*.sh
```

### 3.2 Phase 1 배포 시작

```bash
# Production 환경으로 배포
./scripts/phase1/deploy.sh prod
```

### 3.3 배포 과정

**자동 실행되는 단계**:

1. ✅ **사전 체크** (1분)
   - AWS CLI 설치 확인
   - AWS 자격증명 확인
   - CloudFormation 템플릿 검증

2. ✅ **Account ID 주입** (1분)
   - `phase1-prod-params.json`의 `ACCOUNT_ID` 플레이스홀더를 실제 Account ID로 치환

3. ✅ **CloudFormation 스택 배포** (30-40분)
   - Stack 이름: `deep-insight-infrastructure-prod`
   - 리소스 생성 시작

4. ✅ **스택 출력값 추출** (1분)
   - 생성된 리소스 ID를 `.env` 파일에 저장

### 3.4 배포 모니터링 (별도 터미널)

배포 중 별도 터미널에서 진행 상황을 모니터링할 수 있습니다:

```bash
# 스택 상태 확인 (10초마다 갱신)
watch -n 10 "aws cloudformation describe-stacks \
  --stack-name deep-insight-infrastructure-prod \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus' \
  --output text"
```

**스택 상태 변화**:
```
CREATE_IN_PROGRESS → CREATE_COMPLETE (성공)
CREATE_IN_PROGRESS → ROLLBACK_IN_PROGRESS → ROLLBACK_COMPLETE (실패)
```

### 3.5 예상 배포 시간

| 리소스 | 예상 시간 |
|--------|-----------|
| VPC, Subnets | 2-3분 |
| Internet Gateway | 1분 |
| NAT Gateway | 5-7분 |
| Security Groups | 1-2분 |
| VPC Endpoints (6개) | 15-20분 |
| ALB + Target Group | 3-5분 |
| IAM Roles | 1-2분 |
| **총 예상 시간** | **30-40분** |

### 3.6 배포 완료 확인

배포가 성공하면 다음과 같은 메시지가 표시됩니다:

```bash
============================================
✓ Stack deployment successful!
============================================

Created Resources:

Network:
  VPC ID:            vpc-xxxxxxxxxxxxx
  Private Subnet:    subnet-xxxxxxxxxxxxx (us-east-1a)
  Public Subnet:     subnet-xxxxxxxxxxxxx (us-east-1a)

Security Groups:
  AgentCore SG:      sg-xxxxxxxxxxxxx
  ALB SG:            sg-xxxxxxxxxxxxx
  Fargate SG:        sg-xxxxxxxxxxxxx
  VPC Endpoint SG:   sg-xxxxxxxxxxxxx

Load Balancer:
  ALB ARN:           arn:aws:elasticloadbalancing:us-east-1:...
  ALB DNS:           deep-insight-alb-prod-xxxxx.us-east-1.elb.amazonaws.com
  Target Group:      arn:aws:elasticloadbalancing:us-east-1:...

IAM Roles:
  Task Execution:    arn:aws:iam::123456789012:role/deep-insight-task-execution-role-prod
  Task Role:         arn:aws:iam::123456789012:role/deep-insight-task-role-prod

Next Steps:
  1. Run verification: ./scripts/phase1/verify.sh
  2. Proceed to Phase 2: (Phase 1 완료 후 진행)
```

---

## 4. 검증

### 4.1 자동 검증 스크립트 실행

```bash
./scripts/phase1/verify.sh
```

### 4.2 검증 항목 (총 15개 체크)

**1. VPC 및 네트워크 리소스** (5개):
- VPC 존재 확인
- Private Subnet 존재 확인
- Public Subnet 존재 확인
- NAT Gateway available 확인
- Internet Gateway attached 확인

**2. Security Groups** (4개):
- AgentCore Security Group
- ALB Security Group
- Fargate Security Group
- VPC Endpoint Security Group

**3. VPC Endpoints** (7개):
- 총 6개 엔드포인트 확인
- 각 엔드포인트 available 상태 확인
  - bedrock-agentcore-control
  - bedrock-agentcore
  - ecr.api
  - ecr.dkr
  - logs
  - s3 (Gateway)

**4. Application Load Balancer** (3개):
- ALB State: active
- Target Group Health Check 활성화
- Sticky Sessions 활성화

**5. IAM Roles** (2개):
- Task Execution Role 존재 확인
- Task Role 존재 확인

### 4.3 검증 성공 출력

모든 검증이 통과하면:

```bash
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

### 4.4 .env 파일 확인

생성된 리소스 ID 확인:

```bash
cat .env
```

**예상 내용**:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

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
ALB_DNS=deep-insight-alb-prod-xxxxx.us-east-1.elb.amazonaws.com
TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:...

# IAM Roles
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::123456789012:role/...
TASK_ROLE_ARN=arn:aws:iam::123456789012:role/...
```

---

## 5. 다음 단계

### 5.1 Phase 1 완료 체크리스트

- [x] AWS CLI 설정 완료
- [x] Git Repository Clone 완료
- [x] Phase 1 CloudFormation 배포 성공
- [x] 모든 리소스 검증 통과 (15/15)
- [x] `.env` 파일 생성 및 확인 완료

### 5.2 다음 작업

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

### 5.3 리소스 정리 (테스트 환경)

테스트 환경에서 비용 절감을 위해 리소스를 정리하려면:

```bash
# CloudFormation 스택 삭제 (모든 리소스 한 번에 정리)
aws cloudformation delete-stack \
  --stack-name deep-insight-infrastructure-prod \
  --region us-east-1

# 삭제 완료 대기 (10-15분)
aws cloudformation wait stack-delete-complete \
  --stack-name deep-insight-infrastructure-prod \
  --region us-east-1

# .env 파일 삭제
rm .env
```

---

## 📊 요약

### 전체 프로세스

```
1. 사전 준비 (5분)
   └─ AWS CLI 설정 + IAM 권한 확인

2. Git Clone (2분)
   └─ Repository 다운로드 + 파일 확인

3. Phase 1 배포 (30-40분)
   └─ CloudFormation 스택 배포

4. 검증 (2-3분)
   └─ 15개 항목 자동 검증

총 소요 시간: 40-50분
```

### 주요 명령어

| 작업 | 명령어 |
|------|--------|
| **배포** | `./scripts/phase1/deploy.sh prod` |
| **검증** | `./scripts/phase1/verify.sh` |
| **리소스 확인** | `cat .env` |
| **정리** | `aws cloudformation delete-stack --stack-name deep-insight-infrastructure-prod` |

---

**작성일**: 2025-11-02
**버전**: 2.0.0 (CloudFormation 기반)
**작성자**: Claude Code
