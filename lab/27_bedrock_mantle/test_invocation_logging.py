"""
bedrock-runtime 엔드포인트를 통해 Claude Opus 4.8을 호출하고
Model Invocation Logging 활성화 여부를 확인하는 테스트 스크립트.

사용법:
    uv run python test_invocation_logging.py
"""

import boto3
from datetime import datetime


def check_logging_config():
    """Invocation Logging 설정 상태를 조회한다."""
    client = boto3.client("bedrock", region_name="us-west-2")

    print("=" * 60)
    print("1. Model Invocation Logging 설정 확인")
    print("=" * 60)

    try:
        response = client.get_model_invocation_logging_configuration()
        config = response.get("loggingConfig", {})

        if not config:
            print("⚠️  Invocation Logging이 설정되지 않았습니다.")
            print("   AWS Console > Bedrock > Settings > Model invocation logging 에서 활성화하세요.")
            return False

        print(f"  CloudWatch 로깅: {config.get('cloudWatchConfig', {}).get('logGroupName', '미설정')}")
        print(f"  S3 로깅: {config.get('s3Config', {}).get('bucketName', '미설정')}")
        print(f"  텍스트 데이터 로깅: {config.get('textDataDeliveryEnabled', False)}")
        print(f"  이미지 데이터 로깅: {config.get('imageDataDeliveryEnabled', False)}")
        return True

    except Exception as e:
        print(f"❌ 로깅 설정 조회 실패: {e}")
        return False


def invoke_opus_converse():
    """bedrock-runtime의 Converse API로 Opus 4.8을 호출한다."""
    client = boto3.client("bedrock-runtime", region_name="us-west-2")
    model_id = "us.anthropic.claude-opus-4-8"
    # model_id = "global.anthropic.claude-opus-4-8"

    print()
    print("=" * 60)
    print("2. bedrock-runtime Converse API로 Opus 4.8 호출")
    print("=" * 60)
    print(f"  모델: {model_id}")
    print(f"  시각: {datetime.now().isoformat()}")
    print()

    try:
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "안녕! 너가 Claude Opus 4.8인지 한 문장으로 확인해줘."}],
                }
            ],
            inferenceConfig={
                "maxTokens": 100,
            },
        )

        output_message = response["output"]["message"]
        reply_text = output_message["content"][0]["text"]
        usage = response["usage"]
        stop_reason = response["stopReason"]

        request_id = response["ResponseMetadata"]["RequestId"]

        print(f"  응답: {reply_text}")
        print(f"  종료 사유: {stop_reason}")
        print(f"  입력 토큰: {usage['inputTokens']}")
        print(f"  출력 토큰: {usage['outputTokens']}")
        print(f"  요청ID: {request_id}")
        print()
        print("✅ bedrock-runtime 호출 성공")
        return request_id

    except client.exceptions.AccessDeniedException as e:
        print(f"❌ 접근 거부: {e}")
        print("   Bedrock 콘솔에서 Claude Opus 4.8 모델 접근을 활성화하세요.")
        return None
    except client.exceptions.ValidationException as e:
        print(f"❌ 유효성 검증 실패: {e}")
        return None
    except Exception as e:
        print(f"❌ 호출 실패: {e}")
        return None


def check_cloudwatch_logs(request_id):
    """Invocation Logging이 CloudWatch에 기록되었는지 실제로 조회한다."""
    import time
    import json

    client = boto3.client("logs", region_name="us-west-2")
    log_group = "bedrock/model-invocations"

    print()
    print("=" * 60)
    print("3. CloudWatch 로그 조회")
    print("=" * 60)
    print("  로그 반영 대기 중 (15초)...")
    time.sleep(15)

    now = int(time.time() * 1000)
    five_min_ago = now - 300000

    try:
        response = client.filter_log_events(
            logGroupName=log_group,
            startTime=five_min_ago,
            filterPattern=f'"{request_id}"',
        )

        events = response.get("events", [])
        if not events:
            print("  ⚠️  로그를 찾지 못했습니다. 잠시 후 다시 시도하세요.")
            return

        for event in events:
            msg = json.loads(event["message"])
            print()
            print(f"  시각: {msg['timestamp']}")
            print(f"  작업: {msg['operation']}")
            print(f"  모델: {msg['modelId']}")
            print(f"  요청ID: {msg['requestId']}")
            print(f"  추론 리전: {msg.get('inferenceRegion', 'N/A')}")

            if "input" in msg:
                inp = msg["input"]
                print(f"  입력 토큰: {inp.get('inputTokenCount', 'N/A')}")
                body = inp.get("inputBodyJson", {})
                messages = body.get("messages", [])
                for m in messages:
                    for block in m.get("content", []):
                        if "text" in block:
                            print(f"  입력 프롬프트: {block['text'][:200]}")

            if "output" in msg:
                out = msg["output"]
                print(f"  출력 토큰: {out.get('outputTokenCount', 'N/A')}")
                body = out.get("outputBodyJson", {})
                if "output" in body:
                    content = body["output"]["message"]["content"]
                    for block in content:
                        if "text" in block:
                            print(f"  응답 내용: {block['text'][:200]}")

            print()
            print("  ✅ Invocation Logging 정상 기록 확인!")

    except Exception as e:
        print(f"  ❌ 로그 조회 실패: {e}")


if __name__ == "__main__":
    logging_enabled = check_logging_config()
    request_id = invoke_opus_converse()

    if logging_enabled and request_id:
        check_cloudwatch_logs(request_id)
    elif request_id and not logging_enabled:
        print()
        print("⚠️  호출은 성공했지만 Invocation Logging이 비활성화 상태입니다.")
        print("   로깅을 활성화하려면 AWS Console에서 설정하거나 아래 CLI를 사용하세요:")
        print()
        print('   aws bedrock put-model-invocation-logging-configuration \\')
        print('     --logging-config \'{"cloudWatchConfig": {"logGroupName": "/aws/bedrock/model-invocations", "roleArn": "arn:aws:iam::ACCOUNT:role/BedrockLoggingRole"}, "textDataDeliveryEnabled": true}\'')
