"""
Lab Helper 유틸리티 함수들
기존 전자제품 프로젝트에서 복사 후 이커머스용으로 수정
"""

import boto3
import json
import base64
import hmac
import hashlib
from typing import Any, Dict
from boto3 import Session

# 사용자 이름 상수
username = "testuser"
secret_name = "ecommerce_customer_support_agent"


def get_ssm_parameter(parameter_name: str) -> str:
    """SSM Parameter Store에서 값을 가져옵니다."""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        print(f"SSM Parameter 조회 실패 {parameter_name}: {e}")
        raise


def put_ssm_parameter(parameter_name: str, parameter_value: str, description: str = "") -> None:
    """SSM Parameter Store에 값을 저장합니다."""
    try:
        ssm_client = boto3.client('ssm')
        ssm_client.put_parameter(
            Name=parameter_name,
            Value=parameter_value,
            Type='String',
            Description=description or f"이커머스 에이전트 매개변수: {parameter_name}",
            Overwrite=True
        )
    except Exception as e:
        print(f"SSM Parameter 저장 실패 {parameter_name}: {e}")
        raise


def get_cognito_client_secret() -> str:
    """Cognito 클라이언트 시크릿을 가져옵니다."""
    try:
        # 기존 전자제품 프로젝트와 동일한 방식
        cognito_client = boto3.client('cognito-idp')
        client_id = get_ssm_parameter("/app/ecommerce/agentcore/machine_client_id")
        
        response = cognito_client.describe_user_pool_client(
            UserPoolId=get_ssm_parameter("/app/ecommerce/agentcore/userpool_id"),
            ClientId=client_id
        )
        
        return response['UserPoolClient']['ClientSecret']
    except Exception as e:
        print(f"Cognito 클라이언트 시크릿 조회 실패: {e}")
        raise


def load_api_spec(file_path: str) -> list:
    """API 스펙 파일을 로드합니다."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("API 스펙은 리스트 형태여야 합니다.")
        return data
    except Exception as e:
        print(f"API 스펙 로드 실패 {file_path}: {e}")
        raise


def format_korean_currency(amount: int) -> str:
    """한국 원화 형태로 포맷팅합니다."""
    return f"{amount:,}원"


def format_korean_date(date_str: str) -> str:
    """한국 날짜 형태로 포맷팅합니다."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y년 %m월 %d일 %H시 %M분")
    except:
        return date_str


def get_product_category(product_name: str) -> str:
    """상품명으로 카테고리를 자동 판별합니다."""
    fashion_keywords = [
        "원피스", "블라우스", "셔츠", "니트", "가디건", "청바지", "진", "팬츠", 
        "스커트", "자켓", "코트", "신발", "가방", "벨트", "스카프", "모자"
    ]
    
    beauty_keywords = [
        "립스틱", "립글로스", "파운데이션", "쿠션", "컨실러", "아이섀도", 
        "마스카라", "아이라이너", "스킨", "로션", "크림", "세럼", "토너",
        "클렌저", "향수", "마스크팩", "선크림"
    ]
    
    product_lower = product_name.lower()
    
    if any(keyword in product_lower for keyword in beauty_keywords):
        return "뷰티"
    elif any(keyword in product_lower for keyword in fashion_keywords):
        return "패션"
    else:
        return "기타"


def generate_customer_message(customer_type: str = "일반") -> Dict[str, Any]:
    """고객 유형별 맞춤 메시지를 생성합니다."""
    messages = {
        "VIP": {
            "greeting": "안녕하세요! VIP 고객님, K-Style을 이용해 주셔서 감사합니다.",
            "closing": "앞으로도 더욱 특별한 서비스로 모시겠습니다. 감사합니다!",
            "benefits": ["무료 배송", "15% 할인 쿠폰", "우선 배송", "전용 상담"]
        },
        "일반": {
            "greeting": "안녕하세요! K-Style 고객센터입니다.",
            "closing": "더 나은 서비스로 찾아뵙겠습니다. 감사합니다!",
            "benefits": ["무료 배송", "5% 적립", "당일 배송"]
        },
        "신규": {
            "greeting": "안녕하세요! K-Style에 오신 것을 환영합니다!",
            "closing": "첫 구매 고객님께 특별 혜택을 드렸습니다. 감사합니다!",
            "benefits": ["첫 구매 20% 할인", "무료 배송", "신규 회원 쿠폰"]
        }
    }
    
    return messages.get(customer_type, messages["일반"])


