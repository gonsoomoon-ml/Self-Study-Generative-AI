# 프로덕션 배포 가이드 - 개요

> **목표**: Bedrock Manus Multi-Agent System을 프로덕션 환경에 안전하게 배포

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [사전 요구사항](#사전-요구사항)
4. [배포 단계](#배포-단계)
5. [예상 비용](#예상-비용)
6. [보안 고려사항](#보안-고려사항)

---

## 🎯 개요

이 가이드는 다음 컴포넌트를 프로덕션 환경에 배포하는 방법을 설명합니다:

### 주요 컴포넌트

1. **VPC 인프라**
   - Private/Public Subnets (Single-AZ: us-east-1a)
   - NAT Gateway
   - Internet Gateway
   - VPC Endpoints (Bedrock AgentCore, ECR, S3, CloudWatch Logs)

2. **Fargate Runtime**
   - Python 실행 환경 (Docker 컨테이너)
   - Internal ALB
   - ECS Cluster
   - Auto-scaling

3. **Bedrock AgentCore Runtime**
   - VPC Private 모드
   - Multi-Agent Workflow (Coder → Validator → Reporter)
   - S3 Integration

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │   IGW    │
                    └────┬─────┘
                         │
    ┌────────────────────┴────────────────────┐
    │              VPC (10.0.0.0/16)          │
    │              us-east-1a                  │
    │                                          │
    │  ┌──────────────────────────────────┐  │
    │  │ Public Subnet                    │  │
    │  │ (10.0.11.0/24)                   │  │
    │  │                                   │  │
    │  │  NAT Gateway ─────────────────────┼──┼───> ECR/S3
    │  └──────────────────────────────────┘  │
    │                                          │
    │  ┌──────────────────────────────────┐  │
    │  │ Private Subnet                   │  │
    │  │ (10.0.1.0/24)                    │  │
    │  │                                   │  │
    │  │  ┌──────────────────────────┐    │  │
    │  │  │ Internal ALB             │    │  │
    │  │  └────────┬─────────────────┘    │  │
    │  │           │                       │  │
    │  │  ┌────────▼─────────────────┐    │  │
    │  │  │ Fargate Container        │    │  │
    │  │  └──────────────────────────┘    │  │
    │  └──────────────────────────────────┘  │
    │                                          │
    │  ┌──────────────────────────────────┐  │
    │  │ VPC Endpoints                    │  │
    │  │ (AgentCore, ECR, S3, Logs)       │  │
    │  └──────────────────────────────────┘  │
    └─────────────────────────────────────────┘
             ▲
             │ (via VPC Endpoint)
    ┌────────┴─────────┐
    │ Bedrock          │
    │ AgentCore        │
    │ Runtime          │
    └──────────────────┘
             ▲
             │ (HTTPS API)
    ┌────────┴─────────┐
    │ Your Client      │
    │ (Mac/EC2/Lambda) │
    └──────────────────┘
```

---

## ✅ 사전 요구사항

### 1. AWS 계정 및 권한

- [ ] AWS 계정 보유
- [ ] Administrator Access 또는 다음 권한:
  - CloudFormation
  - VPC, EC2, ECS, ECR
  - IAM (Role 생성)
  - Bedrock AgentCore
  - S3
  - CloudWatch Logs

### 2. 로컬 환경

- [ ] AWS CLI 설치 (v2.0+)
  ```bash
  aws --version
  ```

- [ ] AWS CLI 설정 완료
  ```bash
  aws configure
  # AWS Access Key ID: [입력]
  # AWS Secret Access Key: [입력]
  # Default region name: us-east-1
  # Default output format: json
  ```

- [ ] Docker 설치 (Fargate 이미지 빌드용)
  ```bash
  docker --version
  ```

- [ ] Python 3.12+ 설치
  ```bash
  python3 --version
  ```

- [ ] bedrock_agentcore toolkit 설치
  ```bash
  pip install bedrock_agentcore_starter_toolkit
  ```

### 3. 환경 정보 수집

다음 정보를 미리 결정하세요:

- [ ] **환경 이름**: `dev`, `staging`, `prod` 중 선택
- [ ] **AWS 리전**: 예) `us-east-1`
- [ ] **AWS 계정 ID**: 12자리 숫자
- [ ] **S3 버킷 이름**: 예) `bedrock-logs-prod-{account-id}`
- [ ] **VPC CIDR**: 예) `10.0.0.0/16` (기존 VPC와 겹치지 않도록)

---

## 🚀 배포 단계

전체 배포는 4단계로 진행됩니다:

### Phase 1: 인프라 배포 (30-40분)
→ **가이드**: [STEP_BY_STEP_GUIDE.md](../STEP_BY_STEP_GUIDE.md)

- CloudFormation으로 VPC, Subnets, Security Groups, ALB, ECS Cluster 생성
- VPC Endpoints 생성 (Bedrock AgentCore, ECR, S3, Logs)
- IAM Roles 생성

**결과물**:
- VPC ID
- Subnet IDs
- Security Group IDs
- ALB DNS Name
- ECS Cluster Name

### Phase 2: Fargate Runtime 배포 (15-20분)
→ **가이드**: [02_FARGATE_RUNTIME.md](./02_FARGATE_RUNTIME.md)

- Docker 이미지 빌드 (Python 실행 환경)
- ECR에 이미지 푸시
- ECS Task Definition 등록
- 테스트 Task 실행

**결과물**:
- ECR Repository URI
- Docker Image URI
- Task Definition ARN

### Phase 3: AgentCore Runtime 생성 (10-15분)
→ **가이드**: [03_AGENTCORE_RUNTIME.md](./03_AGENTCORE_RUNTIME.md)

- Phase 1 결과를 기반으로 환경 설정 파일 생성
- `.bedrock_agentcore.yaml` 생성
- AgentCore Runtime 배포 (VPC Private 모드)
- Runtime 상태 확인

**결과물**:
- Runtime ARN
- Runtime ID

### Phase 4: 테스트 및 검증 (10-15분)
→ **가이드**: [04_TESTING.md](./04_TESTING.md)

- 네트워크 연결 테스트
- 간단한 Job 실행 (총 매출액 계산)
- 복잡한 Job 실행 (PDF 보고서 생성)
- 로그 확인 및 성능 검증

**결과물**:
- 테스트 성공 확인
- 성능 메트릭
- 프로덕션 준비 완료

---

## 💰 예상 비용

### 월간 운영 비용 (us-east-1 기준)

| 리소스 | 사양 | 월간 비용 (USD) |
|--------|------|----------------|
| NAT Gateway | 1개 | ~$32.40 |
| VPC Endpoints | 5개 (Interface) | ~$36.00 |
| ALB | Internal | ~$16.00 |
| Fargate | 1 vCPU, 2GB RAM, 10시간/월 | ~$4.00 |
| S3 | 10GB 저장, 1,000 요청 | ~$0.50 |
| CloudWatch Logs | 5GB 수집/월 | ~$2.50 |
| **합계** | | **~$91.40/월** |

### 비용 절감 방안

1. **NAT Gateway 제거**: VPC Endpoints만 사용 (~$32 절감)
   - 단, ECR/S3/CloudWatch 외 인터넷 연결 불가

2. **Fargate Spot 사용**: 70% 할인 (~$3 절감)
   - 중단 가능한 워크로드에 적합

3. **Auto-scaling**: 미사용 시 Task 0으로 (~$4 절감)
   - Cold start 발생 (첫 실행 느림)

4. **개발 환경 Public 모드 사용**: VPC 리소스 불필요 (~$80 절감)
   - 보안 수준 낮음, 프로덕션에는 비추천

---

## 🔒 보안 고려사항

### 1. 네트워크 보안

- ✅ **Private Subnet**: Fargate 컨테이너는 Private Subnet에서 실행
- ✅ **Internal ALB**: 외부 인터넷에서 직접 접근 불가
- ✅ **VPC Endpoints**: 인터넷 경유 없이 AWS 서비스 접근
- ✅ **Security Groups**: 최소 권한 원칙 (Principle of Least Privilege)

### 2. IAM 권한

- ✅ **Task Role**: Fargate가 S3/Bedrock만 접근 가능
- ✅ **Execution Role**: ECS가 ECR/CloudWatch만 접근 가능
- ✅ **Service-Linked Role**: Bedrock AgentCore가 VPC에 ENI 생성

### 3. 데이터 보호

- ✅ **S3 암호화**: SSE-S3 또는 SSE-KMS
- ✅ **CloudWatch Logs 암호화**: KMS Key 사용 (선택)
- ✅ **VPC Flow Logs**: 네트워크 트래픽 모니터링

### 4. Secrets Management

- ⚠️ **현재**: 환경 변수에 하드코딩
- ✅ **권장**: AWS Secrets Manager 또는 Parameter Store 사용

---

## 📊 배포 후 확인사항

배포 완료 후 다음을 확인하세요:

- [ ] VPC 및 Subnets 생성 확인
- [ ] Security Groups 규칙 검증
- [ ] VPC Endpoints 상태 `available`
- [ ] ALB Health Check 통과
- [ ] Fargate Task `RUNNING` 상태
- [ ] AgentCore Runtime `READY` 상태
- [ ] 테스트 Job 실행 성공
- [ ] CloudWatch Logs 정상 수집
- [ ] S3에 Artifacts 업로드 확인

---

## 🆘 트러블슈팅

문제 발생 시 다음을 확인하세요:

### CloudFormation 스택 실패
```bash
# 스택 이벤트 확인
aws cloudformation describe-stack-events \
  --stack-name {스택-이름} \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]' \
  --output table
```

### Fargate Task 시작 실패
```bash
# Task 상세 정보 확인
aws ecs describe-tasks \
  --cluster {클러스터-이름} \
  --tasks {task-arn} \
  --query 'tasks[0].stoppedReason'
```

### AgentCore Runtime Health Check 실패
```bash
# ENI 확인 (Runtime이 VPC에 연결되었는지)
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*bedrock*" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,PrivateIpAddress]' \
  --output table
```

---

## 📚 다음 단계

준비가 완료되었다면 다음 가이드로 진행하세요:

→ **[STEP_BY_STEP_GUIDE.md](../STEP_BY_STEP_GUIDE.md)** - 인프라 배포 시작

---

## 📝 참고 문서

- [AWS Bedrock AgentCore 공식 문서](https://docs.aws.amazon.com/bedrock/)
- [VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-best-practices.html)
- [ECS Fargate 가이드](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [CloudFormation 템플릿 레퍼런스](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html)

---

**작성일**: 2025-10-20
**마지막 업데이트**: 2025-10-20
