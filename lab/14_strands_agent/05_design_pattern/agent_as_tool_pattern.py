"""
Agent as Tool 패턴을 사용한 생성-평가 루프

Strands Agent SDK의 Agent as Tool 패턴을 활용하여
Generator와 Evaluator를 tool로 정의하고,
Coordinator Agent가 이들을 조율하는 구조입니다.
"""

from strands import Agent, tool
import json


# 설정
QUALITY_THRESHOLD = 75
MAX_ATTEMPTS = 3


@tool
def answer_generator(question: str, feedback: str = "") -> str:
    """
    질문에 대한 답변을 생성하는 전문 에이전트입니다.

    Args:
        question: 답변할 질문
        feedback: 이전 평가에서 받은 피드백 (선택사항)

    Returns:
        생성된 답변
    """
    print(f"\n🤖 [GENERATOR] 답변 생성 시작")

    generator_agent = Agent(
        system_prompt="""당신은 포괄적이고 정확한 답변을 작성하는 전문가입니다.

        답변 작성 시 다음을 고려하세요:
        - 정확한 사실과 정보 제공
        - 논리적이고 체계적인 구조
        - 명확하고 이해하기 쉬운 설명
        - 적절한 예시와 세부사항

        모든 답변은 한국어로 작성하세요.""",
        callback_handler=None
    )

    prompt = f"질문: {question}"
    if feedback:
        prompt += f"\n\n이전 피드백: {feedback}\n피드백을 반영하여 개선된 답변을 작성하세요."

    answer = str(generator_agent(prompt))
    print(f"✅ [GENERATOR] 답변 생성 완료 ({len(answer)}자)")

    return answer


@tool
def answer_evaluator(question: str, answer: str) -> str:
    """
    답변의 품질을 평가하는 전문 에이전트입니다.

    Args:
        question: 원본 질문
        answer: 평가할 답변

    Returns:
        JSON 형식의 평가 결과 (점수와 피드백 포함)
    """
    print(f"\n🔍 [EVALUATOR] 답변 평가 시작")

    evaluator_agent = Agent(
        system_prompt="""당신은 답변의 품질을 엄격하게 평가하는 전문 평가자입니다.

        평가 기준:
        1. 정확성 (0-25점): 사실의 정확성과 정밀성
        2. 완성도 (0-25점): 주제의 포괄적 다룸
        3. 명확성 (0-25점): 구조와 가독성
        4. 깊이 (0-25점): 분석의 통찰력과 세부사항

        반드시 다음 JSON 형식으로 응답하세요:
        {
            "score": 숫자(0-100),
            "accuracy": 숫자(0-25),
            "completeness": 숫자(0-25),
            "clarity": 숫자(0-25),
            "depth": 숫자(0-25),
            "feedback": "구체적인 개선 피드백",
            "strengths": "잘한 점",
            "weaknesses": "부족한 점"
        }

        대부분의 답변은 60-85점 범위입니다. 90점 이상은 탁월한 경우만 부여하세요.""",
        callback_handler=None
    )

    prompt = f"""다음 답변을 평가하세요:

질문: {question}

답변: {answer}

JSON 형식으로 평가 결과를 제공하세요."""

    evaluation = str(evaluator_agent(prompt))

    # JSON 추출
    try:
        start_idx = evaluation.find('{')
        end_idx = evaluation.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = evaluation[start_idx:end_idx]
            eval_data = json.loads(json_str)
            score = eval_data.get("score", 0)
            print(f"📊 [EVALUATOR] 평가 점수: {score}/100")
            return json_str
    except:
        pass

    # JSON 파싱 실패 시 기본값
    default_eval = {
        "score": 70,
        "feedback": evaluation,
        "strengths": "N/A",
        "weaknesses": "N/A"
    }
    print(f"📊 [EVALUATOR] 평가 점수: 70/100 (기본값)")
    return json.dumps(default_eval, ensure_ascii=False)


# Coordinator Agent: Generator와 Evaluator를 조율하는 메인 에이전트
def create_coordinator():
    """Generator와 Evaluator tool을 사용하는 Coordinator Agent를 생성합니다."""

    coordinator_prompt = f"""당신은 고품질 답변 생성을 조율하는 코디네이터입니다.

당신의 역할:
1. answer_generator tool을 사용하여 질문에 대한 답변을 생성
2. answer_evaluator tool을 사용하여 답변의 품질을 평가
3. 평가 점수가 {QUALITY_THRESHOLD}점 이상이면 성공으로 처리
4. 점수가 부족하면 피드백을 바탕으로 answer_generator를 다시 호출하여 개선
5. 최대 {MAX_ATTEMPTS}번까지 시도

작업 순서:
- Step 1: answer_generator를 호출하여 첫 답변 생성
- Step 2: answer_evaluator를 호출하여 답변 평가
- Step 3: 점수 확인
  - {QUALITY_THRESHOLD}점 이상: 성공! 최종 답변 출력
  - {QUALITY_THRESHOLD}점 미만: 피드백을 answer_generator에 전달하여 재생성 (Step 1로)

최종 출력 형식:
=== 최종 결과 ===
성공 여부: [예/아니오]
최종 점수: [점수]/100
시도 횟수: [횟수]/{MAX_ATTEMPTS}
답변:
[답변 내용]
==================

반드시 tool을 사용하세요. 직접 답변하지 마세요."""

    return Agent(
        system_prompt=coordinator_prompt,
        tools=[answer_generator, answer_evaluator],
        callback_handler=None
    )


def run_with_coordinator(question: str):
    """
    Coordinator Agent를 사용하여 질문에 대한 고품질 답변을 생성합니다.

    Args:
        question: 답변할 질문
    """
    print("=" * 80)
    print("🎯 Agent as Tool 패턴 실행")
    print(f"📝 질문: {question}")
    print(f"🎚️  목표 점수: {QUALITY_THRESHOLD}/100")
    print(f"🔄 최대 시도: {MAX_ATTEMPTS}회")
    print("=" * 80)

    coordinator = create_coordinator()

    task = f"""다음 질문에 대한 고품질 답변을 생성하세요:

질문: {question}

당신의 system prompt에 명시된 작업 순서를 따라 진행하세요."""

    result = coordinator(task)

    print("\n" + "=" * 80)
    print("🎉 Coordinator 실행 완료")
    print("=" * 80)
    print(result)
    print("=" * 80)

    return result


if __name__ == "__main__":
    # 예제 1: 기본 질문
    question1 = "양자 컴퓨팅이란 무엇이며 왜 중요한가요?"
    run_with_coordinator(question1)

    # 예제 2: 더 복잡한 질문 (주석 해제하여 실행)
    # print("\n\n" + "=" * 100)
    # print("두 번째 예제 시작")
    # print("=" * 100 + "\n")
    # question2 = "블록체인 기술의 작동 원리와 실생활 적용 사례를 설명해주세요."
    # run_with_coordinator(question2)
