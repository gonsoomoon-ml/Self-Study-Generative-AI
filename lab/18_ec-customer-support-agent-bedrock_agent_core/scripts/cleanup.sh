#!/bin/bash

# =============================================================================
# K-Style 이커머스 고객 지원 에이전트 - 리소스 정리 스크립트
# 생성된 AWS 리소스들을 안전하게 삭제합니다
# =============================================================================

set -e
set -o pipefail

# ----- 설정 -----
BUCKET_NAME=${1:-ecommerce-support}
INFRA_STACK_NAME=${2:-EcommerceCustomerSupportStackInfra}
COGNITO_STACK_NAME=${3:-EcommerceCustomerSupportStackCognito}
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FULL_BUCKET_NAME="${BUCKET_NAME}-${ACCOUNT_ID}-${REGION}"
ZIP_FILE="ecommerce_lambda.zip"

echo "🛍️ K-Style 이커머스 리소스 정리"
echo "=================================="
echo "📍 Region: $REGION"
echo "🆔 Account ID: $ACCOUNT_ID"
echo "🪣 S3 Bucket: $FULL_BUCKET_NAME"
echo ""
echo "🗑️ 삭제될 리소스:"
echo "   • CloudFormation 스택: $INFRA_STACK_NAME"
echo "   • CloudFormation 스택: $COGNITO_STACK_NAME"
echo "   • S3 버킷 및 콘텐츠: $FULL_BUCKET_NAME"
echo "   • 로컬 ZIP 파일: $ZIP_FILE"
echo ""

# ----- 삭제 확인 -----
read -p "⚠️ 정말로 K-Style 이커머스 리소스를 모두 삭제하시겠습니까? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "❌ 정리 작업이 취소되었습니다."
  echo "💡 리소스들이 그대로 유지됩니다."
  exit 1
fi

echo ""
echo "🚨 리소스 삭제를 시작합니다..."

# ----- 1. CloudFormation 스택 삭제 -----
delete_stack() {
  local stack_name=$1
  
  # 스택 존재 확인
  if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$REGION" >/dev/null 2>&1; then
    echo "🧨 스택 삭제 중: $stack_name"
    
    aws cloudformation delete-stack --stack-name "$stack_name" --region "$REGION"
    
    echo "⏳ 스택 삭제 대기 중: $stack_name (시간이 걸릴 수 있습니다...)"
    if aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$REGION" 2>/dev/null; then
      echo "✅ 스택 삭제 완료: $stack_name"
    else
      echo "⚠️ 스택 삭제 대기 중 타임아웃: $stack_name (백그라운드에서 계속 삭제됩니다)"
    fi
  else
    echo "ℹ️ 스택이 존재하지 않습니다: $stack_name"
  fi
}

# 인프라 스택 삭제
delete_stack "$INFRA_STACK_NAME"

# Cognito 스택 삭제  
delete_stack "$COGNITO_STACK_NAME"

# ----- 2. S3 버킷 정리 -----
echo ""
echo "🧹 S3 버킷 정리 중..."

if aws s3api head-bucket --bucket "$FULL_BUCKET_NAME" 2>/dev/null; then
  echo "🗑️ S3 버킷 내용 삭제 중: $FULL_BUCKET_NAME"
  aws s3 rm "s3://$FULL_BUCKET_NAME" --recursive || echo "⚠️ 버킷 정리 실패 또는 이미 비어있음"
  
  # 버킷 삭제 여부 확인
  read -p "🪣 S3 버킷 '$FULL_BUCKET_NAME'도 삭제하시겠습니까? (y/N): " delete_bucket
  if [[ "$delete_bucket" == "y" || "$delete_bucket" == "Y" ]]; then
    echo "🚮 S3 버킷 삭제 중: $FULL_BUCKET_NAME"
    aws s3 rb "s3://$FULL_BUCKET_NAME" --force
    echo "✅ S3 버킷 삭제 완료"
  else
    echo "🪣 S3 버킷 유지: $FULL_BUCKET_NAME"
  fi
else
  echo "ℹ️ S3 버킷이 존재하지 않습니다: $FULL_BUCKET_NAME"
fi

# ----- 3. AgentCore 리소스 정리 -----
echo ""
echo "🤖 AgentCore 리소스 정리 확인..."

# Gateway 정리
echo "🚪 AgentCore Gateway 정리..."
if aws ssm get-parameter --name "/app/ecommerce/agentcore/gateway_id" --region "$REGION" >/dev/null 2>&1; then
  GATEWAY_ID=$(aws ssm get-parameter --name "/app/ecommerce/agentcore/gateway_id" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || echo "")
  
  if [ ! -z "$GATEWAY_ID" ]; then
    read -p "🚪 AgentCore Gateway ($GATEWAY_ID)를 삭제하시겠습니까? (y/N): " delete_gateway
    if [[ "$delete_gateway" == "y" || "$delete_gateway" == "Y" ]]; then
      echo "🗑️ Gateway 삭제 중: $GATEWAY_ID"
      aws bedrock-agentcore-control delete-gateway --gateway-identifier "$GATEWAY_ID" --region "$REGION" || echo "⚠️ Gateway 삭제 실패"
      aws ssm delete-parameter --name "/app/ecommerce/agentcore/gateway_id" --region "$REGION" 2>/dev/null || true
      echo "✅ Gateway 삭제 완료"
    fi
  fi
