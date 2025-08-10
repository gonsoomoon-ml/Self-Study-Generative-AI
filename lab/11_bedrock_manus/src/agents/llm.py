import os
from textwrap import dedent
from typing import Optional
from src.utils import bedrock
from src.utils.bedrock import bedrock_info, bedrock_model
from src.config.agents import LLMType
# from src.utils.bedrock import bedrock_utils, bedrock_chain
from src.utils.bedrock import bedrock_utils_tokens, bedrock_chain
from langchain_aws import ChatBedrock
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.config import (
    REASONING_MODEL,
    REASONING_BASE_URL,
    REASONING_API_KEY,
    BASIC_MODEL,
    BASIC_BASE_URL,
    BASIC_API_KEY,
    VL_MODEL,
    VL_BASE_URL,
    VL_API_KEY,
)
"""
Supported models:
"Claude-Instant-V1": "anthropic.claude-instant-v1",
"Claude-V1": "anthropic.claude-v1",
"Claude-V2": "anthropic.claude-v2",
"Claude-V2-1": "anthropic.claude-v2:1",
"Claude-V3-Sonnet": "us.anthropic.claude-3-sonnet-20240229-v1:0",
"Claude-V3-Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
"Claude-V3-Opus": "anthropic.claude-3-sonnet-20240229-v1:0",
"Claude-V3-5-Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
"Claude-V3-5-V-2-Sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
"Claude-V3-5-V-2-Sonnet-CRI": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
"Claude-V3-7-Sonnet-CRI": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
"Jurassic-2-Mid": "ai21.j2-mid-v1",
"Jurassic-2-Ultra": "ai21.j2-ultra-v1",
"Command": "cohere.command-text-v14",
"Command-Light": "cohere.command-light-text-v14",
"Cohere-Embeddings-En": "cohere.embed-english-v3",
"Cohere-Embeddings-Multilingual": "cohere.embed-multilingual-v3",
"Titan-Embeddings-G1": "amazon.titan-embed-text-v1",
"Titan-Text-Embeddings-V2": "amazon.titan-embed-text-v2:0",
"Titan-Text-G1": "amazon.titan-text-express-v1",
"Titan-Text-G1-Light": "amazon.titan-text-lite-v1",
"Titan-Text-G1-Premier": "amazon.titan-text-premier-v1:0",
"Titan-Text-G1-Express": "amazon.titan-text-express-v1",
"Llama2-13b-Chat": "meta.llama2-13b-chat-v1",
"Nova-Canvas": "amazon.nova-canvas-v1:0",
"Nova-Reel": "amazon.nova-reel-v1:0",
"Nova-Micro": "amazon.nova-micro-v1:0",
"Nova-Lite": "amazon.nova-lite-v1:0",
"Nova-Pro": "amazon.nova-pro-v1:0",
"Nova-Pro-CRI": "us.amazon.nova-pro-v1:0",
"SD-3-5-Large": "stability.sd3-5-large-v1:0",
"SD-Ultra": "stability.stable-image-ultra-v1:1",
"SD-3-Large": "stability.sd3-large-v1:0"
"""

class llm_call():

    def __init__(self, **kwargs):

        self.llm=kwargs["llm"]
        self.verbose = kwargs.get("verbose", False)
        self.chain = bedrock_chain(bedrock_utils.converse_api) | bedrock_chain(bedrock_utils.outputparser)

        self.origin_max_tokens = self.llm.inference_config["maxTokens"]
        self.origin_temperature = self.llm.inference_config["temperature"]
            
    def invoke(self, **kwargs):

        agent_name = kwargs.get("agent_name", None)
        system_prompts = kwargs.get("system_prompts", None)
        messages = kwargs["messages"]
        enable_reasoning = kwargs.get("enable_reasoning", False)
        reasoning_budget_tokens = kwargs.get("reasoning_budget_tokens", 1024)
        tool_config = kwargs.get("tool_config", None)
        efficient_token = kwargs.get("efficient_token", False)
        #print ("enable_reasoning", enable_reasoning)
        
        if efficient_token:
            additional_model_request_fields = self.llm.additional_model_request_fields
            if self.llm.additional_model_request_fields == None:
                efficient_token_config = {
                    "anthropic_beta": ["token-efficient-tools-2025-02-19"]  # Add this beta flag
                }
            else:
                additional_model_request_fields["anthropic_beta"] = ["token-efficient-tools-2025-02-19"]  # Add this beta flag
                efficient_token_config = additional_model_request_fields
            self.llm.additional_model_request_fields = efficient_token_config

        if enable_reasoning:
            additional_model_request_fields = self.llm.additional_model_request_fields
            if self.llm.additional_model_request_fields == None:
                reasoning_config = {
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": reasoning_budget_tokens
                    }
                }
            else:
                additional_model_request_fields["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": reasoning_budget_tokens
                }
                reasoning_config = additional_model_request_fields

            # Ensure maxTokens is greater than reasoning_budget
            if self.llm.inference_config["maxTokens"] <= reasoning_budget_tokens:
                # Make it just one token more than the reasoning budget
                adjusted_max_tokens = reasoning_budget_tokens + 1
                print(f'Info: Extended Thinking enabled increasing maxTokens from {self.llm.inference_config["maxTokens"]} to {adjusted_max_tokens} to exceed reasoning budget')
                self.llm.inference_config["maxTokens"] = adjusted_max_tokens

            self.llm.additional_model_request_fields = reasoning_config
            self.llm.inference_config["temperature"] = 1.0
                       
        response, ai_message = self.chain( ## pipeline의 제일 처음 func의 argument를 입력으로 한다. 여기서는 converse_api의 arg를 쓴다.
            llm=self.llm,
            system_prompts=system_prompts,
            messages=messages,
            tool_config=tool_config,
            verbose=self.verbose
        )
        
        # Reset
        if enable_reasoning:
            self.llm.additional_model_request_fields = None
            self.llm.inference_config["maxTokens"] = self.origin_max_tokens
            self.llm.inference_config["temperature"] = self.origin_temperature
            
        return response, ai_message

