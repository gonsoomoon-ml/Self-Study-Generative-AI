#!/usr/bin/env python3
"""
Dynamic Code Executor for Fargate V2 - HTTP Server Version
300번의 코드 실행 요청을 처리하고 세션 완료 시 S3에 업로드
"""

import sys
import os
import json
import uuid
import traceback
import threading
import time
import subprocess
import re
from datetime import datetime
from io import StringIO
import contextlib
import boto3
from flask import Flask, request, jsonify
from pathlib import Path
import shutil

app = Flask(__name__)

# 글로벌 상태 관리
class SessionManager:
    def __init__(self):
        self.session_id = os.environ.get('SESSION_ID', str(uuid.uuid4())[:8])
        self.executions = []
        self.max_executions = 300
        self.start_time = datetime.now()
        self.is_complete = False
        self.workspace = f"/tmp/session_{self.session_id}"
        os.makedirs(self.workspace, exist_ok=True)

        # File I/O를 위한 data와 artifacts 디렉토리 생성
        self.data_dir = "/app/data"
        self.artifacts_dir = "/app/artifacts"
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.artifacts_dir, exist_ok=True)

    def add_execution(self, result):
        self.executions.append(result)
        execution_num = len(self.executions)

        # 로컬에 각 실행 결과 저장
        output_file = f"{self.workspace}/execution_{execution_num}.json"

        # execution_time_ms를 duration_ms로 변환하여 저장
        save_result = result.copy()
        if 'execution_time_ms' in save_result:
            save_result['duration_ms'] = save_result.pop('execution_time_ms')

        with open(output_file, 'w') as f:
            json.dump(save_result, f, indent=2)

        print(f"💾 Saved execution {execution_num} to {output_file}", flush=True)

        # 300번 실행 완료 체크 또는 강제 업로드 조건
        if execution_num >= self.max_executions:
            self.complete_session()

        # 1회 실행마다 중간 저장 (디버깅용) - ✅ DISABLED: S3 upload only at session completion
        # 이유: Mid-session S3 upload가 Flask를 blocking하여 다음 요청 처리 지연 발생 (HTTP 502)
        # PDF 생성 완료 후 session complete 시 한번에 모든 파일 업로드
        # else:
        #     print(f"🔄 Mid-session S3 backup at execution {execution_num}", flush=True)
        #     try:
        #         session_result = {
        #             "session_id": self.session_id,
        #             "status": "in_progress",
        #             "start_time": str(self.start_time),
        #             "current_time": str(datetime.now()),
        #             "executions": self.executions,
        #             "backup_execution": execution_num
        #         }
        #         self.upload_to_s3(session_result)
        #     except Exception as e:
        #         print(f"⚠️ Mid-session backup failed: {e}", flush=True)

    def complete_session(self):
        """세션 완료 처리 - 모든 결과를 S3에 업로드"""
        if self.is_complete:
            return

        self.is_complete = True
        print(f"🏁 Session {self.session_id} complete. Uploading to S3...", flush=True)

        try:
            # 전체 세션 결과 생성
            session_result = {
                "session_id": self.session_id,
                "total_executions": len(self.executions),
                "start_time": str(self.start_time),
                "end_time": str(datetime.now()),
                "executions": self.executions
            }

            # S3에 업로드
            self.upload_to_s3(session_result)

            print(f"✅ Session {self.session_id} uploaded to S3", flush=True)
        except Exception as e:
            print(f"❌ Failed to upload session to S3: {e}", flush=True)

    def upload_to_s3(self, session_result):
        """S3에 세션 결과 및 생성된 파일들 업로드"""
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket = "bedrock-logs-gonsoomoon"

        print(f"☁️ Starting S3 upload to s3://{bucket}/manus/fargate_sessions/{self.session_id}/", flush=True)

        # 전체 세션 결과를 debug 폴더에 저장
        s3_key = f"manus/fargate_sessions/{self.session_id}/debug/session_status.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(session_result, indent=2),
            ContentType='application/json'
        )
        print(f"  📄 Uploaded debug/session_status.json", flush=True)

        # 개별 실행 결과들을 debug 폴더에 저장
        for i, execution in enumerate(self.executions, 1):
            s3_key = f"manus/fargate_sessions/{self.session_id}/debug/execution_{i}.json"
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=json.dumps(execution, indent=2),
                ContentType='application/json'
            )
        print(f"  📄 Uploaded {len(self.executions)} execution result files to debug/", flush=True)

        # artifacts 폴더 업로드 (생성된 파일들) - 즉시 업로드 활성화
        artifacts_path = "/app/artifacts"
        if os.path.exists(artifacts_path):
            artifacts_uploaded = self._upload_directory_to_s3(
                s3_client, bucket, artifacts_path,
                f"manus/fargate_sessions/{self.session_id}/artifacts"
            )
            print(f"  📁 Uploaded {artifacts_uploaded} files from artifacts/", flush=True)

        # data 폴더 업로드 (생성된 데이터 파일들)
        data_path = "/app/data"
        if os.path.exists(data_path):
            data_uploaded = self._upload_directory_to_s3(
                s3_client, bucket, data_path,
                f"manus/fargate_sessions/{self.session_id}/data"
            )
            print(f"  📁 Uploaded {data_uploaded} files from data/", flush=True)

        print(f"✅ S3 upload completed for session {self.session_id}", flush=True)

    def _upload_directory_to_s3(self, s3_client, bucket, local_dir, s3_prefix):
        """디렉토리 내 모든 파일을 S3에 업로드"""
        uploaded_count = 0

        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_dir)
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')

                try:
                    # 파일 타입에 따른 ContentType 설정
                    content_type = 'application/octet-stream'
                    if file.endswith('.json'):
                        content_type = 'application/json'
                    elif file.endswith('.txt'):
                        content_type = 'text/plain'
                    elif file.endswith('.csv'):
                        content_type = 'text/csv'
                    elif file.endswith('.png'):
                        content_type = 'image/png'
                    elif file.endswith('.jpg') or file.endswith('.jpeg'):
                        content_type = 'image/jpeg'
                    elif file.endswith('.pdf'):
                        content_type = 'application/pdf'
                    elif file.endswith('.py'):
                        content_type = 'text/x-python'

                    s3_client.upload_file(
                        local_file_path, bucket, s3_key,
                        ExtraArgs={'ContentType': content_type}
                    )
                    uploaded_count += 1
                    print(f"    📤 {relative_path} → s3://{bucket}/{s3_key}", flush=True)
                except Exception as e:
                    print(f"    ❌ Upload failed for {relative_path}: {e}", flush=True)

        return uploaded_count

