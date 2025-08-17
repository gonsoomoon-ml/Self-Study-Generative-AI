#!/bin/bash

# K-Style 고객 지원 에이전트 시작 스크립트

echo "🛍️ K-Style 고객 지원 에이전트"
echo "=============================="
echo ""

# 가상환경 활성화 확인
if [ ! -d ".venv" ]; then
    echo "⚠️ 가상환경이 설정되지 않았습니다."
    echo "다음 명령어로 환경을 설정하세요:"
    echo "  ./setup/create_kstyle_env_flexible.sh"
    echo ""
    exit 1
fi

# 가상환경 활성화
echo "🔄 가상환경 활성화 중..."
source .venv/bin/activate

# Customer Support UI 실행
echo "🚀 고객 지원 Streamlit 앱을 시작합니다..."
echo "브라우저에서 http://localhost:8501 로 접속하세요"
echo ""

streamlit run use_cases/customer_support/ui/streamlit_app.py