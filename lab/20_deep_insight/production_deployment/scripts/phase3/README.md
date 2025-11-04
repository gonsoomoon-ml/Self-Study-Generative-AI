# Phase 3: AgentCore Runtime 배포 스크립트

Phase 3에서는 Bedrock AgentCore Runtime을 VPC Private 모드로 배포합니다.

## 📋 사전 요구사항

- ✅ Phase 1 완료 (VPC 인프라)
- ✅ Phase 2 완료 (Fargate Runtime)
- ✅ Python 3.x 설치
- ✅ bedrock_agentcore_starter_toolkit 패키지 (자동 설치됨)

## 🚀 스크립트 사용법

### 1. deploy.sh - AgentCore Runtime 배포

**기능**:
- AgentCore Runtime 소스 파일 복사
- `.bedrock_agentcore.yaml` 자동 생성 (VPC 모드)
- bedrock_agentcore toolkit으로 Runtime 배포
- Docker 이미지 빌드 및 ECR 푸시
- Runtime ARN을 .env에 저장

**사용법**:
```bash
./deploy.sh prod
```

**예상 소요 시간**: 10-15분
- Docker 이미지 빌드: 5-7분
- ECR 푸시: 2-3분
- Runtime 생성: 3-5분

**출력**:
```
============================================
Phase 3: AgentCore Runtime 배포
Environment: prod
============================================

[1/7] 사전 체크...
  ✓ .env 파일 확인
  ✓ 필수 환경 변수 확인 (9개)
  ✓ AWS CLI 확인
  ✓ Python3 확인
  ✓ bedrock_agentcore toolkit 확인

[2/7] AgentCore Runtime 소스 파일 준비...
  ✓ agentcore_runtime.py
  ✓ src/ (graph, tools, utils, prompts)
  ✓ requirements.txt

[3/7] .bedrock_agentcore.yaml 생성...
  ✓ .bedrock_agentcore.yaml 생성 완료

[4/7] 환경 변수 파일 생성...
  ✓ .env 파일 생성 완료

[5/7] AgentCore Runtime 배포 시작...
  [1/2] Configuration...
  ✓ Configuration 완료
  [2/2] Runtime 배포 (launch)...
  ✓ Runtime 배포 완료

[6/7] Runtime ARN 가져오기...
  ✓ Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...

[7/7] .env 파일 업데이트...
  ✓ .env 파일 업데이트 완료

============================================
✓ Phase 3 배포 완료!
============================================

Deployment Summary:
  Runtime Name: bedrock_manus_runtime_prod_1730518400
  Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
  Network Mode: VPC
  VPC ID: vpc-xxx
  Subnet: subnet-xxx
  Security Group: sg-xxx
```

---

### 2. verify.sh - Runtime 검증

**기능**:
- Runtime 상태 확인 (READY 여부)
- Network Mode 확인 (VPC 모드)
- Security Group 및 Subnet 확인
- ENI 생성 확인
- CloudWatch Logs 확인 (선택 사항)

**사용법**:
```bash
./verify.sh
```

**검증 항목** (총 8개):
1. ✅ Runtime exists
2. ✅ Runtime status (READY)
3. ✅ Network mode (VPC)
4. ✅ Security group
5. ✅ Subnet
6. ✅ ENI found
7. ✅ Runtime ARN saved in .env
8. ✅ Runtime name saved in .env

**출력 예시**:
```
============================================
Phase 3: AgentCore Runtime Verification
============================================

1. Checking AgentCore Runtime...

  Runtime exists                              ✓ OK (bedrock_manus_runtime_prod_xxx)
  Runtime status                              ✓ READY
  Network mode                                ✓ VPC
  Security group                              ✓ sg-xxx
  Subnet                                      ✓ subnet-xxx

2. Checking Network Interface (ENI)...

  ✓ ENI found (count: 1)

  ENI Details:
    ID: eni-xxx
    Status: in-use
    Private IP: 10.0.1.45
    VPC: vpc-xxx

3. Checking CloudWatch Logs (optional)...

  ✓ CloudWatch Log Group found (count: 1)

  Log Group Details:
    Name: /aws/bedrock-agentcore/runtime/xxx
    Retention: 7 days

4. Checking Runtime Metadata...

  Runtime ARN saved in .env                   ✓ OK
  Runtime name saved in .env                  ✓ OK

============================================
Verification Summary
============================================

Total Checks:  8
Passed:        8

============================================
✓ All checks passed!
============================================

Runtime Information:
  Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
  Status: READY
  Network Mode: VPC

Next Steps:
  1. ENI가 생성되지 않았다면 첫 번째 Job을 실행하세요
  2. Phase 4 진행: 테스트 및 검증
```

---

### 3. cleanup.sh - Runtime 정리

**기능**:
- AgentCore Runtime 삭제
- ECR Repository 삭제 (선택적)
- agentcore-runtime/ 디렉토리 삭제 (선택적)
- .env 파일의 Phase 3 섹션 정리

