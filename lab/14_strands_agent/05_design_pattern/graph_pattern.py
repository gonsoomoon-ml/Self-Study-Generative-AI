"""
Graph 패턴을 사용한 생성-평가 루프

Strands Agent SDK의 agent_graph tool을 활용하여
Generator와 Evaluator 노드를 그래프로 연결하는 구조입니다.
"""

from strands import Agent
from strands_tools import agent_graph


# 설정
QUALITY_THRESHOLD = 75
MAX_ATTEMPTS = 3


def create_generator_evaluator_graph():
    """Generator와 Evaluator를 포함하는 에이전트 그래프를 생성합니다."""

    print("\n🔧 [SETUP] 에이전트 그래프 생성 중...")

    # Agent Graph를 사용할 수 있는 에이전트 생성
    graph_manager = Agent(tools=[agent_graph])

    # 그래프 생성
    result = graph_manager.tool.agent_graph(
        action="create",
        graph_id="qa_refinement_system",
        topology={
            "type": "custom",
            "nodes": [
                {
                    "id": "coordinator",
                    "role": "coordinator",
                    "system_prompt": f"""당신은 고품질 답변 생성 프로세스를 조율하는 코디네이터입니다.

당신의 역할:
1. 사용자의 질문을 받음
2. generator에게 답변 생성을 요청
3. evaluator에게 답변 평가를 요청
4. 평가 결과가 {QUALITY_THRESHOLD}점 이상이면 완료
5. 점수가 부족하면 피드백과 함께 generator에게 재생성 요청
6. 최대 {MAX_ATTEMPTS}번까지 반복

진행 상황을 명확하게 출력하세요."""
                },
                {
                    "id": "generator",
                    "role": "generator",
                    "system_prompt": """당신은 질문에 대한 답변을 생성하는 전문 에이전트입니다.

받은 메시지에서:
- '질문:'으로 시작하면 새로운 답변 생성
- '피드백:'이 포함되면 피드백을 반영하여 답변 개선

답변 작성 기준:
- 정확하고 사실에 기반한 정보
- 논리적이고 체계적인 구조
- 명확하고 이해하기 쉬운 표현
- 적절한 예시와 세부사항 포함

모든 답변은 한국어로 작성하세요.

답변 형식:
=== 답변 시작 ===
[여기에 답변 작성]
=== 답변 끝 ==="""
                },
                {
                    "id": "evaluator",
                    "role": "evaluator",
                    "system_prompt": """당신은 답변의 품질을 평가하는 전문 평가자입니다.

평가 기준:
1. 정확성 (0-25점): 사실의 정확성
2. 완성도 (0-25점): 주제의 포괄성
3. 명확성 (0-25점): 가독성과 구조
4. 깊이 (0-25점): 통찰력과 세부사항

평가 결과 형식:
점수: [0-100]
정확성: [0-25]
완성도: [0-25]
명확성: [0-25]
깊이: [0-25]
강점: [잘한 점]
약점: [부족한 점]
피드백: [구체적인 개선 방안]

엄격하되 공정하게 평가하세요. 대부분은 60-85점, 탁월한 경우만 90점 이상입니다."""
                }
            ],
            "edges": [
                {"from": "coordinator", "to": "generator"},
                {"from": "coordinator", "to": "evaluator"},
                {"from": "generator", "to": "coordinator"},
                {"from": "evaluator", "to": "coordinator"}
            ]
        }
    )

    print(f"✅ [SETUP] 그래프 생성 완료: {result}")
    return graph_manager


