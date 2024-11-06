import os
from PIL import Image
import base64
from io import BytesIO


# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Shows how to use tools with the Converse API and the Cohere Command R model.
"""

import json
import boto3


from botocore.exceptions import ClientError


def print_json(response):
    print(json.dumps(response, ensure_ascii=False, indent=2))


def generate_text(bedrock_client, model_id, tool_config, prompt, input_image, inference_config, tools, verbose=False):

    print("## Generating text with model %s", model_id)


    with open(input_image, "rb") as f:
        image = f.read()

    message = {
        "role": "user",
        "content": [
            {
                "text": prompt
            },
            {
                    "image": {
                        "format": 'png',
                        "source": {
                            "bytes": image
                        }
                    }
            }
        ]
    }

    messages = [message]


    if tools:
        print("ToolUse is used")
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config,
            inferenceConfig = inference_config,
        )

    else:
        print("ToolUse is NOT used")        
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig = inference_config,
        )

    output_message = response['output']['message']

    if verbose:
        print("##response: after the first converse() with the query and tool_config ")
        print_json(response)
        messages.append(output_message)
        print("## messages: ", messages)
        


    return output_message
    

def parse_korean_comments(message):
    output = message['content'][0]['text']

    print(format_text_with_line_breaks(output))
    

def parse_korean_comments_tools(message):
    # Access the content list
    content = message.get('content', [])

    print("## content: \n", content)
    
    # Look for toolUse dictionary in content
    for item in content:
        if 'toolUse' in item:
            tool_input = item['toolUse'].get('input', {})
            comment_1 = tool_input.get('korean_comment_1', '')
            print("Describe image :")
            print(format_text_with_line_breaks(comment_1))    

            comment_2 = tool_input.get('korean_comment_2', '')
            print("Gender 2:", comment_2)            
            print(format_text_with_line_breaks(comment_2))    

            comment_3 = tool_input.get('korean_comment_3', '')
            print("Skin color:", comment_3)            
            print(format_text_with_line_breaks(comment_3))    




    # return korean_comment_1, korean_comment_2, korean_comment_3


def format_text_with_line_breaks(text):
    """
    텍스트를 마침표 단위로 줄 바꿈하는 함수 (빈 줄 없음)
    
    Args:
        text (str): 원본 텍스트
        
    Returns:
        str: 마침표 단위로 줄 바꿈된 텍스트
    """
    # 줄바꿈으로 텍스트를 분리하여 각 줄을 처리
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # '##'로 시작하는 줄은 그대로 유지
        if line.startswith('##'):
            formatted_lines.append(line)
            continue
            
        # 마침표로 문장을 분리하고 각 문장 뒤에 줄바꿈 추가
        sentences = line.split('.')
        # 빈 문장 제거 및 마침표 다시 추가
        sentences = [s.strip() + '.' for s in sentences if s.strip()]
        # 각 문장을 새 줄에 추가 (빈 줄 없음)
        formatted_lines.extend(sentences)
    
    # 모든 줄을 줄바꿈으로 합쳐서 하나의 문자열로 만듦
    return '\n'.join(formatted_lines)