class EcommerceAgentUtils:
    """이커머스 에이전트 전용 유틸리티 클래스"""
    
    @staticmethod
    def parse_size_option(option_str: str) -> Dict[str, str]:
        """옵션 문자열을 파싱합니다. 예: '화이트/M' -> {'color': '화이트', 'size': 'M'}"""
        try:
            if '/' in option_str:
                parts = option_str.split('/')
                return {
                    'color': parts[0].strip(),
                    'size': parts[1].strip() if len(parts) > 1 else ''
                }
            else:
                # 사이즈만 있는 경우
                return {'color': '', 'size': option_str.strip()}
        except:
            return {'color': '', 'size': ''}
    
    @staticmethod
    def get_shipping_carrier(tracking_number: str) -> str:
        """운송장 번호로 택배사를 자동 판별합니다."""
        # 실제로는 택배사별 운송장 번호 패턴으로 판별
        carriers = {
            "1": "CJ대한통운",
            "2": "한진택배", 
            "3": "로젠택배",
            "4": "우체국택배"
        }
        
        first_digit = tracking_number[0] if tracking_number else "1"
        return carriers.get(first_digit, "CJ대한통운")
    
    @staticmethod
    def calculate_refund_amount(original_price: int, shipping_fee: int = 0) -> Dict[str, int]:
        """환불 금액을 계산합니다."""
        return {
            "product_price": original_price,
            "shipping_fee": shipping_fee,
            "total_refund": original_price - shipping_fee
        }
    
    @staticmethod
    def get_trend_keywords() -> Dict[str, list]:
        """2024년 패션/뷰티 트렌드 키워드를 반환합니다."""
        return {
            "fashion": [
                "오버사이즈 블레이저", "플리츠 스커트", "와이드 진", 
                "크롭 니트", "버킷백", "처키 스니커즈", "맥시 코트"
            ],
            "beauty": [
                "코랄 메이크업", "글래스 스킨", "그러데이션 립",
                "또렷한 아이라이너", "내추럴 브로우", "크림 블러셔"
            ],
            "colors": [
                "베리 버간디", "로맨틱 코랄", "소프트 라벤더",
                "클래식 네이비", "웜 베이지", "미스트 그레이"
            ]
        }


def create_mock_order_data(order_number: str) -> Dict[str, Any]:
    """테스트용 모킹 주문 데이터를 생성합니다."""
    import random
    from datetime import datetime, timedelta
    
    fashion_items = [
        "플라워 패턴 원피스", "크롭 니트 가디건", "와이드 데님 팬츠",
        "플리츠 미디 스커트", "오버사이즈 블레이저", "체크 셔츠"
    ]
    
    beauty_items = [
        "쿠션 파운데이션", "매트 립스틱", "글로우 하이라이터",
        "볼륨 마스카라", "코랄 블러셔", "내추럴 아이브로우"
    ]
    
    all_items = fashion_items + beauty_items
    selected_item = random.choice(all_items)
    
    return {
        "order_number": order_number,
        "customer_name": random.choice(["김영희", "이철수", "박민지", "최준호"]),
        "item_name": selected_item,
        "category": get_product_category(selected_item),
        "price": random.randint(20000, 150000),
        "status": random.choice(["주문 확인", "배송 준비", "배송 중", "배송 완료"]),
        "order_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "vip_level": random.choice(["일반", "실버", "골드", "다이아몬드"])
    }


def get_aws_account_id() -> str:
    """현재 AWS 계정 ID를 가져옵니다."""
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]


def get_aws_region() -> str:
    """현재 AWS 리전을 가져옵니다."""
    session = Session()
    return session.region_name


