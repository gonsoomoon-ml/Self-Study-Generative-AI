# Phase 3: AgentCore Runtime 실행 가이드

## 📋 개요

Phase 3에서는 AgentCore Runtime을 VPC Private 모드로 생성하고 테스트합니다.

**노트북 자동화**: `agentcore_runtime.ipynb`의 로직을 3개의 Python 스크립트로 자동화했습니다.

---

## 🎯 실행 순서

### 1️⃣ 01_create_agentcore_runtime.py - Runtime 생성

**목적**: VPC Private 모드로 AgentCore Runtime 생성

**주요 작업**:
- `production_deployment/.env`에서 VPC 정보 로드
- 기존 IAM Role 재사용 (Phase 1에서 생성)
- `.bedrock_agentcore.yaml` 생성 (VPC 설정 포함)
- AWS CLI로 `create-agent-runtime` 호출
- Runtime ARN을 `.env`에 저장

**실행**:
```bash
python3 01_create_agentcore_runtime.py
```

**예상 소요 시간**: 5-10분

**출력 예시**:
```
============================================================
AgentCore Runtime 생성 (VPC Private 모드)
============================================================

[1/7] 환경 설정 로드...
✅ 환경 설정 로드 완료
  - Region: us-east-1
  - VPC: vpc-xxxxx
  - Subnet: subnet-xxxxx
  - Security Group: sg-xxxxx

[2/7] IAM Role 설정...
✅ 기존 IAM Role 재사용: arn:aws:iam::xxx:role/...

[3/7] AgentCore Runtime 설정...
✅ Configuration 완료
  - Config: .bedrock_agentcore.yaml
  - Dockerfile: Dockerfile

[4/7] VPC 설정 추가...
⚠️  버그 우회: configure()가 VPC 설정을 YAML에 저장하지 못함
ℹ️  YAML 파일을 수동으로 수정합니다

✅ VPC 설정 추가 완료
  - Network Mode: VPC
  - Subnets: subnet-xxxxx
  - Security Groups: sg-xxxxx
  - Observability: ENABLED (CloudWatch Logs)

[5/7] AgentCore Runtime 생성...
⚠️  SDK 버그 우회: AWS CLI로 직접 create-agent-runtime 호출

  - Runtime Name: bedrock_manus_runtime_vpc_1730518400
  - ECR Image: xxx.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest

🚀 Runtime 생성 중...
✅ Runtime 생성 요청 완료
  - ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
  - ID: bedrock_manus_runtime_vpc_1730518400-PtBWr17D4z
  - Status: CREATING

[6/7] Runtime 상태 확인...
⏳ Runtime이 READY 상태가 될 때까지 대기 중...

  Status: CREATING
  Status: READY

✅ Runtime이 READY 상태입니다!

ℹ️  🔒 VPC Private 연결 활성화
ℹ️     모든 트래픽이 VPC Endpoint를 통해 전송됩니다

[7/7] .env 파일 업데이트...
✅ .env 파일 업데이트 완료
  - RUNTIME_NAME: bedrock_manus_runtime_vpc_1730518400
  - RUNTIME_ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...

============================================================
✅ AgentCore Runtime 생성 완료!
============================================================

Runtime 정보:
  Runtime Name: bedrock_manus_runtime_vpc_1730518400
  Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
  Network Mode: VPC
  VPC ID: vpc-xxxxx
  Subnet: subnet-xxxxx
  Security Group: sg-xxxxx

다음 단계:
  1. Runtime이 완전히 시작될 때까지 1-2분 대기
  2. 테스트 실행: python3 03_invoke_agentcore_job_vpc.py
```

---

### 2️⃣ 02_agentcore_runtime.py - Runtime 진입점

**목적**: AgentCore Runtime의 진입점 (Fargate Container에서 실행)

**주요 작업**:
- Strands SDK와 Bedrock AgentCore 통합
- Fargate 세션 관리
- 스트리밍 실행
- Observability 제공

**실행**: 이 파일은 직접 실행하지 않습니다. AgentCore Runtime이 자동으로 실행합니다.

**참고**: 기존 `agentcore_runtime.py`와 동일한 파일입니다.

---

### 3️⃣ 03_invoke_agentcore_job_vpc.py - Runtime 테스트

**목적**: VPC 모드로 배포된 AgentCore Runtime 테스트

**주요 작업**:
- `production_deployment/.env`에서 Runtime ARN 로드
- AgentCore Runtime 호출
- 스트리밍 응답 처리
- 에러 발생 시 CloudWatch Logs에 기록

**실행**:
```bash
python3 03_invoke_agentcore_job_vpc.py
```

**예상 소요 시간**:
- 간단한 프롬프트: 2-5분
- 복잡한 프롬프트 (PDF 보고서): 20-25분

**출력 예시**:
```
============================================================
🚀 AgentCore Runtime Job 시작
📅 시작 시간: 2025-11-03 15:30:00
🎯 Agent ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
🌐 Region: us-east-1
============================================================

📤 요청 전송 중...
💬 프롬프트: ./data/Dat-fresh-food-claude.csv 파일을 분석해서 총 매출액을 계산하고...

📥 스트리밍 응답 수신 시작...

[Supervisor] Planning...
[Coder] Executing...
[Validator] Validating...
[Reporter] Generating report...

============================================================
✅ AgentCore Runtime Job 완료
📅 종료 시간: 2025-11-03 15:50:00
⏱️  총 소요 시간: 1200.00초 (20.00분)
============================================================
```

