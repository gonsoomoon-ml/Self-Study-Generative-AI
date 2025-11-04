#!/usr/bin/env python3
"""
01_create_agentcore_runtime.py

목적:
    AgentCore Runtime을 VPC Private 모드로 생성합니다.
    최신 boto3/bedrock_agentcore_starter_toolkit의 네이티브 launch() 메서드를 사용합니다.

사용법:
    cd setup && uv sync && ./patch_dockerignore_template.sh
    cd ..
    python3 01_create_agentcore_runtime.py

주요 작업:
    1. production_deployment/.env에서 VPC 정보 로드
    2. 기존 IAM Role 재사용 (Phase 1에서 생성)
    3. Runtime.configure()로 VPC 설정 포함하여 구성
    4. Runtime.launch()로 Docker 빌드 + ECR 푸시 + Runtime 생성
    5. Runtime ARN을 .env에 저장

주의사항:
    - 최신 boto3 (>=1.40.65) 및 bedrock_agentcore_starter_toolkit (>=0.1.28) 필요
    - 사전에 setup/patch_dockerignore_template.sh 실행 필수!
    - 지원되는 AZ만 사용 (use1-az2, use1-az4 등)
    - Observability 자동 활성화 (CloudWatch Logs)

실행 순서:
    01_create_agentcore_runtime.py → 03_invoke_agentcore_job_vpc.py (테스트)
"""

import os
import sys
import yaml
import time
from datetime import datetime
from dotenv import load_dotenv
import boto3

