## 기본적인 Bedrock Agent 호출 예시

python
import boto3
import json

# Bedrock Agent Runtime 클라이언트 생성
bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name='us-west-2'  # 사용 중인 리전으로 변경
)

# 에이전트 호출 (동기식)
def invoke_agent(agent_id, agent_alias_id, input_text):
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId='test-session-001',  # 세션 ID는 고유한 값으로 설정
            inputText=input_text
        )
        
        # 응답 처리
        completion = response.get('completion', {})
        if 'text' in completion:
            return completion['text']
        else:
            return "응답 텍스트를 찾을 수 없습니다."
            
    except Exception as e:
        return f"에러 발생: {str(e)}"

# 에이전트 호출 예시
agent_id = '2HEFECONPQ'  # 실제 에이전트 ID로 변경
agent_alias_id = 'XSNDBWQRKS'  # 실제 에이전트 별칭 ID로 변경
result = invoke_agent(agent_id, agent_alias_id, "갈비찜 레시피를 알려주세요.")
print(result)


## 스트리밍 응답을 위한 Bedrock Agent 호출 예시

python
import boto3
import json

# Bedrock Agent Runtime 클라이언트 생성
bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name='us-west-2'  # 사용 중인 리전으로 변경
)

# 에이전트 스트리밍 호출
def invoke_agent_streaming(agent_id, agent_alias_id, input_text):
    try:
        # 스트리밍 응답 요청
        response = bedrock_agent_runtime.invoke_agent_streaming(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId='test-session-002',  # 세션 ID는 고유한 값으로 설정
            inputText=input_text
        )
        
        # 스트리밍 응답 처리
        for event in response.get('completion'):
            # 청크 타입 확인
            chunk_type = event.get('chunkType')
            
            if chunk_type == 'text':
                # 텍스트 청크 처리
                text = event.get('text', '')
                print(text, end='', flush=True)  # 실시간으로 출력
            elif chunk_type == 'trace':
                # 트레이스 정보 처리 (선택 사항)
                trace = json.loads(event.get('trace', '{}'))
                print(f"\n[Trace]: {trace}")
        
        print("\n스트리밍 완료")
            
    except Exception as e:
        print(f"에러 발생: {str(e)}")

# 에이전트 스트리밍 호출 예시
# agent_id = '2HEFECONPQ'  # 실제 에이전트 ID로 변경
# agent_alias_id = 'XSNDBWQRKS'  # 실제 에이전트 별칭 ID로 변경
# invoke_agent_streaming(agent_id, agent_alias_id, "갈비찜 레시피를 알려주세요.")

