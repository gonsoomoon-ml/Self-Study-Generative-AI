# Bedrock Manus - 프로덕션 배포 가이드

> **Bedrock AgentCore Multi-Agent System**을 프로덕션 환경에 배포하기 위한 완전한 가이드

---

## 🎯 개요

이 디렉토리는 Bedrock Manus Multi-Agent System을 프로덕션 AWS 환경에 배포하기 위한 모든 리소스를 포함합니다.

**주요 특징**:
- ✅ Infrastructure as Code (CloudFormation)
- ✅ VPC Private 모드 지원
- ✅ Multi-AZ 고가용성
- ✅ 단계별 배포 가이드
- ✅ 자동화 스크립트
- ✅ 프로덕션 보안 best practices

---

## 📁 폴더 구조

```
production_deployment/
├── README.md                     # 이 파일
├── STATUS.md                     # 배포 진행 상황 추적
│
├── docs/                         # 📚 단계별 배포 가이드
│   ├── 00_OVERVIEW.md            # 전체 개요 및 아키텍처
│   ├── 01_INFRASTRUCTURE.md      # Phase 1: 인프라 배포
│   ├── 02_FARGATE_RUNTIME.md     # Phase 2: Fargate Runtime 배포
│   ├── 03_AGENTCORE_RUNTIME.md   # Phase 3: AgentCore Runtime 생성
│   └── 04_TESTING.md             # Phase 4: 테스트 및 검증
│
├── cloudformation/               # ☁️ CloudFormation 템플릿
│   └── infrastructure.yaml       # (생성 예정) VPC, ALB, Fargate, VPC Endpoints
│
├── parameters/                   # ⚙️ 환경별 파라미터
│   ├── dev-params.json           # (생성 예정) Development 환경
│   ├── staging-params.json       # (생성 예정) Staging 환경
│   └── prod-params.json          # (생성 예정) Production 환경
│
├── scripts/                      # 🔧 자동화 스크립트
│   ├── deploy.sh                 # (생성 예정) 전체 배포 오케스트레이션
│   ├── deploy-fargate-runtime.sh # (생성 예정) Fargate Docker 빌드/푸시
│   └── cleanup.sh                # (생성 예정) 리소스 정리
│
├── monitoring/                   # 📊 모니터링 및 알람
│   └── dashboard.json            # (생성 예정) CloudWatch Dashboard
│
├── agentcore-runtime/            # (배포 시 생성) AgentCore Runtime 소스
│   ├── agentcore_runtime.py
│   ├── src/
│   ├── .bedrock_agentcore.yaml
│   └── invoke_agentcore_job.py
│
└── deployment.env                # (배포 시 생성) 환경 변수
```

---

## 🚀 빠른 시작

### 1. 사전 요구사항 확인

```bash
# AWS CLI 설치 확인
aws --version  # v2.0 이상 필요

# Docker 설치 확인 (Fargate 이미지 빌드용)
docker --version

# Python 3.12+ 확인
python3 --version

# bedrock_agentcore toolkit 설치
pip install bedrock_agentcore_starter_toolkit
```

### 2. 배포 가이드 읽기

**필수 읽기 순서**:

1. **[00_OVERVIEW.md](./docs/00_OVERVIEW.md)** ⭐
   - 전체 아키텍처 이해
   - 사전 요구사항 확인
   - 예상 비용 검토

2. **[STATUS.md](./STATUS.md)**
   - 배포 진행 상황 추적

### 3. 단계별 배포 시작

배포는 **4개 Phase**로 진행됩니다:

#### Phase 1: 인프라 배포 (30-40분)
→ **[01_INFRASTRUCTURE.md](./docs/01_INFRASTRUCTURE.md)**

- VPC, Subnets, NAT Gateway, IGW
- Security Groups
- VPC Endpoints (Bedrock, ECR, S3, Logs)
- Internal ALB
- ECS Cluster
- IAM Roles

**결과**: VPC ID, Subnet IDs, ALB DNS, Security Group IDs

#### Phase 2: Fargate Runtime 배포 (15-20분)
→ **[02_FARGATE_RUNTIME.md](./docs/02_FARGATE_RUNTIME.md)**

- Docker 이미지 빌드 (Python 실행 환경)
- ECR에 이미지 푸시
- ECS Task Definition 등록
- 테스트 Task 실행

**결과**: ECR Image URI, Task Definition ARN

