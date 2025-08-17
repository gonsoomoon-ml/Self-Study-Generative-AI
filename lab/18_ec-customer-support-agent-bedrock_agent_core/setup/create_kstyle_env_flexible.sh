#!/bin/bash

# =============================================================================
# K-Style 이커머스 고객 지원 에이전트 - 유연한 환경 설정 스크립트
# Python 버전 선택 가능 (3.11 또는 3.12)
# =============================================================================

set -e
set -o pipefail

echo "🛍️ K-Style 이커머스 고객 지원 에이전트 환경 설정"
echo "==============================================="
echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ----- Python 버전 선택 -----
echo "🐍 Python 버전을 선택하세요:"
echo ""
echo "1. Python 3.12 (권장 - 최신 기능 및 성능)"
echo "2. Python 3.11 (안정 - 모든 패키지 검증됨)"
echo ""
read -p "선택 (1 또는 2, 기본값 1): " python_choice

case $python_choice in
    2)
        PYTHON_VERSION="3.11"
        echo "✅ Python 3.11 선택됨 (안정 버전)"
        ;;
    *)
        PYTHON_VERSION="3.12"
        echo "✅ Python 3.12 선택됨 (최신 버전)"
        ;;
esac

echo ""

# ----- 가상환경 이름 설정 -----
export VirtualEnv=".venv"
echo "🐍 가상환경 이름: $VirtualEnv"
echo "📂 프로젝트 디렉토리: $(pwd)"
echo "🔢 Python 버전: $PYTHON_VERSION"
echo ""

# ----- uv 설치 확인 및 설치 -----
echo "🔧 UV 패키지 매니저 확인 중..."
if ! command -v uv &> /dev/null; then
    echo "📦 UV 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # UV 설치 확인
    if ! command -v uv &> /dev/null; then
        echo "❌ UV 설치 실패"
        exit 1
    fi
    echo "✅ UV 설치 완료"
else
    echo "✅ UV가 이미 설치되어 있습니다"
fi

# PATH에 UV 추가
export PATH="$HOME/.local/bin:$PATH"

# UV 접근 가능 여부 최종 확인
if ! command -v uv &> /dev/null; then
    echo "❌ UV에 접근할 수 없습니다. 터미널을 재시작하거나 다음을 실행하세요:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

echo "🎯 UV 버전: $(uv --version)"
echo ""

# ----- Python 설치 및 가상환경 생성 -----
echo "🐍 Python $PYTHON_VERSION 설치 및 가상환경 생성 중..."
echo "   • Python $PYTHON_VERSION 설치..."
uv python install $PYTHON_VERSION
if [ $? -ne 0 ]; then
    echo "❌ Python $PYTHON_VERSION 설치 실패"
    exit 1
fi

echo "   • 가상환경 생성 중..."
uv venv --python $PYTHON_VERSION
if [ $? -ne 0 ]; then
    echo "❌ 가상환경 생성 실패"
    exit 1
fi

echo "⏳ 가상환경 초기화 대기 중... (5초)"
sleep 5

# ----- 가상환경 활성화 -----
echo "🔄 가상환경 활성화 중..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ 가상환경 활성화 완료"
else
    echo "❌ 가상환경 활성화 스크립트를 찾을 수 없습니다"
    exit 1
fi

echo "🐍 현재 Python 환경:"
echo "   • Python 경로: $(which python)"
echo "   • Python 버전: $(python --version)"
echo ""

echo "⏳ 환경 확인 완료... (5초)"
sleep 5

# ----- uv 프로젝트 초기화 -----
echo "📦 UV 프로젝트 초기화 중..."
if [ ! -f "pyproject.toml" ]; then
    uv init --name "k-style-ecommerce-agent" --package
    if [ $? -ne 0 ]; then
        echo "❌ UV 프로젝트 초기화 실패"
        exit 1
    fi
    echo "✅ 새 프로젝트 초기화 완료"
