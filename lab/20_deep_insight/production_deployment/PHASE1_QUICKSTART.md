# 🚀 Phase 1 Quick Start Guide

> Production 계정에서 Phase 1 인프라를 배포하는 빠른 시작 가이드

---

## 📋 사전 요구사항

### AWS CLI & 권한
```bash
# AWS CLI 버전 확인
aws --version  # v2.0 이상 필요

# AWS 설정 (Production 계정 자격증명)
aws configure

# 확인
aws sts get-caller-identity
```

**필요한 권한**:
- VPC, EC2, ECS, ECR 생성 권한
- CloudFormation 스택 생성 권한
- IAM Role 생성 권한 (CAPABILITY_NAMED_IAM)

---

## 🔧 Step 1: Git Clone

```bash
# Repository Clone
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git

# 프로젝트 디렉토리로 이동
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2/production_deployment

# 파일 확인
ls -la
```

**확인해야 할 파일**:
```
✓ cloudformation/phase1-infrastructure.yaml
✓ cloudformation/parameters/phase1-prod-params.json
✓ scripts/phase1/deploy.sh
✓ scripts/phase1/verify.sh
✓ .env.template
```

---

## ⚙️ Step 2: 환경 설정

### 2.1 파라미터 파일 확인 (선택 사항)

원하는 경우 Availability Zone을 변경할 수 있습니다:

```bash
# 파라미터 파일 확인
cat cloudformation/parameters/phase1-prod-params.json

# (선택) AZ 변경
vi cloudformation/parameters/phase1-prod-params.json
# "AvailabilityZone": "us-east-1a" → "us-east-1b" 등으로 변경 가능
```

**기본 설정**:
- Environment: prod
- VPC CIDR: 10.0.0.0/16
- Private Subnet: 10.0.1.0/24
- Public Subnet: 10.0.11.0/24
- Availability Zone: us-east-1a

### 2.2 스크립트 실행 권한 부여

```bash
chmod +x scripts/phase1/*.sh
```

---

## 🚀 Step 3: Phase 1 배포

### 3.1 배포 실행

```bash
./scripts/phase1/deploy.sh
```

**예상 소요 시간**: 30-40분

**배포 과정**:
1. AWS 계정 ID 자동 확인
2. CloudFormation 템플릿 검증
3. 배포 확인 (yes 입력)
4. CloudFormation 스택 생성
5. 리소스 생성 (VPC, Subnets, SG, VPC Endpoints, ALB, IAM)
6. Outputs 추출 및 .env 파일 생성

### 3.2 배포 모니터링 (별도 터미널)

```bash
# 별도 터미널에서 스택 상태 모니터링
watch -n 10 aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'Stacks[0].StackStatus' \
  --output text

# VPC Endpoints 상태 확인 (가장 오래 걸림, 10-15분)
watch -n 30 aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
  --output table
```

---

## ✅ Step 4: 배포 검증

배포가 완료되면 검증 스크립트를 실행합니다:

```bash
./scripts/phase1/verify.sh
```

**검증 항목** (20개 이상):
- ✅ VPC 생성 확인
- ✅ Private/Public Subnet 생성 확인
- ✅ NAT Gateway, Internet Gateway 확인
- ✅ Security Groups 4개 확인
- ✅ VPC Endpoints 6개 모두 `available` 상태
- ✅ ALB `active` 상태
- ✅ Target Group Health Check 활성화
- ✅ Sticky Sessions 활성화 (24시간)
- ✅ IAM Roles 생성 확인

**성공 시 출력**:
```
============================================
✓ All checks passed!
============================================

Next Steps:
  1. Proceed to Phase 2: ./scripts/phase2/1-deploy-infrastructure.sh
```

---

## 📄 Step 5: 생성된 리소스 확인

### 5.1 .env 파일 확인

```bash
cat .env
```

**자동으로 저장된 값들**:
- VPC_ID
- PRIVATE_SUBNET_ID, PUBLIC_SUBNET_ID
- Security Group IDs (4개)
- ALB_ARN, ALB_DNS, TARGET_GROUP_ARN
- IAM Role ARNs (2개)

### 5.2 AWS Console에서 확인