#### Phase 3: AgentCore Runtime 생성 (10-15분)
→ **[03_AGENTCORE_RUNTIME.md](./docs/03_AGENTCORE_RUNTIME.md)**

- AgentCore Runtime 소스 준비
- VPC 모드 설정 파일 생성
- Runtime 배포
- Runtime 상태 확인

**결과**: Runtime ARN, ENI ID

#### Phase 4: 테스트 및 검증 (10-30분)
→ **[04_TESTING.md](./docs/04_TESTING.md)**

- 기본 연결 테스트
- 간단한 Job 실행 (총 매출액 계산)
- 복잡한 Job 실행 (PDF 보고서 생성)
- 성능 검증

**결과**: 프로덕션 준비 완료 확인

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
    │                                          │
    │  ┌──────────────┐    ┌──────────────┐  │
    │  │ Public       │    │ Public       │  │
    │  │ Subnet A     │    │ Subnet B     │  │
    │  │  (us-east-1a)│    │  (us-east-1c)│  │
    │  │  NAT GW ─────┼────┼──────────────┼──┼───> ECR/S3
    │  └──────────────┘    └──────────────┘  │
    │                                          │
    │  ┌──────────────┐    ┌──────────────┐  │
    │  │ Private      │    │ Private      │  │
    │  │ Subnet A     │    │ Subnet B     │  │
    │  │  (us-east-1a)│    │  (us-east-1c)│  │
    │  │ ┌──────────┐ │    │ ┌──────────┐ │  │
    │  │ │ Internal │◄├────┤►│ Fargate  │ │  │
    │  │ │   ALB    │ │    │ │ Container│ │  │
    │  │ └────▲─────┘ │    │ └──────────┘ │  │
    │  └──────┼────────┘    └──────────────┘  │
    │         │                                │
    │  ┌──────▼──────────┐                    │
    │  │ VPC Endpoints   │                    │
    │  │ (AgentCore,ECR) │                    │
    │  └─────────────────┘                    │
    └─────────────────────────────────────────┘
             ▲
             │ (VPC Private Connection)
    ┌────────┴─────────┐
    │ Bedrock          │
    │ AgentCore        │
    │ Runtime (VPC)    │
    └──────────────────┘
             ▲
             │ (HTTPS API)
    ┌────────┴─────────┐
    │ Your Client      │
    │ (Mac/EC2/Lambda) │
    └──────────────────┘
```

**주요 특징**:
- ✅ **Private Subnets**: Fargate 컨테이너는 Private에서만 실행
- ✅ **Internal ALB**: 외부 인터넷 접근 불가
- ✅ **VPC Endpoints**: AWS 서비스에 Private 연결
- ✅ **Multi-AZ**: 고가용성을 위한 2개 AZ 배포

---

## 💰 예상 비용

### 월간 운영 비용 (us-east-1 기준)

| 리소스 | 사양 | 월간 비용 (USD) |
|--------|------|----------------|
| NAT Gateway | 1개 | ~$32.40 |
| VPC Endpoints | 5개 (Interface) | ~$36.00 |
| ALB | Internal | ~$16.00 |
| Fargate | 1 vCPU, 2GB, 10시간/월 | ~$4.00 |
| S3 | 10GB, 1,000 요청 | ~$0.50 |
| CloudWatch Logs | 5GB/월 | ~$2.50 |
| **합계** | | **~$91.40/월** |

**비용 절감 방안**:
- NAT Gateway 제거 (VPC Endpoints만 사용): -$32/월
- Fargate Spot 사용: -70% (Fargate 비용)
- Auto-scaling (미사용 시 0 Task): -$4/월

---

## 🔒 보안 Best Practices

이 배포 가이드는 다음 보안 원칙을 따릅니다:

### 1. 네트워크 격리
- ✅ Fargate는 Private Subnet에서만 실행
- ✅ Internal ALB (인터넷 접근 불가)
- ✅ VPC Endpoints (인터넷 경유 없이 AWS 서비스 접근)

### 2. 최소 권한 원칙
- ✅ Security Groups: 필요한 포트만 개방
- ✅ IAM Roles: 최소 권한만 부여
- ✅ S3 Bucket Policy: 특정 리소스만 접근 가능

### 3. 데이터 보호
- ✅ S3 암호화: SSE-S3 (또는 SSE-KMS)
- ✅ CloudWatch Logs 암호화
- ✅ VPC Flow Logs (네트워크 트래픽 모니터링)

### 4. Secrets Management
- ⚠️ 현재: 환경 변수 사용
- ✅ 권장: AWS Secrets Manager 또는 Parameter Store

---

## 📊 모니터링 & 운영

### CloudWatch Logs

- **Fargate Runtime**: `/ecs/fargate-runtime-{environment}`
- **AgentCore Runtime**: `/aws/bedrock-agentcore/runtimes/...`

### CloudWatch Metrics

- ECS Task CPU/Memory 사용률
- ALB 요청 수, 에러율
- VPC Endpoint 트래픽
- S3 업로드 성공/실패

### 알람 설정 (권장)

- Fargate Task 실패
- ALB 5XX 에러 증가
- VPC Endpoint 연결 실패
- S3 업로드 실패

---

## 🆘 트러블슈팅

### 일반적인 문제

**CloudFormation 스택 생성 실패**
→ [01_INFRASTRUCTURE.md](./docs/01_INFRASTRUCTURE.md#트러블슈팅)

**Docker 빌드/푸시 실패**
→ [02_FARGATE_RUNTIME.md](./docs/02_FARGATE_RUNTIME.md#트러블슈팅)

**AgentCore Runtime Health Check 실패**
→ [03_AGENTCORE_RUNTIME.md](./docs/03_AGENTCORE_RUNTIME.md#트러블슈팅)

**Job 실행 에러**
→ [04_TESTING.md](./docs/04_TESTING.md#트러블슈팅)

### 로그 확인

```bash
# Fargate Runtime 로그
aws logs tail /ecs/fargate-runtime-prod --follow

