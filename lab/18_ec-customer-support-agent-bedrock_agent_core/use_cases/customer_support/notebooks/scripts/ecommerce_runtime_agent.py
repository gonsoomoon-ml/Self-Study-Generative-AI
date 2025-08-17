"""
이커머스 고객 지원 에이전트 (AgentCore Runtime용)
기존 전자제품 프로젝트 구조를 유지하면서 이커머스로 전환
"""

import os
import argparse
from boto3.session import Session
from opentelemetry import baggage, context

# 기존 전자제품 프로젝트와 동일한 구조 유지
from lab_helpers.utils import get_ssm_parameter

from strands import Agent
from strands.models import BedrockModel


def parse_arguments():
    parser = argparse.ArgumentParser(description="이커머스 고객 지원 에이전트")
    parser.add_argument(
        "--session-id",
        type=str,
        required=True,
        help="이 에이전트 실행과 연결할 세션 ID",
    )
    return parser.parse_args()


def set_session_context(session_id):
    """추적 상관관계를 위해 OpenTelemetry baggage에 세션 ID 설정"""
    ctx = baggage.set_baggage("session.id", session_id)
    token = context.attach(ctx)
    print(f"세션 ID '{session_id}'가 텔레메트리 컨텍스트에 연결되었습니다")
    return token


def main():
    # 명령줄 인수 구문 분석
    args = parse_arguments()

    # 텔레메트리를 위한 세션 컨텍스트 설정
    context_token = set_session_context(args.session_id)

    # 리전 가져오기
    boto_session = Session()
    region = boto_session.region_name

    try:
        # Lab 1에서와 동일한 기본 에이전트 생성
        MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        
        MODEL = BedrockModel(
            model_id=MODEL_ID,
            temperature=0.3,
            region_name=region,
        )

        # 이커머스 특화 시스템 프롬프트
        SYSTEM_PROMPT = \"\"\"당신은 한국 패션/뷰티 전문 온라인 쇼핑몰 'K-Style'의 친절하고 전문적인 고객 상담원입니다.

🏪 K-Style 쇼핑몰 소개:
- 패션: 여성/남성 의류, 신발, 가방, 액세서리
- 뷰티: 스킨케어, 메이크업, 향수, 헤어케어
- 전문 서비스: 반품/교환 당일 처리, 스타일링 상담

👨‍💼 상담원 역할:
- 반품/교환 신청을 신속하고 정확하게 처리
- 사이즈, 색상, 스타일 관련 전문 상담 제공
- 패션 트렌드 및 뷰티 사용법 안내
- 항상 존댓말 사용, 친근하고 전문적인 응대
- 고객의 스타일과 선호도를 고려한 맞춤 서비스

💡 응대 원칙:
- 반품/교환은 고객의 당연한 권리임을 인식
- 사이즈 가이드와 실제 착용감의 차이를 이해
- 온라인 쇼핑의 한계를 공감하며 최선의 해결책 제시
- 재구매 의향을 높이는 긍정적 경험 제공

현재 이것은 프로덕션 환경에서 실행되고 있으며, 고객에게 최고의 서비스를 제공하겠습니다!\"\"\"\n",
    "\n",
    "        # 이커머스 도구들 (기존 전자제품 프로젝트와 동일한 구조)\n",
    "        from ecommerce_agent import (\n",
    "            process_return,\n",
    "            process_exchange, \n",
    "            web_search\n",
    "        )\n",
    "\n",
    "        basic_agent = Agent(\n",
    "            model=MODEL,\n",
    "            tools=[\n",
    "                process_return,   # 반품 처리\n",
    "                process_exchange, # 교환 처리 \n",
    "                web_search,      # 패션/뷰티 정보 검색\n",
    "            ],\n",
    "            system_prompt=SYSTEM_PROMPT,\n",
    "        )\n",
    "\n",
    "        # 이커머스 고객 응대 작업 실행\n",
    "        query = \"\"\"고객님을 환영합니다! K-Style 고객센터입니다. \n",
    "패션과 뷰티 관련하여 궁금한 점이나 도움이 필요한 사항이 있으시면 언제든 말씀해 주세요.\n",
    "반품, 교환, 스타일링 조언, 상품 문의 등 무엇이든 도와드리겠습니다!\"\"\"\n",
    "\n",
    "        result = basic_agent(query)\n",
    "        print(\"결과:\", result)\n",
    "\n",
    "        print(\"✅ 이커머스 에이전트가 성공적으로 실행되었고 추적이 CloudWatch로 전송되었습니다\")\n",
    "        \n",
    "    finally:\n",
    "        # 완료 시 컨텍스트 분리\n",
    "        context.detach(context_token)\n",
    "\n",
    "\n",
    "if __name__ == \"__main__\":\n",
    "    main()