---

## 📁 파일 구조

### 새로 생성된 파일 (번호 접두사로 실행 순서 명시)

```
05_insight_extractor_strands_sdk_workshop_phase_2/
├── 01_create_agentcore_runtime.py      # ✅ Runtime 생성
├── 02_agentcore_runtime.py              # ✅ Runtime 진입점
├── 03_invoke_agentcore_job_vpc.py       # ✅ Runtime 테스트
└── PHASE3_EXECUTION_GUIDE.md            # ✅ 이 파일
```

### 백업 파일 (원본 유지)

```
├── agentcore_runtime.py.backup
├── invoke_agentcore_job_vpc.py.backup
└── agentcore_runtime.ipynb              # 원본 노트북
```

---

## ⚙️ 설정 파일

### production_deployment/.env

**Phase 1에서 생성**:
```bash
# Phase 1: Infrastructure
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
VPC_ID=vpc-xxxxx
PRIVATE_SUBNET_ID=subnet-xxxxx
SG_AGENTCORE_ID=sg-xxxxx
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::xxx:role/...
```

**Phase 3에서 추가** (01_create_agentcore_runtime.py 실행 후):
```bash
# Phase 3: AgentCore Runtime
RUNTIME_NAME=bedrock_manus_runtime_vpc_1730518400
RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
RUNTIME_ID=bedrock_manus_runtime_vpc_1730518400-PtBWr17D4z
```

---

## 🔧 주의사항

### 1. bedrock_agentcore SDK 버그

**문제**: `agentcore_runtime.configure()`가 VPC `network_mode_config`를 YAML에 저장하지 못합니다.

**해결**: 01_create_agentcore_runtime.py가 YAML 파일을 수동으로 수정합니다.

### 2. 지원되는 AZ

**중요**: Bedrock AgentCore는 특정 AZ만 지원합니다.

**us-east-1 지원 AZ**:
- ✅ use1-az1 (us-east-1d)
- ✅ use1-az2 (us-east-1a) ← 사용 중
- ✅ use1-az4 (us-east-1b)
- ❌ use1-az6 (us-east-1c) - **지원 안 됨!**

**Phase 1에서** `PRIVATE_SUBNET_ID`가 use1-az2 (us-east-1a)에 생성되어야 합니다.

### 3. Observability 활성화

**필수**: CloudWatch Logs를 활성화해야 디버깅이 가능합니다.

01_create_agentcore_runtime.py가 자동으로 활성화합니다:
```yaml
observability:
  enabled: true
```

---

## 🧪 테스트 시나리오

### 간단한 테스트 (2-5분)

03_invoke_agentcore_job_vpc.py에서 프롬프트 수정:
```python
PROMPT = "./data/Dat-fresh-food-claude.csv 파일의 총 매출액 계산해줘. PDF 보고서는 만들지 마."
```

### 복잡한 테스트 (20-25분)

기본 프롬프트 사용:
```python
PROMPT = "./data/Dat-fresh-food-claude.csv 파일을 분석해서 총 매출액을 계산하고, 카테고리별 매출 비중도 함께 보여줘. 그리고 pdf 로 보고서 생성해줘"
```

---

## 🛟 트러블슈팅

### 문제 1: .env 파일이 없음

**증상**:
```
❌ .env 파일이 없습니다: production_deployment/.env
⚠️  Phase 1, 2를 먼저 배포하세요
```

**해결**: Phase 1, 2를 먼저 배포하세요.

### 문제 2: RUNTIME_ARN이 없음

**증상**:
```
❌ RUNTIME_ARN이 설정되지 않았습니다
⚠️  01_create_agentcore_runtime.py를 먼저 실행하세요
```

**해결**: 01_create_agentcore_runtime.py를 먼저 실행하세요.

### 문제 3: Runtime 생성 실패 (CREATE_FAILED)

**원인**:
- Subnet이 지원되지 않는 AZ에 있음
- Security Group 규칙 오류
- VPC Endpoint 미생성

**해결**:
```bash
# AZ ID 확인
aws ec2 describe-subnets \
  --subnet-ids $PRIVATE_SUBNET_ID \
  --query 'Subnets[0].[AvailabilityZone,AvailabilityZoneId]'

# use1-az2, use1-az4, use1-az1만 지원됨
```

### 문제 4: Health Check 실패

**원인**: Container가 시작되지 않음

**해결**:
1. CloudWatch Logs 확인 (Observability 활성화 필요)
2. Security Group 규칙 확인
3. Fargate Task가 실행 중인지 확인

---

## 📊 비용

**Phase 3 추가 비용**:
- AgentCore Runtime: $0 (실행 시간만 과금)
- ECR Repository: ~$0.10/월
- CloudWatch Logs: ~$0.50/월
- **총 ~$0.60/월** (Runtime 미실행 시)

**Runtime 실행 시**:
- Fargate Task: ~$0.04/시간 (실행 중일 때만)

---

## 🎯 다음 단계

Phase 3 완료 후:
1. ✅ 개발 계정에서 테스트
2. ✅ Git에 푸시
3. ✅ Production 계정에서 배포
4. ✅ Phase 4 진행: 통합 테스트 및 검증

---

**작성일**: 2025-11-03
**버전**: 1.0.0
**참고**: agentcore_runtime.ipynb의 자동화 버전