# 세션 매니저 초기화
session_manager = SessionManager()

def create_compact_error_response(exception, traceback_text=None):
    """
    에러 응답을 스트리밍에 적합하도록 간소화

    Args:
        exception: 발생한 예외 객체
        traceback_text: traceback.format_exc() 결과

    Returns:
        dict: 간소화된 에러 정보
    """
    error_type = type(exception).__name__
    error_message = str(exception)

    # 메시지 길이 제한 (8192자)
    if len(error_message) > 4096*2:
        error_message = error_message[:4096*2] + "..."

    # 라인 번호 추출
    line_number = None
    if traceback_text:
        # "line 205"와 같은 패턴에서 라인 번호 추출
        line_match = re.search(r'line (\d+)', traceback_text)
        if line_match:
            line_number = int(line_match.group(1))

    # 에러 타입별 핵심 정보 추출
    key_info = extract_error_key_info(error_type, error_message, traceback_text)

    compact_error = {
        "type": error_type,
        "message": error_message,
        "line": line_number,
        "key_info": key_info
    }

    # traceback 전체 포함 (8192자 제한)
    if traceback_text:
        if len(traceback_text) > 4096*2:
            compact_error["traceback"] = traceback_text[:4096*2] + "..."
        else:
            compact_error["traceback"] = traceback_text

    return compact_error

def extract_error_key_info(error_type, error_message, traceback_text):
    """에러 타입별 핵심 정보 추출"""
    key_info = {}

    if error_type == "SyntaxError":
        # 문법 오류의 경우 구체적인 문제점 추출
        if "invalid decimal literal" in error_message:
            key_info["issue"] = "Invalid number format (possibly CSS in Python code)"
        elif "format code" in error_message:
            key_info["issue"] = "f-string formatting error"
        elif "unexpected EOF" in error_message:
            key_info["issue"] = "Missing closing bracket or quote"

    elif error_type == "ValueError":
        if "Unknown format code" in error_message:
            key_info["issue"] = "f-string format specifier error"
        elif "Cannot specify" in error_message:
            key_info["issue"] = "Invalid format combination"

    elif error_type == "NameError":
        # 변수명 추출
        if "is not defined" in error_message:
            var_match = re.search(r"'(\w+)' is not defined", error_message)
            if var_match:
                key_info["undefined_variable"] = var_match.group(1)

    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        # 모듈명 추출
        module_match = re.search(r"No module named '(\w+)'", error_message)
        if module_match:
            key_info["missing_module"] = module_match.group(1)

    return key_info

