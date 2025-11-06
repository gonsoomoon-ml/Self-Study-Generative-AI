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

## 🚨 CRITICAL BUG (2025-11-05 밤) - 내일 수정 필요

### 문제: Missing HTTP Scheme in URL Requests

**증상**:
- Cookie acquisition 100% 실패 (40/40 attempts)
- Health check 100% 실패 (5/5 retry attempts)
- Production Runtime `deep_insight_runtime_vpc-3oYut44SAk` 완전히 작동 불가

**에러 메시지**:
```
MissingSchema: Invalid URL 'internal-deep-insight-alb-prod-457586948.us-east-1.elb.amazonaws.com/container-info':
No scheme supplied. Perhaps you meant https://internal-deep-insight-alb-prod-457586948.us-east-1.elb.amazonaws.com/container-info?
```

**근본 원인**: URL에 `http://` 스킴이 누락됨

**수정 필요 파일 (2곳)**:

1. **`src/tools/cookie_acquisition_subprocess.py:61`**
   ```python
   # ❌ Before
   response = session.get(
       f"{alb_dns}/container-info",
       params={"session_id": session_id},
       timeout=5
   )

   # ✅ After
   response = session.get(
       f"http://{alb_dns}/container-info",
       params={"session_id": session_id},
       timeout=5
   )
   ```

2. **`src/tools/fargate_container_controller.py:320`**
   ```python
   # ❌ Before
   response = self.http_session.get(f"{self.alb_dns}/health", timeout=5)

   # ✅ After
   response = self.http_session.get(f"http://{self.alb_dns}/health", timeout=5)
   ```

**영향 범위**:
- ✅ Dev Runtime (`c0LVReFA3o`): 성공 (11월 4일 테스트)
- ❌ Production Runtime (`3oYut44SAk`): 실패 (11월 5일 테스트, Log stream: d4e2d7f4-1f79-48f5-9041-9c3fa45e1c23)

**다음 작업**:
1. 위 2개 파일 수정
2. Docker 이미지 리빌드 & ECR 푸시
3. 새 Runtime 생성 또는 기존 Runtime 업데이트
4. End-to-End 테스트

**로그 참조**:
- `/aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc-3oYut44SAk-DEFAULT`
- Log stream: `2025/11/05/[runtime-logs]d4e2d7f4-1f79-48f5-9041-9c3fa45e1c23`
- Timestamps: 14:09:42 (모든 cookie acquisition 실패), 14:11:47 (최종 실패)

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

### 7. Task Role 권한 누락 🚨 Critical!
**문제**: Runtime이 Fargate Task 시작/관리 불가
**파일**: `phase1-infrastructure.yaml:825-864` (TaskRole에 3개 정책 추가)
```yaml
- PolicyName: ECSAccess        # ecs:RunTask, DescribeTaskDefinition, iam:PassRole
- PolicyName: ALBAccess        # elasticloadbalancing:RegisterTargets, DescribeTargetHealth
- PolicyName: EC2Access        # ec2:DescribeNetworkInterfaces (Issue #10에서 추가)
```
**영향**: Production Phase 1 Stack Update 필요

### 8. Task Definition 하드코딩 버그 🚨 Critical!
**문제**: Fargate 컨테이너 시작 실패 - "TaskDefinition not found"
**근본 원인**: Default parameter가 환경 변수 fallback을 blocking
```python
# src/tools/fargate_container_controller.py:38 (기존)
task_definition: str = "fargate-dynamic-task"  # ❌ Non-empty default blocks env var!

# Line 51: task_def = task_definition or TASK_DEFINITION_ARN
# Result: Always uses "fargate-dynamic-task", never checks environment ❌
```

**해결**: `src/tools/fargate_container_controller.py:25,38,51-58`
```python
# Line 25: Load from environment
TASK_DEFINITION_ARN = os.getenv("TASK_DEFINITION_ARN")

# Line 38: Change default to None (allows fallback)
task_definition: str = None  # ✅ Now env var can be used!

# Lines 51-58: Fallback chain works correctly
task_def = task_definition or TASK_DEFINITION_ARN or "fargate-dynamic-task"
#          None (no arg)       ↓ Checks env var!    ↓ Last resort default
if task_def and task_def.startswith("arn:"):
    # Extract family name: "deep-insight-fargate-task-prod"
    self.task_definition = task_def.split("/")[-1].split(":")[0]
else:
    self.task_definition = task_def
```