import boto3
import json
from langfuse.decorators import observe, langfuse_context
from botocore.exceptions import ClientError
 
class llm_call_langfuse():

    def __init__(self, **kwargs):

        self.llm=kwargs["llm"]
        self.verbose = kwargs.get("verbose", False)
        self.chain = bedrock_chain(bedrock_utils_tokens.converse_api) | bedrock_chain(bedrock_utils_tokens.outputparser)
        # self.chain_no_stream = bedrock_chain(bedrock_utils_tokens.converse_api)

        self.origin_max_tokens = self.llm.inference_config["maxTokens"]
        self.origin_temperature = self.llm.inference_config["temperature"]
            
    def invoke(self, **kwargs):

        agent_name = kwargs.get("agent_name", None)
        system_prompts = kwargs.get("system_prompts", None)
        messages = kwargs["messages"]
        enable_reasoning = kwargs.get("enable_reasoning", False)
        reasoning_budget_tokens = kwargs.get("reasoning_budget_tokens", 1024)
        tool_config = kwargs.get("tool_config", None)
        efficient_token = kwargs.get("efficient_token", False)
        #print ("enable_reasoning", enable_reasoning)
        
        if efficient_token:
            additional_model_request_fields = self.llm.additional_model_request_fields
            if self.llm.additional_model_request_fields == None:
                efficient_token_config = {
                    "anthropic_beta": ["token-efficient-tools-2025-02-19"]  # Add this beta flag
                }
            else:
                additional_model_request_fields["anthropic_beta"] = ["token-efficient-tools-2025-02-19"]  # Add this beta flag
                efficient_token_config = additional_model_request_fields
            self.llm.additional_model_request_fields = efficient_token_config

        if enable_reasoning:
            additional_model_request_fields = self.llm.additional_model_request_fields
            if self.llm.additional_model_request_fields == None:
                reasoning_config = {
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": reasoning_budget_tokens
                    }
                }
            else:
                additional_model_request_fields["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": reasoning_budget_tokens
                }
                reasoning_config = additional_model_request_fields

            # Ensure maxTokens is greater than reasoning_budget
            if self.llm.inference_config["maxTokens"] <= reasoning_budget_tokens:
                # Make it just one token more than the reasoning budget
                adjusted_max_tokens = reasoning_budget_tokens + 1
                print(f'Info: Extended Thinking enabled increasing maxTokens from {self.llm.inference_config["maxTokens"]} to {adjusted_max_tokens} to exceed reasoning budget')
                self.llm.inference_config["maxTokens"] = adjusted_max_tokens

            self.llm.inference_config["temperature"] = 1.0 # 추론 모드에서는 1.0 이외는 에러 발생 함.

        
        # 기본 함수 이름 설정
        observation_name = agent_name
        
        # 함수를 직접 호출하는 대신, 먼저 데코레이터를 동적으로 적용
        # 이렇게 하면 observe에서 사용하는
        # 장식된 함수가 매번 새롭게 생성됩니다
        decorated_func = observe(as_type="generation", name=observation_name)(self.wrapped_bedrock_converse)
        
        response, ai_message = decorated_func(
            agent_name=agent_name,
            llm=self.llm,
            system_prompts=system_prompts,
            messages=messages,
            tool_config=tool_config,
            modelId = self.llm.model_id,
            inferenceConfig = self.llm.inference_config,
            additionalModelRequestFields = self.llm.additional_model_request_fields,
            verbose=self.verbose
        )   

        # Reset
        if enable_reasoning:
            self.llm.additional_model_request_fields = None
            self.llm.inference_config["maxTokens"] = self.origin_max_tokens
            self.llm.inference_config["temperature"] = self.origin_temperature
        
        return response, ai_message
    
    def wrapped_bedrock_converse(self, **kwargs):

        function_name = kwargs.pop('agent_name', "Bedrock Converse")
        # Langfuse 컨텍스트에 이름 업데이트
        langfuse_context.update_current_observation(name=function_name)    

        # 1. extract model metadata
        kwargs_clone = kwargs.copy()
        system_prompts = kwargs_clone.pop('system_prompts', None)
        messages = kwargs_clone.pop('messages', None)
        tool_config = kwargs_clone.pop('tool_config', None)
        # system = kwargs_clone.pop('system', None)
        
        # messages와 system을 형식에 맞게 처리
        input_data = {
            "kwargs": {
                "system": system_prompts,            
                "messages": messages,
            }
        }    

        modelId = kwargs_clone.pop('modelId', None)

        model_parameters = {
            **kwargs_clone.pop('inferenceConfig', {}),
        }
        ##############################3
        # 1. Langfuse 관측 컨텍스트에 입력, 모델 ID, 파라미터, 기타 메타데이터를 업데이트합니다.
        ##############################3
        langfuse_context.update_current_observation(
            input=input_data,
            model=modelId,
            model_parameters=model_parameters,
            # metadata=kwargs_clone
        )
        ##############################3
        # 2. model call with error handling
        ##############################3
        import time
        
        max_attempts = 3
        delay_seconds = 60
        response = None
        ai_message = None
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response, ai_message = self.chain(
                    llm=self.llm,
                    system_prompts=system_prompts,
                    messages=messages,
                    tool_config=tool_config,
                    verbose=self.verbose
                )
                # 성공하면 반복문 종료
                break
                
            except (ClientError, Exception) as e:
                last_error = e
                error_message = f"Attempt {attempt + 1}/{max_attempts}: ERROR: Can't invoke '{modelId}'. Reason: {e}"
                print(error_message)
                
                # 마지막 시도가 아니면 대기 후 재시도
                if attempt < max_attempts - 1:
                    time.sleep(delay_seconds)
                    continue
                
                # 마지막 시도에서 실패한 경우
                final_error_message = f"ERROR: Can't invoke '{modelId}' after {max_attempts} attempts. Last error: {last_error}"
                langfuse_context.update_current_observation(level="ERROR", status_message=final_error_message)
                print("Error in exception during calling chain: ", final_error_message)
                return {"text": final_error_message}, {"error": final_error_message}
    

        ##############################3
        # 3. extract response metadata
        ##############################3
        # Langfuse에 출력 텍스트, 토큰 사용량, 응답 메타데이터를 기록합니다.
        try:
            response_text = response["text"]
            reasoning_text = response["reasoning"]
            print("## response in wrapped_bedrock_converse: \n", json.dumps(response, indent=2, ensure_ascii=False))

            token_usage = response["token_usage"]
            input_tokens = token_usage.get("inputTokens", 0)
            output_tokens = token_usage.get("outputTokens", 0)
            total_tokens = token_usage.get("totalTokens", 0)

            langfuse_context.update_current_observation(
                output=response_text,
                usage_details={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                metadata={
                    "reasoning_text": reasoning_text, 
                }
            )

        except (ClientError, Exception) as e:
            print("## response in except in adding to langfuse: \n", response) 
            error_message = f"ERROR: Can't parse:  Reason: {e}"
            langfuse_context.update_current_observation(level="ERROR", status_message=error_message)
            print(error_message)
            # Always return a dict with 'text' key to avoid KeyError downstream
            return {"text": error_message}, {"error": error_message}

        # return {"text": response_text}, ai_message
        return response, ai_message


def get_llm_by_type(llm_type: LLMType):
    """
    Get LLM instance by type. Returns cached instance if available.
    """

    boto3_bedrock = bedrock.get_bedrock_client(
        assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
        endpoint_url=os.environ.get("BEDROCK_ENDPOINT_URL", None),
        region=os.environ.get("AWS_DEFAULT_REGION", None),
    )

    if llm_type == "reasoning":
        llm = bedrock_model(
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 4096,  # 8192*3에서 4096으로 수정
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
        
    elif llm_type == "basic":
        llm = bedrock_model(
            # model_id=bedrock_info.get_model_id(model_name="Nova-Pro-CRI"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V3-Haiku"),
            # model_id=bedrock_info.get_model_id(model_name="Nova-Lite"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-Sonnet"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V4-0-Sonnet-CRI"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 4096,  # 8192에서 4096으로 수정
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
    elif llm_type == "vision":
        llm = bedrock_model(
            #model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            # model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-Sonnet"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 4096,  # 8192에서 4096으로 수정
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
    elif llm_type == "browser":
        llm = ChatBedrock(
            #model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            client=boto3_bedrock,
            model_kwargs={
                "max_tokens": 4096,  # 8192에서 4096으로 수정
                "stop_sequences": ["\n\nHuman"],
            },
            #streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}")
        
    return llm


# Initialize LLMs for different purposes - now these will be cached
reasoning_llm = get_llm_by_type("reasoning")
basic_llm = get_llm_by_type("basic")
browser_llm = get_llm_by_type("browser")

if __name__ == "__main__":
    stream = reasoning_llm.stream("what is mcp?")
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    print(full_response)

    basic_llm.invoke("Hello")
    browser_llm.invoke("Hello")