def create_compact_output(output_text, output_type="stdout", max_length=500):
    """
    stdout/stderr 출력을 스트리밍에 적합하도록 간소화

    Args:
        output_text: 원본 출력 텍스트
        output_type: 출력 타입 ("stdout" 또는 "stderr")
        max_length: 최대 길이 (기본값: 500자)

    Returns:
        str 또는 dict: 간소화된 출력 정보
    """
    if not output_text or not output_text.strip():
        return output_text

    # 원본 길이
    original_length = len(output_text)

    # 길이가 제한 내에 있으면 그대로 반환
    if original_length <= max_length:
        return output_text

    # 길이가 초과하면 요약 정보 생성
    lines = output_text.strip().split('\n')
    total_lines = len(lines)

    # 처음 3줄과 마지막 3줄만 유지
    if total_lines > 6:
        first_lines = '\n'.join(lines[:3])
        last_lines = '\n'.join(lines[-3:])
        compact_text = f"{first_lines}\n\n... ({total_lines - 6} lines omitted) ...\n\n{last_lines}\n\n[Output truncated: {original_length} chars, {total_lines} lines total]"
    else:
        # 줄 수가 적으면 단순 절단
        compact_text = output_text[:max_length] + f"...\n\n[Output truncated: {original_length} chars total]"

    return compact_text

def get_file_snapshot(directories=['/app/artifacts', '/app/data']):
    """파일 시스템 스냅샷 생성"""
    snapshot = {}
    for directory in directories:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        snapshot[file_path] = {
                            'mtime': stat.st_mtime,
                            'size': stat.st_size
                        }
                    except:
                        pass
    return snapshot

def get_changed_files(before_snapshot, after_snapshot):
    """변경된 파일 목록 추출"""
    changed = []

    # 새로 생성되거나 수정된 파일
    for file_path, info in after_snapshot.items():
        if file_path not in before_snapshot:
            changed.append({'path': file_path, 'type': 'created'})
        elif info['mtime'] > before_snapshot[file_path]['mtime']:
            changed.append({'path': file_path, 'type': 'modified'})

    return changed

def read_file_content(file_path, max_size=1024*1024):
    """파일 내용 읽기 (최대 1MB)"""
    try:
        stat = os.stat(file_path)
        if stat.st_size > max_size:
            return {'error': f'File too large: {stat.st_size} bytes'}

        # 바이너리 파일 체크
        with open(file_path, 'rb') as f:
            chunk = f.read(512)
            if b'\x00' in chunk:
                return {'error': 'Binary file', 'size': stat.st_size}

        # 텍스트 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return {'content': content, 'size': len(content)}
    except Exception as e:
        return {'error': str(e)}

