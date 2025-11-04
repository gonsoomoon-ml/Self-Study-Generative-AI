#!/bin/bash

#==============================================================================
# Phase 3: AgentCore Runtime 검증 스크립트
#==============================================================================
# 설명: Phase 3에서 배포한 AgentCore Runtime을 검증합니다.
# 사용법: ./verify.sh
#==============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 카운터
TOTAL_CHECKS=0
PASSED_CHECKS=0

# 체크 함수
check() {
    local description="$1"
    local command="$2"
    local expected="$3"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    printf "  %-50s" "$description"

    result=$(eval "$command" 2>/dev/null || echo "")

    if [ "$expected" = "exists" ]; then
        if [ -n "$result" ]; then
            echo -e "${GREEN}✓ OK${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        else
            echo -e "${RED}✗ FAILED${NC}"
            return 1
        fi
    elif [ "$expected" = "not-empty" ]; then
        if [ -n "$result" ]; then
            echo -e "${GREEN}✓ OK ($result)${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        else
            echo -e "${RED}✗ FAILED (empty)${NC}"
            return 1
        fi
    else
        if [ "$result" = "$expected" ]; then
            echo -e "${GREEN}✓ $expected${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        else
            echo -e "${YELLOW}⚠ $result (expected: $expected)${NC}"
            return 1
        fi
    fi
}