# AgentCore Runtime 로그
aws logs tail /aws/bedrock-agentcore/runtimes/... --follow

# CloudFormation 스택 이벤트
aws cloudformation describe-stack-events \
  --stack-name bedrock-manus-infrastructure-prod
```

---

## 📚 추가 리소스

### 공식 문서

- [AWS Bedrock AgentCore 공식 문서](https://docs.aws.amazon.com/bedrock/)
- [VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-best-practices.html)
- [ECS Fargate 가이드](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [CloudFormation 레퍼런스](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html)

### 프로젝트 문서

- [CLAUDE.md](../CLAUDE.md) - 전체 프로젝트 히스토리
- [README.md](../README.md) - 메인 프로젝트 README

---

## 🔄 업데이트 및 유지보수

### 배포 업데이트

```bash
# 1. Fargate Runtime 업데이트 (새 Docker 이미지)
cd production_deployment
./scripts/deploy-fargate-runtime.sh prod

# 2. AgentCore Runtime 업데이트 (코드 변경)
cd agentcore-runtime
bedrock_agentcore launch

# 3. 인프라 업데이트 (CloudFormation 변경)
aws cloudformation deploy \
  --template-file cloudformation/infrastructure.yaml \
  --stack-name bedrock-manus-infrastructure-prod \
  --parameter-overrides file://parameters/prod-params.json
```

### 리소스 정리

```bash
# ⚠️ 주의: 모든 리소스가 삭제됩니다!

# 1. AgentCore Runtime 삭제
bedrock_agentcore delete-runtime

# 2. Fargate Tasks 중지
aws ecs list-tasks --cluster {cluster-name} | xargs -I {} aws ecs stop-task --task {}

# 3. CloudFormation 스택 삭제
aws cloudformation delete-stack \
  --stack-name bedrock-manus-infrastructure-prod

# 4. ECR 이미지 삭제
aws ecr batch-delete-image \
  --repository-name fargate-runtime-prod \
  --image-ids imageTag=latest

# 5. S3 버킷 비우기 및 삭제
aws s3 rm s3://bedrock-logs-prod-{account-id} --recursive
aws s3 rb s3://bedrock-logs-prod-{account-id}
```

---

## 🎯 다음 단계

1. **[00_OVERVIEW.md](./docs/00_OVERVIEW.md)** 읽기 - 전체 이해
2. **[STATUS.md](./STATUS.md)** 확인 - 진행 상황 추적
3. **Phase 1부터 순차 진행** - 단계별 배포

---

## 📞 지원

문제가 발생하면:

1. 각 Phase의 트러블슈팅 섹션 참조
2. CloudWatch Logs 확인
3. AWS Support 케이스 생성
4. GitHub Issues 등록

---

**작성일**: 2025-10-20
**마지막 업데이트**: 2025-10-20
**버전**: 1.0.0
