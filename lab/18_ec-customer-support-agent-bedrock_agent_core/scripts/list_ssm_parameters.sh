#!/bin/bash

# =============================================================================
# K-Style 이커머스 고객 지원 에이전트 - SSM Parameter 조회 스크립트
# 이커머스 프로젝트 관련 SSM Parameter들을 조회하고 표시합니다
# =============================================================================

set -e
set -o pipefail

# ----- 설정 -----
ECOMMERCE_NAMESPACE="/app/ecommerce"
CUSTOMERSUPPORT_NAMESPACE="/app/customersupport"  # 기존 전자제품 프로젝트 리소스
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

echo "🛍️ K-Style 이커머스 SSM Parameter 조회"
echo "======================================="
echo "📍 Region: $REGION"
echo "🕐 조회 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ----- Parameter 조회 함수 -----
list_parameters() {
  local namespace=$1
  local description=$2
  
  echo "📋 $description"
  echo "   네임스페이스: $namespace"
  echo "   ----------------------------------------"
  
  # Parameter 존재 확인
  if aws ssm get-parameters-by-path \
    --path "$namespace" \
    --recursive \
    --region "$REGION" \
    --query "Parameters[0]" \
    --output text >/dev/null 2>&1; then
    
    # Parameter 목록 조회 및 표시
    aws ssm get-parameters-by-path \
      --path "$namespace" \
      --recursive \
      --with-decryption \
      --region "$REGION" \
      --query "Parameters[*].{Name:Name,Value:Value,Type:Type}" \
      --output table
  else
    echo "   ℹ️ Parameter가 없습니다."
  fi
  
  echo ""
}

# ----- 1. 이커머스 전용 Parameter -----
list_parameters "$ECOMMERCE_NAMESPACE" "🛍️ 이커머스 전용 Parameter"

# ----- 2. 공유 리소스 Parameter (기존 고객지원) -----
list_parameters "$CUSTOMERSUPPORT_NAMESPACE" "🔗 공유 리소스 Parameter (기존 고객지원)"

# ----- 3. AgentCore 관련 주요 Parameter 요약 -----
echo "🤖 AgentCore 주요 리소스 상태"
echo "================================"

check_resource() {
  local param_name=$1
  local resource_type=$2
  local description=$3
  
  if aws ssm get-parameter --name "$param_name" --region "$REGION" >/dev/null 2>&1; then
    local value=$(aws ssm get-parameter --name "$param_name" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || echo "조회 실패")
    echo "✅ $resource_type: $value"
    echo "   └─ $description"
  else
    echo "❌ $resource_type: 설정되지 않음"
    echo "   └─ $description"
  fi
}

# 주요 리소스 상태 확인
check_resource "/app/ecommerce/agentcore/memory_id" "Memory" "고객 개인화 메모리"
check_resource "/app/ecommerce/agentcore/gateway_id" "Gateway" "MCP 도구 통합"
check_resource "/app/ecommerce/agentcore/runtime_config_id" "Runtime" "프로덕션 배포"
check_resource "/app/customersupport/agentcore/lambda_arn" "Lambda" "반품 자격 검증"
check_resource "/app/customersupport/agentcore/cognito_user_pool_id" "Cognito" "사용자 인증"

echo ""

# ----- 4. 개발 환경 정보 -----
echo "🔧 개발 환경 정보"
echo "=================="
echo "📍 AWS Region: $REGION"
echo "🆔 Account ID: $(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo '조회 실패')"
echo "👤 IAM User/Role: $(aws sts get-caller-identity --query Arn --output text 2>/dev/null || echo '조회 실패')"
echo ""

# ----- 5. 빠른 진단 -----
echo "🩺 빠른 시스템 진단"
echo "==================="

# 필수 Parameter 체크
required_params=(
  "/app/customersupport/agentcore/lambda_arn"
  "/app/customersupport/agentcore/machine_client_id"
  "/app/customersupport/agentcore/cognito_user_pool_id"
)

missing_params=()
for param in "${required_params[@]}"; do
  if ! aws ssm get-parameter --name "$param" --region "$REGION" >/dev/null 2>&1; then
    missing_params+=("$param")
  fi
done

if [ ${#missing_params[@]} -eq 0 ]; then
  echo "✅ 모든 필수 Parameter가 설정되어 있습니다."
  echo "🚀 K-Style 이커머스 에이전트를 실행할 수 있습니다!"
else
  echo "⚠️ 누락된 필수 Parameter:"
  for param in "${missing_params[@]}"; do
    echo "   • $param"
  done
  echo ""
  echo "💡 해결 방법:"
  echo "   1. 기존 전자제품 프로젝트의 Parameter 확인"
  echo "   2. ./scripts/prereq.sh 실행하여 인프라 구성"
  echo "   3. 수동으로 필요한 리소스 생성"
fi

echo ""

# ----- 6. 유용한 명령어 안내 -----
echo "💡 유용한 명령어"
echo "================"
echo "🏃 Streamlit 앱 실행:"
echo "   streamlit run streamlit_app.py"
echo ""
echo "📚 튜토리얼 시작:"
echo "   jupyter notebook lab-01-create-ecommerce-agent.ipynb"
echo ""
echo "🧹 리소스 정리:"
echo "   ./scripts/cleanup.sh"
echo ""
echo "🔄 Parameter 새로고침:"
echo "   ./scripts/list_ssm_parameters.sh"
echo ""
echo "🛍️ K-Style 고객센터 구축을 시작하세요!"