else
    echo "✅ 기존 pyproject.toml 발견, 초기화 건너뛰기"
fi

# ----- pyproject.toml Python 버전 업데이트 -----
if [ -f "setup/pyproject.toml" ]; then
    echo "📝 pyproject.toml Python 버전 업데이트 중..."
    if [ "$PYTHON_VERSION" = "3.11" ]; then
        sed -i 's/requires-python = ">=3.12"/requires-python = ">=3.11"/' setup/pyproject.toml
        echo "✅ pyproject.toml을 Python 3.11용으로 업데이트"
    else
        sed -i 's/requires-python = ">=3.11"/requires-python = ">=3.12"/' setup/pyproject.toml
        echo "✅ pyproject.toml을 Python 3.12용으로 유지"
    fi
fi

# ----- 이커머스 특화 패키지 설치 -----
echo "🛍️ K-Style 이커머스 특화 패키지 설치 중..."

# 핵심 AI/ML 패키지
echo "   • AI/ML 패키지..."
uv add "strands-agents>=0.7.0" "boto3>=1.39.15" "strands-agents-tools"
uv add "bedrock_agentcore" "ddgs"

# 웹 애플리케이션 패키지
echo "   • 웹 애플리케이션 패키지..."
uv add "streamlit>=1.29.0" "plotly>=5.17.0" "pandas>=2.1.0" "pillow>=10.0.0"

# 개발 도구
echo "   • 개발 도구..."
uv add "jupyter>=1.0.0" "ipykernel>=6.25.0" "jupyterlab>=4.0.0"

# 유틸리티 패키지
echo "   • 유틸리티 패키지..."
uv add "requests>=2.31.0" "pyyaml>=6.0" "python-dotenv>=1.0.0"

if [ $? -ne 0 ]; then
    echo "⚠️ 일부 패키지 설치 실패 (호환성 문제일 수 있음)"
    echo "   setup/COMPATIBILITY.md 파일을 참조하세요"
fi

echo "⏳ 패키지 설치 완료... (5초)"
sleep 5

# ----- Jupyter 커널 설정 -----
echo "📔 Jupyter 커널 설정 중..."

# ipykernel이 설치되어 있는지 확인하고 없으면 설치
if ! python -c "import ipykernel" 2>/dev/null; then
    echo "   • ipykernel 설치 중..."
    uv add ipykernel
    if [ $? -ne 0 ]; then
        echo "❌ ipykernel 설치 실패"
        exit 1
    fi
    echo "✅ ipykernel 설치 완료"
else
    echo "✅ ipykernel이 이미 설치되어 있습니다"
fi

# Jupyter 커널 생성
echo "   • Jupyter 커널 생성 중..."
python -m ipykernel install --user --name=ecommerce-agent --display-name="Ecommerce Agent (.venv Python $PYTHON_VERSION)"
if [ $? -eq 0 ]; then
    echo "✅ Jupyter 커널 'ecommerce-agent' 생성 완료"
    echo "   • 커널 이름: ecommerce-agent"
    echo "   • 표시 이름: Ecommerce Agent (.venv Python $PYTHON_VERSION)"
else
    echo "⚠️ Jupyter 커널 생성 실패 (선택사항)"
    echo "   수동으로 다음 명령어를 실행하세요:"
    echo "   python -m ipykernel install --user --name=ecommerce-agent --display-name=\"Ecommerce Agent (.venv)\""
fi

echo "⏳ Jupyter 설정 완료... (5초)"
sleep 5

# ----- AWS CLI 설정 확인 -----
echo "☁️ AWS 환경 확인 중..."
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI 설치됨"
    
    # AWS 자격 증명 확인
    if aws sts get-caller-identity >/dev/null 2>&1; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        REGION=$(aws configure get region 2>/dev/null || echo "설정되지 않음")
        echo "   • 계정 ID: $ACCOUNT_ID"
        echo "   • 리전: $REGION"
        echo "✅ AWS 자격 증명 설정됨"
    else
        echo "⚠️ AWS 자격 증명이 설정되지 않았습니다"
        echo "   다음 명령어로 설정하세요: aws configure"
    fi
