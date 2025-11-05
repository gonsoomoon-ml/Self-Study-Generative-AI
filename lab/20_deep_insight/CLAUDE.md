# Claude Code 작업 일지

> 📦 상세 히스토리: `CLAUDE.md.backup_20251105_detailed` 참조

---

## 🎯 프로젝트 현황

**상태**: ✅ **Production Ready** - VPC Runtime 완전 작동 (2025-11-04 검증)

**개발 환경**: Development Account (057716757052, us-east-1)
**배포 방식**: Dev → Git Push → Production Account → Feedback Loop

---

## 🚀 현재 배포 상태

### VPC Runtime
- **Runtime ID**: `deep_insight_runtime_vpc-c0LVReFA3o`
- **Network Mode**: VPC (Test VPC: vpc-05975448296a22c21, 10.100.0.0/16)
- **Status**: READY ✅
- **검증 완료**: End-to-End 네트워크 플로우, Multi-Agent Workflow, PDF 보고서 생성

### 주요 AWS 리소스
```
ECS Cluster:      my-fargate-cluster
Task Definition:  fargate-dynamic-task:6
Docker Image:     v19-fix-exec-exception
VPC:              vpc-05975448296a22c21 (10.100.0.0/16)
Subnet:           subnet-0b2fb367d6e823a79 (use1-az2)
Security Groups:
  - AgentCore:    sg-0affaea9ac4dc26b1
  - ALB:          sg-061896ca7967f6183
  - Fargate:      sg-0e1314a2421686c2c
  - VPC Endpoint: sg-085cf66da6c4027d2
S3 Bucket:        bedrock-logs-gonsoomoon
```

---

## 🔧 주요 수정 사항 (2025-11-05)

### 1. Fargate 네트워크 환경 변수 추가 ⭐
**파일**: `production_deployment/scripts/phase3/deploy.sh:236-237`
```bash
FARGATE_SUBNET_IDS=${PRIVATE_SUBNET_1_ID},${PRIVATE_SUBNET_2_ID}
FARGATE_SECURITY_GROUP_IDS=${SG_FARGATE_ID}
```

### 2. Security Group 규칙 추가 ⭐
**파일**: `production_deployment/cloudformation/phase1-infrastructure.yaml`
- VPC Endpoint SG: HTTPS from VPC CIDR
- AgentCore SG: All traffic from VPC Endpoint
- AgentCore SG: HTTPS from Fargate SG

### 3. IAM 권한 추가 ⭐
**파일**: `production_deployment/cloudformation/phase1-infrastructure.yaml`
```yaml
# ECS 권한 (line 757)
- ecs:DescribeTaskDefinition

# CloudWatch Logs Delivery (lines 730-738)
- logs:CreateDelivery, PutDeliverySource, PutDeliveryDestination
- logs:GetDelivery, DescribeDeliveries, DeleteDelivery
- logs:UpdateDeliveryConfiguration, DescribeDeliverySource, DescribeDeliveryDestination

# Bedrock 권한 (lines 748, 823)
- bedrock:AllowVendedLogDeliveryForResource
```

### 4. OTEL 환경 변수 추가 ✅
**파일**: `.env.example`, `01_create_agentcore_runtime.py`
- 6개 OTEL 변수로 per-invocation 로그 스트림 활성화

### 5. 자동화 스크립트 생성 ✅
**파일**: `production_deployment/scripts/setup_env.sh` (354줄)
- CloudFormation Outputs에서 .env 자동 생성 (프로젝트 루트)
- 35개 환경 변수 자동화

### 6. 환경 파일 구조 정리 ✅
**최종 구조**:
```
프로젝트 루트/
├── .env              # 실제 환경 변수 (Git 제외)
├── .env.example      # 템플릿 (Git 포함)
└── production_deployment/scripts/setup_env.sh
```

