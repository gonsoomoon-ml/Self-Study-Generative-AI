"""
이커머스 전용 메모리 훅
기존 전자제품 프로젝트의 메모리 시스템을 패션/뷰티 도메인으로 전환
"""

import logging
from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent
from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)


class EcommerceCustomerMemoryHooks(HookProvider):
    """패션/뷰티 이커머스 고객 메모리 훅"""

    def __init__(
        self, memory_id: str, client: MemoryClient, customer_id: str, session_id: str
    ):
        self.memory_id = memory_id
        self.client = client
        self.customer_id = customer_id
        self.session_id = session_id
        self.namespaces = {
            strategy["type"]: strategy["namespaces"][0]
            for strategy in self.client.get_memory_strategies(self.memory_id)
        }

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """고객 맥락을 검색하여 개인화된 응답을 제공합니다."""
        messages = event.agent.messages
        if (
            messages[-1]["role"] == "user"
            and "toolResult" not in messages[-1]["content"][0]
        ):
            user_query = messages[-1]["content"][0]["text"]

            try:
                all_context = []

                for context_type, namespace in self.namespaces.items():
                    # AgentCore Memory에서 고객 맥락 검색
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.customer_id),
                        query=user_query,
                        top_k=3,
                    )
                    
                    # 메모리를 맥락 문자열로 포맷
                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get("content", {})
                            if isinstance(content, dict):
                                text = content.get("text", "").strip()
                                if text:
                                    # 이커머스 특화 맥락 태그
                                    context_tag = self._get_context_tag(context_type, text)
                                    all_context.append(f"[{context_tag}] {text}")

                # 고객 맥락을 쿼리에 주입
                if all_context:
                    context_text = "\\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    
                    # 한국어로 맥락 정보 제공
                    messages[-1]["content"][0]["text"] = f"""고객 정보:
{context_text}

고객 문의: {original_text}"""
                    
                    logger.info(f"고객 맥락 {len(all_context)}개 항목 검색 완료")

            except Exception as e:
                logger.error(f"고객 맥락 검색 실패: {e}")

    def save_ecommerce_interaction(self, event: AfterInvocationEvent):
        """이커머스 상호작용을 저장합니다."""
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                # 마지막 고객 쿼리와 에이전트 응답 가져오기
                customer_query = None
                agent_response = None

                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif (
                        msg["role"] == "user"
                        and not customer_query
                        and "toolResult" not in msg["content"][0]
                    ):
                        customer_query = msg["content"][0]["text"]
                        break

                if customer_query and agent_response:
                    # 이커머스 상호작용 저장
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.customer_id,
                        session_id=self.session_id,
                        messages=[
                            (customer_query, "USER"),
                            (agent_response, "ASSISTANT"),
                        ],
                    )
                    logger.info("이커머스 상호작용 메모리에 저장 완료")

        except Exception as e:
            logger.error(f"이커머스 상호작용 저장 실패: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """이커머스 메모리 훅을 등록합니다."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_ecommerce_interaction)
        logger.info("이커머스 고객 메모리 훅 등록 완료")

    def _get_context_tag(self, context_type: str, text: str) -> str:
        """맥락 유형에 따른 한국어 태그를 반환합니다."""
        if context_type.upper() == "USER_PREFERENCE":
            if "사이즈" in text:
                return "선호 사이즈"
            elif "브랜드" in text:
                return "선호 브랜드"
            elif "색상" in text:
                return "선호 색상"
            elif "스타일" in text:
                return "선호 스타일"
            elif "반품" in text or "교환" in text:
                return "반품/교환 이력"
            else:
                return "고객 선호도"
        elif context_type.upper() == "SEMANTIC":
            if "반품" in text:
                return "반품 이력"
            elif "교환" in text:
                return "교환 이력"
            elif "문의" in text:
                return "이전 문의"
            elif "주문" in text:
                return "주문 이력"
            else:
                return "구매 정보"
        else:
            return context_type.upper()


def create_or_get_ecommerce_memory_resource():
    """이커머스 전용 메모리 리소스를 생성하거나 가져옵니다."""
    import boto3
    from bedrock_agentcore.memory.constants import StrategyType
    from lab_helpers.utils import get_ssm_parameter, put_ssm_parameter
    
    session = boto3.session.Session()
    region = session.region_name
    
    memory_client = MemoryClient(region_name=region)
    memory_name = "EcommerceCustomerMemory"
    
    try:
        # 기존 메모리 ID 확인
        memory_id = get_ssm_parameter("/app/ecommerce/agentcore/memory_id")
        memory_client.gmcp_client.get_memory(memoryId=memory_id)
        return memory_id
    except:
        try:
            # 이커머스 특화 메모리 전략
            strategies = [
                {
                    StrategyType.USER_PREFERENCE.value: {
                        "name": "EcommerceCustomerPreferences",
                        "description": "고객의 패션/뷰티 선호도, 사이즈, 브랜드 등을 저장",
                        "namespaces": ["ecommerce/customer/{actorId}/preferences"],
                    }
                },
                {
                    StrategyType.SEMANTIC.value: {
                        "name": "EcommerceCustomerHistory", 
                        "description": "고객의 구매 이력, 반품/교환 내역, 문의 사항 저장",
                        "namespaces": ["ecommerce/customer/{actorId}/history"],
                    }
                },
            ]
            
            print("이커머스 AgentCore Memory 리소스 생성 중... 몇 분 소요될 수 있습니다.")
            
            # 이커머스 메모리 리소스 생성
            response = memory_client.create_memory_and_wait(
                name=memory_name,
                description="패션/뷰티 이커머스 고객 지원 메모리",
                strategies=strategies,
                event_expiry_days=90,  # 메모리는 90일 후 만료
            )
            
            memory_id = response["id"]
            
            try:
                put_ssm_parameter(
                    "/app/ecommerce/agentcore/memory_id", 
                    memory_id,
                    "이커머스 고객 메모리 ID"
                )
            except:
                pass
            
            return memory_id
            
        except Exception as e:
            print(f"메모리 리소스 생성 실패: {e}")
            return None


# 이커머스 특화 메모리 시드 데이터
def seed_ecommerce_customer_data(memory_client: MemoryClient, memory_id: str, customer_id: str):
    """이커머스 고객 테스트 데이터를 시드합니다."""
    
    # 한국 패션/뷰티 고객 상호작용 예시
    ecommerce_interactions = [
        ("지난달에 산 원피스 사이즈가 작아서 L로 교환했어요.", "USER"),
        ("사이즈 교환 처리해드렸습니다. 플라워 패턴이 잘 어울리실 것 같아요!", "ASSISTANT"),
        
        ("제가 건성 피부인데 어떤 파운데이션이 좋을까요?", "USER"), 
        ("건성 피부에는 보습 쿠션이나 글로우 타입을 추천드립니다. 히알루론산 성분이 들어간 제품이 좋아요.", "ASSISTANT"),
        
        ("평소에 M 사이즈 입는데 이 브랜드는 어떤가요?", "USER"),
        ("해당 브랜드는 사이즈가 작게 나오는 편이니 L 사이즈를 추천드립니다. 실측 사이즈를 확인해보세요.", "ASSISTANT"),
        
        ("베이지색 가방이 마음에 들어요. 어떤 옷과 잘 어울릴까요?", "USER"),
        ("베이지는 정말 활용도가 높은 색상이에요! 화이트, 네이비, 블랙 등 어떤 색과도 잘 어울립니다.", "ASSISTANT"),
        
        ("이 립스틱 색깔이 사진과 달라요. 교환 가능한가요?", "USER"),
        ("색상 차이로 인한 교환은 무료로 처리됩니다. 원하시는 색상으로 바로 교환해드릴게요!", "ASSISTANT"),
    ]
    
    # 이전 상호작용 저장
    try:
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=customer_id,
            session_id="previous_ecommerce_session",
            messages=ecommerce_interactions
        )
        print("✅ 이커머스 고객 이력 데이터 시드 완료")
    except Exception as e:
        print(f"⚠️ 이커머스 이력 시드 오류: {e}")