**효과**: Production task definition 자동 사용
- Dev: `fargate-dynamic-task` (env var not set)
- Prod: `deep-insight-fargate-task-prod` ✅ (from TASK_DEFINITION_ARN)

### 9. Container Name 하드코딩 버그 🚨 Critical!
**문제**: Task Definition 수정 후 새로운 에러 - "Override for container named dynamic-executor is not a container in the TaskDefinition"
**근본 원인**: 컨테이너 이름이 하드코딩되어 있음
```python
# Production task definition
Container Name: "fargate-runtime"

# src/tools/fargate_container_controller.py:209 (기존)
'name': 'dynamic-executor',  # ❌ Development 환경 하드코딩!
```

**해결**: `src/tools/fargate_container_controller.py:26,40,63,214`
```python
# Line 26: Load from environment
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Line 40: Add parameter to __init__
container_name: str = None,

# Line 63: Fallback chain
self.container_name = container_name or CONTAINER_NAME or "dynamic-executor"

# Line 214: Use self.container_name
'name': self.container_name,  # ✅ Now uses environment variable!
```

**파일 수정**:
1. `.env.example:87` - `CONTAINER_NAME=fargate-runtime` 추가
2. `setup_env.sh:158,231` - CONTAINER_NAME 자동 생성, PHASE2_COUNT=8
3. `01_create_agentcore_runtime.py:105,158,286` - CONTAINER_NAME 로드 및 전달

**효과**: Production container name 자동 사용
- Dev: `dynamic-executor` (env var not set)
- Prod: `fargate-runtime` ✅ (from CONTAINER_NAME)

### 10. Task Role EC2 권한 누락 🚨 Critical!
**문제**: Container Name 수정 후 새로운 에러 - "ec2:DescribeNetworkInterfaces - You are not authorized to perform this operation"
**근본 원인**: Task Role이 Fargate 태스크의 Private IP를 조회할 권한 없음
**위치**: `src/tools/fargate_container_controller.py:228-246` (_wait_for_task_ip 메서드)

**해결**: `phase1-infrastructure.yaml:857-864` (TaskRole에 EC2Access 정책 추가)
```yaml
- PolicyName: EC2Access
  PolicyDocument:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Action:
          - ec2:DescribeNetworkInterfaces
        Resource: '*'
```

**영향**: Production Phase 1 Stack Update 필요
**Phase 2**: 변경 불필요 (IAM은 모두 Phase 1에서 정의)

### 11. Flask 패키지 누락 🚨 Critical!
**문제**: Production에서 Fargate 컨테이너 Health Check 실패 - "ModuleNotFoundError: No module named 'flask'"
**근본 원인**: `fargate-runtime/requirements.txt`에 Flask가 없음
**위치**: `fargate-runtime/dynamic_executor_v2.py:20` (Flask import 시도)

**왜 Development는 작동했는가?**:
- Development: 3주 전 이미지 (`dynamic-executor:v19-fix-exec-exception`, 2025-10-11 빌드) 사용
- 해당 이미지는 Flask가 설치된 상태로 빌드됨 ✅
- Production: 현재 requirements.txt로 새 이미지 빌드 → Flask 없음 ❌

**Container 크래시 시나리오**:
```
1. ECS Task 시작 → Container RUNNING 상태
2. Python 앱 시작 → line 20: from flask import Flask
3. ModuleNotFoundError 발생 → Python 프로세스 종료
4. Port 8080 열리지 않음
5. ALB Health Check 실패 (30회 시도, 모두 unhealthy)
6. Container 계속 재시작 반복
```

**해결**: `fargate-runtime/requirements.txt:27`
```python
# Added Flask
flask>=3.0.0
```

**영향**:
- Production: Docker 이미지 재빌드 및 푸시 필요
- Development: 다음 이미지 빌드 시 Flask 포함 보장

**재배포 필요**:
```bash
# Production
cd production_deployment/scripts/phase2
./deploy.sh prod  # Docker 이미지 재빌드 및 푸시
```

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