**사용법**:
```bash
# Interactive 모드 (확인 필요)
./cleanup.sh prod

# Force 모드 (자동 삭제)
./cleanup.sh prod --force
```

**Interactive 모드 예시**:
```
============================================
Phase 3: AgentCore Runtime 정리
Environment: prod
Mode: INTERACTIVE (확인 필요)
============================================

다음 리소스가 삭제됩니다:
  - AgentCore Runtime: arn:aws:bedrock-agentcore:...
  - ECR Repository: bedrock_manus_runtime_prod_xxx (bedrock_agentcore가 생성한 경우)
  - agentcore-runtime/ 디렉토리
  - .env 파일의 Phase 3 섹션

계속하시겠습니까? (y/N): y

[1/4] AgentCore Runtime 삭제...
  ✓ Runtime 삭제 요청 완료
  ✓ Runtime 삭제 완료

[2/4] ECR Repository 확인...
  다음 ECR Repository가 발견되었습니다:
    - bedrock-agentcore-runtime-xxx

  ECR Repository를 삭제하시겠습니까? (y/N): y
    ✓ bedrock-agentcore-runtime-xxx 삭제 완료

[3/4] agentcore-runtime/ 디렉토리 삭제...
  agentcore-runtime/ 디렉토리를 삭제하시겠습니까? (y/N): y
  ✓ 디렉토리 삭제 완료

[4/4] .env 파일 정리...
  ✓ .env 파일에서 Phase 3 섹션 삭제 완료

============================================
✓ Phase 3 정리 완료!
============================================
```

**Force 모드** (자동 삭제):
```bash
./cleanup.sh prod --force
```
- 모든 확인 단계를 건너뛰고 자동으로 삭제합니다
- CI/CD 파이프라인에서 사용하기 적합합니다

---

## 📁 생성되는 리소스

### AWS 리소스
- **AgentCore Runtime**: VPC Private 모드
- **ECR Repository**: bedrock_agentcore toolkit이 자동 생성 (Runtime용 Docker 이미지)
- **ENI**: Runtime이 VPC에 접근하기 위한 Network Interface
- **CloudWatch Log Group**: Observability 활성화 시 (선택 사항)

### 로컬 파일
- **agentcore-runtime/**: Runtime 소스 코드 디렉토리
  - `agentcore_runtime.py`: EntryPoint
  - `src/`: Graph, Tools, Utils, Prompts
  - `.bedrock_agentcore.yaml`: Runtime 설정
  - `.env`: 환경 변수
  - `requirements.txt`: Python 의존성

- **.env 파일에 추가되는 항목**:
  ```bash
  # Phase 3: AgentCore Runtime
  RUNTIME_NAME=bedrock_manus_runtime_prod_1730518400
  RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/...
  ```

---

## 🔧 트러블슈팅

### 1. bedrock_agentcore toolkit 설치 실패

**증상**:
```
pip install bedrock_agentcore_starter_toolkit
ERROR: Could not find a version that satisfies the requirement
```

**해결**:
```bash
# Python 버전 확인 (3.8 이상 필요)
python3 --version

# pip 업그레이드
pip install --upgrade pip

# 재시도
pip install bedrock_agentcore_starter_toolkit
```

### 2. Runtime 생성 실패 (CREATE_FAILED)

**증상**:
```
bedrock_agentcore launch
ERROR: Runtime creation failed
```

**원인**:
- Subnet이 지원되지 않는 AZ에 있음
- Security Group 규칙 오류
- VPC Endpoint 미생성

**해결**:
```bash
# Runtime 상세 에러 확인
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --query 'failureReasons' \
  --output text

# AZ ID 확인 (use1-az2, use1-az4, use1-az6만 지원)
aws ec2 describe-subnets \
  --subnet-ids $PRIVATE_SUBNET_ID \
  --query 'Subnets[0].[AvailabilityZone,AvailabilityZoneId]' \
  --output table
```

### 3. ENI가 생성되지 않음

**증상**:
```
./verify.sh
⚠ ENI not found yet
```

**원인**: ENI는 첫 번째 Job 실행 시 생성됩니다.

**해결**: 정상 동작입니다. 첫 번째 Job을 실행한 후 ENI가 생성됩니다.

### 4. cleanup 시 Runtime 삭제 실패

**증상**:
```
./cleanup.sh prod
✗ Runtime 삭제 실패
```

**해결**:
```bash
# Runtime 상태 확인
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --query 'status' \
  --output text

# 수동 삭제
aws bedrock-agentcore delete-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --region us-east-1
```

---

## 📊 예상 소요 시간

| 작업 | 소요 시간 |
|------|-----------|
| deploy.sh | 10-15분 |
| verify.sh | 1-2분 |
| cleanup.sh | 3-5분 |

---

## 🎯 다음 단계

Phase 3 배포 완료 후:
1. ✅ verify.sh 실행하여 Runtime 상태 확인
2. ✅ Phase 4 진행: 테스트 및 검증
3. ✅ 첫 번째 AgentCore Job 실행

---

**작성일**: 2025-11-03
**버전**: 1.0.0