#------------------------------------------------------------------------------
# 시작
#------------------------------------------------------------------------------

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Phase 3: AgentCore Runtime Verification${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROD_DEPLOY_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# .env 파일 확인
ENV_FILE="$PROD_DEPLOY_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ .env 파일이 없습니다.${NC}"
    exit 1
fi

# .env 로드
source "$ENV_FILE"

# 필수 환경 변수 확인
if [ -z "$RUNTIME_ARN" ]; then
    echo -e "${RED}✗ RUNTIME_ARN이 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}  Phase 3 배포를 먼저 실행하세요: ./scripts/phase3/deploy.sh prod${NC}"
    exit 1
fi

#------------------------------------------------------------------------------
# 1. Runtime 상태 확인
#------------------------------------------------------------------------------

echo -e "${YELLOW}1. Checking AgentCore Runtime...${NC}"
echo ""

# Runtime 상세 정보 가져오기
RUNTIME_INFO=$(aws bedrock-agentcore get-agent-runtime \
    --agent-runtime-arn "$RUNTIME_ARN" \
    --region "$AWS_REGION" \
    --output json 2>/dev/null || echo "")

if [ -z "$RUNTIME_INFO" ]; then
    echo -e "${RED}✗ Runtime을 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}  ARN: $RUNTIME_ARN${NC}"
    exit 1
fi

# Runtime 존재 확인
check "Runtime exists" \
    "echo '$RUNTIME_INFO' | jq -r '.agentRuntimeName // empty'" \
    "not-empty"

# Runtime 상태 확인
RUNTIME_STATUS=$(echo "$RUNTIME_INFO" | jq -r '.status // empty')
check "Runtime status" \
    "echo '$RUNTIME_STATUS'" \
    "READY"

# Network Mode 확인
NETWORK_MODE=$(echo "$RUNTIME_INFO" | jq -r '.networkConfiguration.networkMode // empty')
check "Network mode" \
    "echo '$NETWORK_MODE'" \
    "VPC"

# Security Group 확인
RUNTIME_SG=$(echo "$RUNTIME_INFO" | jq -r '.networkConfiguration.networkModeConfig.securityGroups[0] // empty')
check "Security group" \
    "echo '$RUNTIME_SG'" \
    "$SG_AGENTCORE_ID"

# Subnet 확인
RUNTIME_SUBNET=$(echo "$RUNTIME_INFO" | jq -r '.networkConfiguration.networkModeConfig.subnets[0] // empty')
check "Subnet" \
    "echo '$RUNTIME_SUBNET'" \
    "$PRIVATE_SUBNET_ID"

echo ""

#------------------------------------------------------------------------------
# 2. ENI 확인
#------------------------------------------------------------------------------

echo -e "${YELLOW}2. Checking Network Interface (ENI)...${NC}"
echo ""

# ENI 검색 (Bedrock AgentCore용)
ENI_INFO=$(aws ec2 describe-network-interfaces \
    --filters \
        "Name=vpc-id,Values=$VPC_ID" \
        "Name=status,Values=in-use" \
    --region "$AWS_REGION" \
    --query "NetworkInterfaces[?contains(Description, 'bedrock') || contains(Description, 'agentcore')]" \
    --output json 2>/dev/null || echo "[]")

ENI_COUNT=$(echo "$ENI_INFO" | jq 'length')

if [ "$ENI_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✓ ENI found (count: $ENI_COUNT)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))

    # ENI 상세 정보 출력
    ENI_ID=$(echo "$ENI_INFO" | jq -r '.[0].NetworkInterfaceId // empty')
    ENI_STATUS=$(echo "$ENI_INFO" | jq -r '.[0].Status // empty')
    ENI_PRIVATE_IP=$(echo "$ENI_INFO" | jq -r '.[0].PrivateIpAddress // empty')

    echo ""
    echo -e "${BLUE}  ENI Details:${NC}"
    echo -e "    ID: $ENI_ID"
    echo -e "    Status: $ENI_STATUS"
    echo -e "    Private IP: $ENI_PRIVATE_IP"
    echo -e "    VPC: $VPC_ID"
else
    echo -e "${YELLOW}  ⚠ ENI not found yet${NC}"
    echo -e "${YELLOW}    ENI는 첫 번째 Job 실행 시 생성될 수 있습니다.${NC}"
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo ""

#------------------------------------------------------------------------------
# 3. CloudWatch Logs 확인 (선택 사항)
#------------------------------------------------------------------------------

echo -e "${YELLOW}3. Checking CloudWatch Logs (optional)...${NC}"
echo ""

# AgentCore Runtime의 CloudWatch Log Group 검색
LOG_GROUP_INFO=$(aws logs describe-log-groups \
    --log-group-name-prefix "/aws/bedrock-agentcore" \
    --region "$AWS_REGION" \
    --query "logGroups[?contains(logGroupName, 'runtime') || contains(logGroupName, 'agentcore')]" \
    --output json 2>/dev/null || echo "[]")

LOG_GROUP_COUNT=$(echo "$LOG_GROUP_INFO" | jq 'length')

if [ "$LOG_GROUP_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✓ CloudWatch Log Group found (count: $LOG_GROUP_COUNT)${NC}"

    # Log Group 정보 출력
    LOG_GROUP_NAME=$(echo "$LOG_GROUP_INFO" | jq -r '.[0].logGroupName // empty')
    LOG_RETENTION=$(echo "$LOG_GROUP_INFO" | jq -r '.[0].retentionInDays // empty')

    echo ""
    echo -e "${BLUE}  Log Group Details:${NC}"
    echo -e "    Name: $LOG_GROUP_NAME"
    echo -e "    Retention: $LOG_RETENTION days"
else
    echo -e "${YELLOW}  ⚠ CloudWatch Log Group not found${NC}"
    echo -e "${YELLOW}    Observability가 활성화되지 않았을 수 있습니다.${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# 4. Runtime 메타데이터 확인
#------------------------------------------------------------------------------

echo -e "${YELLOW}4. Checking Runtime Metadata...${NC}"
echo ""

# Runtime ARN 확인
check "Runtime ARN saved in .env" \
    "grep -q 'RUNTIME_ARN=' '$ENV_FILE' && echo 'yes' || echo 'no'" \
    "yes"

# Runtime Name 확인
check "Runtime name saved in .env" \
    "grep -q 'RUNTIME_NAME=' '$ENV_FILE' && echo 'yes' || echo 'no'" \
    "yes"

echo ""

#------------------------------------------------------------------------------
# 검증 요약
#------------------------------------------------------------------------------

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "Total Checks:  ${TOTAL_CHECKS}"
echo -e "Passed:        ${GREEN}${PASSED_CHECKS}${NC}"
echo ""

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "${BLUE}Runtime Information:${NC}"
    echo -e "  Runtime ARN: ${RUNTIME_ARN}"
    echo -e "  Status: ${RUNTIME_STATUS}"
    echo -e "  Network Mode: ${NETWORK_MODE}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. ENI가 생성되지 않았다면 첫 번째 Job을 실행하세요"
    echo -e "  2. Phase 4 진행: 테스트 및 검증"
    echo ""
elif [ $PASSED_CHECKS -ge $((TOTAL_CHECKS * 80 / 100)) ]; then
    echo -e "${YELLOW}============================================${NC}"
    echo -e "${YELLOW}⚠ Most checks passed (${PASSED_CHECKS}/${TOTAL_CHECKS})${NC}"
    echo -e "${YELLOW}============================================${NC}"
    echo ""
    echo -e "${YELLOW}일부 항목이 실패했지만 Runtime은 정상적으로 작동할 수 있습니다.${NC}"
    echo -e "${YELLOW}실패한 항목을 확인하고 필요 시 수동으로 수정하세요.${NC}"
    echo ""
else
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}✗ Verification failed (${PASSED_CHECKS}/${TOTAL_CHECKS})${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo -e "${RED}Phase 3 배포에 문제가 있습니다.${NC}"
    echo -e "${YELLOW}위의 에러 메시지를 확인하고 수정하세요.${NC}"
    echo ""
    exit 1
fi