else
    echo "⚠️ AWS CLI가 설치되지 않았습니다"
fi
echo ""

# ----- 설치된 패키지 확인 -----
echo "📋 설치된 주요 패키지 확인:"
echo "================================"
uv pip list | grep -E "(strands|boto3|streamlit|bedrock|plotly|jupyter)" || echo "주요 패키지를 찾을 수 없습니다"
echo ""

# ----- 호환성 보고서 -----
echo "📊 Python $PYTHON_VERSION 호환성 보고서:"
echo "====================================="
if [ "$PYTHON_VERSION" = "3.12" ]; then
    echo "⚠️ Python 3.12는 최신 버전입니다."
    echo "   • 대부분의 패키지는 호환됩니다"
    echo "   • 일부 패키지는 테스트가 필요할 수 있습니다"
    echo "   • 문제 발생 시 Python 3.11을 사용해보세요"
    echo ""
    echo "📄 상세 호환성 정보: setup/COMPATIBILITY.md"
else
    echo "✅ Python 3.11은 안정 버전입니다."
    echo "   • 모든 패키지가 검증되었습니다"
    echo "   • 프로덕션 환경에 적합합니다"
fi
echo ""

# ----- 환경 설정 완료 및 사용법 안내 -----
echo "🎉 K-Style 이커머스 환경 설정 완료!"
echo "==================================="
echo ""
echo "🚀 다음 단계:"
echo "   1. 가상환경 활성화:"
echo "      source .venv/bin/activate"
echo ""
echo "   2. Streamlit 앱 실행:"
echo "      streamlit run use_cases/customer_support/ui/streamlit_app.py"
echo ""
echo "   3. Jupyter Lab 시작:"
echo "      jupyter lab"
echo ""
echo "📚 도움말:"
echo "   • README.md - 프로젝트 가이드"
echo "   • ARCHITECTURE.md - 시스템 아키텍처"
echo "   • setup/COMPATIBILITY.md - 호환성 정보"
echo ""

# ----- 환경 변수 설정 파일 생성 -----
echo "⚙️ 환경 설정 파일 생성 중..."
cat > .env.example << EOF
# K-Style 이커머스 고객 지원 에이전트 환경 변수
# Python 버전: $PYTHON_VERSION
# 생성일: $(date '+%Y-%m-%d %H:%M:%S')

# AWS 설정
AWS_REGION=us-east-1
AWS_PROFILE=default

# AgentCore 설정
AGENTCORE_MEMORY_ID=
AGENTCORE_GATEWAY_ID=
AGENTCORE_RUNTIME_ID=

# Streamlit 설정
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost

# 개발 모드
DEBUG=true
ENVIRONMENT=development
PYTHON_VERSION=$PYTHON_VERSION

# K-Style 브랜딩
BRAND_NAME=K-Style
BRAND_DESCRIPTION=한국 패션/뷰티 전문 온라인 쇼핑몰
EOF

echo "✅ 환경 설정 템플릿 생성: .env.example"
echo ""

echo "✨ Python $PYTHON_VERSION 환경 설정 완료! 즐거운 개발 되세요! ✨"

# =============================================================================
# 🔄 환경 재설치 방법
# =============================================================================
#
# 완전 정리 후 재설치 (권장)
# cd /home/ubuntu/Self-Study-Generative-AI/lab/18_ec-customer-support-agent-bedrock_agent_core
# jupyter kernelspec remove ecommerce-agent
# rm -rf .venv
# bash setup/create_kstyle_env_flexible.sh
#
# 주의사항:
# - 가상환경 삭제 전 중요한 설정이나 추가 패키지 백업
# - 새로 설치 후 VS Code 재시작 권장
# - VS Code에서 "Ecommerce Agent (.venv Python 3.x)" 커널 선택
# =============================================================================