def create_agentcore_runtime_execution_role():
    """AgentCore Runtime 실행 역할을 생성합니다."""
    iam = boto3.client("iam")
    boto_session = Session()
    region = boto_session.region_name
    account_id = get_aws_account_id()
    
    role_name = f"EcommerceCustomerSupportBedrockAgentCoreRole-{region}"
    policy_name = f"EcommerceCustomerSupportBedrockAgentCorePolicy-{region}"
    
    # 기존 정책과 역할 삭제 (있는 경우)
    try:
        # 기존 정책 분리 및 삭제
        try:
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"✅ 기존 정책 분리: {policy_name}")
        except:
            pass
        
        try:
            iam.delete_policy(PolicyArn=f"arn:aws:iam::{account_id}:policy/{policy_name}")
            print(f"✅ 기존 정책 삭제: {policy_name}")
        except:
            pass
            
        try:
            iam.delete_role(RoleName=role_name)
            print(f"✅ 기존 역할 삭제: {role_name}")
        except:
            pass
    except Exception as e:
        print(f"기존 리소스 정리 중 오류 (무시 가능): {e}")
    
    # Trust relationship policy
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    },
                },
            }
        ],
    }
    
    # IAM policy document
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                "Resource": [f"arn:aws:ecr:{region}:{account_id}:repository/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogGroups"],
                "Resource": [f"arn:aws:logs:{region}:{account_id}:log-group:*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ],
            },
            {
                "Sid": "ECRTokenAccess",
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Resource": "*",
                "Action": "cloudwatch:PutMetricData",
                "Condition": {
                    "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                },
            },
            {
                "Sid": "GetAgentAccessToken",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetWorkloadAccessToken",
                    "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                    "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*",
                ],
            },
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:inference-profile/*",
                ],
            },
            {
                "Sid": "BedrockAgentCoreMemoryAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:ListMemoryNodes",
                    "bedrock-agentcore:GetMemoryNode",
                    "bedrock-agentcore:CreateMemoryNode",
                    "bedrock-agentcore:UpdateMemoryNode",
                    "bedrock-agentcore:DeleteMemoryNode",
                ],
                "Resource": [f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/*"],
            },
            {
                "Sid": "SSMParameterAccess",
                "Effect": "Allow",
                "Action": ["ssm:GetParameter", "ssm:GetParameters"],
                "Resource": [f"arn:aws:ssm:{region}:{account_id}:parameter/app/ecommerce/*"],
            },
        ],
    }
    
    # IAM Role 생성 (새로 만들기)
    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Ecommerce Customer Support AgentCore Runtime Execution Role",
    )
    print(f"✅ Created IAM role: {role_name}")
    
    # Policy 생성 (새로 만들기)
    policy_response = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
        Description="Ecommerce Customer Support AgentCore Runtime Policy",
    )
    policy_arn = policy_response["Policy"]["Arn"]
    print(f"✅ Created policy: {policy_name}")
    
    # Policy를 Role에 연결
    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    print(f"✅ Attached policy to role")
    
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    print(f"Role ARN: {role_arn}")
    print(f"Policy ARN: {policy_arn}")
    
    return role_arn


def save_customer_support_secret(secret_value):
    """Secret을 AWS Secrets Manager에 저장합니다."""
    boto_session = Session()
    region = boto_session.region_name
    secrets_client = boto3.client("secretsmanager", region_name=region)

    try:
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=secret_value,
            Description="Ecommerce Customer Support Agent Cognito Configuration",
        )
        print(f"✅ Created secret: {secret_name}")
    except secrets_client.exceptions.ResourceExistsException:
        secrets_client.update_secret(SecretId=secret_name, SecretString=secret_value)
        print(f"✅ Updated existing secret: {secret_name}")
    except Exception as e:
        print(f"❌ Error saving secret: {str(e)}")
        return False
    return True


def setup_cognito_user_pool():
    """이커머스 에이전트용 Cognito 사용자 풀을 설정합니다."""
    boto_session = Session()
    region = boto_session.region_name
    # Cognito 클라이언트 초기화
    cognito_client = boto3.client("cognito-idp", region_name=region)
    
    # 사용자 풀 생성
    user_pool_response = cognito_client.create_user_pool(
        PoolName="EcommerceCustomerSupportPool", 
        Policies={"PasswordPolicy": {"MinimumLength": 8}}
    )
    pool_id = user_pool_response["UserPool"]["Id"]
    
    # 앱 클라이언트 생성
    app_client_response = cognito_client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="MCPServerPoolClient",
        GenerateSecret=True,
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_SRP_AUTH",
        ],
    )
    print(app_client_response["UserPoolClient"])
    client_id = app_client_response["UserPoolClient"]["ClientId"]
    client_secret = app_client_response["UserPoolClient"]["ClientSecret"]
    
    # 사용자 생성
    cognito_client.admin_create_user(
        UserPoolId=pool_id,
        Username=username,
        TemporaryPassword="Temp123!",
        MessageAction="SUPPRESS",
    )
    
    # 영구 비밀번호 설정
    cognito_client.admin_set_user_password(
        UserPoolId=pool_id,
        Username=username,
        Password="MyPassword123!",
        Permanent=True,
    )
    
    app_client_id = client_id
    key = client_secret
    message = bytes(username + app_client_id, "utf-8")
    key = bytes(key, "utf-8")
    secret_hash = base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
    
    # 사용자 인증 및 액세스 토큰 가져오기
    auth_response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": "testuser",
            "PASSWORD": "MyPassword123!",
            "SECRET_HASH": secret_hash,
        },
    )
    bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
    
    # 필요한 값들 출력
    print(f"Pool id: {pool_id}")
    print(
        f"Discovery URL: https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
    )
    print(f"Client ID: {client_id}")
    print(f"Bearer Token: {bearer_token}")
    
    # 추가 처리를 위한 값들 반환
    cognito_config = {
        "pool_id": pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "secret_hash": secret_hash,
        "bearer_token": bearer_token,
        "discovery_url": f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration",
    }
    save_customer_support_secret(json.dumps(cognito_config))
    
    return cognito_config


def reauthenticate_user(client_id, client_secret):
    """사용자를 재인증하고 새로운 토큰을 반환합니다."""
    boto_session = Session()
    region = boto_session.region_name
    # Cognito 클라이언트 초기화
    cognito_client = boto3.client("cognito-idp", region_name=region)
    
    # 사용자 인증 및 액세스 토큰 가져오기
    message = bytes(username + client_id, "utf-8")
    key = bytes(client_secret, "utf-8")
    secret_hash = base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
    
    auth_response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": "MyPassword123!",
            "SECRET_HASH": secret_hash,
        },
    )
    bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
    return bearer_token