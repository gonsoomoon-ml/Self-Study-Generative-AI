#!/bin/bash

# =============================================================================
# K-Style 이커머스 고객 지원 에이전트 - AWS 환경 설정 스크립트
# AWS CLI 설정 및 필수 서비스 확인
# =============================================================================

set -e
set -o pipefail

echo "☁️ K-Style AWS 환경 설정"
echo "======================="
echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ----- AWS CLI 설치 확인 -----
echo "🔍 AWS CLI 설치 확인 중..."
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI가 설치되지 않았습니다."
    echo ""
    echo "💡 AWS CLI 설치 방법:"
    echo "   Ubuntu/Debian:"
    echo "     sudo apt update"
    echo "     sudo apt install awscli"
    echo ""
    echo "   또는 최신 버전:"
    echo "     curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\""
    echo "     unzip awscliv2.zip"
    echo "     sudo ./aws/install"
    echo ""
    exit 1
else
    echo "✅ AWS CLI 설치됨: $(aws --version)"
fi

# ----- AWS 자격 증명 확인 -----
echo ""
echo "🔑 AWS 자격 증명 확인 중..."
if aws sts get-caller-identity >/dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    REGION=$(aws configure get region 2>/dev/null || echo "설정되지 않음")
    
    echo "✅ AWS 자격 증명 설정됨"
    echo "   • 계정 ID: $ACCOUNT_ID"
    echo "   • 사용자/역할: $USER_ARN"
    echo "   • 기본 리전: $REGION"
    
    if [ "$REGION" = "설정되지 않음" ]; then
        echo ""
        echo "⚠️ 기본 리전이 설정되지 않았습니다."
        read -p "🌍 사용할 AWS 리전을 입력하세요 (예: us-east-1): " input_region
        if [ ! -z "$input_region" ]; then
            aws configure set region "$input_region"
            echo "✅ 리전이 $input_region 으로 설정되었습니다."
            REGION="$input_region"
        fi
    fi
else
    echo "❌ AWS 자격 증명이 설정되지 않았습니다."
    echo ""
    echo "💡 AWS 자격 증명 설정 방법:"
    echo "   aws configure"
    echo ""
    echo "   필요한 정보:"
    echo "   • AWS Access Key ID"
    echo "   • AWS Secret Access Key"
    echo "   • Default region name (예: us-east-1)"
    echo "   • Default output format (json 권장)"
    echo ""
    exit 1
fi

# ----- 필수 AWS 서비스 권한 확인 -----
echo ""
echo "🛡️ 필수 AWS 서비스 권한 확인 중..."

services_check=(
    "bedrock:ListFoundationModels"
    "ssm:GetParameter"
    "sts:GetCallerIdentity"
    "s3:ListBuckets"
    "cloudformation:ListStacks"
)

failed_services=()

for service_action in "${services_check[@]}"; do
    service=$(echo $service_action | cut -d':' -f1)
    action=$(echo $service_action | cut -d':' -f2)
    
    case $service in
        "bedrock")
            if aws bedrock list-foundation-models --region $REGION >/dev/null 2>&1; then
                echo "✅ $service_action"
            else
                echo "❌ $service_action"
                failed_services+=("$service_action")
            fi
            ;;
        "ssm")
            if aws ssm get-parameters-by-path --path "/aws" --region $REGION >/dev/null 2>&1; then
                echo "✅ $service_action"
            else
                echo "❌ $service_action"
                failed_services+=("$service_action")
            fi
            ;;
        "sts")
            if aws sts get-caller-identity >/dev/null 2>&1; then
                echo "✅ $service_action"
            else
                echo "❌ $service_action"
                failed_services+=("$service_action")
            fi
            ;;
        "s3")
            if aws s3 ls >/dev/null 2>&1; then
                echo "✅ $service_action"
            else
                echo "❌ $service_action"
                failed_services+=("$service_action")
            fi
            ;;
        "cloudformation")
            if aws cloudformation list-stacks --region $REGION >/dev/null 2>&1; then
                echo "✅ $service_action"
            else
                echo "❌ $service_action"
                failed_services+=("$service_action")
            fi
            ;;
    esac
done

