# File Sync Investigation Summary

## 📋 Investigation Results

### Session: 2025-10-06-06-30-14

**Problem**: CSV 파일이 S3에 있지만 컨테이너 `/data/`에 없음

---

## 🔍 Evidence Collected

### 1. S3 Evidence ✅

```bash
$ aws s3 ls s3://.../2025-10-06-06-30-14/input/
2025-10-06 06:31:02  112391 Dat-fresh-food-claude.csv

$ aws s3 cp s3://.../input/Dat-fresh-food-claude.csv - | head -5
날짜,카테고리,제품명,수량,단가,금액
2023-01-01,육류,오리고기,8,12964,103712
...
```

**Result**: ✅ CSV 파일이 S3에 정상적으로 존재

### 2. Container Evidence ❌

```json
{
  "execution_num": 1,
  "timestamp": "2025-10-06 06:36:19",
  "code": "BASH: ls -la ./data/",
  "stdout": "total 8\ndrwxr-xr-x 2 root root 4096 Oct  6 06:31 .\n...",
  "container_ip": "172.31.52.6"
}
```

**Result**: ❌ 컨테이너 `/data/` 디렉토리 비어있음

### 3. Workflow Analysis ✅

```python
# coder_agent_fargate_tool.py:88-95
if csv_file_path and os.path.exists(csv_file_path):
    fargate_manager.ensure_session_with_data(csv_file_path)  # ✅ 호출됨
else:
    fargate_manager.ensure_session()  # ← 이게 호출되었을 수도?
```

### 4. Validator/Reporter Analysis ✅

```bash
$ grep -rn "ensure_session" validator_agent_fargate_tool.py
# No matches found
```

**Result**: ✅ Validator/Reporter는 `ensure_session`을 호출하지 않음

---

## 💡 Key Findings

### Finding 1: Fix 1 Unnecessary

**Conclusion**: Validator/Reporter가 `ensure_session`을 호출하지 않으므로, 파일 존재 확인 로직을 추가해도 실행되지 않음.

**Reasoning**:
- Coder만 `ensure_session_with_data()` 호출
- Validator/Reporter는 기존 세션 재사용만
- 파일 동기화는 Coder 단계에서 1회만 실행

### Finding 2: Logging Insufficient

**Current Logging** (`global_fargate_coordinator.py:394-430`):
```python
def _sync_csv_from_s3_to_container(self, s3_key: str):
    # ❌ 시작 로그 없음
    sync_request = {...}
    response = http_client.post(f"{alb_dns}/file-sync", ...)
    # ❌ HTTP 요청/응답 상세 로그 없음

    if response.status_code != 200:
        raise Exception(f"File sync failed: {response.text}")

    result = response.json()
    logger.info(f"📥 Synced {result.get('files_count', 0)} files")  # ← 성공 시만
    time.sleep(10)
    # ❌ 대기 완료 로그 없음
```

**Missing Logs**:
1. 파일 동기화 시작 (`🔄 Starting file sync...`)
2. S3 key 확인 (`S3 key: manus/fargate_sessions/.../input/`)
3. HTTP 요청 상세 (`POST /file-sync with request: {...}`)
4. HTTP 응답 상세 (`Response: {status: 200, files_count: 1}`)
5. 대기 시작/완료 (`⏳ Waiting...`, `✅ Wait complete`)

### Finding 3: Timing Analysis

**Timeline**:
```
06:31:02 - S3 upload complete
06:31:XX - _sync_csv_from_s3_to_container() called?
06:31:XX - time.sleep(10) → 06:31:XX + 10s
06:36:19 - Execution 1 (5 minutes later!)
```

**Gap**: 5분 간격 → 10초 대기는 충분했을 것

**Question**: 왜 5분 후에 실행?

---

## 🎯 Root Cause Hypotheses

### Hypothesis 1: `ensure_session_with_data()` Not Called

**Scenario**:
```python
# Coder Agent
csv_file_path = shared_state.get("csv_file_path")  # ← None?

if csv_file_path and os.path.exists(csv_file_path):
    # ✅ 이 경로
    fargate_manager.ensure_session_with_data(csv_file_path)
else:
    # ❌ 이 경로가 실행되었을 수도?
    fargate_manager.ensure_session()  # CSV 없이 세션 생성!
```

**Evidence Needed**:
- `shared_state.get("csv_file_path")` 값 확인
- Coder Agent 로그에서 `ensure_session_with_data` vs `ensure_session` 호출 확인

### Hypothesis 2: Early Return Logic

**Code**:
```python
# global_fargate_coordinator.py:320-322
if self._current_request_id in self._sessions:
    logger.info("♻️ Session exists - skipping CSV upload")
    return True  # ← 파일 동기화 건너뜀!
```

**Scenario**:
- 이전 세션이 `_sessions`에 남아있음
- `ensure_session_with_data()` 조기 반환
- 파일 동기화 건너뜀

**Evidence Needed**:
- `♻️ Session exists` 로그 존재 여부

### Hypothesis 3: HTTP /file-sync Failure

**Code**:
```python
# global_fargate_coordinator.py:417-418
if response.status_code != 200:
    raise Exception(f"File sync failed: {response.text}")
```