**VPC**:
```bash
# VPC ID 출력
echo $VPC_ID  # .env 파일을 source한 경우
source .env && echo $VPC_ID
```
→ AWS Console → VPC → Your VPCs → VPC ID 검색

**ALB**:
```bash
echo $ALB_DNS
```
→ AWS Console → EC2 → Load Balancers

**VPC Endpoints**:
```bash
aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State]' \
  --output table
```

---

## 🎯 생성된 리소스 요약

### Network (5개)
- VPC (10.0.0.0/16)
- Private Subnet (10.0.1.0/24)
- Public Subnet (10.0.11.0/24)
- Internet Gateway
- NAT Gateway

### Security Groups (4개)
- AgentCore Security Group
- ALB Security Group
- Fargate Security Group
- VPC Endpoint Security Group

### VPC Endpoints (6개)
- bedrock-agentcore (Data Plane)
- bedrock-agentcore.gateway
- ecr.api
- ecr.dkr
- logs
- s3 (Gateway)

### Load Balancer (3개)
- Internal ALB
- Target Group (Health Check + **Sticky Sessions 24h**)
- Listener (Port 80)

### IAM (2개)
- Task Execution Role
- Task Role

---

## 🔧 트러블슈팅

### 1. CloudFormation 스택 생성 실패

```bash
# 실패 이유 확인
aws cloudformation describe-stack-events \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
  --output table

# 스택 삭제 후 재시도
aws cloudformation delete-stack --stack-name bedrock-manus-infrastructure-prod
```

### 2. VPC Endpoints 생성 시간 초과

**정상**: VPC Endpoints는 10-15분 소요됩니다.

```bash
# 상태 확인
aws ec2 describe-vpc-endpoints \
  --filters "Name=tag:Environment,Values=prod" \
  --query 'VpcEndpoints[*].[ServiceName,State]' \
  --output table
```

모든 Endpoints가 `available`이 될 때까지 기다려야 합니다.

### 3. IAM 권한 부족

```bash
# Error: User is not authorized to perform: iam:CreateRole
```

**해결**: IAM User에 `IAMFullAccess` 또는 `AdministratorAccess` 권한 추가

### 4. Availability Zone 미지원

```bash
# Error: Availability Zone not supported for VPC Endpoint
```

**해결**: 파라미터 파일에서 다른 AZ로 변경
```bash
vi cloudformation/parameters/phase1-prod-params.json
# "AvailabilityZone": "us-east-1b" (또는 us-east-1c, us-east-1d)
```

---

## 🧹 리소스 정리 (테스트 후)

**⚠️ 주의**: 모든 Phase 1 리소스가 삭제됩니다!

```bash
# CloudFormation 스택 삭제
aws cloudformation delete-stack \
  --stack-name bedrock-manus-infrastructure-prod

# 삭제 확인 (15-20분 소요)
watch -n 30 aws cloudformation describe-stacks \
  --stack-name bedrock-manus-infrastructure-prod \
  --query 'Stacks[0].StackStatus' \
  --output text
```

**정리 소요 시간**: 15-20분 (VPC Endpoints 삭제 때문)

---

## 💰 Phase 1 월간 비용 (us-east-1 기준)

| 리소스 | 사양 | 월간 비용 (USD) |
|--------|------|----------------|
| NAT Gateway | 1개 | ~$32.40 |
| VPC Endpoints | 5개 (Interface) | ~$36.00 |
| ALB | Internal | ~$16.00 |
| **Phase 1 총합** | | **~$84.40/월** |

**참고**: Fargate, S3, CloudWatch Logs 비용은 Phase 2, 3에서 추가됩니다.

---

## 📞 지원

문제가 발생하면:

1. **CloudWatch Logs 확인**: CloudFormation 이벤트 로그 확인
2. **GitHub Issues**: 이슈 등록
3. **AWS Support**: Support 케이스 생성

---

## 🎉 다음 단계

Phase 1 검증이 완료되면:

1. ✅ **Phase 1 성공**: Phase 2 준비 (Fargate Runtime)
2. 📊 **피드백 제공**: GitHub Issues에 테스트 결과 공유
3. 🔄 **개선 사항**: 발견한 문제점 또는 개선 사항 제안

---

**작성일**: 2025-11-01
**버전**: 1.0.0
**테스트 환경**: us-east-1
