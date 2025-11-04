#!/bin/bash

#==============================================================================
# Phase 3: AgentCore Runtime 배포 스크립트
#==============================================================================
# 설명: AgentCore Runtime을 VPC Private 모드로 배포합니다.
# 사용법: ./deploy.sh <environment>
# 예시: ./deploy.sh prod
#==============================================================================

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment 설정
ENVIRONMENT=${1:-prod}

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Phase 3: AgentCore Runtime 배포${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

#------------------------------------------------------------------------------
# 1. 사전 체크
#------------------------------------------------------------------------------

echo -e "${YELLOW}[1/7] 사전 체크...${NC}"

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROD_DEPLOY_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_ROOT="$(cd "$PROD_DEPLOY_DIR/.." && pwd)"

echo "  - Script Directory: $SCRIPT_DIR"
echo "  - Production Deployment: $PROD_DEPLOY_DIR"
echo "  - Project Root: $PROJECT_ROOT"

# .env 파일 확인
ENV_FILE="$PROD_DEPLOY_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ .env 파일이 없습니다. Phase 1, 2를 먼저 배포하세요.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ .env 파일 확인${NC}"

# .env 로드
source "$ENV_FILE"

# 필수 환경 변수 확인
REQUIRED_VARS=(
    "AWS_REGION"
    "AWS_ACCOUNT_ID"
    "VPC_ID"
    "PRIVATE_SUBNET_ID"
    "SG_AGENTCORE_ID"
    "ALB_DNS"
    "TARGET_GROUP_ARN"
    "ECS_CLUSTER_NAME"
    "S3_BUCKET_NAME"
)

for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        echo -e "${RED}✗ 환경 변수 $VAR가 설정되지 않았습니다.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}  ✓ 필수 환경 변수 확인 (${#REQUIRED_VARS[@]}개)${NC}"

# AWS CLI 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI가 설치되지 않았습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ AWS CLI 확인${NC}"

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3가 설치되지 않았습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Python3 확인${NC}"

# bedrock_agentcore toolkit 확인
if ! python3 -m pip show bedrock_agentcore_starter_toolkit &> /dev/null; then
    echo -e "${YELLOW}⚠ bedrock_agentcore_starter_toolkit이 설치되지 않았습니다.${NC}"
    echo -e "${YELLOW}  설치 중...${NC}"
    pip install bedrock_agentcore_starter_toolkit
fi

echo -e "${GREEN}  ✓ bedrock_agentcore toolkit 확인${NC}"

echo ""

#------------------------------------------------------------------------------
# 2. AgentCore Runtime 디렉토리 생성 및 파일 복사
#------------------------------------------------------------------------------

echo -e "${YELLOW}[2/7] AgentCore Runtime 소스 파일 준비...${NC}"

# agentcore-runtime 디렉토리 생성
RUNTIME_DIR="$PROD_DEPLOY_DIR/agentcore-runtime"
mkdir -p "$RUNTIME_DIR"

echo "  - Runtime Directory: $RUNTIME_DIR"

# 필수 파일 복사
echo "  - agentcore_runtime.py 복사 중..."
if [ -f "$PROJECT_ROOT/agentcore_runtime.py" ]; then
    cp "$PROJECT_ROOT/agentcore_runtime.py" "$RUNTIME_DIR/"
    echo -e "${GREEN}    ✓ agentcore_runtime.py${NC}"
else
    echo -e "${RED}    ✗ agentcore_runtime.py 없음${NC}"
    exit 1
fi

echo "  - src/ 디렉토리 복사 중..."
if [ -d "$PROJECT_ROOT/src" ]; then
    cp -r "$PROJECT_ROOT/src" "$RUNTIME_DIR/"
    echo -e "${GREEN}    ✓ src/ (graph, tools, utils, prompts)${NC}"
else
    echo -e "${RED}    ✗ src/ 디렉토리 없음${NC}"
    exit 1
fi

echo "  - requirements.txt 복사 중..."
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    cp "$PROJECT_ROOT/requirements.txt" "$RUNTIME_DIR/"
    echo -e "${GREEN}    ✓ requirements.txt${NC}"
elif [ -f "$PROJECT_ROOT/setup/requirements.txt" ]; then
    cp "$PROJECT_ROOT/setup/requirements.txt" "$RUNTIME_DIR/"
    echo -e "${GREEN}    ✓ requirements.txt (from setup/)${NC}"
else
    echo -e "${YELLOW}    ⚠ requirements.txt 없음 (생성 필요)${NC}"
    # 기본 requirements.txt 생성
    cat > "$RUNTIME_DIR/requirements.txt" <<EOF
boto3>=1.28.0
langgraph>=0.0.20
langchain>=0.1.0
python-dotenv>=1.0.0
pydantic>=2.0.0
EOF
    echo -e "${GREEN}    ✓ requirements.txt (기본값 생성)${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# 3. .bedrock_agentcore.yaml 생성
#------------------------------------------------------------------------------

echo -e "${YELLOW}[3/7] .bedrock_agentcore.yaml 생성...${NC}"

# Subnets 배열 형식으로 변환 (comma separated → yaml list)
SUBNET_ARRAY="          - ${PRIVATE_SUBNET_ID}"

# Runtime 이름 생성 (타임스탬프 포함)
TIMESTAMP=$(date +%s)
RUNTIME_NAME="bedrock_manus_runtime_${ENVIRONMENT}_${TIMESTAMP}"

echo "  - Runtime Name: $RUNTIME_NAME"
echo "  - VPC ID: $VPC_ID"
echo "  - Subnet: $PRIVATE_SUBNET_ID"
echo "  - Security Group: $SG_AGENTCORE_ID"

# .bedrock_agentcore.yaml 생성
cat > "$RUNTIME_DIR/.bedrock_agentcore.yaml" <<EOF
default_agent: ${RUNTIME_NAME}
agents:
  ${RUNTIME_NAME}:
    name: ${RUNTIME_NAME}
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
          - ${SG_AGENTCORE_ID}
          subnets:
${SUBNET_ARRAY}
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

echo -e "${GREEN}  ✓ .bedrock_agentcore.yaml 생성 완료${NC}"
echo ""

#------------------------------------------------------------------------------
# 4. 환경 변수 파일 생성
#------------------------------------------------------------------------------

echo -e "${YELLOW}[4/7] 환경 변수 파일 생성...${NC}"

cat > "$RUNTIME_DIR/.env" <<EOF
# AWS Configuration
AWS_REGION=${AWS_REGION}
AWS_DEFAULT_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

# S3 Bucket
S3_BUCKET_NAME=${S3_BUCKET_NAME}

# Fargate Configuration
FARGATE_CLUSTER_NAME=${ECS_CLUSTER_NAME}
INTERNAL_ALB_DNS=${ALB_DNS}
ALB_TARGET_GROUP_ARN=${TARGET_GROUP_ARN}

# Observability
AGENT_OBSERVABILITY_ENABLED=true
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_RESOURCE_ATTRIBUTES=service.name=deep-insight-${ENVIRONMENT}
EOF

echo -e "${GREEN}  ✓ .env 파일 생성 완료${NC}"
echo ""

#------------------------------------------------------------------------------
# 5. Runtime 배포 (bedrock_agentcore toolkit)
#------------------------------------------------------------------------------

echo -e "${YELLOW}[5/7] AgentCore Runtime 배포 시작...${NC}"
echo ""
echo -e "${BLUE}  📦 Docker 이미지 빌드 및 ECR 푸시 중...${NC}"
echo -e "${BLUE}  ⏱️  예상 소요 시간: 5-10분${NC}"
echo ""

cd "$RUNTIME_DIR"

# bedrock_agentcore configure
echo "  [1/2] Configuration..."
if ! python3 -m bedrock_agentcore_starter_toolkit configure --config .bedrock_agentcore.yaml; then
    echo -e "${RED}✗ bedrock_agentcore configure 실패${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Configuration 완료${NC}"
echo ""

# bedrock_agentcore launch
echo "  [2/2] Runtime 배포 (launch)..."
if ! python3 -m bedrock_agentcore_starter_toolkit launch; then
    echo -e "${RED}✗ bedrock_agentcore launch 실패${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Runtime 배포 완료${NC}"
echo ""

#------------------------------------------------------------------------------
# 6. Runtime ARN 가져오기
#------------------------------------------------------------------------------

echo -e "${YELLOW}[6/7] Runtime ARN 가져오기...${NC}"

# Runtime ARN 추출 (bedrock_agentcore toolkit)
RUNTIME_ARN=$(python3 -m bedrock_agentcore_starter_toolkit get-runtime-arn 2>/dev/null || true)

# 실패 시 AWS CLI로 재시도
if [ -z "$RUNTIME_ARN" ]; then
    echo "  - toolkit에서 ARN을 가져오지 못했습니다. AWS CLI로 재시도..."
    RUNTIME_ARN=$(aws bedrock-agentcore list-agent-runtimes \
        --region $AWS_REGION \
        --query "agentRuntimes[?contains(agentRuntimeName, '${RUNTIME_NAME}')].agentRuntimeArn" \
        --output text | head -1)
fi

if [ -z "$RUNTIME_ARN" ]; then
    echo -e "${RED}✗ Runtime ARN을 가져올 수 없습니다.${NC}"
    echo -e "${YELLOW}  수동으로 확인하세요: aws bedrock-agentcore list-agent-runtimes${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Runtime ARN: $RUNTIME_ARN${NC}"
echo ""

#------------------------------------------------------------------------------
# 7. .env 파일 업데이트
#------------------------------------------------------------------------------

echo -e "${YELLOW}[7/7] .env 파일 업데이트...${NC}"

# Phase 3 섹션 추가
cat >> "$ENV_FILE" <<EOF

# Phase 3: AgentCore Runtime
RUNTIME_NAME=${RUNTIME_NAME}
RUNTIME_ARN=${RUNTIME_ARN}
EOF

# Runtime 디렉토리의 .env도 업데이트
echo "RUNTIME_ARN=${RUNTIME_ARN}" >> "$RUNTIME_DIR/.env"

echo -e "${GREEN}  ✓ .env 파일 업데이트 완료${NC}"
echo ""

#------------------------------------------------------------------------------
# 배포 완료
#------------------------------------------------------------------------------

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Phase 3 배포 완료!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}Deployment Summary:${NC}"
echo -e "  Runtime Name: ${RUNTIME_NAME}"
echo -e "  Runtime ARN: ${RUNTIME_ARN}"
echo -e "  Network Mode: VPC"
echo -e "  VPC ID: ${VPC_ID}"
echo -e "  Subnet: ${PRIVATE_SUBNET_ID}"
echo -e "  Security Group: ${SG_AGENTCORE_ID}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. 검증 실행: ./scripts/phase3/verify.sh"
echo -e "  2. ENI 상태 확인: aws ec2 describe-network-interfaces --filters \"Name=vpc-id,Values=$VPC_ID\""
echo -e "  3. Phase 4 진행: 테스트 및 검증"
echo ""
echo -e "${YELLOW}참고: Runtime이 READY 상태가 되는 데 3-5분 소요될 수 있습니다.${NC}"
echo ""

cd "$PROD_DEPLOY_DIR"