**Scenario**:
- `/file-sync` 엔드포인트가 200이 아닌 응답 반환
- Exception 발생
- 하지만 에러가 무시되었을 수도?

**Evidence Needed**:
- `❌ File sync failed` 로그 존재 여부
- HTTP response status code

### Hypothesis 4: S3 Download Failure (Silent)

**Code**:
```python
# fargate-runtime/dynamic_executor_v2.py:734
s3_client.download_file(bucket_name, s3_key, local_file_path)
```

**Scenario**:
- S3 다운로드 실패 (권한, 네트워크, 파일 없음)
- Exception이 catch되어 200 OK 반환
- 하지만 실제로는 파일 다운로드 안 됨

**Evidence Needed**:
- Fargate 컨테이너 Flask 로그 (`⬇️ Downloaded: ...` 또는 에러)

---

## 📊 Investigation Limitations

### Cannot Investigate

1. **Fargate Container Logs**: 컨테이너가 이미 종료됨, CloudWatch 로그 없음
2. **AgentCore Runtime Logs**: CloudWatch 조회 너무 느림, 타임아웃
3. **Real-time Debugging**: 해당 세션 종료됨

### Can Investigate

1. **Code Analysis**: ✅ 완료
2. **S3 Evidence**: ✅ 완료
3. **Execution Results**: ✅ 완료
4. **Next Job Test**: ⏳ 새 Job으로 검증 필요

---

## 🛠️ Recommended Actions

### Action 1: Enhanced Logging (Immediate)

**Location**: `src/tools/global_fargate_coordinator.py:394-430`

```python
def _sync_csv_from_s3_to_container(self, s3_key: str):
    """S3에서 컨테이너로 CSV 파일 동기화 (Enhanced Logging)"""
    try:
        alb_dns = self._session_manager.alb_dns
        filename = s3_key.split('/')[-1]

        # ✅ 1. 시작 로그
        logger.info(f"🔄 Starting file sync...")
        logger.info(f"   S3 Key: {s3_key}")
        logger.info(f"   Filename: {filename}")
        logger.info(f"   Target: /app/data/{filename}")

        sync_request = {
            "action": "sync_data_from_s3",
            "bucket_name": "bedrock-logs-gonsoomoon",
            "s3_key_prefix": f"manus/fargate_sessions/{s3_key.split('/')[2]}/input/",
            "local_path": "/app/data/"
        }

        # ✅ 2. 요청 로그
        logger.info(f"📤 Sending file sync request:")
        logger.info(f"   URL: {alb_dns}/file-sync")
        logger.info(f"   Request: {sync_request}")

        http_client = self._get_http_client(self._current_request_id)
        response = http_client.post(
            f"{alb_dns}/file-sync",
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
        import time
        logger.info("⏳ Waiting 10 seconds for file sync to complete...")
        time.sleep(10)

        # ✅ 6. 대기 완료 로그
        logger.info("✅ File sync wait complete")

    except Exception as e:
        logger.error(f"❌ File sync failed: {e}")
        logger.error(f"   Exception type: {type(e).__name__}")
        logger.error(f"   Exception details: {str(e)[:1000]}")
        raise
```

### Action 2: Add Debug Endpoint (Short-term)

**Location**: `fargate-runtime/dynamic_executor_v2.py`

```python
@app.route('/debug/files', methods=['GET'])
def debug_files():
    """디버그: 파일 목록 확인"""
    import os
    files = {
        '/app/data': os.listdir('/app/data') if os.path.exists('/app/data') else [],
        '/app/artifacts': os.listdir('/app/artifacts') if os.path.exists('/app/artifacts') else []
    }
    return jsonify(files)
```

**Usage**:
```python
# global_fargate_coordinator.py에서 호출
response = http_client.get(f"{alb_dns}/debug/files")
logger.info(f"Container files: {response.json()}")
```

### Action 3: Test with Next Job (Verification)

**Test Plan**:
1. Enhanced logging 적용
2. 새 Job 배포
3. 로그에서 파일 동기화 과정 추적:
   - `🔄 Starting file sync...`
   - `📤 Sending file sync request`
   - `📥 File sync response: Status: 200`
   - `✅ File sync completed: Files synced: 1`
   - `⏳ Waiting 10 seconds...`
   - `✅ File sync wait complete`
4. Execution 1에서 `ls -la ./data/` 확인
5. 파일 존재 여부 검증

---

## 🎓 Key Learnings

### 1. Logging is Critical

- 성공/실패 로그만으로는 부족
- 모든 단계의 상세 로그 필요
- 디버깅 없이는 근본 원인 파악 불가

### 2. Workflow Understanding

- Validator/Reporter가 세션 생성하지 않음
- Coder가 파일 동기화의 유일한 진입점
- Fix 1은 불필요 (Validator/Reporter 호출 안 함)

### 3. Investigation Limitations

- 종료된 세션은 조사 어려움
- 실시간 로깅이 필수
- 재현 테스트 필요

---

## 📝 Next Steps

1. ✅ Enhanced logging 구현
2. ⏳ 새 Job 배포 및 테스트
3. ⏳ 로그 분석으로 실제 근본 원인 파악
4. ⏳ 필요시 수정 적용

**Status**: Investigation incomplete - Enhanced logging needed for root cause identification

**Last Updated**: 2025-10-06
**Author**: Claude Code Investigation