fi

# Memory 정리  
echo "🧠 AgentCore Memory 정리..."
if aws ssm get-parameter --name "/app/ecommerce/agentcore/memory_id" --region "$REGION" >/dev/null 2>&1; then
  MEMORY_ID=$(aws ssm get-parameter --name "/app/ecommerce/agentcore/memory_id" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || echo "")
  
  if [ ! -z "$MEMORY_ID" ]; then
    read -p "🧠 AgentCore Memory ($MEMORY_ID)를 삭제하시겠습니까? (y/N): " delete_memory
    if [[ "$delete_memory" == "y" || "$delete_memory" == "Y" ]]; then
      echo "🗑️ Memory 삭제 중: $MEMORY_ID"
      aws bedrock-agentcore-memory delete-memory --memory-identifier "$MEMORY_ID" --region "$REGION" || echo "⚠️ Memory 삭제 실패"
      aws ssm delete-parameter --name "/app/ecommerce/agentcore/memory_id" --region "$REGION" 2>/dev/null || true
      echo "✅ Memory 삭제 완료"
    fi
  fi
fi

# Runtime 정리
echo "🏃 AgentCore Runtime 정리..."
if aws ssm get-parameter --name "/app/ecommerce/agentcore/runtime_config_id" --region "$REGION" >/dev/null 2>&1; then
  RUNTIME_ID=$(aws ssm get-parameter --name "/app/ecommerce/agentcore/runtime_config_id" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || echo "")
  
  if [ ! -z "$RUNTIME_ID" ]; then
    read -p "🏃 AgentCore Runtime ($RUNTIME_ID)를 삭제하시겠습니까? (y/N): " delete_runtime
    if [[ "$delete_runtime" == "y" || "$delete_runtime" == "Y" ]]; then
      echo "🗑️ Runtime 삭제 중: $RUNTIME_ID"
      aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-identifier "$RUNTIME_ID" --region "$REGION" || echo "⚠️ Runtime 삭제 실패"
      aws ssm delete-parameter --name "/app/ecommerce/agentcore/runtime_config_id" --region "$REGION" 2>/dev/null || true
      echo "✅ Runtime 삭제 완료"
    fi
  fi
fi

# ----- 4. SSM Parameter 정리 -----
echo ""
echo "⚙️ 이커머스 SSM Parameter 정리..."
ECOMMERCE_PARAMS=$(aws ssm get-parameters-by-path --path "/app/ecommerce" --recursive --query "Parameters[*].Name" --output text --region "$REGION" 2>/dev/null || echo "")

if [ ! -z "$ECOMMERCE_PARAMS" ]; then
  echo "📋 발견된 이커머스 관련 Parameter:"
  for param in $ECOMMERCE_PARAMS; do
    echo "   • $param"
  done
  
  read -p "🗑️ 이 Parameter들을 삭제하시겠습니까? (y/N): " delete_params
  if [[ "$delete_params" == "y" || "$delete_params" == "Y" ]]; then
    for param in $ECOMMERCE_PARAMS; do
      echo "🗑️ Parameter 삭제: $param"
      aws ssm delete-parameter --name "$param" --region "$REGION" 2>/dev/null || true
    done
    echo "✅ Parameter 정리 완료"
  fi
fi

# ----- 5. 로컬 파일 정리 -----
echo ""
echo "🗑️ 로컬 파일 정리 중..."
files_to_clean=("$ZIP_FILE" "ddgs-layer.zip" "lambda.zip")

for file in "${files_to_clean[@]}"; do
  if [ -f "$file" ]; then
    echo "🗑️ 파일 삭제: $file"
    rm -f "$file"
  fi
done

# ----- 6. 정리 완료 -----
echo ""
echo "=================================================="
echo "🎉 K-Style 이커머스 리소스 정리 완료!"
echo "=================================================="
echo ""
echo "✅ 정리된 리소스:"
echo "   • CloudFormation 스택들"
echo "   • S3 버킷 (선택적)"
echo "   • AgentCore 리소스들 (선택적)"
echo "   • SSM Parameters (선택적)"
echo "   • 로컬 임시 파일들"
echo ""
echo "💡 참고사항:"
echo "   • 일부 AWS 리소스는 완전히 삭제되기까지 시간이 걸릴 수 있습니다"
echo "   • CloudWatch 로그는 별도로 정리가 필요할 수 있습니다"
echo "   • Bedrock 사용 이력은 AWS 콘솔에서 확인 가능합니다"
echo ""
echo "🛍️ K-Style 프로젝트 정리가 완료되었습니다!"