if [ ${#failed_services[@]} -ne 0 ]; then
    echo ""
    echo "⚠️ 일부 서비스에 대한 권한이 없습니다:"
    for service in "${failed_services[@]}"; do
        echo "   • $service"
    done
    echo ""
    echo "💡 필요한 IAM 권한:"
    echo "   • BedrockFullAccess (또는 BedrockInvokeModel)"
    echo "   • SSMReadOnlyAccess"
    echo "   • CloudFormationReadOnlyAccess"
    echo "   • S3ReadOnlyAccess"
    echo ""
fi

# ----- Bedrock 모델 액세스 확인 -----
echo ""
echo "🤖 Bedrock 모델 액세스 확인 중..."
if aws bedrock list-foundation-models --region $REGION >/dev/null 2>&1; then
    # Claude 모델 확인
    claude_models=$(aws bedrock list-foundation-models \
        --region $REGION \
        --query "modelSummaries[?contains(modelName, 'Claude') || contains(modelId, 'claude')].[modelId,modelName]" \
        --output text 2>/dev/null | head -5)
    
    if [ ! -z "$claude_models" ]; then
        echo "✅ Bedrock 모델 액세스 가능"
        echo "   사용 가능한 Claude 모델 (일부):"
        echo "$claude_models" | while read -r model_id model_name; do
            echo "   • $model_id"
        done
        
        # 권장 모델 확인
        if echo "$claude_models" | grep -q "claude-3"; then
            echo "✅ Claude 3 모델 사용 가능 (권장)"
        else
            echo "⚠️ Claude 3 모델을 찾을 수 없습니다. 모델 액세스를 확인하세요."
        fi
    else
        echo "⚠️ Claude 모델을 찾을 수 없습니다."
    fi
else
    echo "❌ Bedrock 서비스에 액세스할 수 없습니다."
fi

# ----- 기존 리소스 확인 -----
echo ""
echo "🔍 기존 K-Style 리소스 확인 중..."

# SSM Parameters 확인
echo "   • SSM Parameters:"
ecommerce_params=$(aws ssm get-parameters-by-path --path "/app/ecommerce" --region $REGION --query "Parameters[*].Name" --output text 2>/dev/null || echo "")
customersupport_params=$(aws ssm get-parameters-by-path --path "/app/customersupport" --region $REGION --query "Parameters[*].Name" --output text 2>/dev/null || echo "")

if [ ! -z "$ecommerce_params" ]; then
    echo "     ✅ 이커머스 Parameter 발견: $(echo $ecommerce_params | wc -w)개"
else
    echo "     ⚠️ 이커머스 Parameter 없음"
fi

if [ ! -z "$customersupport_params" ]; then
    echo "     ✅ 고객지원 Parameter 발견: $(echo $customersupport_params | wc -w)개"
else
    echo "     ⚠️ 고객지원 Parameter 없음"
fi

# CloudFormation 스택 확인
echo "   • CloudFormation 스택:"
cf_stacks=$(aws cloudformation list-stacks --region $REGION --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "StackSummaries[?contains(StackName, 'Customer') || contains(StackName, 'Ecommerce')].[StackName,StackStatus]" --output text 2>/dev/null || echo "")

if [ ! -z "$cf_stacks" ]; then
    echo "     ✅ 관련 스택 발견:"
    echo "$cf_stacks" | while read -r stack_name stack_status; do
        echo "       • $stack_name ($stack_status)"
    done
else
    echo "     ⚠️ 관련 CloudFormation 스택 없음"
fi

# ----- 환경 설정 요약 -----
echo ""
echo "📋 AWS 환경 설정 요약"
echo "==================="
echo "✅ AWS CLI: 설치됨"
echo "✅ 자격 증명: 설정됨 ($ACCOUNT_ID)"
echo "✅ 기본 리전: $REGION"

if [ ${#failed_services[@]} -eq 0 ]; then
    echo "✅ 서비스 권한: 모두 확인됨"
else
    echo "⚠️ 서비스 권한: 일부 제한됨 (${#failed_services[@]}개)"
fi

echo ""
echo "🚀 다음 단계:"
echo "   1. 가상환경 설정:"
echo "      ./setup/create_kstyle_env.sh"
echo ""
echo "   2. 인프라 구성 (필요시):"
echo "      ./scripts/prereq.sh"
echo ""
echo "   3. 리소스 상태 확인:"
echo "      ./scripts/list_ssm_parameters.sh"
echo ""
echo "   4. 애플리케이션 실행:"
echo "      streamlit run streamlit_app.py"
echo ""

if [ ${#failed_services[@]} -ne 0 ]; then
    echo "⚠️ 주의: 일부 권한이 제한되어 있어 기능이 제한될 수 있습니다."
    echo "   관리자에게 필요한 IAM 권한을 요청하세요."
    echo ""
fi

echo "☁️ AWS 환경 설정 확인 완료!"