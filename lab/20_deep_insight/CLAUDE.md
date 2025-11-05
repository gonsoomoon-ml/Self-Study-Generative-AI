# Claude Code 작업 일지

> 📦 상세 히스토리: `CLAUDE.md.backup_20251105` 참조

---

## 🔄 Development/Production Workflow

**⚠️ IMPORTANT**: This environment is a **development account**.

### Workflow Process
1. **Development**: Code changes and testing are performed in this development account
2. **Git Push**: Once tasks are completed, code is pushed to the git repository
3. **Production Testing**: Code is deployed and tested in a **production account** (which Claude Code cannot access)
4. **Error Feedback Loop**: If errors occur in production:
   - User provides error messages from the production account
   - Claude Code fixes the code in the development account
   - Fixed code is pushed to git and re-tested in production

This iterative process ensures that all code is properly tested before final production deployment.

---

## 🎯 프로젝트 현황

### ✅ Production Ready - VPC Runtime 완전 작동

**현재 상태**: VPC Private 모드에서 Multi-Agent Workflow 완전 작동 확인 (2025-11-04)

---

## 🚀 현재 배포 상태

### Production VPC Runtime

**Runtime 정보**:
- Runtime ID: `deep_insight_runtime_vpc-c0LVReFA3o`
- Runtime ARN: `arn:aws:bedrock-agentcore:us-east-1:057716757052:runtime/deep_insight_runtime_vpc-c0LVReFA3o`
- Network Mode: **VPC** (Test VPC: vpc-05975448296a22c21)
- Status: **READY** ✅
- 생성 시간: 2025-11-04 11:20:02 UTC

**네트워크 구성**:
- VPC CIDR: 10.100.0.0/16
- Subnet: subnet-0b2fb367d6e823a79 (Private, use1-az2)
- Security Group: sg-0affaea9ac4dc26b1
- Internal ALB: test-vpc-private-alb
- Target Group: test-vpc-private-tg

**검증 완료**:
- ✅ End-to-End 네트워크 플로우 (Mac → Bedrock → VPC → ALB → Fargate)
- ✅ Fargate Container 정상 작동 (ECR image pull, Health check, Code execution)
- ✅ Multi-Agent Workflow (Coder → Validator → Reporter)
- ✅ S3 File Sync
- ✅ PDF 보고서 생성

---

## 📊 주요 AWS 리소스

### ECS/Fargate
- Cluster: `my-fargate-cluster`
- Task Definition: `fargate-dynamic-task:6`
- Docker Image: `057716757052.dkr.ecr.us-east-1.amazonaws.com/dynamic-executor:v19-fix-exec-exception`

### VPC Infrastructure
- Test VPC: `vpc-05975448296a22c21` (10.100.0.0/16)
- NAT Gateway: `nat-084c84d8f7ab9ac5c`
- VPC Endpoints: Bedrock AgentCore (2), ECR (2), CloudWatch Logs, S3

### Security Groups
- AgentCore: `sg-0affaea9ac4dc26b1`
- ALB: `sg-061896ca7967f6183`
- Fargate: `sg-0e1314a2421686c2c`
- VPC Endpoint: `sg-085cf66da6c4027d2`

### S3
- Bucket: `bedrock-logs-gonsoomoon`

---

## 🔧 최근 해결한 주요 문제

### 1. 환경 변수 이름 불일치 (2025-11-05)
**문제**: Production에서 Runtime 시작 실패 - `TARGET_GROUP_ARN` vs `ALB_TARGET_GROUP_ARN` 불일치
**해결**: 모든 스크립트와 문서를 `ALB_TARGET_GROUP_ARN`으로 통일
**영향**: Production Runtime 재생성 필요

### 2. Security Group 규칙 누락 (ECR 접근 불가)
**문제**: Fargate가 ECR에서 Docker 이미지를 pull하지 못함
**해결**: VPC Endpoint SG에 Fargate SG로부터의 HTTPS(443) 인바운드 규칙 추가

### 3. ALB Target Group VPC 불일치
**문제**: Default VPC의 Target Group 사용 시 ValidationError
**해결**: Test VPC용 Target Group으로 변경

### 4. Retry 로직 개선
**문제**: Non-retryable 에러도 재시도하여 시간 낭비
**해결**: ValidationException 등은 즉시 실패, Throttling 등만 재시도

---

## 🎯 다음 단계

### Production 계정 배포
1. **Phase 1**: VPC, ALB, Security Groups, VPC Endpoints, IAM Roles
   - CloudFormation: `production_deployment/cloudformation/phase1-infrastructure.yaml`
   - 예상 시간: 30-40분

2. **Phase 2**: ECR, Docker Image, ECS Cluster, Task Definition
   - CloudFormation: `production_deployment/cloudformation/phase2-fargate.yaml`
   - Three-Stage 배포 (ECR → Docker → Full Stack)
   - 예상 시간: 15-20분

3. **Phase 3**: AgentCore Runtime VPC 모드 생성
   - Script: `01_create_agentcore_runtime.py`
   - 예상 시간: 10-15분

4. **Phase 4**: 통합 테스트 및 검증
   - 예상 시간: 10-30분

**총 예상 시간**: 65-105분 (약 1-2시간)

---

## 📚 주요 문서

### Production 배포 가이드
- `production_deployment/README.md` - 메인 가이드
- `production_deployment/DEPLOYMENT_WORKFLOW.md` - 배포 워크플로우
- `production_deployment/PHASE3_QUICKSTART.md` - Phase 3 배포 가이드

### 스크립트
- `01_create_agentcore_runtime.py` - Runtime 생성/업데이트 (VPC 모드)
- `02_agentcore_runtime.py` - Runtime 실행 (로컬 테스트)
- `03_invoke_agentcore_job_vpc.py` - Runtime 호출 (VPC)

### 분석 보고서
- `assets/VPC_Job_실행_네트워크_워크플로우_보고서.md` - VPC 네트워크 플로우 분석
- `CLAUDE.md.backup_20251105` - 상세 작업 히스토리 (1469줄)

---

## 💰 비용 고려

**Test VPC 월간 비용** (24/7 운영 시):
- NAT Gateway: ~$32.40/월
- VPC Endpoints (Interface 5개): ~$36.00/월
- Fargate Task (실행 시): ~$0.04/시간
- **총 ~$68/월**

**권장**: 테스트 완료 후 미사용 리소스 정리 고려

---

**마지막 업데이트**: 2025-11-05
**상태**: Production Ready - VPC Runtime 완전 작동 ✅
**환경**: Development Account (AWS Account: 057716757052)
