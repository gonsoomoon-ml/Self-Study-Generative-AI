#!/usr/bin/env python3
"""
Session-Based Fargate Manager
세션별 컨테이너 생명주기 자동 관리
- Session 시작 → 새 컨테이너 생성 → ALB 등록
- Session 완료 → S3 업로드 → 컨테이너 삭제
"""

import boto3
import json
import time
import uuid
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class SessionBasedFargateManager:
    def __init__(self,
                 cluster_name: str = "my-fargate-cluster",
                 task_definition: str = "fargate-dynamic-task",
                 alb_target_group_arn: str = "arn:aws:elasticloadbalancing:us-east-1:057716757052:targetgroup/fargate-flask-tg-default/0bcd6380352d5e78",
                 alb_dns: str = "http://fargate-flask-alb-862273998.us-east-1.elb.amazonaws.com",
                 subnets: list = None,
                 security_groups: list = None,
                 region: str = "us-east-1"):
        """
        세션 기반 Fargate 관리자 초기화
        """
        self.cluster_name = cluster_name
        self.task_definition = task_definition
        self.alb_target_group_arn = alb_target_group_arn
        self.alb_dns = alb_dns
        self.region = region
        self.subnets = subnets or ["subnet-46162921", "subnet-6b1d5f55"]
        self.security_groups = security_groups or ["sg-05d4ccf6d9cfde284"]

        # AWS 클라이언트
        self.ecs_client = boto3.client('ecs', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)

        # HTTP 세션은 global_fargate_coordinator에서 주입됨 (요청별 격리)
        self.http_session = None

        # 현재 세션 정보
        self.current_session = None

    def set_http_session(self, http_session):
        """HTTP Session 설정 (global_fargate_coordinator에서 주입)"""
        self.http_session = http_session
        print(f"🔗 HTTP session injected for request-specific cookie isolation", flush=True)

    def create_session(self, session_id: Optional[str] = None, max_executions: int = 300) -> Dict[str, Any]:
        """
        세션 생성 또는 기존 컨테이너 재사용
        - 최초 요청: 새 컨테이너 생성
        - 후속 요청: 기존 컨테이너 상태 확인 후 재사용

        Args:
            session_id: 세션 ID (None이면 자동 생성)
            max_executions: 최대 실행 횟수

        Returns:
            세션 정보
        """
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]

        print(f"🚀 [Session {session_id}] Creating or reusing session...", flush=True)

        try:
            # 1. 기존 세션이 있는지 확인
            if self.current_session:
                print(f"🔍 [Session {session_id}] Checking existing container health...", flush=True)

                # 기존 컨테이너 상태 확인
                if self._check_existing_container_health():
                    print(f"✅ [Session {session_id}] Reusing existing container: {self.current_session['session_id']}", flush=True)
                    print(f"   Task ARN: {self.current_session['task_arn']}", flush=True)
                    print(f"   Private IP: {self.current_session['private_ip']}", flush=True)
                    print(f"   ALB DNS: {self.alb_dns}", flush=True)

                    # 기존 세션 정보 업데이트
                    self.current_session['session_id'] = session_id
                    self.current_session['max_executions'] = max_executions
                    self.current_session['status'] = 'active'

                    return {
                        "session_id": session_id,
                        "alb_url": self.alb_dns,
                        "private_ip": self.current_session['private_ip'],
                        "max_executions": max_executions,
                        "status": "ready",
                        "container_reused": True
                    }
                else:
                    print(f"❌ [Session {session_id}] Existing container unhealthy - TERMINATING WITH ERROR", flush=True)
                    raise Exception("Existing container is unhealthy and cannot be reused. Session terminated.")

            # 2. 최초 세션 생성: 새 Fargate Task 시작
            print(f"🆕 [Session {session_id}] Creating new container (first time)...", flush=True)
            task_arn = self._start_fargate_task(session_id)

            # 3. Task IP 확인
            private_ip = self._wait_for_task_ip(task_arn)

            # 4. ALB Target Group에 등록
            self._register_to_alb(private_ip)

            # 5. 세션 정보 저장 (헬스체크는 global_fargate_coordinator에서 처리)
            self.current_session = {
                "session_id": session_id,
                "task_arn": task_arn,
                "private_ip": private_ip,
                "max_executions": max_executions,
                "start_time": datetime.now(),
                "status": "active"
            }

            print(f"✅ [Session {session_id}] New container created successfully!", flush=True)
            print(f"   Task ARN: {task_arn}", flush=True)
            print(f"   Private IP: {private_ip}", flush=True)
            print(f"   ALB DNS: {self.alb_dns}", flush=True)

            return {
                "session_id": session_id,
                "alb_url": self.alb_dns,
                "private_ip": private_ip,
                "max_executions": max_executions,
                "status": "ready",
                "container_reused": False
            }

        except Exception as e:
            print(f"❌ [Session {session_id}] Failed to create/reuse session: {e}", flush=True)
            raise

    def _start_fargate_task(self, session_id: str) -> str:
        """Fargate Task 시작"""
        print(f"🏗️ [Session {session_id}] Starting Fargate task...", flush=True)

        response = self.ecs_client.run_task(
            cluster=self.cluster_name,
            taskDefinition=self.task_definition,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': self.subnets,
                    'securityGroups': self.security_groups,
                    'assignPublicIp': 'ENABLED'
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'dynamic-executor',
                        'environment': [
                            {
                                'name': 'SESSION_ID',
                                'value': session_id
                            }
                        ]
                    }
                ]
            }
        )

        if response['failures']:
            raise Exception(f"Task execution failed: {response['failures']}")

        task_arn = response['tasks'][0]['taskArn']
        print(f"📋 [Session {session_id}] Task started: {task_arn}", flush=True)
        return task_arn

    def _wait_for_task_ip(self, task_arn: str, timeout: int = 60) -> str:
        """Task의 Private IP 주소 대기"""
        print(f"⏳ Waiting for task IP...", flush=True)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.ecs_client.describe_tasks(
                    cluster=self.cluster_name,
                    tasks=[task_arn]
                )

                if not response['tasks']:
                    raise Exception("Task not found")

                task = response['tasks'][0]

                # ENI 정보에서 Private IP 추출
                for attachment in task.get('attachments', []):
                    if attachment.get('type') == 'ElasticNetworkInterface':
                        eni_id = None
                        for detail in attachment.get('details', []):
                            if detail.get('name') == 'networkInterfaceId':
                                eni_id = detail.get('value')
                                break

                        if eni_id:
                            eni_response = self.ec2_client.describe_network_interfaces(
                                NetworkInterfaceIds=[eni_id]
                            )
                            if eni_response['NetworkInterfaces']:
                                private_ip = eni_response['NetworkInterfaces'][0].get('PrivateIpAddress')
                                if private_ip:
                                    print(f"🌐 Task Private IP: {private_ip}", flush=True)
                                    return private_ip

                time.sleep(3)

            except Exception as e:
                print(f"⏳ Still waiting for IP... ({e})", flush=True)
                time.sleep(3)

        raise TimeoutError("Failed to get task IP within timeout")

    def _register_to_alb(self, private_ip: str):
        """ALB Target Group에 IP 등록"""
        print(f"🔗 Registering {private_ip} to ALB Target Group...", flush=True)

        # 기존 타겟들 확인
        current_targets = self._get_current_targets()
        print(f"📋 Current targets in ALB: {[t['Id'] for t in current_targets]}", flush=True)

        # 새 타겟 등록
        self.elbv2_client.register_targets(
            TargetGroupArn=self.alb_target_group_arn,
            Targets=[{
                'Id': private_ip,
                'Port': 8080
            }]
        )

        # ✅ 여러 job 동시 실행을 위해 기존 타겟 제거 로직 삭제
        # 각 세션이 종료될 때 _cleanup_session()에서 개별적으로 제거됨
        print(f"✅ Registered {private_ip} to ALB (keeping {len(current_targets)} existing targets)", flush=True)

    def _get_current_targets(self) -> list:
        """현재 ALB Target Group의 타겟들 조회"""
        response = self.elbv2_client.describe_target_health(
            TargetGroupArn=self.alb_target_group_arn
        )

        return [
            {
                'Id': target['Target']['Id'],
                'Port': target['Target']['Port']
            }
            for target in response['TargetHealthDescriptions']
            if target['TargetHealth']['State'] in ['healthy', 'unhealthy', 'initial']
        ]

    def _check_existing_container_health(self) -> bool:
        """기존 컨테이너의 Health 상태 확인"""
        try:
            if not self.http_session:
                print(f"⚠️ HTTP session not initialized")
                return False

            response = self.http_session.get(f"{self.alb_dns}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get('status', '')
                if status == 'healthy':
                    print(f"✅ 기존 컨테이너 정상 - 재사용 가능")
                    return True
                else:
                    print(f"❌ 기존 컨테이너 비정상 상태: {status}")
                    return False
            else:
                print(f"❌ 컨테이너 Health Check 실패 - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 컨테이너 연결 실패: {e}")
            return False

    # _wait_for_health_check() 제거됨
    # 멀티 Job 환경에서는 global_fargate_coordinator._acquire_cookie_for_ip()가
    # IP 기반 검증과 쿠키 획득을 처리합니다.

    def execute_code(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        고정된 컨테이너에서 코드 실행
        - 컨테이너가 반응하지 않으면 전체 작업 에러 종료
        - 새 컨테이너 생성 금지

        Args:
            code: 실행할 코드
            description: 실행 설명

        Returns:
            실행 결과
        """
        if not self.current_session:
            raise Exception("No active session. Call create_session() first.")

        if not self.http_session:
            raise Exception("No HTTP session. Call set_http_session() first.")

        print(f"🔄 [Session {self.current_session['session_id']}] Executing on FIXED container: {description}", flush=True)
        

        try:
            # 🍪 http_session 사용 (Sticky Session 쿠키 포함 - request별 격리)
            response = self.http_session.post(
                f"{self.alb_dns}/execute",
                json={"code": code},
                timeout=180  # Increased for large PDF generation and complex data processing
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Execution completed on fixed container: {result['execution_num']}/{result['total_executions']}", flush=True)
                return result
            else:
                error_msg = f"FIXED CONTAINER NOT RESPONDING: HTTP {response.status_code} - TERMINATING ENTIRE WORKFLOW"
                print(f"❌ {error_msg}", flush=True)
                raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"FIXED CONTAINER CONNECTION FAILED: {str(e)} - TERMINATING ENTIRE WORKFLOW"
            print(f"❌ {error_msg}", flush=True)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"FIXED CONTAINER EXECUTION FAILED: {str(e)} - TERMINATING ENTIRE WORKFLOW"
            print(f"❌ {error_msg}", flush=True)
            raise Exception(error_msg)

    def complete_session(self, wait_for_s3: bool = True) -> Dict[str, Any]:
        """
        현재 세션 완료 및 정리

        Args:
            wait_for_s3: S3 업로드 완료 대기 여부

        Returns:
            완료 정보
        """
        if not self.current_session:
            return {"error": "No active session"}

        session_id = self.current_session['session_id']
        print(f"🏁 [Session {session_id}] Completing session...", flush=True)

        try:
            if not self.http_session:
                print(f"⚠️ HTTP session not available for completion", flush=True)
                return {"error": "No HTTP session"}

            # 1. 세션 완료 신호 전송 (🍪 http_session 사용 - request별 격리)
            response = self.http_session.post(f"{self.alb_dns}/session/complete", timeout=10)
            result = response.json() if response.status_code == 200 else {}

            # 2. S3 업로드 대기
            if wait_for_s3:
                print(f"⏳ Waiting for S3 upload...", flush=True)
                time.sleep(10)

            # 3. 세션 정리
            self._cleanup_session(self.current_session)

            # 4. 현재 세션 정보 초기화
            self.current_session = None

            print(f"✅ [Session {session_id}] Session completed successfully!", flush=True)

            return {
                "session_id": session_id,
                "status": "completed",
                "total_executions": result.get('total_executions', 0)
            }

        except Exception as e:
            print(f"❌ [Session {session_id}] Error completing session: {e}", flush=True)
            return {"error": str(e)}

    def _cleanup_session(self, session_info: Dict[str, Any]):
        """세션 정리 (ALB 제거 + Task 종료)"""
        session_id = session_info['session_id']
        private_ip = session_info['private_ip']
        task_arn = session_info['task_arn']

        try:
            # 1. ALB에서 제거
            print(f"🔗 [Session {session_id}] Removing from ALB...", flush=True)
            self.elbv2_client.deregister_targets(
                TargetGroupArn=self.alb_target_group_arn,
                Targets=[{
                    'Id': private_ip,
                    'Port': 8080
                }]
            )

            # 2. Task 종료 (컨테이너 삭제)
            print(f"🛑 [Session {session_id}] Stopping task and deleting container...", flush=True)
            self.ecs_client.stop_task(
                cluster=self.cluster_name,
                task=task_arn,
                reason=f'Session {session_id} completed - Container deletion'
            )

            print(f"🧹 [Session {session_id}] Cleanup completed - Container deleted", flush=True)

        except Exception as e:
            print(f"⚠️ [Session {session_id}] Cleanup error: {e}", flush=True)

    def get_session_status(self) -> Dict[str, Any]:
        """현재 세션 상태 조회"""
        if not self.current_session:
            return {"status": "no_session"}

        if not self.http_session:
            return {"error": "No HTTP session"}

        try:
            response = self.http_session.get(f"{self.alb_dns}/session/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                status['session_info'] = self.current_session
                return status
            else:
                return {"error": f"Status check failed: HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

def test_session_manager():
    """세션 매니저 테스트"""
    print("=" * 70)
    print("🧪 Testing Session-Based Fargate Manager")
    print("=" * 70)

    manager = SessionBasedFargateManager()

    try:
        # 1. 첫 번째 세션 생성
        print("\n1️⃣ Creating first session...")
        session1 = manager.create_session(session_id="test-001", max_executions=5)

        # 2. 코드 실행
        print("\n2️⃣ Executing codes...")
        codes = [
            "print('Session 1 - Code 1: Hello Fargate!')",
            "print('Session 1 - Code 2: Data processing')\nimport pandas as pd\ndf = pd.DataFrame({'x': [1,2,3]})\nprint(f'DF shape: {df.shape}')"
        ]

        for i, code in enumerate(codes, 1):
            manager.execute_code(code, f"Test code {i}")
            time.sleep(1)

        # 3. 첫 번째 세션 완료
        print("\n3️⃣ Completing first session...")
        manager.complete_session()

        # 4. 두 번째 세션 생성 (새 컨테이너)
        print("\n4️⃣ Creating second session (new container)...")
        session2 = manager.create_session(session_id="test-002", max_executions=3)

        # 5. 새 세션에서 코드 실행
        print("\n5️⃣ Executing codes in new session...")
        manager.execute_code("print('Session 2 - Fresh container!')", "New session test")

        # 6. 두 번째 세션 완료
        print("\n6️⃣ Completing second session...")
        manager.complete_session()

        print("\n" + "=" * 70)
        print("✅ Session-based lifecycle management test completed!")
        print("   ✓ Session 1: Created → Executed → Destroyed")
        print("   ✓ Session 2: Created → Executed → Destroyed")
        print("   ✓ Automatic container lifecycle management")
        print("   ✓ ALB target management")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        # 정리 시도
        if manager.current_session:
            manager._cleanup_session(manager.current_session)

if __name__ == "__main__":
    test_session_manager()