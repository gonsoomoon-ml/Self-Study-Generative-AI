import boto3
import logging
import time
from botocore.exceptions import ClientError

# 로깅 레벨을 ERROR로 변경하여 INFO 메시지 숨기기
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def invoke_bedrock_agent(agent_id, alias_id, prompt, session_id, streaming=False):
    """
    Amazon Bedrock Agent를 호출하는 함수
    
    Args:
        agent_id (str): Agent ID
        alias_id (str): Agent Alias ID  
        prompt (str): 사용자 입력 프롬프트
        session_id (str): 세션 ID (대화 연속성을 위해)
        streaming (bool): 스트리밍 모드 여부 (기본값: False)
    
    Returns:
        tuple: (Agent의 응답, 첫 번째 단어 출력 시간)
    """
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name="us-west-2"
    )
    
    try:
        start_time = time.time()
        first_word_time = None
        
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            enableTrace=False,
            sessionId=session_id,
            inputText=prompt,
            streamingConfigurations={
                "applyGuardrailInterval": 20,
                "streamFinalResponse": streaming
            }
        )
        
        completion = ""
        for event in response.get("completion"):
            if 'chunk' in event:
                chunk = event["chunk"]
                chunk_text = chunk["bytes"].decode()
                completion += chunk_text
                
                # 첫 번째 단어 시간 측정
                if first_word_time is None and chunk_text.strip():
                    first_word_time = time.time() - start_time
                
                # 스트리밍 모드일 때 실시간 출력
                if streaming:
                    print(chunk_text, end="", flush=True)
        
        return completion, first_word_time
        
    except ClientError as e:
        logger.error(f"Agent 호출 실패: {e}")
        raise

# 사용 예시
if __name__ == "__main__":
    agent_id = '2HEFECONPQ'
    alias_id = 'XSNDBWQRKS'

    session_id = "unique_session_id"
    prompt = "갈비찜 레시피를 알려주세요."
    
    # 스트리밍 모드
    print("=== 스트리밍 모드 ===")
    start_time = time.time()
    response_streaming, first_word_time_streaming = invoke_bedrock_agent(agent_id, alias_id, prompt, session_id, streaming=True)
    total_time_streaming = time.time() - start_time
    
    print(f"\n첫 번째 단어 출력 시간: {first_word_time_streaming:.2f}초")
    print(f"전체 응답 시간: {total_time_streaming:.2f}초")


    # 일반 모드 (스트리밍 비활성화)
    print("\n")
    print("=== 일반 모드 ===")
    start_time = time.time()
    response, first_word_time = invoke_bedrock_agent(agent_id, alias_id, prompt, session_id, streaming=False)
    total_time = time.time() - start_time
    
    print(f"첫 번째 단어 출력 시간: {first_word_time:.2f}초")
    print(f"전체 응답 시간: {total_time:.2f}초")
    print(f"응답: {response}")
    
    print("\n" + "="*50 + "\n")
    

    