def execute_code(code_string, execution_num):
    """동적 코드를 실행하고 결과를 반환 (Python 코드 또는 Bash 명령어)"""

    print(f"🚀 Execution {execution_num} starting...", flush=True)

    # # 실행 전 파일 스냅샷 - 주석 처리됨 (필요 없음)
    # before_snapshot = get_file_snapshot()

    # 코드 타입 감지
    code_type = "bash" if code_string.strip().startswith("BASH:") else "python"

    if code_type == "bash":
        # BASH: 접두사 제거
        bash_command = code_string.strip()[5:].strip()
        print(f"🐧 Executing bash command: {bash_command}", flush=True)
    else:
        print(f"🐍 Executing python code", flush=True)

    # Container IP 가져오기
    import socket
    try:
        hostname = socket.gethostname()
        container_ip = socket.gethostbyname(hostname)
    except Exception:
        container_ip = "unknown"

    result = {
        "execution_num": execution_num,
        "timestamp": str(datetime.now()),
        "code": code_string[:200] + "..." if len(code_string) > 200 else code_string,
        "code_type": code_type,
        "status": "running",
        "stdout": "",
        "stderr": "",
        "error": None,
        "execution_time_ms": 0,
        "container_ip": container_ip
    }

    start_time = datetime.now()

    try:
        if code_type == "bash":
            # Bash 명령어 실행 (작업 디렉토리를 /app/으로 설정)
            process = subprocess.run(
                bash_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd="/app",
                timeout=30
            )

            result["status"] = "completed" if process.returncode == 0 else "failed"
            result["stdout"] = process.stdout
            result["stderr"] = process.stderr

            if process.returncode != 0:
                result["error"] = {
                    "type": "BashError",
                    "message": f"Command failed with return code {process.returncode}",
                    "return_code": process.returncode
                }
                print(f"❌ Bash execution {execution_num} failed with code {process.returncode}", flush=True)
            else:
                print(f"✅ Bash execution {execution_num} completed successfully", flush=True)

        else:
            # Python 코드 실행
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                # 필요한 import 자동 추가
                exec_globals = {
                    '__builtins__': __builtins__,
                    'datetime': datetime,
                    'json': json,
                    'os': os,
                    'workspace': session_manager.workspace
                }

                # 코드 실행 - Explicit exception handling to prevent container instability
                try:
                    exec(code_string, exec_globals)
                    result["status"] = "completed"
                except Exception as exec_error:
                    # Catch exec() errors immediately to prevent container crash
                    result["status"] = "failed"
                    traceback_text = traceback.format_exc()
                    result["error"] = create_compact_error_response(exec_error, traceback_text)
                    print(f"❌ Python execution {execution_num} failed during exec(): {exec_error}", flush=True)

            # Capture stdout/stderr regardless of success or failure
            result["stdout"] = stdout_capture.getvalue()
            result["stderr"] = stderr_capture.getvalue()

            if result["status"] == "completed":
                print(f"✅ Python execution {execution_num} completed successfully", flush=True)

    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = {
            "type": "TimeoutError",
            "message": "Command timed out after 30 seconds"
        }
        print(f"⏰ Execution {execution_num} timed out", flush=True)

    except Exception as e:
        result["status"] = "failed"
        if code_type == "python":
            result["stdout"] = stdout_capture.getvalue()
            result["stderr"] = stderr_capture.getvalue()

        # 스트리밍에 적합한 간소화된 에러 응답 생성
        traceback_text = traceback.format_exc()
        result["error"] = create_compact_error_response(e, traceback_text)

        print(f"❌ Execution {execution_num} failed: {e}", flush=True)

    finally:
        end_time = datetime.now()
        result["execution_time_ms"] = int((end_time - start_time).total_seconds() * 1000)

        # # 실행 후 파일 스냅샷 및 변경 파일 추출 - 주석 처리됨 (필요 없음)
        # after_snapshot = get_file_snapshot()
        # changed_files = get_changed_files(before_snapshot, after_snapshot)
        #
        # # 변경된 파일 내용 읽기
        # files_data = {}
        # for file_info in changed_files:
        #     file_path = file_info['path']
        #     file_content = read_file_content(file_path)
        #
        #     # 상대 경로로 변환
        #     if file_path.startswith('/app/'):
        #         relative_path = file_path[5:]  # /app/ 제거
        #     else:
        #         relative_path = file_path
        #
        #     files_data[relative_path] = {
        #         'type': file_info['type'],
        #         'path': file_path,
        #         'relative_path': relative_path,
        #         **file_content
        #     }
        #
        # # 결과에 파일 정보 추가
        # result["files"] = files_data
        #
        # if files_data:
        #     print(f"📁 {len(files_data)} file(s) created/modified", flush=True)
        #     for path in files_data.keys():
        #         print(f"  - {path}", flush=True)

    return result

@app.route('/health', methods=['GET'])
def health():
    """헬스 체크 엔드포인트 (ALB Health Check용)"""
    return jsonify({
        "status": "healthy",
        "session_id": session_manager.session_id,
        "executions_completed": len(session_manager.executions),
        "max_executions": session_manager.max_executions,
        "is_complete": session_manager.is_complete
    })


@app.route('/container-info', methods=['GET'])
def container_info():
    """컨테이너 정보 반환 (Sticky Session 쿠키 검증용)

    멀티 Job 지원:
    - session_id 파라미터로 특정 세션 검증 가능
    - known_sessions 리스트로 이 컨테이너가 알고 있는 모든 세션 ID 반환
    """
    import socket
    try:
        hostname = socket.gethostname()
        private_ip = socket.gethostbyname(hostname)
    except Exception as e:
        hostname = "unknown"
        private_ip = "unknown"

    # 이 컨테이너가 알고 있는 세션 ID 리스트
    # session_manager.session_id는 이 컨테이너가 시작된 세션
    known_sessions = [session_manager.session_id] if session_manager.session_id else []

    return jsonify({
        "private_ip": private_ip,
        "hostname": hostname,
        "session_id": session_manager.session_id,  # 이 컨테이너의 메인 세션
        "known_sessions": known_sessions,  # 멀티 Job 검증용
        "executions_completed": len(session_manager.executions)
    })

