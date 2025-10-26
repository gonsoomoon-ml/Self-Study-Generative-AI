#!/usr/bin/env python3
"""
AgentCore Runtime Job Invoker - VPC Mode Runtime 테스트

VPC 모드로 배포된 AgentCore Runtime을 테스트합니다.

사용법:
    cd test_vpc_private_setup
    python invoke_agentcore_job_vpc.py

Runtime 정보:
    - Runtime ID: bedrock_manus_runtime_vpc_final-7XCALx4Xuw
    - Network Mode: VPC
    - Subnet: subnet-0b2fb367d6e823a79 (use1-az2)
    - Security Group: sg-0affaea9ac4dc26b1
"""

import json
import sys
import os
from datetime import datetime
import traceback

# 경로 설정 (test_vpc_private_setup에서 실행)
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.abspath(os.path.join(current_dir, '..'))  # 한 단계 위로 (05_insight_extractor_strands_sdk_workshop_phase_2)
sys.path.insert(0, utils_dir)

import boto3
from boto3.session import Session
from botocore.config import Config
from src.utils.strands_sdk_utils import strands_utils

# 설정 - VPC Mode Runtime (새로 성공한 Runtime 사용)
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:057716757052:runtime/bedrock_manus_runtime_vpc_1760773105-PtBWr17D4z"
REGION = "us-east-1"
CLOUDWATCH_LOG_GROUP = "/aws/bedrock-agentcore/client-errors-vpc"  # VPC Runtime 에러 로그 그룹
CLOUDWATCH_LOG_STREAM_PREFIX = "invoke-job-vpc-PtBWr17D4z"  # 로그 스트림 접두사 (VPC runtime ID 포함)

# 프롬프트 복잡도별 예상 시간
# PROMPT = "./data/Dat-fresh-food-claude.csv 파일의 총 매출액 계산해줘. PDF 보고서는 만들지 마."  # 2-5분 (가장 빠름) - VPC 테스트용
# PROMPT = "./data/Dat-fresh-food-claude.csv 파일의 총 매출액을 계산하고 차트 1개와 PDF 보고서를 생성해줘"  # 15-20분
PROMPT = "./data/Dat-fresh-food-claude.csv 파일을 분석해서 총 매출액을 계산하고, 카테고리별 매출 비중도 함께 보여줘. 그리고 pdf 로 보고서 생성해줘"  # 20-25분


def send_error_to_cloudwatch(logs_client, error_message, error_type, full_traceback=None):
    """CloudWatch Logs에 에러 전송

    Args:
        logs_client: boto3 CloudWatch Logs 클라이언트
        error_message: 에러 메시지
        error_type: 에러 타입 (예: "IncompleteRead", "Timeout")
        full_traceback: 전체 traceback 문자열 (optional)
    """
    try:
        # Log stream 이름 생성 (timestamp 포함)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        log_stream_name = f"{CLOUDWATCH_LOG_STREAM_PREFIX}-{timestamp}"

        # Log group이 없으면 생성
        try:
            logs_client.create_log_group(logGroupName=CLOUDWATCH_LOG_GROUP)
            print(f"📝 CloudWatch Log Group 생성: {CLOUDWATCH_LOG_GROUP}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass  # 이미 존재함
        except Exception as e:
            print(f"⚠️  CloudWatch Log Group 생성 실패: {e}")

        # Log stream 생성
        try:
            logs_client.create_log_stream(
                logGroupName=CLOUDWATCH_LOG_GROUP,
                logStreamName=log_stream_name
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass  # 이미 존재함
        except Exception as e:
            print(f"⚠️  CloudWatch Log Stream 생성 실패: {e}")
            return

        # 에러 정보를 JSON으로 구성
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error_message),
            "agent_arn": AGENT_ARN,
        }

        if full_traceback:
            log_entry["traceback"] = full_traceback

        # CloudWatch Logs에 전송
        logs_client.put_log_events(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            logStreamName=log_stream_name,
            logEvents=[
                {
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'message': json.dumps(log_entry, indent=2)
                }
            ]
        )

        print(f"✅ CloudWatch Logs에 에러 기록됨:")
        print(f"   Log Group: {CLOUDWATCH_LOG_GROUP}")
        print(f"   Log Stream: {log_stream_name}")

    except Exception as log_error:
        print(f"⚠️  CloudWatch Logs 전송 실패: {log_error}")


def parse_sse_data(sse_bytes):
    """SSE 데이터 파싱"""
    if not sse_bytes or len(sse_bytes) == 0:
        return None

    try:
        text = sse_bytes.decode('utf-8').strip()
        if not text or text == '':
            return None

        if text.startswith('data: '):
            json_text = text[6:].strip()
            if json_text:
                return json.loads(json_text)
        else:
            return json.loads(text)

    except Exception as e:
        pass

    return None

def main():
    """AgentCore Runtime 호출"""
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"🚀 AgentCore Runtime Job 시작")
    print(f"📅 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Agent ARN: {AGENT_ARN}")
    print(f"{'='*60}\n")

    # boto3 클라이언트 생성
    boto_session = Session()

    my_config = Config(
        connect_timeout=60*100,
        read_timeout=3600,  # 1 시간
        retries={'max_attempts': 0}  # 재시도 비활성화
    )

    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name=REGION,
        config=my_config,
    )

    # CloudWatch Logs 클라이언트 생성 (에러 로깅용)
    logs_client = boto3.client('logs', region_name=REGION)

    # AgentCore Runtime 호출
    print(f"📤 요청 전송 중...")
    print(f"💬 프롬프트: {PROMPT}\n")

    try:
        boto3_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": PROMPT})
        )

        # 응답 처리
        if "text/event-stream" in boto3_response.get("contentType", ""):
            print(f"📥 스트리밍 응답 수신 시작...\n")
            content = []

            for event in boto3_response["response"].iter_lines(chunk_size=1):
                event_data = parse_sse_data(event)
                if event_data is None:
                    continue
                else:
                    strands_utils.process_event_for_display(event_data)
        else:
            print(f"📥 단일 응답 수신...\n")
            try:
                events = []
                for event in boto3_response.get("response", []):
                    print("이벤트:", event)
                    events.append(event)
            except Exception as e:
                print(f"❌ 이벤트 스트림 읽기 에러: {e}")

        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        print(f"\n{'='*60}")
        print(f"✅ AgentCore Runtime Job 완료")
        print(f"📅 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  총 소요 시간: {elapsed_time:.2f}초 ({elapsed_time/60:.2f}분)")
        print(f"{'='*60}\n")

    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__

        # Traceback 전체 문자열 얻기
        full_traceback = traceback.format_exc()

        # 터미널에 출력
        print(f"\n❌ 에러 발생: {error_message}")
        print(f"📛 에러 타입: {error_type}")
        print(f"\nTraceback:")
        print(full_traceback)

        # CloudWatch Logs에 전송
        print(f"\n📤 CloudWatch Logs에 에러 전송 중...")
        try:
            send_error_to_cloudwatch(
                logs_client=logs_client,
                error_message=error_message,
                error_type=error_type,
                full_traceback=full_traceback
            )
        except Exception as log_err:
            print(f"⚠️  CloudWatch 전송 중 추가 에러: {log_err}")

        sys.exit(1)

if __name__ == "__main__":
    main()
