#!/usr/bin/env python3
"""
Global Fargate Session Manager for Tools
도구들이 공유하는 글로벌 세션 매니저

This module provides a singleton session manager for coordinating Fargate container
sessions across multiple tools and concurrent requests. It handles:
- Multi-request session isolation with separate HTTP clients and cookies
- Container lifecycle management (creation, health checks, cleanup)
- ALB sticky session management with subprocess-based cookie acquisition
- S3 data synchronization for CSV files
- Automatic cleanup on program exit
"""

# ============================================================================
# IMPORTS
# ============================================================================

import logging
import os
import time
import json
import subprocess
import atexit
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (don't override Runtime env vars)
load_dotenv(override=False)

# ECS and ALB configuration from environment
# These must be provided via environment variables (no hardcoded defaults)
ECS_CLUSTER_NAME = os.getenv("ECS_CLUSTER_NAME")
ALB_TARGET_GROUP_ARN = os.getenv("ALB_TARGET_GROUP_ARN")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Third-party imports
import boto3
import requests
from botocore.exceptions import ClientError

# Local imports
from src.tools.fargate_container_controller import SessionBasedFargateManager

# ============================================================================
# LOGGER SETUP
# ============================================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# GLOBAL FARGATE SESSION MANAGER (SINGLETON)
# ============================================================================

class GlobalFargateSessionManager:
    """
    Singleton session manager for coordinating Fargate container sessions.

    Features:
    - Per-request session isolation (cookies, HTTP clients, containers)
    - Exponential backoff retry for session creation
    - ALB health checks and sticky session management
    - S3 data synchronization
    - Automatic cleanup on exit
    """

    # ========================================================================
    # CLASS VARIABLES (SINGLETON STATE)
    # ========================================================================

    _instance = None
    _session_manager = None
    _sessions = {}  # {request_id: session_info} - 요청별 세션 관리
    _http_clients = {}  # {request_id: http_session} - 요청별 HTTP 클라이언트 (쿠키 격리)
    _used_container_ips = {}  # {container_ip: request_id} - IP 기반 컨테이너 소유권 추적
    _current_request_id = None  # 현재 컨텍스트의 요청 ID
    _retry_count = 0
    _max_retries = 2
    _session_creation_failures = {}  # {request_id: failure_count} - 세션 생성 실패 횟수 추적
    _max_session_failures = 5  # 최대 세션 생성 실패 허용 횟수 (ECS Task Limit 대응)
    _cleaned_up_requests = set()  # 이미 cleanup된 요청 ID 추적 (재생성 방지)

    # ========================================================================
    # 📦 INITIALIZATION (SINGLETON PATTERN)
    # ========================================================================

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(GlobalFargateSessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the session manager (only once due to singleton)"""
        if self._session_manager is None:
            logger.info("🚀 Initializing Global Fargate Session Manager")
            self._session_manager = SessionBasedFargateManager()
            atexit.register(self._auto_cleanup)

    # ========================================================================
    # 🌐 PUBLIC API METHODS
    # ========================================================================

    def set_request_context(self, request_id: str):
        """현재 요청 컨텍스트 설정"""
        self._current_request_id = request_id
        logger.info(f"📋 Request context set: {request_id}")

    def ensure_session(self):
        """
        세션이 없거나 비활성화된 경우 새 세션 생성 (요청별 세션 관리, Exponential Backoff 적용)

        Returns:
            bool: True if session exists or was created successfully, False otherwise
        """
        try:
            if not self._current_request_id:
                raise Exception("Request context not set. Call set_request_context() first.")

            # ✅ 이미 cleanup된 요청은 새 세션 생성 금지 (중복 컨테이너 방지)
            if self._current_request_id in self._cleaned_up_requests:
                error_msg = f"❌ FATAL: Request {self._current_request_id} already cleaned up - cannot create new session. This prevents duplicate container creation after workflow completion."
                logger.error(error_msg)
                raise Exception(error_msg)

            # 현재 요청의 세션 확인
            if self._current_request_id in self._sessions:
                return self._reuse_existing_session()

            # 새 세션 생성 (Exponential Backoff 적용)
            return self._create_new_session()

        except Exception as e:
            logger.error(f"❌ Failed to ensure session: {e}")

            # ✅ 치명적 에러는 재발생 (워크플로우 중단)
            if "FATAL" in str(e):
                raise

            return False

    def ensure_session_with_data(self, csv_file_path: str):
        """
        CSV 파일과 함께 세션 생성 (세션 확인 → S3 업로드 → 컨테이너 동기화)

        Args:
            csv_file_path: Path to CSV file to upload

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"🚀 Creating session with data: {csv_file_path}")

            # ✅ 1. 먼저 세션 생성 (Timestamp 생성)
            if not self.ensure_session():
                raise Exception("Failed to create Fargate session")

            # ✅ 2. 생성된 세션 ID를 사용하여 S3 업로드
            session_id = self._sessions[self._current_request_id]['session_id']
            s3_key = self._upload_csv_to_s3_with_session_id(csv_file_path, session_id)
            logger.info(f"📤 CSV uploaded to S3: {s3_key}")

            # 3. 컨테이너에 S3 → 로컬 동기화
            self._sync_csv_from_s3_to_container(s3_key)
            logger.info("✅ CSV file synced to container")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create session with data: {e}")
            return False

    def execute_code(self, code: str, description: str = ""):
        """
        코드 실행 with 자동 세션 관리 및 연결 재시도

        Args:
            code: Python code to execute
            description: Description of the code execution

        Returns:
            dict: Execution result or error
        """
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                # 세션 확인 및 생성
                if not self.ensure_session():
                    return {"error": "Failed to create or maintain session"}

                # 코드 실행
                result = self._session_manager.execute_code(code, description)

                # 성공하면 바로 반환
                return result

            except Exception as e:
                error_msg = str(e)

                # 연결 관련 에러인지 확인
                is_connection_error = any(keyword in error_msg.upper() for keyword in [
                    "CONNECTION FAILED",
                    "NOT RESPONDING",
                    "TIMEOUT",
                    "CONNECTIONERROR",
                    "HTTPERROR"
                ])

                if is_connection_error:
                    # 연결 에러 - 재시도
                    logger.warning(f"⚠️ Connection error (attempt {attempt}/{max_retries}): {error_msg}")

                    if attempt < max_retries:
                        logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"❌ Connection failed after {max_retries} attempts. Giving up.")
                        return {
                            "error": f"Connection failed after {max_retries} attempts: {error_msg}"
                        }
                else:
                    # 코드 실행 에러 등 - 재시도 안 함
                    logger.error(f"❌ Code execution failed: {e}")
                    # ⚠️ 세션을 None으로 리셋하지 않음!
                    # 컨테이너 통신 에러가 발생해도 다음 Agent가 재시도할 수 있도록 세션 유지
                    # 여러 Agent가 같은 컨테이너를 공유해야 하므로 세션 초기화 금지
                    return {"error": str(e)}

    def cleanup_session(self, request_id: str = None):
        """
        특정 요청의 세션 정리

        Args:
            request_id: Request ID to cleanup (defaults to current request)
        """
        try:
            # request_id가 없으면 현재 컨텍스트 사용
            cleanup_request_id = request_id or self._current_request_id

            if not cleanup_request_id:
                logger.warning("⚠️ No request ID for cleanup")
                return

            if cleanup_request_id in self._sessions:
                session_info = self._sessions[cleanup_request_id]
                logger.info(f"🧹 Cleaning up session for request {cleanup_request_id}: {session_info['session_id']}")

                container_ip = session_info.get('container_ip')

                # ✅ FIX: complete_session()을 먼저 호출 (ALB 제거 전에)
                # 1. 먼저 컨테이너가 S3에 업로드하도록 허용
                logger.info(f"🏁 Completing session (S3 upload)...")
                self._session_manager.current_session = session_info['fargate_session']
                self._session_manager.complete_session()

                # 2. 그 다음 컨테이너 IP 해제 및 ALB 제거 (이제 안전함)
                if container_ip and container_ip in self._used_container_ips:
                    del self._used_container_ips[container_ip]
                    logger.info(f"🧹 Released container IP: {container_ip}")
                    logger.info(f"   Remaining IPs: {list(self._used_container_ips.keys())}")

                    # ✅ ALB Target Group에서 컨테이너 제거 (zombie target 방지)
                    # complete_session() 이후에 실행하여 HTTP 502 에러 방지
                    self._deregister_from_alb(container_ip)

                # 세션 딕셔너리에서 제거
                del self._sessions[cleanup_request_id]
                logger.info(f"✅ Session cleanup completed. Remaining sessions: {len(self._sessions)}")
            else:
                logger.warning(f"⚠️ No session found for request {cleanup_request_id}")

            # ✅ HTTP 클라이언트도 정리 (쿠키 제거)
            if cleanup_request_id in self._http_clients:
                del self._http_clients[cleanup_request_id]
                logger.info(f"🍪 Removed HTTP client for request {cleanup_request_id}")

            # ✅ 실패 카운터도 정리
            if cleanup_request_id in self._session_creation_failures:
                del self._session_creation_failures[cleanup_request_id]
                logger.info(f"🧹 Cleared failure counter for request {cleanup_request_id}")

            # ✅ cleanup된 요청 ID를 추적 (재생성 방지)
            self._cleaned_up_requests.add(cleanup_request_id)
            logger.info(f"🔒 Request {cleanup_request_id} marked as cleaned up - new session creation blocked")

        except Exception as e:
            logger.error(f"❌ Session cleanup failed: {e}")

    # ========================================================================
    # 🔧 SESSION MANAGEMENT (PRIVATE HELPERS)
    # ========================================================================

    def _reuse_existing_session(self):
        """기존 세션 재사용 (헬스 체크 포함)"""
        session_info = self._sessions[self._current_request_id]
        container_ip = session_info.get('container_ip', 'unknown')

        logger.info(f"♻️ Reusing existing session for request {self._current_request_id}: {session_info['session_id']}")

        # 🔍 Container Health Check (ALB Target Health)
        if container_ip != 'unknown':
            target_health = self._check_alb_target_health(container_ip)
            logger.info(f"   🏥 Container ALB Health: {target_health}")

            if target_health not in ['healthy', 'initial']:
                logger.warning(f"⚠️ WARNING: Reusing session with container in '{target_health}' state!")
                logger.warning(f"   This may cause connection failures!")
                logger.warning(f"   Container IP: {container_ip}")
                logger.warning(f"   Session ID: {session_info['session_id']}")
                logger.warning(f"   Consider implementing automatic cleanup for stopped containers")

        # SessionBasedFargateManager의 current_session 업데이트
        self._session_manager.current_session = session_info['fargate_session']

        # ✅ HTTP Session도 재주입 (세션 재사용 시에도 필요)
        http_client = self._get_http_client(self._current_request_id)
        self._session_manager.set_http_session(http_client)

        return True

    def _create_new_session(self):
        """새 세션 생성 (Exponential Backoff 적용)"""
        for attempt in range(1, self._max_session_failures + 1):
            try:
                # 🔍 동시 실행 감지 로그
                active_sessions = [req_id for req_id in self._sessions.keys() if req_id not in self._cleaned_up_requests]
                logger.info(f"📦 Creating new Fargate session for request {self._current_request_id} (attempt {attempt}/{self._max_session_failures})...")
                logger.info(f"   Current active sessions: {len(active_sessions)}")
                if active_sessions:
                    logger.info(f"   Active request IDs: {active_sessions}")
                    logger.info(f"   Active container IPs: {[self._sessions[req_id]['container_ip'] for req_id in active_sessions if req_id in self._sessions]}")

                timestamp_id = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

                fargate_session_info = self._session_manager.create_session(
                    session_id=timestamp_id,
                    max_executions=300
                )

                # ✅ HTTP Session 주입 (요청별 쿠키 격리)
                http_client = self._get_http_client(self._current_request_id)
                self._session_manager.set_http_session(http_client)
                logger.info(f"🔗 HTTP session injected for request {self._current_request_id}")

                # ✅ 컨테이너 IP 등록 (AWS VPC가 유니크한 IP 보장)
                expected_private_ip = self._session_manager.current_session['private_ip']
                self._used_container_ips[expected_private_ip] = self._current_request_id
                logger.info(f"📝 Registered container IP: {expected_private_ip}")
                logger.info(f"   Request ID: {self._current_request_id}")
                logger.info(f"   All registered IPs: {list(self._used_container_ips.keys())}")

                # ⚠️ FIX: 세션 저장을 Health Check 완료 후로 이동 (Race Condition 방지)
                # 이 시점에는 self._sessions에 저장하지 않음!
                # → ensure_session() 동시 호출 시 unhealthy 세션 재사용 방지

                # Wait for ALB health check and acquire cookie
                if not self._wait_for_container_ready(expected_private_ip, fargate_session_info['session_id']):
                    # 실패 시 IP 등록 해제
                    if expected_private_ip in self._used_container_ips:
                        del self._used_container_ips[expected_private_ip]
                    return False

                # ✅ FIX: Health Check + Cookie 획득 완료 후 세션 저장 (Race Condition 방지)
                # 이제 안전하게 세션을 self._sessions에 저장
                # → 다른 스레드가 ensure_session() 호출 시 healthy 세션만 재사용
                self._sessions[self._current_request_id] = {
                    'session_id': fargate_session_info['session_id'],
                    'request_id': self._current_request_id,
                    'container_ip': expected_private_ip,
                    'fargate_session': self._session_manager.current_session,
                    'created_at': datetime.now()
                }
                logger.info(f"✅ Session created and saved for request {self._current_request_id}: {fargate_session_info['session_id']}")
                logger.info(f"   Total active sessions: {len(self._sessions)}")

                # ✅ 세션 생성 성공 - 실패 카운터 리셋
                if self._current_request_id in self._session_creation_failures:
                    del self._session_creation_failures[self._current_request_id]

                self._retry_count = 0
                return True

            except ClientError as create_error:
                error_code = create_error.response['Error']['Code']
                error_message = create_error.response['Error']['Message']
                logger.error(f"❌ Session creation failed (attempt {attempt}/{self._max_session_failures}): [{error_code}] {error_message}")

                # 세션 생성 자체가 실패한 경우만 cleanup
                if self._current_request_id in self._sessions:
                    del self._sessions[self._current_request_id]
                self._cleanup_orphaned_containers()

                # ❌ Configuration errors - FAIL FAST (don't retry)
                NON_RETRYABLE_ERRORS = [
                    'ValidationException',  # Invalid parameters (e.g., wrong VPC, subnet, etc.)
                    'InvalidParameterException',  # Invalid parameters
                    'AccessDeniedException',  # IAM permission issues
                    'ResourceNotFoundException',  # Resource not found
                    'UnauthorizedException',  # Auth issues
                ]

                if error_code in NON_RETRYABLE_ERRORS:
                    logger.error(f"❌ FATAL: Non-retryable configuration error detected: {error_code}")
                    logger.error(f"   Error: {error_message}")
                    logger.error(f"   Fix the configuration and try again. Not retrying.")
                    failure_count = self._session_creation_failures.get(self._current_request_id, 0)
                    self._session_creation_failures[self._current_request_id] = failure_count + 1
                    raise

                # ✅ Transient errors - retry with exponential backoff
                # (e.g., ThrottlingException, ServiceUnavailable, etc.)
                if attempt < self._max_session_failures:
                    wait_time = 3 ** attempt  # 3, 9, 27, 81초
                    logger.warning(f"⏳ Transient error - waiting {wait_time}s before retry (exponential backoff: 3^{attempt})...")
                    time.sleep(wait_time)
                else:
                    # 마지막 시도 실패 - 실패 카운터 증가 후 에러 발생
                    failure_count = self._session_creation_failures.get(self._current_request_id, 0)
                    self._session_creation_failures[self._current_request_id] = failure_count + 1
                    logger.error(f"❌ FATAL: Session creation failed {self._max_session_failures} times for request {self._current_request_id}")
                    logger.error(f"   Total backoff time: {3 + 9 + 27 + 81} seconds")
                    raise

            except Exception as create_error:
                # Handle non-AWS exceptions (e.g., network errors, Python exceptions)
                logger.error(f"❌ Session creation failed (attempt {attempt}/{self._max_session_failures}): {create_error}")

                # 세션 생성 자체가 실패한 경우만 cleanup
                if self._current_request_id in self._sessions:
                    del self._sessions[self._current_request_id]
                self._cleanup_orphaned_containers()

                # Retry non-AWS exceptions
                if attempt < self._max_session_failures:
                    wait_time = 3 ** attempt  # 3, 9, 27, 81초
                    logger.warning(f"⏳ Waiting {wait_time}s before retry (exponential backoff: 3^{attempt})...")
                    time.sleep(wait_time)
                else:
                    # 마지막 시도 실패 - 실패 카운터 증가 후 에러 발생
                    failure_count = self._session_creation_failures.get(self._current_request_id, 0)
                    self._session_creation_failures[self._current_request_id] = failure_count + 1
                    logger.error(f"❌ FATAL: Session creation failed {self._max_session_failures} times for request {self._current_request_id}")
                    logger.error(f"   Total backoff time: {3 + 9 + 27 + 81} seconds")
                    raise

    def _wait_for_container_ready(self, expected_ip: str, session_id: str) -> bool:
        """컨테이너 준비 대기 (ALB Health Check + Cookie 획득)"""
        # 🐛 DEBUG: Checkpoint before health check
        logger.info(f"🔍 DEBUG: About to start ALB health check wait for {expected_ip}")

        # 🆕 ALB가 Health Check를 시작할 시간 확보 (60초 대기, keep-alive 로그)
        logger.info(f"⏳ Waiting 60 seconds for ALB to begin health checks...")
        logger.info(f"   This prevents 'ALB never sent health checks' issue")

        # Keep-alive: 60초를 6번의 10초로 나누어 중간에 로그 출력
        for wait_i in range(6):
            time.sleep(10)
            logger.info(f"   ⏱️  Waiting for ALB... ({(wait_i+1)*10}/60s)")

        # ⏰ ALB Health Check 대기 (Container가 healthy 상태가 될 때까지)
        logger.info(f"⏰ Waiting for container {expected_ip} to be healthy in ALB...")
        alb_healthy = False
        for wait_attempt in range(1, 31):  # 최대 150초 (30 * 5s)
            target_health = self._check_alb_target_health(expected_ip)
            logger.info(f"   Attempt {wait_attempt}/30: ALB health = {target_health}")

            if target_health == 'healthy':
                logger.info(f"✅ Container is healthy in ALB after {wait_attempt * 5}s")
                alb_healthy = True
                break
            elif target_health in ['unhealthy', 'draining']:
                logger.warning(f"⚠️ Container is {target_health} - continuing to wait...")
            elif target_health == 'not_registered':
                logger.info(f"   Container not yet registered to ALB - waiting...")

            if wait_attempt < 30:
                time.sleep(5)

        if not alb_healthy:
            logger.warning(f"⚠️ Container not healthy after 150s, but will try cookie acquisition anyway")

        # 🍪 IP 기반 쿠키 획득 (세션 ID 검증 포함)
        cookie_acquired = self._acquire_cookie_for_ip(expected_ip, session_id)

        if not cookie_acquired:
            logger.warning(f"⚠️ Failed to acquire Sticky Session cookie")
            logger.warning(f"   Releasing IP registration: {expected_ip}")
            logger.warning(f"   Cookie acquisition failed - session NOT saved")
            return False

        return True

    def _get_http_client(self, request_id: str):
        """요청별 HTTP 클라이언트 반환 (쿠키 격리)"""
        if request_id not in self._http_clients:
            self._http_clients[request_id] = requests.Session()
            logger.info(f"🍪 Created new HTTP client for request {request_id}")
        return self._http_clients[request_id]

    def _check_alb_target_health(self, target_ip: str) -> str:
        """
        Check if the specified IP is registered and healthy in the ALB target group

        Returns:
            'healthy', 'unhealthy', 'initial', 'draining', 'unused', 'not_registered', 'unknown'
        """
        try:
            if not ALB_TARGET_GROUP_ARN:
                raise ValueError("ALB_TARGET_GROUP_ARN environment variable is required")

            elbv2_client = boto3.client('elbv2', region_name='us-east-1')
            response = elbv2_client.describe_target_health(TargetGroupArn=ALB_TARGET_GROUP_ARN)

            for target_health in response.get('TargetHealthDescriptions', []):
                if target_health['Target']['Id'] == target_ip:
                    state = target_health['TargetHealth']['State']
                    return state

            return 'not_registered'
        except Exception as e:
            logger.warning(f"⚠️ Failed to check ALB target health: {e}")
            return 'unknown'

    # ========================================================================
    # 🍪 COOKIE ACQUISITION (SUBPROCESS-BASED)
    # ========================================================================

    def _acquire_cookie_for_ip(self, expected_ip: str, session_id: str) -> bool:
        """
        subprocess를 사용하여 특정 IP의 컨테이너로부터 Sticky Session 쿠키 획득

        subprocess 사용 이유:
        - 완전한 프로세스 격리 → 독립적인 TCP Connection Pool
        - ALB Round Robin이 정상 작동 (Connection: close/Pool Control 불필요)
        - 멀티 Job 환경에서 각 Job이 독립적으로 쿠키 획득 가능

        작동 원리:
        1. 독립된 Python 프로세스로 인라인 스크립트 실행
        2. subprocess 내부에서 40번 시도 (각각 새로운 TCP 연결)
        3. ALB Round Robin으로 목표 컨테이너 도달 시 쿠키 획득
        4. 세션 ID 검증을 통해 올바른 컨테이너인지 확인 (멀티 Job 지원)
        5. JSON 형태로 결과 반환 (stdout)
        6. Parent process에서 쿠키를 HTTP Client에 설정
        """
        # ✅ CloudWatch 공인 IP 로깅 (AgentCore Runtime → ALB 첫 연결)
        # ALB Security Group이 실제로 검증하는 공인 IP (NAT Gateway IP) 기록
        # NOTE: Disabled to keep all traffic 100% private (no internet access needed)
        # try:
        #     # AWS checkip 서비스를 통해 공인 IP 확인
        #     response = requests.get("https://checkip.amazonaws.com", timeout=3)
        #     public_ip = response.text.strip()
        #     logger.info(f"🌐🌐🌐 PUBLIC IP DETECTED 🌐🌐🌐 First ALB connection from public IP: {public_ip} to ALB: {self._session_manager.alb_dns}")
        # except Exception as ip_err:
        #     logger.warning(f"⚠️ Failed to detect public IP: {ip_err}")
        #     public_ip = "unknown"

        logger.info(f"🍪 Acquiring cookie for container: {expected_ip}")
        logger.info(f"   Session ID: {session_id}")
        other_ips = [ip for ip in self._used_container_ips.keys() if ip != expected_ip]
        if other_ips:
            logger.info(f"   Other active containers: {other_ips}")
        else:
            logger.info(f"   No other active containers")

        try:
            # Get path to cookie acquisition subprocess script
            current_file = Path(__file__)
            script_path = current_file.parent / "cookie_acquisition_subprocess.py"

            if not script_path.exists():
                raise FileNotFoundError(f"Cookie acquisition script not found: {script_path}")

            # subprocess로 별도 파일 실행
            logger.info(f"🔧 Launching subprocess for cookie acquisition...")
            logger.info(f"   Script: {script_path}")

            result = subprocess.run(
                ["python3", str(script_path), self._session_manager.alb_dns, expected_ip, session_id],
                capture_output=True,
                text=True,
                timeout=240  # 4분 (40 attempts * 5s = 200s + buffer)
            )

            # ✅ Subprocess stderr 로깅 (진행 상황 및 디버깅 정보)
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if line.strip():
                        logger.info(f"   {line}")

            # stdout 파싱
            output = result.stdout.strip()
            if not output:
                logger.error(f"❌ Subprocess produced no output")
                if result.stderr:
                    logger.error(f"   Full stderr: {result.stderr}")
                return False

            data = json.loads(output)

            if data.get("success"):
                cookie_value = data.get("cookie")
                attempt = data.get("attempt")
                actual_ip = data.get("ip")

                logger.info(f"✅ Cookie acquired! (attempt {attempt})")
                logger.info(f"   My container IP: {actual_ip}")
                logger.info(f"   Cookie value: {cookie_value[:20]}...")

                # HTTP Client에 쿠키 설정
                http_client = requests.Session()
                http_client.cookies.set('AWSALB', cookie_value)

                # 저장
                self._http_clients[self._current_request_id] = http_client
                return True
            else:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"❌ Cookie acquisition failed: {error_msg}")
                logger.error(f"   Expected IP: {expected_ip}")
                logger.error(f"   Registered IPs: {list(self._used_container_ips.keys())}")
                return False

        except subprocess.TimeoutExpired as e:
            logger.error(f"❌ Cookie acquisition timeout (4 minutes)")
            logger.error(f"   Expected IP: {expected_ip}")
            if e.stderr:
                # ✅ Timeout stderr도 로깅 (bytes → string 안전 변환)
                stderr_text = str(e.stderr, 'utf-8') if isinstance(e.stderr, bytes) else e.stderr
                for line in stderr_text.strip().split('\n'):
                    if line.strip():
                        logger.error(f"   {line}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse subprocess output: {e}")
            logger.error(f"   Output: {result.stdout}")
            if result.stderr:
                logger.error(f"   Full stderr: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Cookie acquisition subprocess failed: {e}")
            logger.error(f"   Expected IP: {expected_ip}")
            return False

    # ========================================================================
    # 📤 DATA SYNC METHODS (S3 UPLOAD/DOWNLOAD)
    # ========================================================================

    def _upload_csv_to_s3_with_session_id(self, csv_file_path: str, session_id: str) -> str:
        """세션 ID를 받아서 S3에 업로드 (Timestamp 불일치 방지)"""
        try:
            # ✅ 세션 ID를 그대로 사용 (새 timestamp 생성 안함)
            original_filename = os.path.basename(csv_file_path)
            s3_key = f"manus/fargate_sessions/{session_id}/input/{original_filename}"

            # S3 업로드
            s3_client = boto3.client('s3', region_name='us-east-1')
            s3_client.upload_file(
                csv_file_path,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )

            logger.info(f"📤 Uploaded {csv_file_path} → s3://{S3_BUCKET_NAME}/{s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"❌ S3 upload failed: {e}")
            raise

    def _sync_csv_from_s3_to_container(self, s3_key: str):
        """S3에서 컨테이너로 CSV 파일 동기화 (Enhanced Logging)"""
        try:
            # ALB DNS (세션 매니저에서 가져오기)
            alb_dns = self._session_manager.alb_dns
            filename = s3_key.split('/')[-1]

            # ✅ 1. 시작 로그
            logger.info(f"🔄 Starting file sync...")
            logger.info(f"   S3 Key: {s3_key}")
            logger.info(f"   Filename: {filename}")
            logger.info(f"   Target: /app/data/{filename}")

            # 파일 동기화 요청
            # s3_key 형태: "manus/fargate_sessions/{session_id}/input/file.csv"
            sync_request = {
                "action": "sync_data_from_s3",
                "bucket_name": S3_BUCKET_NAME,
                "s3_key_prefix": f"manus/fargate_sessions/{s3_key.split('/')[2]}/input/",
                "local_path": "/app/data/"
            }

            # ✅ 2. 요청 로그
            logger.info(f"📤 Sending file sync request:")
            logger.info(f"   URL: {alb_dns}/file-sync")
            logger.info(f"   Request: {sync_request}")

            # ✅ 요청별 HTTP 클라이언트 사용 (쿠키 격리)
            http_client = self._get_http_client(self._current_request_id)
            response = http_client.post(
                f"http://{alb_dns}/file-sync",
                json=sync_request,
                timeout=30
            )

            # ✅ 3. 응답 로그
            logger.info(f"📥 File sync response:")
            logger.info(f"   Status: {response.status_code}")
            logger.info(f"   Body: {response.text[:500]}")  # 처음 500자만

            if response.status_code != 200:
                logger.error(f"❌ File sync failed with status {response.status_code}")
                raise Exception(f"File sync failed: {response.text}")

            result = response.json()
            files_count = result.get('files_count', 0)
            downloaded_files = result.get('downloaded_files', [])

            # ✅ 4. 결과 로그
            logger.info(f"✅ File sync completed:")
            logger.info(f"   Files synced: {files_count}")
            logger.info(f"   Downloaded: {downloaded_files}")

            # ✅ 5. 대기 시작 로그
            logger.info("⏳ Waiting 10 seconds for file sync to complete...")
            time.sleep(10)  # 10초 대기 (파일 동기화 완료 시간)

            # ✅ 6. 대기 완료 로그
            logger.info("✅ File sync wait complete")

        except Exception as e:
            logger.error(f"❌ File sync failed: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            logger.error(f"   Exception details: {str(e)[:1000]}")
            raise

    # ========================================================================
    # 🧹 CLEANUP METHODS
    # ========================================================================

    def _cleanup_orphaned_containers(self):
        """세션 생성 실패 시 현재 요청의 컨테이너만 정리 (다른 요청의 컨테이너는 보호)"""
        try:
            ecs_client = boto3.client('ecs', region_name='us-east-1')

            # 현재 요청의 Task ARN 확인
            current_task_arn = None
            if self._current_request_id and self._current_request_id in self._sessions:
                session_info = self._sessions[self._current_request_id]
                fargate_session = session_info.get('fargate_session', {})
                current_task_arn = fargate_session.get('task_arn')

            if not current_task_arn:
                logger.warning(f"⚠️ No task ARN found for current request {self._current_request_id} - skipping cleanup")
                return

            # ✅ 현재 요청의 컨테이너만 종료 (다른 요청의 컨테이너는 건드리지 않음)
            try:
                logger.info(f"🧹 Cleaning up orphaned container for request {self._current_request_id}: {current_task_arn.split('/')[-1][:12]}...")
                ecs_client.stop_task(
                    cluster=ECS_CLUSTER_NAME,
                    task=current_task_arn,
                    reason=f'Session creation failed - cleanup (request: {self._current_request_id})'
                )
                logger.info(f"   ✅ Stopped container: {current_task_arn.split('/')[-1][:12]}")
            except Exception as stop_error:
                logger.warning(f"   ⚠️ Failed to stop container {current_task_arn.split('/')[-1][:12]}: {stop_error}")

        except Exception as e:
            logger.warning(f"⚠️ Orphaned container cleanup failed: {e}")

    def _deregister_from_alb(self, container_ip: str):
        """ALB Target Group에서 컨테이너 제거"""
        try:
            elbv2_client = boto3.client('elbv2', region_name=self._session_manager.region)
            elbv2_client.deregister_targets(
                TargetGroupArn=self._session_manager.alb_target_group_arn,
                Targets=[{
                    'Id': container_ip,
                    'Port': 8080
                }]
            )
            logger.info(f"🔗 Deregistered target from ALB: {container_ip}:8080")
        except Exception as alb_error:
            # ALB 제거 실패해도 세션 정리는 계속 진행
            logger.warning(f"⚠️ Failed to deregister ALB target {container_ip}: {alb_error}")

    def _auto_cleanup(self):
        """프로그램 종료 시 자동으로 모든 세션 정리"""
        try:
            if self._sessions:
                logger.info(f"🧹 Auto-cleanup: Closing {len(self._sessions)} Fargate sessions on exit...")
                # 모든 세션 정리
                for request_id in list(self._sessions.keys()):
                    self.cleanup_session(request_id)

            # ✅ 모든 HTTP 클라이언트 정리
            if self._http_clients:
                logger.info(f"🧹 Auto-cleanup: Clearing {len(self._http_clients)} HTTP clients...")
                self._http_clients.clear()

            # ✅ 모든 실패 카운터 정리
            if self._session_creation_failures:
                logger.info(f"🧹 Auto-cleanup: Clearing {len(self._session_creation_failures)} failure counters...")
                self._session_creation_failures.clear()

            # ✅ 모든 cleanup 추적 정리
            if self._cleaned_up_requests:
                logger.info(f"🧹 Auto-cleanup: Clearing {len(self._cleaned_up_requests)} cleaned-up request trackers...")
                self._cleaned_up_requests.clear()
        except Exception as e:
            logger.warning(f"⚠️ Auto-cleanup failed: {e}")

    # ========================================================================
    # ⚠️ UNUSED FUNCTIONS (COMMENTED OUT FOR REFERENCE)
    # ========================================================================

    # ⚠️ UNUSED FUNCTION - Commented out (2025-10-12)
    # Not used anywhere in the codebase (only found commented reference in fargate_python_tool.py:120)
    # Kept for potential future reference
    # def get_session_info(self):
    #     """현재 요청의 세션 정보 반환"""
    #     if not self._current_request_id:
    #         return {"status": "no_context"}
    #
    #     if self._current_request_id in self._sessions:
    #         session_info = self._sessions[self._current_request_id]
    #         return {
    #             "request_id": self._current_request_id,
    #             "session_id": session_info['session_id'],
    #             "status": "active",
    #             "private_ip": session_info['fargate_session']['private_ip']
    #         }
    #     else:
    #         return {"status": "no_session", "request_id": self._current_request_id}

    # ⚠️ UNUSED FUNCTION - Commented out (2025-10-12)
    # LEGACY function that creates new timestamp (causes timestamp mismatch)
    # Replaced by _upload_csv_to_s3_with_session_id which uses existing session_id
    # Not used anywhere in the codebase
    # Kept for potential future reference
    # def _upload_csv_to_s3(self, csv_file_path: str) -> str:
    #     """CSV 파일을 S3에 업로드 (레거시 - 새 timestamp 생성)"""
    #     try:
    #         # 현재 세션 ID 기반 S3 키 생성
    #         timestamp_id = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    #
    #         # 원본 파일명 추출
    #         original_filename = os.path.basename(csv_file_path)
    #         s3_key = f"manus/fargate_sessions/{timestamp_id}/input/{original_filename}"
    #
    #         # S3 업로드
    #         s3_client = boto3.client('s3', region_name='us-east-1')
    #         s3_client.upload_file(
    #             csv_file_path,
    #             'bedrock-logs-gonsoomoon',
    #             s3_key,
    #             ExtraArgs={'ContentType': 'text/csv'}
    #         )
    #
    #         logger.info(f"📤 Uploaded {csv_file_path} → s3://bedrock-logs-gonsoomoon/{s3_key}")
    #         return s3_key
    #
    #     except Exception as e:
    #         logger.error(f"❌ S3 upload failed: {e}")
    #         raise


# ============================================================================
# GLOBAL INSTANCE (SINGLETON)
# ============================================================================

# 글로벌 인스턴스 (싱글톤)
global_fargate_session = GlobalFargateSessionManager()


def get_global_session():
    """글로벌 세션 매니저 인스턴스 반환"""
    return global_fargate_session