# 색상 정의
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(message):
    """헤더 출력"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{message}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def print_success(message):
    """성공 메시지 출력"""
    print(f"{GREEN}✅ {message}{NC}")

def print_error(message):
    """에러 메시지 출력"""
    print(f"{RED}❌ {message}{NC}")

def print_warning(message):
    """경고 메시지 출력"""
    print(f"{YELLOW}⚠️  {message}{NC}")

def print_info(message):
    """정보 메시지 출력"""
    print(f"{BLUE}ℹ️  {message}{NC}")

def main():
    """메인 함수"""
    print_header("AgentCore Runtime 생성 - Native launch() 메서드")

    # ============================================================
    # 1. 환경 설정 로드
    # ============================================================
    print(f"{YELLOW}[1/5] 환경 설정 로드...{NC}")

    # 현재 디렉토리 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = current_dir

    # production_deployment/.env 로드
    env_file = os.path.join(current_dir, "production_deployment", ".env")
    if not os.path.exists(env_file):
        print_error(f".env 파일이 없습니다: {env_file}")
        print_warning("Phase 1, 2를 먼저 배포하세요")
        sys.exit(1)

    load_dotenv(env_file)

    # 필수 환경 변수
    AWS_REGION = os.getenv("AWS_REGION")
    AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")
    VPC_ID = os.getenv("VPC_ID")
    PRIVATE_SUBNET_ID = os.getenv("PRIVATE_SUBNET_ID")  # use1-az2 (지원됨)
    SG_AGENTCORE_ID = os.getenv("SG_AGENTCORE_ID")
    TASK_EXECUTION_ROLE_ARN = os.getenv("TASK_EXECUTION_ROLE_ARN")

    # 기존 Runtime 정보 (있으면 업데이트, 없으면 생성)
    EXISTING_RUNTIME_ARN = os.getenv("RUNTIME_ARN")
    EXISTING_RUNTIME_ID = EXISTING_RUNTIME_ARN.split('/')[-1] if EXISTING_RUNTIME_ARN else None

    # 검증
    required_vars = {
        "AWS_REGION": AWS_REGION,
        "AWS_ACCOUNT_ID": AWS_ACCOUNT_ID,
        "VPC_ID": VPC_ID,
        "PRIVATE_SUBNET_ID": PRIVATE_SUBNET_ID,
        "SG_AGENTCORE_ID": SG_AGENTCORE_ID,
        "TASK_EXECUTION_ROLE_ARN": TASK_EXECUTION_ROLE_ARN
    }

    for var_name, var_value in required_vars.items():
        if not var_value:
            print_error(f"환경 변수 {var_name}가 설정되지 않았습니다")
            sys.exit(1)

    print_success("환경 설정 로드 완료")
    print(f"  - Region: {AWS_REGION}")
    print(f"  - VPC: {VPC_ID}")
    print(f"  - Subnet: {PRIVATE_SUBNET_ID}")
    print(f"  - Security Group: {SG_AGENTCORE_ID}")
    if EXISTING_RUNTIME_ID:
        print(f"  - Existing Runtime: {EXISTING_RUNTIME_ID} (will update)")
    print()

    # ============================================================
    # 2. IAM Role 설정
    # ============================================================
    print(f"{YELLOW}[2/5] IAM Role 설정...{NC}")

    execution_role_arn = TASK_EXECUTION_ROLE_ARN
    print_success(f"기존 IAM Role 재사용: {execution_role_arn}")
    print()

    # ============================================================
    # 3. Runtime 설정 (configure with VPC)
    # ============================================================
    print(f"{YELLOW}[3/5] AgentCore Runtime 설정...{NC}")

    try:
        from bedrock_agentcore_starter_toolkit import Runtime
    except ImportError:
        print_error("bedrock_agentcore_starter_toolkit이 설치되지 않았습니다")
        print_info("설치: cd setup && uv sync && ./patch_dockerignore_template.sh")
        sys.exit(1)

    # Runtime 이름 (고정된 이름 사용)
    agent_name = "deep_insight_runtime_vpc"

    if EXISTING_RUNTIME_ID:
        print_info(f"기존 Runtime을 업데이트합니다: {agent_name}")
    else:
        print_info(f"새 Runtime을 생성합니다: {agent_name}")

    agentcore_runtime = Runtime()

    print(f"  - Agent Name: {agent_name}")
    print(f"  - Entrypoint: agentcore_runtime.py")
    print(f"  - Requirements: requirements.txt")
    print()

    # Configure (VPC 설정 포함 - 올바른 파라미터 사용)
    print_info("configure() 호출 중... (VPC 설정 포함)")
    print_info("파라미터: vpc_enabled=True, vpc_subnets=[...], vpc_security_groups=[...]")
    print()

    # NOTE: CodeBuild Execution Role 설정
    # - 현재: toolkit이 자동으로 Role을 생성하거나 재사용 (권장)
    # - 향후: Phase 1 CloudFormation에서 CodeBuild Role을 생성한 경우,
    #         아래 주석을 해제하고 .env에서 CODEBUILD_EXECUTION_ROLE_ARN 로드하여 사용
    #
    # CODEBUILD_EXECUTION_ROLE_ARN = os.getenv("CODEBUILD_EXECUTION_ROLE_ARN")
    # if CODEBUILD_EXECUTION_ROLE_ARN:
    #     print_info(f"Phase 1 CodeBuild Role 사용: {CODEBUILD_EXECUTION_ROLE_ARN}")

    response = agentcore_runtime.configure(
        agent_name=agent_name,
        entrypoint="agentcore_runtime.py",
        execution_role=execution_role_arn,
        # code_build_execution_role=CODEBUILD_EXECUTION_ROLE_ARN,  # 주석 해제하여 사용
        auto_create_ecr=True,
        requirements_file="requirements.txt",
        region=AWS_REGION,
        # VPC 설정 (올바른 파라미터 이름 사용!)
        vpc_enabled=True,
        vpc_subnets=[PRIVATE_SUBNET_ID],
        vpc_security_groups=[SG_AGENTCORE_ID],
        # 추가 설정
        non_interactive=True
    )

    print_success("Configuration 완료")
    print(f"  - Config: {response.config_path}")
    print(f"  - Dockerfile: {response.dockerfile_path}")
    print()

    # YAML 파일 확인 (VPC 설정이 제대로 저장되었는지)
    print_info("YAML 파일 확인 중...")
    config_file_path = response.config_path
    with open(config_file_path, 'r') as f:
        bedrock_config = yaml.safe_load(f)

    if agent_name in bedrock_config['agents']:
        agent_config = bedrock_config['agents'][agent_name]
        if 'network_configuration' in agent_config.get('aws', {}):
            print_success("✅ VPC 설정이 YAML에 저장되었습니다!")
            print(f"  {agent_config['aws']['network_configuration']}")
        else:
            print_warning("⚠️ VPC 설정이 YAML에 저장되지 않았습니다")
            print_warning("최신 toolkit 버전을 사용 중인지 확인하세요")
    print()

    # ============================================================
    # 4. launch() 호출 (Docker 빌드 + ECR 푸시 + Runtime 생성)
    # ============================================================
    print(f"{YELLOW}[4/5] Runtime 배포 (launch)...{NC}")
    print_warning("이 단계는 5-10분 소요됩니다 (Docker 빌드 + ECR 푸시 + Runtime 생성)")
    print()

    print_info("🐳 Docker 이미지 빌드 중...")
    print_info("📦 ECR 푸시 중...")
    print_info("🚀 Runtime 생성 중...")
    print()

    try:
        # launch()는 agent_name 파라미터를 받지 않음 (configure()에서 이미 설정함)
        launch_response = agentcore_runtime.launch()

        print_success("launch() 완료!")

        # LaunchResult의 올바른 속성 이름 사용
        agent_arn = launch_response.agent_arn
        agent_id = launch_response.agent_id

        print(f"  - Runtime ARN: {agent_arn}")
        print(f"  - Runtime ID: {agent_id}")
        print()

        runtime_id = agent_id

    except Exception as e:
        print_error(f"launch() 실패: {e}")
        print()
        print_warning("에러 원인:")
        print(f"  1. VPC 설정 문제 (지원되지 않는 AZ, Security Group 규칙)")
        print(f"  2. Docker 빌드 실패 (requirements.txt 에러)")
        print(f"  3. ECR 푸시 실패 (권한 부족)")
        print(f"  4. Patch script 미실행 (coordinator.md 누락)")
        print()
        print_info("해결 방법:")
        print(f"  cd setup && ./patch_dockerignore_template.sh")
        print()

        sys.exit(1)

    # ============================================================
    # 5. Runtime 상태 확인 및 .env 업데이트
    # ============================================================
    print(f"{YELLOW}[5/5] Runtime 상태 확인...{NC}")

    agentcore_control = boto3.client('bedrock-agentcore-control', region_name=AWS_REGION)

    end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    current_status = 'CREATING'

    print(f"⏳ Runtime이 READY 상태가 될 때까지 대기 중...")
    print()

    max_attempts = 60  # 10분 (10초 x 60)
    attempts = 0

    while current_status not in end_status and attempts < max_attempts:
        time.sleep(10)
        attempts += 1

        try:
            response_data = agentcore_control.get_agent_runtime(agentRuntimeId=runtime_id)
            current_status = response_data['status']
            print(f"  [{attempts}/{max_attempts}] Status: {current_status}")
        except Exception as e:
            print_error(f"상태 확인 실패: {e}")
            break

    print()

    if current_status == 'READY':
        print_success("Runtime이 READY 상태입니다!")
        print()

        # Runtime 상세 정보
        print_info("Runtime 상세 정보:")
        response_data = agentcore_control.get_agent_runtime(agentRuntimeId=runtime_id)

        print(f"  - Runtime Name: {response_data['agentRuntimeName']}")
        print(f"  - Runtime ARN: {response_data['agentRuntimeArn']}")
        print(f"  - Network Mode: {response_data.get('networkConfiguration', {}).get('networkMode', 'N/A')}")

        if 'networkConfiguration' in response_data:
            network_config = response_data['networkConfiguration']
            if 'networkModeConfig' in network_config:
                mode_config = network_config['networkModeConfig']
                print(f"  - Subnets: {mode_config.get('subnets', [])}")
                print(f"  - Security Groups: {mode_config.get('securityGroups', [])}")

        print()

        # .env 파일 업데이트
        print_info(".env 파일 업데이트 중...")

        with open(env_file, 'r') as f:
            env_lines = f.readlines()

        # 기존 Runtime 정보 제거
        new_lines = []
        skip_section = False
        for line in env_lines:
            if line.strip().startswith("# Phase 3: AgentCore Runtime"):
                skip_section = True
                continue
            if skip_section and (line.startswith("RUNTIME_NAME=") or
                               line.startswith("RUNTIME_ARN=") or
                               line.startswith("RUNTIME_ID=")):
                continue
            elif skip_section and line.strip() == "":
                skip_section = False
                continue
            else:
                skip_section = False
                new_lines.append(line)

        # 새 Runtime 정보 추가
        new_lines.append(f"\n# Phase 3: AgentCore Runtime (최신 - {datetime.now().strftime('%Y-%m-%d')})\n")
        new_lines.append(f"RUNTIME_NAME={agent_name}\n")
        new_lines.append(f"RUNTIME_ARN={agent_arn}\n")
        new_lines.append(f"RUNTIME_ID={runtime_id}\n")

        # .env 파일 쓰기
        with open(env_file, 'w') as f:
            f.writelines(new_lines)

        print_success(".env 파일 업데이트 완료")
        print()

        print_success("🎉 VPC Runtime 배포 성공!")
        print()

        # CloudWatch Logs 확인
        print_info("CloudWatch Logs 확인:")
        print(f"  aws logs tail /aws/bedrock-agentcore/runtimes/{agent_name} --follow --region {AWS_REGION}")
        print()

    else:
        print_error(f"Runtime 상태: {current_status}")
        print_warning("CloudWatch Logs에서 상세 정보를 확인하세요")
        print()

        if attempts >= max_attempts:
            print_warning(f"최대 대기 시간 초과 ({max_attempts * 10}초)")

        sys.exit(1)

    # ============================================================
    # 완료
    # ============================================================
    print_header("✅ 배포 완료!")

    print(f"{BLUE}Runtime 정보:{NC}")
    print(f"  Runtime Name: {agent_name}")
    print(f"  Runtime ARN: {agent_arn}")
    print(f"  Runtime ID: {runtime_id}")
    print(f"  Network Mode: VPC")
    print(f"  Subnet: {PRIVATE_SUBNET_ID}")
    print(f"  Security Group: {SG_AGENTCORE_ID}")
    print()

    print(f"{BLUE}다음 단계:{NC}")
    print(f"  1. Runtime 테스트: python3 03_invoke_agentcore_job_vpc.py")
    print(f"  2. CloudWatch Logs 확인:")
    print(f"     - 'Coordinator started' 메시지 확인")
    print(f"     - 'FileNotFoundError: coordinator.md' 없는지 확인")
    print()

if __name__ == "__main__":
    main()