@app.route('/execute', methods=['POST'])
def execute():
    """코드 실행 엔드포인트"""

    if session_manager.is_complete:
        return jsonify({
            "error": "Session is already complete",
            "session_id": session_manager.session_id
        }), 400

    # 요청에서 코드 가져오기
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({"error": "No code provided"}), 400

    code = data['code']
    execution_num = len(session_manager.executions) + 1

    # 코드 실행
    result = execute_code(code, execution_num)

    # 결과 저장
    session_manager.add_execution(result)

    # 스트리밍 안정성을 위해 stdout/stderr 출력 크기 제한
    compact_stdout = create_compact_output(result["stdout"], "stdout", max_length=4096*2)
    compact_stderr = create_compact_output(result["stderr"], "stderr", max_length=4096*2)

    # 응답 반환 (파일 정보 포함)
    response_data = {
        "session_id": session_manager.session_id,
        "execution_num": execution_num,
        "status": result["status"],
        "stdout": compact_stdout,
        "stderr": compact_stderr,
        "error": result["error"],
        "execution_time_ms": result["execution_time_ms"],
        "total_executions": len(session_manager.executions),
        "is_session_complete": session_manager.is_complete
    }

    # # 파일 정보가 있으면 추가 - 주석 처리됨 (필요 없음)
    # if 'files' in result and result['files']:
    #     response_data['files'] = result['files']

    # 실시간 백업 비활성화 - 세션 종료 시에만 S3 업로드
    response_data['s3_backup'] = "skipped_until_session_end"

    return jsonify(response_data)

@app.route('/session/status', methods=['GET'])
def session_status():
    """세션 상태 조회"""
    return jsonify({
        "session_id": session_manager.session_id,
        "executions_completed": len(session_manager.executions),
        "max_executions": session_manager.max_executions,
        "is_complete": session_manager.is_complete,
        "workspace": session_manager.workspace,
        "uptime_seconds": int((datetime.now() - session_manager.start_time).total_seconds())
    })

@app.route('/session/complete', methods=['POST'])
def complete_session():
    """세션 강제 완료 (30번 전에도 종료 가능)"""
    session_manager.complete_session()
    return jsonify({
        "message": "Session completed",
        "session_id": session_manager.session_id,
        "total_executions": len(session_manager.executions)
    })

