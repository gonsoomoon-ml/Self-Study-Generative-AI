#!/bin/bash

#==============================================================================
# Phase 3: AgentCore Runtime 정리 스크립트
#==============================================================================
# 설명: Phase 3에서 생성한 AgentCore Runtime을 삭제합니다.
# 사용법: ./cleanup.sh <environment> [--force]
# 예시: ./cleanup.sh prod
#       ./cleanup.sh prod --force  # 확인 없이 자동 삭제
#==============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment 설정
ENVIRONMENT=${1:-prod}
FORCE_MODE=false

if [ "$2" = "--force" ]; then
    FORCE_MODE=true
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Phase 3: AgentCore Runtime 정리${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
if [ "$FORCE_MODE" = true ]; then
    echo -e "${YELLOW}Mode: FORCE (자동 삭제)${NC}"
else
    echo -e "${YELLOW}Mode: INTERACTIVE (확인 필요)${NC}"
fi
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

# RUNTIME_ARN 확인
if [ -z "$RUNTIME_ARN" ]; then
    echo -e "${YELLOW}⚠ RUNTIME_ARN이 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}  Phase 3가 배포되지 않았거나 이미 정리되었습니다.${NC}"
    exit 0
fi

echo -e "${YELLOW}다음 리소스가 삭제됩니다:${NC}"
echo -e "  - AgentCore Runtime: ${RUNTIME_ARN}"
echo -e "  - ECR Repository: ${RUNTIME_NAME} (bedrock_agentcore가 생성한 경우)"
echo -e "  - agentcore-runtime/ 디렉토리"
echo -e "  - .env 파일의 Phase 3 섹션"
echo ""

# 확인 (Force 모드가 아닐 경우)
if [ "$FORCE_MODE" = false ]; then
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}정리가 취소되었습니다.${NC}"
        exit 0
    fi
    echo ""
fi

#------------------------------------------------------------------------------
# Step 1: AgentCore Runtime 삭제
#------------------------------------------------------------------------------

echo -e "${YELLOW}[1/4] AgentCore Runtime 삭제...${NC}"

# Runtime 존재 확인
RUNTIME_INFO=$(aws bedrock-agentcore get-agent-runtime \
    --agent-runtime-arn "$RUNTIME_ARN" \
    --region "$AWS_REGION" \
    --output json 2>/dev/null || echo "")

if [ -n "$RUNTIME_INFO" ]; then
    echo "  - Runtime ARN: $RUNTIME_ARN"

    # Runtime 삭제
    if aws bedrock-agentcore delete-agent-runtime \
        --agent-runtime-arn "$RUNTIME_ARN" \
        --region "$AWS_REGION" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Runtime 삭제 요청 완료${NC}"

        # 삭제 대기 (최대 5분)
        echo "  - 삭제 진행 중... (최대 5분)"
        MAX_WAIT=300
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            RUNTIME_STATUS=$(aws bedrock-agentcore get-agent-runtime \
                --agent-runtime-arn "$RUNTIME_ARN" \
                --region "$AWS_REGION" \
                --query 'status' \
                --output text 2>/dev/null || echo "DELETED")

            if [ "$RUNTIME_STATUS" = "DELETED" ] || [ -z "$RUNTIME_STATUS" ]; then
                echo -e "${GREEN}  ✓ Runtime 삭제 완료${NC}"
                break
            fi

            echo "    Status: $RUNTIME_STATUS (${ELAPSED}s elapsed)"
            sleep 10
            ELAPSED=$((ELAPSED + 10))
        done

        if [ $ELAPSED -ge $MAX_WAIT ]; then
            echo -e "${YELLOW}  ⚠ Runtime 삭제 시간 초과 (5분)${NC}"
            echo -e "${YELLOW}    AWS Console에서 수동으로 확인하세요.${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Runtime 삭제 실패 (이미 삭제되었을 수 있음)${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Runtime을 찾을 수 없습니다 (이미 삭제됨)${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# Step 2: ECR Repository 삭제 (bedrock_agentcore가 생성한 경우)
#------------------------------------------------------------------------------

echo -e "${YELLOW}[2/4] ECR Repository 확인...${NC}"

# bedrock_agentcore toolkit이 생성한 ECR Repository 검색
ECR_REPOS=$(aws ecr describe-repositories \
    --region "$AWS_REGION" \
    --query "repositories[?contains(repositoryName, '${RUNTIME_NAME}') || contains(repositoryName, 'bedrock') && contains(repositoryName, 'agentcore')].repositoryName" \
    --output text 2>/dev/null || echo "")

