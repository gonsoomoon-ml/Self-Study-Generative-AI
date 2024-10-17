import os
from PIL import Image
import base64
from io import BytesIO


# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Shows how to use tools with the Converse API and the Cohere Command R model.
"""

import logging
import json
import boto3


from botocore.exceptions import ClientError


class StationNotFoundError(Exception):
    """Raised when a radio station isn't found."""
    pass


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def print_json(response):
    print(json.dumps(response, ensure_ascii=False, indent=2))


def generate_text(bedrock_client, model_id, tool_config, input_text):
    """Generates text using the supplied Amazon Bedrock model. If necessary,
    the function handles tool use requests and sends the result to the model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The Amazon Bedrock model ID.
        tool_config (dict): The tool configuration.
        input_text (str): The input text.
    Returns:
        Nothing.
    """

    print("## Generating text with model %s", model_id)

   # Create the initial message from the user input.
    messages = [{
        "role": "user",
        "content": [{"text": input_text}]
    }]

    # print("## messages given: This is a query a user ask")
    # print_json(messages)

    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        toolConfig=tool_config
    )

    print("##response: after the first converse() with the query and tool_config ")
    print_json(response)

    # output_message = response['output']['message']
    # messages.append(output_message)
    # print the final response from the model.
    

def load_and_prep_images(directory='.'):
    image_data = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            try:
                # Open the image
                img_path = os.path.join(directory, filename)
                with Image.open(img_path) as img:
                    # Convert to RGB if the image is in a different mode
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Add the image to the list
                    image_data.append({
                        'filename': filename,
                        'image': img.copy()
                    })
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    return image_data



def rotate_image(image, i = 1):
    return image.rotate(90 * i)

def upscale_image_to_1568(image):
    # Calculate the aspect ratio
    aspect_ratio = image.width / image.height
    
    # Determine new dimensions
    if image.width > image.height:
        new_width = 1568
        new_height = int(1568 / aspect_ratio)
    else:
        new_height = 1568
        new_width = int(1568 * aspect_ratio)
    
    # Resize the image
    return image.resize((new_width, new_height), Image.LANCZOS)




from langchain_core.messages import HumanMessage
import base64
from io import BytesIO
from langchain_aws import ChatBedrockConverse
from anthropic import AnthropicBedrock

mistral_large = ChatBedrockConverse(
    model="mistral.mistral-large-2407-v1:0",
    temperature=0,
    max_tokens=None,
)

def unpack_comments(response):
    formatted_comments = ""
    for key, comment in response.content[0].input.items():
        formatted_comments += f"{key}: {comment}\n"
    
    return formatted_comments

def invoke_prompt_with_image(prompt, image, tools=False):
    client = AnthropicBedrock()
    
    # Convert PIL Image to bytes
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()

    # Encode bytes to base64 string
    img_str = base64.b64encode(img_bytes).decode('utf-8')

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_str
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]

    if tools:
        tools = build_comment_tool_output_structure()
        print("t## ools: \n", tools)
        response = client.messages.create(
            model="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            messages=messages,
            temperature=0,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "tool", "name": "Comments"},
        )
    else:
        response = client.messages.create(
            model="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            messages=messages,
            temperature=0,
            max_tokens=4096
        )

    print("## resposne in invoke_prompt_with_image: \n", response)

    if tools:
        return unpack_comments(response)
    else:
        return response.content[0].text

def classify_denial(response):
    message = HumanMessage(
        content=[
            {"type": "text", "text": f"Classify the following llm response, as to whether or not it's denying analyzing an image based on it's contents: \n\n’’’\n{response}\n’’’\n\n Provide only your classification in the following format: 'DENIAL|ACCEPTED’ where ‘DENIAL’ indicates a denial, and ‘ACCEPTED’ indicated no denial. Just provide the classification, no other text or characters."},
        ],
    )
    ai_msg = mistral_large.invoke([message])
    return ai_msg.content

def run_investigation(prompt, prepped_images, tools = False):
    for image in prepped_images:
        passed = False
        
        response = invoke_prompt_with_image(prompt, image['image'], tools = tools)
        print("## response after invoke_prompt_with_image: \n", response)
        classification = classify_denial(response)
        
        if classification != "DENIAL":
            passed = True

        
        print(f"Image: {image['filename']}, Classification: {classification}")
                    
        print(f"Image: {image['filename']}, passed: {passed}\n")
        print()    