def run_with_graph(question: str):
    """
    Agent Graph를 사용하여 질문에 대한 고품질 답변을 생성합니다.

    Args:
        question: 답변할 질문
    """
    print("=" * 80)
    print("🎯 Graph 패턴 실행")
    print(f"📝 질문: {question}")
    print(f"🎚️  목표 점수: {QUALITY_THRESHOLD}/100")
    print(f"🔄 최대 시도: {MAX_ATTEMPTS}회")
    print("=" * 80)

    # 그래프 생성
    graph_manager = create_generator_evaluator_graph()

    # Coordinator에게 작업 전달
    print("\n📤 [TASK] Coordinator에게 작업 전달 중...")

    task_message = f"""새로운 질문에 대한 고품질 답변을 생성해주세요.

질문: {question}

프로세스:
1. generator에게 답변 생성 요청
2. evaluator에게 답변 평가 요청
3. 점수가 {QUALITY_THRESHOLD}점 이상이면 완료
4. 미달이면 피드백과 함께 generator에게 재생성 요청 (최대 {MAX_ATTEMPTS}번)

각 단계의 진행 상황을 명확하게 보고하세요."""

    result = graph_manager.tool.agent_graph(
        action="message",
        graph_id="qa_refinement_system",
        message={
            "target": "coordinator",
            "content": task_message
        }
    )

    print("\n" + "=" * 80)
    print("🎉 Graph 실행 완료")
    print("=" * 80)
    print("\n📊 최종 결과:")
    print(result)
    print("=" * 80)

    return result


def manual_orchestration(question: str):
    """
    Agent Graph를 사용하되, 수동으로 각 노드를 조율하는 방식입니다.
    (Graph 패턴의 대안 - 더 세밀한 제어 가능)
    """
    print("=" * 80)
    print("🎯 Graph 패턴 (수동 조율) 실행")
    print(f"📝 질문: {question}")
    print("=" * 80)

    graph_manager = create_generator_evaluator_graph()

    feedback = ""
    best_answer = ""
    best_score = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n{'='*60}")
        print(f"🔄 시도 {attempt}/{MAX_ATTEMPTS}")
        print(f"{'='*60}")

        # 1. Generator에게 답변 생성 요청
        gen_prompt = f"질문: {question}"
        if feedback:
            gen_prompt += f"\n피드백: {feedback}"

        print("\n📤 Generator에게 메시지 전송...")
        gen_result = graph_manager.tool.agent_graph(
            action="message",
            graph_id="qa_refinement_system",
            message={
                "target": "generator",
                "content": gen_prompt
            }
        )
        print(f"✅ 답변 생성 완료")

        # 2. Evaluator에게 평가 요청
        eval_prompt = f"""질문: {question}

답변: {gen_result}

위 답변을 평가해주세요."""

        print("\n📤 Evaluator에게 메시지 전송...")
        eval_result = graph_manager.tool.agent_graph(
            action="message",
            graph_id="qa_refinement_system",
            message={
                "target": "evaluator",
                "content": eval_prompt
            }
        )

        # 3. 점수 추출
        try:
            score_line = [line for line in str(eval_result).split('\n') if '점수:' in line][0]
            score = int(''.join(filter(str.isdigit, score_line)))
        except:
            score = 70

        print(f"📊 평가 점수: {score}/100")

        if score > best_score:
            best_score = score
            best_answer = gen_result

        # 4. 점수 확인
        if score >= QUALITY_THRESHOLD:
            print(f"\n{'='*60}")
            print(f"✅ 성공! 목표 점수 달성")
            print(f"{'='*60}")
            print(f"\n최종 답변:\n{gen_result}")
            print(f"\n{'='*60}")
            return {
                "success": True,
                "answer": gen_result,
                "score": score,
                "attempts": attempt
            }
        else:
            print(f"❌ 점수 부족 ({score} < {QUALITY_THRESHOLD})")
            try:
                feedback = str(eval_result).split('피드백:')[1].strip().split('\n')[0]
            except:
                feedback = "답변의 품질을 개선해주세요."

    print(f"\n{'='*60}")
    print(f"⚠️  최대 시도 횟수 도달")
    print(f"{'='*60}")
    print(f"\n최고 점수: {best_score}/100")
    print(f"\n최선의 답변:\n{best_answer}")
    print(f"\n{'='*60}")

    return {
        "success": False,
        "answer": best_answer,
        "score": best_score,
        "attempts": MAX_ATTEMPTS
    }


if __name__ == "__main__":
    question = "양자 컴퓨팅이란 무엇이며 왜 중요한가요?"

    # 방법 1: Coordinator가 자동으로 조율 (권장)
    print("\n" + "="*100)
    print("방법 1: Coordinator 자동 조율")
    print("="*100)
    run_with_graph(question)

    # 방법 2: 수동 조율 (더 세밀한 제어)
    # print("\n\n" + "="*100)
    # print("방법 2: 수동 조율")
    # print("="*100)
    # manual_orchestration(question)
