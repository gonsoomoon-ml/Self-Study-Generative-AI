# Phase 3: AgentCore Runtime 생성

> **소요 시간**: 10-15분
> **난이도**: 중급
> **사전 요구사항**: Phase 1, 2 완료

---

## 📋 목차

1. [개요](#개요)
2. [Step 1: AgentCore 파일 준비](#step-1-agentcore-파일-준비)
3. [Step 2: Runtime 설정 파일 생성](#step-2-runtime-설정-파일-생성)
4. [Step 3: Runtime 배포](#step-3-runtime-배포)
5. [Step 4: Runtime 검증](#step-4-runtime-검증)
6. [트러블슈팅](#트러블슈팅)

---

## 🎯 개요

이 단계에서는 Bedrock AgentCore Runtime을 VPC Private 모드로 생성합니다.

### 주요 작업

- ✅ AgentCore Runtime 소스 코드 준비
- ✅ `.bedrock_agentcore.yaml` 설정 파일 생성
- ✅ VPC 모드 Runtime 배포
- ✅ Runtime 상태 및 ENI 확인
- ✅ Runtime ARN 저장

---

## Step 1: AgentCore 파일 준비

### 1.1 필수 파일 복사

```bash
# 프로젝트 루트로 이동
cd production_deployment

# AgentCore Runtime 디렉토리 생성
mkdir -p agentcore-runtime
cd agentcore-runtime

# 필수 파일 복사
cp ../../agentcore_runtime.py .
cp -r ../../src .
cp ../../requirements.txt .
cp ../../.env.example .env

echo "✅ AgentCore Runtime 파일 복사 완료"
```

### 1.2 필수 파일 확인

```bash
# 파일 구조 확인
tree -L 2 .

# 예상 출력:
# .
# ├── agentcore_runtime.py
# ├── src/
# │   ├── graph/
# │   ├── prompts/
# │   ├── tools/
# │   └── utils/
# ├── requirements.txt
# └── .env
```

**필수 파일**:
- `agentcore_runtime.py` - EntryPoint
- `src/graph/builder.py` - Workflow graph
- `src/tools/` - Fargate tools (global_fargate_coordinator.py 등)
- `src/utils/` - Utilities (strands_sdk_utils.py 등)
- `src/prompts/` - Agent prompts (coder.md, validator.md, reporter.md)

---

## Step 2: Runtime 설정 파일 생성

### 2.1 환경 변수 로드

```bash
# Phase 1, 2에서 생성한 환경 변수 로드
cd ..
source deployment.env

# 확인
echo "VPC ID: $VPC_ID"
echo "Subnets: $PRIVATE_SUBNET_IDS"
echo "Security Group: $AGENTCORE_SECURITY_GROUP"
echo "AWS Account: $AWS_ACCOUNT_ID"
```

### 2.2 `.bedrock_agentcore.yaml` 생성

```bash
# Subnets를 배열 형식으로 변환
SUBNET_ARRAY=$(echo $PRIVATE_SUBNET_IDS | sed 's/,/\n          - /g')

# .bedrock_agentcore.yaml 생성
cat > agentcore-runtime/.bedrock_agentcore.yaml <<EOF
default_agent: bedrock_manus_runtime_${ENVIRONMENT}
agents:
  bedrock_manus_runtime_${ENVIRONMENT}:
    name: bedrock_manus_runtime_${ENVIRONMENT}
    entrypoint: ./agentcore_runtime.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      execution_role_auto_create: false
      account: '${AWS_ACCOUNT_ID}'
      region: ${AWS_REGION}
      ecr_repository: null
      ecr_auto_create: true
      network_configuration:
        network_mode: VPC
        network_mode_config:
          security_groups:
          - ${AGENTCORE_SECURITY_GROUP}
          subnets:
          - ${SUBNET_ARRAY}
      protocol_configuration:
        server_protocol: HTTP
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      agent_session_id: null
    codebuild:
      project_name: null
      execution_role: null
      source_bucket: null
    authorizer_configuration: null
    oauth_configuration: null
EOF

echo "✅ .bedrock_agentcore.yaml 생성 완료"
cat agentcore-runtime/.bedrock_agentcore.yaml
```

### 2.3 환경 변수 파일 설정

```bash
# .env 파일 업데이트
cat > agentcore-runtime/.env <<EOF
# AWS Configuration
AWS_REGION=${AWS_REGION}
AWS_DEFAULT_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

# S3 Bucket
S3_BUCKET_NAME=${S3_BUCKET_NAME}

# Fargate Configuration
FARGATE_CLUSTER_NAME=${ECS_CLUSTER_NAME}
INTERNAL_ALB_DNS=${INTERNAL_ALB_DNS}
ALB_TARGET_GROUP_ARN=${ALB_TARGET_GROUP_ARN}

# Observability
AGENT_OBSERVABILITY_ENABLED=true
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_RESOURCE_ATTRIBUTES=service.name=bedrock-manus-${ENVIRONMENT}
EOF

echo "✅ .env 파일 설정 완료"
cat agentcore-runtime/.env
```

---

## Step 3: Runtime 배포

### 3.1 bedrock_agentcore toolkit 확인

```bash
# bedrock_agentcore toolkit 설치 확인
python3 -m pip show bedrock_agentcore_starter_toolkit

# 설치되지 않은 경우:
# pip install bedrock_agentcore_starter_toolkit
```

### 3.2 Runtime 배포

```bash
# agentcore-runtime 디렉토리로 이동
cd agentcore-runtime

# Runtime 배포 (configure + launch)
bedrock_agentcore configure --config .bedrock_agentcore.yaml
bedrock_agentcore launch

echo "✅ AgentCore Runtime 배포 시작"
```

**예상 소요 시간**: 5-10분

**배포 과정**:
1. Docker 이미지 빌드 (AgentCore Runtime 컨테이너)
2. ECR에 이미지 푸시
3. Bedrock AgentCore 서비스에 등록
4. VPC ENI 생성 및 연결
5. Runtime 상태 `READY` 전환

### 3.3 배포 진행 상황 모니터링

**방법 1: Toolkit 로그 확인**
```bash
# 터미널에서 bedrock_agentcore launch 출력 확인
# 예상 로그:
# [INFO] Building Docker image...
# [INFO] Pushing to ECR...
# [INFO] Creating Runtime...
# [INFO] Runtime Status: CREATING...
# [INFO] Runtime Status: READY
```

**방법 2: AWS CLI로 확인**
```bash
# Runtime 목록 확인
aws bedrock-agentcore list-agent-runtimes \
  --region $AWS_REGION \
  --query 'agentRuntimes[?contains(agentRuntimeName, `bedrock_manus_runtime_${ENVIRONMENT}`)]' \
  --output table
```

---

## Step 4: Runtime 검증

### 4.1 Runtime ARN 가져오기

```bash
# Runtime ARN 추출
RUNTIME_ARN=$(bedrock_agentcore get-runtime-arn)

# 또는 AWS CLI로:
RUNTIME_ARN=$(aws bedrock-agentcore list-agent-runtimes \
  --region $AWS_REGION \
  --query 'agentRuntimes[?contains(agentRuntimeName, `bedrock_manus_runtime_'${ENVIRONMENT}'`)].agentRuntimeArn' \
  --output text | head -1)

echo "Runtime ARN: $RUNTIME_ARN"

# 환경 변수에 저장
cd ..
echo "RUNTIME_ARN=$RUNTIME_ARN" >> deployment.env
```

### 4.2 Runtime 상태 확인

```bash
# Runtime 상세 정보
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --region $AWS_REGION \
  --output table
```

**확인 사항**:
- [ ] Status: `READY` (또는 `ACTIVE`)
- [ ] Network Mode: `VPC`
- [ ] Subnets: Phase 1에서 생성한 Private Subnets
- [ ] Security Groups: AgentCore Security Group

### 4.3 ENI 확인

```bash
# VPC에 생성된 ENI 확인 (Bedrock AgentCore용)
aws ec2 describe-network-interfaces \
  --filters \
    "Name=vpc-id,Values=$VPC_ID" \
    "Name=description,Values=*bedrock*" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,PrivateIpAddress,Description]' \
  --output table
```

**예상 출력**:
```
----------------------------------------------------------------------
|                  DescribeNetworkInterfaces                          |
+-------------------+-----------+---------------+---------------------+
|  eni-0abc123def  |  in-use   |  10.0.1.45    |  bedrock-agentcore  |
+-------------------+-----------+---------------+---------------------+
```

**중요**: ENI가 생성되고 `in-use` 상태여야 Runtime이 정상 작동합니다.

### 4.4 Observability 확인 (선택 사항)

```bash
# CloudWatch Log Group 확인
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/bedrock-agentcore" \
  --region $AWS_REGION \
  --query 'logGroups[*].[logGroupName,creationTime]' \
  --output table
```

**참고**: Observability가 활성화되면 Runtime 실행 로그가 CloudWatch에 기록됩니다.

---

## Step 5: 최종 설정 파일 생성

### 5.1 invoke_agentcore_job.py 생성

```bash
# invoke 스크립트 생성
cat > agentcore-runtime/invoke_agentcore_job.py <<'EOF'
#!/usr/bin/env python3
"""
AgentCore Runtime Job Invoker - Production
"""
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

import boto3
from boto3.session import Session
from botocore.config import Config

# 설정
AGENT_ARN = os.getenv("RUNTIME_ARN")
if not AGENT_ARN:
    print("❌ RUNTIME_ARN 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

REGION = os.getenv("AWS_REGION", "us-east-1")

# 프롬프트 (인자로 받거나 기본값 사용)
PROMPT = sys.argv[1] if len(sys.argv) > 1 else \
    "./data/Dat-fresh-food-claude.csv 파일의 총 매출액 계산해줘."

def parse_sse_data(sse_bytes):
    """SSE 데이터 파싱"""
    if not sse_bytes or len(sse_bytes) == 0:
        return None

    try:
        text = sse_bytes.decode('utf-8').strip()
        if not text or text == '':
            return None

        if text.startswith('data: '):
            json_text = text[6:].strip()
            if json_text:
                return json.loads(json_text)
        else:
            return json.loads(text)
    except Exception:
        pass

    return None

def main():
    """AgentCore Runtime 호출"""
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"🚀 AgentCore Runtime Job 시작")
    print(f"📅 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Agent ARN: {AGENT_ARN}")
    print(f"{'='*60}\n")

    # boto3 클라이언트 생성
    my_config = Config(
        connect_timeout=60*100,
        read_timeout=3600,
        retries={'max_attempts': 0}
    )

    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name=REGION,
        config=my_config,
    )

    print(f"📤 요청 전송 중...")
    print(f"💬 프롬프트: {PROMPT}\n")

    try:
        boto3_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": PROMPT})
        )

        # 응답 처리
        if "text/event-stream" in boto3_response.get("contentType", ""):
            print(f"📥 스트리밍 응답 수신 시작...\n")

            for event in boto3_response["response"].iter_lines(chunk_size=1):
                event_data = parse_sse_data(event)
                if event_data:
                    print(f"Event: {json.dumps(event_data, indent=2)}")

        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        print(f"\n{'='*60}")
        print(f"✅ AgentCore Runtime Job 완료")
        print(f"📅 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  총 소요 시간: {elapsed_time:.2f}초 ({elapsed_time/60:.2f}분)")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x agentcore-runtime/invoke_agentcore_job.py
echo "✅ invoke_agentcore_job.py 생성 완료"
```

### 5.2 .env 파일에 RUNTIME_ARN 추가

```bash
# RUNTIME_ARN을 .env에 추가
echo "RUNTIME_ARN=$RUNTIME_ARN" >> agentcore-runtime/.env

echo "✅ .env 파일 업데이트 완료"
```

---

## Step 6: 간단한 테스트 (선택 사항)

### 6.1 빠른 테스트 실행

```bash
cd agentcore-runtime

# 간단한 프롬프트 테스트
python3 invoke_agentcore_job.py "Hello, AgentCore!"
```

**예상 출력**:
```
🚀 AgentCore Runtime Job 시작
📅 시작 시간: 2025-10-20 16:00:00
🎯 Agent ARN: arn:aws:bedrock-agentcore:us-east-1:xxx:runtime/bedrock_manus_runtime_prod-xxx
...
📥 스트리밍 응답 수신 시작...
Event: {...}
...
✅ AgentCore Runtime Job 완료
⏱️  총 소요 시간: 45.23초
```

---

## ✅ 완료 확인

다음이 모두 완료되었으면 Phase 3가 성공적으로 완료되었습니다:

- [x] AgentCore Runtime 파일 준비 완료
- [x] `.bedrock_agentcore.yaml` 생성 완료
- [x] Runtime 배포 성공
- [x] Runtime 상태: `READY`
- [x] Network Mode: `VPC`
- [x] ENI 생성 및 `in-use` 상태 확인
- [x] RUNTIME_ARN 저장 완료
- [x] `invoke_agentcore_job.py` 생성 완료

**STATUS.md 업데이트**:
```bash
# production_deployment/STATUS.md 파일을 편집하여 Phase 3 체크박스를 완료로 표시하세요
```

---

## 🔧 트러블슈팅

### 문제 1: Runtime 생성 실패 (CREATE_FAILED)

**증상**:
```
Runtime Status: CREATE_FAILED
```

**해결 방법**:
```bash
# Runtime 상세 에러 확인
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --query 'failureReasons' \
  --output text

# 일반적인 원인:
# - Subnet이 지원되지 않는 AZ에 있음
# - Security Group 규칙 오류
# - VPC Endpoint 미생성
# - Service-Linked Role 부족
```

**해결**:
1. AZ ID 확인: us-east-1a는 `use1-az2`여야 함
2. VPC Endpoints 상태 확인: 모두 `available`
3. Service-Linked Role 확인:
   ```bash
   aws iam get-role \
     --role-name AWSServiceRoleForBedrockAgentCoreNetwork
   ```

### 문제 2: ENI가 생성되지 않음

**증상**:
```
Runtime Status: READY
하지만 ENI 없음
```

**참고**: 이는 정상일 수 있습니다. ENI는 첫 Job 실행 시 생성됩니다.

**확인 방법**:
```bash
# 간단한 Job 실행 후 ENI 재확인
python3 invoke_agentcore_job.py "test"

# ENI 재확인
aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,Description]' \
  --output table
```

### 문제 3: bedrock_agentcore toolkit 에러

**증상**:
```
bedrock_agentcore: command not found
```

**해결 방법**:
```bash
# Toolkit 재설치
pip install --upgrade bedrock_agentcore_starter_toolkit

# 또는 Python 모듈로 실행
python3 -m bedrock_agentcore_starter_toolkit configure --config .bedrock_agentcore.yaml
python3 -m bedrock_agentcore_starter_toolkit launch
```

### 문제 4: VPC 모드 업데이트 실패

**증상**:
```
UPDATE_FAILED: Cannot update network mode from PUBLIC to VPC
```

**해결 방법**:
새로운 Runtime을 VPC 모드로 생성하고, 기존 PUBLIC Runtime을 삭제합니다.

```bash
# 기존 Runtime 삭제 (주의: 프로덕션에서는 신중하게)
aws bedrock-agentcore delete-agent-runtime \
  --agent-runtime-arn $OLD_RUNTIME_ARN

# 새 Runtime 생성
bedrock_agentcore launch
```

---

## 📚 다음 단계

Phase 3 완료를 축하합니다! 🎉

다음 단계로 진행하세요:

→ **[04_TESTING.md](./04_TESTING.md)** - 테스트 및 검증

---

**작성일**: 2025-10-20
**마지막 업데이트**: 2025-10-20