if [ -n "$ECR_REPOS" ]; then
    echo -e "${YELLOW}  다음 ECR Repository가 발견되었습니다:${NC}"
    for REPO in $ECR_REPOS; do
        echo "    - $REPO"
    done
    echo ""

    # 확인 (Force 모드가 아닐 경우)
    DELETE_ECR=false
    if [ "$FORCE_MODE" = true ]; then
        DELETE_ECR=true
    else
        read -p "  ECR Repository를 삭제하시겠습니까? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            DELETE_ECR=true
        fi
    fi

    if [ "$DELETE_ECR" = true ]; then
        for REPO in $ECR_REPOS; do
            echo "  - Deleting ECR Repository: $REPO"
            if aws ecr delete-repository \
                --repository-name "$REPO" \
                --region "$AWS_REGION" \
                --force 2>/dev/null; then
                echo -e "${GREEN}    ✓ $REPO 삭제 완료${NC}"
            else
                echo -e "${YELLOW}    ⚠ $REPO 삭제 실패${NC}"
            fi
        done
    else
        echo -e "${YELLOW}  ECR Repository 삭제를 건너뛰었습니다.${NC}"
    fi
else
    echo -e "${GREEN}  ✓ bedrock_agentcore가 생성한 ECR Repository 없음${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# Step 3: agentcore-runtime/ 디렉토리 삭제
#------------------------------------------------------------------------------

echo -e "${YELLOW}[3/4] agentcore-runtime/ 디렉토리 삭제...${NC}"

RUNTIME_DIR="$PROD_DEPLOY_DIR/agentcore-runtime"

if [ -d "$RUNTIME_DIR" ]; then
    echo "  - Directory: $RUNTIME_DIR"

    # 확인 (Force 모드가 아닐 경우)
    DELETE_DIR=false
    if [ "$FORCE_MODE" = true ]; then
        DELETE_DIR=true
    else
        read -p "  agentcore-runtime/ 디렉토리를 삭제하시겠습니까? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            DELETE_DIR=true
        fi
    fi

    if [ "$DELETE_DIR" = true ]; then
        rm -rf "$RUNTIME_DIR"
        echo -e "${GREEN}  ✓ 디렉토리 삭제 완료${NC}"
    else
        echo -e "${YELLOW}  디렉토리 삭제를 건너뛰었습니다.${NC}"
    fi
else
    echo -e "${GREEN}  ✓ 디렉토리 없음 (이미 삭제됨)${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# Step 4: .env 파일 정리
#------------------------------------------------------------------------------

echo -e "${YELLOW}[4/4] .env 파일 정리...${NC}"

# Phase 3 섹션 삭제
if grep -q "# Phase 3: AgentCore Runtime" "$ENV_FILE"; then
    # Phase 3 섹션부터 다음 Phase 섹션 전까지 또는 파일 끝까지 삭제
    sed -i '/# Phase 3: AgentCore Runtime/,/# Phase [0-9]/{ /# Phase 3: AgentCore Runtime/d; /# Phase [0-9]/!d; }' "$ENV_FILE"

    # 파일 끝까지 Phase 3만 있는 경우
    sed -i '/# Phase 3: AgentCore Runtime/,$d' "$ENV_FILE"

    echo -e "${GREEN}  ✓ .env 파일에서 Phase 3 섹션 삭제 완료${NC}"
else
    echo -e "${YELLOW}  ⚠ .env 파일에 Phase 3 섹션이 없습니다${NC}"
fi

echo ""

#------------------------------------------------------------------------------
# 정리 완료
#------------------------------------------------------------------------------

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Phase 3 정리 완료!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}삭제된 리소스:${NC}"
echo -e "  - AgentCore Runtime"
echo -e "  - ECR Repository (선택적)"
echo -e "  - agentcore-runtime/ 디렉토리 (선택적)"
echo -e "  - .env 파일의 Phase 3 섹션"
echo ""
echo -e "${YELLOW}참고:${NC}"
echo -e "  - ENI는 Runtime 삭제 시 자동으로 삭제됩니다 (수 분 소요)"
echo -e "  - CloudWatch Logs는 자동으로 삭제되지 않습니다 (수동 삭제 필요)"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo -e "  - Phase 3를 재배포하려면: ./scripts/phase3/deploy.sh ${ENVIRONMENT}"
echo -e "  - Phase 2 정리: ./scripts/phase2/cleanup.sh ${ENVIRONMENT}"
echo -e "  - Phase 1 정리: ./scripts/phase1/cleanup.sh ${ENVIRONMENT}"
echo ""
