from PIL import Image

def resize_with_padding(input_path, output_path, target_size=(1280, 720)):
    # 이미지 열기
    with Image.open(input_path) as img:
        # 원본 이미지의 비율 계산
        target_ratio = target_size[0] / target_size[1]
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            # 이미지가 더 넓은 경우
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
        else:
            # 이미지가 더 높은 경우
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
            
        # 비율 유지하며 리사이즈
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 흰색 배경의 새 이미지 생성
        new_img = Image.new('RGB', target_size, (255, 255, 255))
        
        # 중앙에 배치하기 위한 좌표 계산
        paste_x = (target_size[0] - new_width) // 2
        paste_y = (target_size[1] - new_height) // 2
        
        # 리사이즈된 이미지를 중앙에 붙여넣기
        new_img.paste(resized_img, (paste_x, paste_y))
        
        # 결과 이미지 저장
        new_img.save(output_path, quality=95)

import base64
import json

def call_video_creation(bedrock_runtime, bucket_name, input_image, text_prompt ):
    # Load the input image as a Base64 string. Note, the image resolution 
    # must be exactly 1280x720.
    input_image_path = input_image
    with open(input_image_path, "rb") as f:
        input_image_bytes = f.read()
        input_image_base64 = base64.b64encode(input_image_bytes).decode("utf-8")

    model_input = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": text_prompt,
            "images": [
                {
                    "format": "jpeg",
                    "source": {
                        "bytes": input_image_base64
                    }
                }
            ]
            },
        "videoGenerationConfig": {
            "durationSeconds": 6,
            "fps": 24,
            "dimension": "1280x720",
            "seed": 0
        },
    }

    # Start the asynchronous video generation job.
    invocation = bedrock_runtime.start_async_invoke(
        modelId="amazon.nova-reel-v1:0",
        modelInput=model_input,
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{bucket_name}"
            }
        },
    )

    # Print the response JSON.
    print("Response:")
    response = json.dumps(invocation, indent=2, default=str)
    print(response)       

    return invocation



def show_status_video_creation(bedrock_runtime, invocationArn):
    # Create the Bedrock Runtime client.
    
    invocation = bedrock_runtime.get_async_invoke(
        invocationArn= invocationArn
    )

    # Print the JSON response
    print(json.dumps(invocation, indent=2, default=str))

    invocation_arn = invocation["invocationArn"]
    status = invocation["status"]
    if (status == "Completed"):
        bucket_uri = invocation["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
        video_uri = bucket_uri + "/output.mp4"
        print(f"Video is available at: {video_uri}")

    elif (status == "InProgress"):
        start_time = invocation["submitTime"]
        # print(f"Job {invocation_arn} is in progress. Started at: {start_time}")

    elif (status == "Failed"):
        failure_message = invocation["failureMessage"]
        print(f"Job {invocation_arn} failed. Failure message: {failure_message}")

    return status, invocation


from datetime import datetime

def show_date_str():

    # Get current date and time
    current_datetime = datetime.now()

    # Format it as yyyy-mm-dd-hh-mm
    formatted_datetime = current_datetime.strftime('%Y-%m-%d-%H-%M')
    print(formatted_datetime)    

    return formatted_datetime


import os
import subprocess
import platform
import boto3

def download_file_from_s3(bucket_name, object_key, local_file_path):
    # Create an S3 client
    s3_client = boto3.client('s3')

    # Download the file from S3
    try:
        s3_client.download_file(bucket_name, object_key, local_file_path)
        print(f"Video downloaded successfully to {local_file_path}")
            
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