### 7. Task Role ECS/ALB 권한 누락 🚨 Critical!
**문제**: Runtime이 Fargate Task 시작 불가
**파일**: `phase1-infrastructure.yaml:825-856` (TaskRole에 2개 정책 추가)
```yaml
- PolicyName: ECSAccess        # ecs:RunTask, DescribeTaskDefinition, iam:PassRole
- PolicyName: ALBAccess        # elasticloadbalancing:RegisterTargets, DescribeTargetHealth
```
**영향**: Production Phase 1 Stack Update 필요

### 8. Task Definition 하드코딩 버그 🚨 Critical!
**문제**: Fargate 컨테이너 시작 실패 - "TaskDefinition not found"
**원인**: 개발 환경 값 하드코딩 ("fargate-dynamic-task")
```python
# src/tools/fargate_container_controller.py:37 (기존)
task_definition: str = "fargate-dynamic-task"  # ❌ Development value hardcoded!
```

**해결**: `src/tools/fargate_container_controller.py:25,51-58`
```python
# Line 25: Load from environment
TASK_DEFINITION_ARN = os.getenv("TASK_DEFINITION_ARN")

# Lines 51-58: Use environment variable and extract family name from ARN
task_def = task_definition or TASK_DEFINITION_ARN or "fargate-dynamic-task"
if task_def and task_def.startswith("arn:"):
    # Extract family name: "deep-insight-fargate-task-prod"
    self.task_definition = task_def.split("/")[-1].split(":")[0]
else:
    self.task_definition = task_def
```

**효과**: Production task definition 자동 사용
- Dev: `fargate-dynamic-task`
- Prod: `deep-insight-fargate-task-prod` ✅

---

## 🎯 Production 배포 단계

1. **Phase 1**: VPC, ALB, Security Groups, IAM (30-40분)
   - CloudFormation: `phase1-infrastructure.yaml`

2. **Phase 2**: ECR, Docker, ECS Cluster (15-20분)
   - CloudFormation: `phase2-fargate.yaml`
   - Three-Stage: ECR → Docker → Full Stack

3. **Phase 3**: AgentCore Runtime (10-15분)
   - Script: `01_create_agentcore_runtime.py`

4. **Phase 4**: 통합 테스트 (10-30분)
   - Script: `03_invoke_agentcore_job_vpc.py`

**총 예상 시간**: 65-105분 (약 1-2시간)

---

## 📚 주요 문서

**배포 가이드**:
- `production_deployment/README.md` - 메인 가이드
- `production_deployment/DEPLOYMENT_WORKFLOW.md` - 배포 워크플로우
- `production_deployment/PHASE3_QUICKSTART.md` - Phase 3 상세

**분석 보고서**:
- `assets/VPC_Job_실행_네트워크_워크플로우_보고서.md` - VPC 네트워크 플로우
- `CLAUDE.md.backup_20251105_detailed` - 상세 이슈 히스토리

**스크립트**:
- `01_create_agentcore_runtime.py` - Runtime 생성/업데이트
- `03_invoke_agentcore_job_vpc.py` - Runtime 호출 테스트

---

## 🛠️ 빠른 트러블슈팅

### Runtime 시작 실패
- ✅ FARGATE_SUBNET_IDS, FARGATE_SECURITY_GROUP_IDS 환경 변수 확인
- ✅ Security Group 규칙 확인 (VPC Endpoint → ECR 접근)
- ✅ IAM 권한 확인 (ecs:DescribeTaskDefinition, logs:CreateDelivery)

### ECR 접근 불가
- ✅ VPC Endpoint SG: HTTPS from VPC CIDR 규칙 확인
- ✅ NAT Gateway 상태 확인
- ✅ Route Table 확인 (0.0.0.0/0 → NAT Gateway)

### 로그 스트림 미생성
- ✅ OTEL 환경 변수 확인 (6개)
- ✅ CloudWatch Logs Delivery 권한 확인 (9개)
- ✅ bedrock:AllowVendedLogDeliveryForResource 권한 확인

---

## 💰 비용

**Test VPC 월간 비용** (24/7):
- NAT Gateway: ~$32/월
- VPC Endpoints: ~$36/월
- **총**: ~$68/월

---

**마지막 업데이트**: 2025-11-05
**상태**: Production Ready ✅
**환경**: Development Account (057716757052)