@app.route('/get_file', methods=['POST'])
def get_file():
    """파일 내용 가져오기 엔드포인트 (Method 1 구현)"""
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({"error": "No file_path provided"}), 400

        file_path = data['file_path']

        # 보안: 절대 경로로 변환하고 /app 내부로 제한
        if not file_path.startswith('/'):
            # 상대 경로인 경우 /app 기준으로 처리
            if file_path.startswith('./artifacts/'):
                file_path = f"/app/artifacts/{file_path[12:]}"
            elif file_path.startswith('./data/'):
                file_path = f"/app/data/{file_path[7:]}"
            elif file_path.startswith('artifacts/'):
                file_path = f"/app/artifacts/{file_path[10:]}"
            elif file_path.startswith('data/'):
                file_path = f"/app/data/{file_path[5:]}"
            else:
                file_path = f"/app/{file_path}"

        # 파일 존재 확인
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    "exists": True,
                    "file_path": file_path,
                    "content": content,
                    "size": len(content)
                })
            except Exception as e:
                return jsonify({
                    "exists": True,
                    "file_path": file_path,
                    "error": f"Cannot read file: {str(e)}"
                }), 500
        else:
            return jsonify({
                "exists": False,
                "file_path": file_path,
                "error": "File not found"
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/file-sync', methods=['POST'])
def file_sync():
    """S3를 통한 파일 동기화 처리"""

    try:
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({"error": "No action specified"}), 400

        action = data['action']
        bucket_name = data.get('bucket_name')
        s3_key_prefix = data.get('s3_key_prefix')
        local_path = data.get('local_path')

        if not all([bucket_name, s3_key_prefix, local_path]):
            return jsonify({"error": "Missing required parameters"}), 400

        s3_client = boto3.client('s3', region_name='us-east-1')

        if action == "sync_data_from_s3":
            # S3에서 데이터를 다운로드
            result = sync_from_s3(s3_client, bucket_name, s3_key_prefix, local_path)
            return jsonify(result)

        elif action == "sync_artifacts_to_s3":
            # 아티팩트를 S3에 업로드
            result = sync_to_s3(s3_client, bucket_name, s3_key_prefix, local_path)
            return jsonify(result)

        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400

    except Exception as e:
        print(f"❌ File sync error: {e}", flush=True)
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

def sync_from_s3(s3_client, bucket_name, s3_key_prefix, local_path):
    """S3에서 로컬로 파일들 다운로드"""
    downloaded_files = []

    try:
        # 로컬 디렉토리 생성
        Path(local_path).mkdir(parents=True, exist_ok=True)

        # S3 객체 목록 조회
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=s3_key_prefix
        )

        if 'Contents' not in response:
            print(f"⚠️ No files found in S3 with prefix: {s3_key_prefix}", flush=True)
            return {
                "status": "success",
                "message": "No files to download",
                "files_count": 0,
                "downloaded_files": []
            }

        for obj in response['Contents']:
            s3_key = obj['Key']

            # S3 키에서 상대 경로 추출
            relative_path = s3_key[len(s3_key_prefix):].lstrip('/')
            if not relative_path:  # 빈 키는 건너뛰기
                continue

            local_file_path = os.path.join(local_path, relative_path)

            # 로컬 디렉토리 생성
            local_file_dir = os.path.dirname(local_file_path)
            Path(local_file_dir).mkdir(parents=True, exist_ok=True)

            try:
                s3_client.download_file(bucket_name, s3_key, local_file_path)
                downloaded_files.append(local_file_path)
                print(f"  ⬇️ Downloaded: s3://{bucket_name}/{s3_key} → {local_file_path}", flush=True)
            except Exception as e:
                print(f"  ❌ Download failed for {s3_key}: {e}", flush=True)

        return {
            "status": "success",
            "message": f"Downloaded {len(downloaded_files)} files from S3",
            "files_count": len(downloaded_files),
            "downloaded_files": downloaded_files
        }

    except Exception as e:
        print(f"❌ S3 download error: {e}", flush=True)
        return {
            "status": "error",
            "message": str(e),
            "files_count": 0
        }

def sync_to_s3(s3_client, bucket_name, s3_key_prefix, local_path):
    """로컬에서 S3로 파일들 업로드"""
    uploaded_files = []

    try:
        if not os.path.exists(local_path):
            return {
                "status": "success",
                "message": "Local path does not exist",
                "files_count": 0,
                "uploaded_files": []
            }

        for root, dirs, files in os.walk(local_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_path)
                s3_key = f"{s3_key_prefix}/{relative_path}".replace('\\', '/')

                try:
                    s3_client.upload_file(local_file_path, bucket_name, s3_key)
                    uploaded_files.append(s3_key)
                    print(f"  📤 Uploaded: {local_file_path} → s3://{bucket_name}/{s3_key}", flush=True)
                except Exception as e:
                    print(f"  ❌ Upload failed for {local_file_path}: {e}", flush=True)

        return {
            "status": "success",
            "message": f"Uploaded {len(uploaded_files)} files to S3",
            "files_count": len(uploaded_files),
            "uploaded_files": uploaded_files
        }

    except Exception as e:
        print(f"❌ S3 upload error: {e}", flush=True)
        return {
            "status": "error",
            "message": str(e),
            "files_count": 0
        }

def auto_shutdown():
    """1시간 후 자동 종료"""
    time.sleep(3600)  # 1시간

    print("⏰ Auto-shutdown timeout reached", flush=True)

    if not session_manager.is_complete:
        session_manager.complete_session()

    time.sleep(10)  # S3 업로드 완료 대기
    sys.exit(0)

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("🔥 FARGATE DYNAMIC CODE EXECUTOR V2 - HTTP Server", flush=True)
    print(f"📍 Session ID: {session_manager.session_id}", flush=True)
    print(f"📊 Max Executions: {session_manager.max_executions}", flush=True)
    print("=" * 60, flush=True)

    # 자동 종료 스레드 시작
    shutdown_thread = threading.Thread(target=auto_shutdown)
    shutdown_thread.daemon = True
    shutdown_thread.start()

    # Flask 서버 시작
    app.run(host='0.0.0.0', port=8080, debug=False)