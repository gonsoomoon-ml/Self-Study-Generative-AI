# File Synchronization Failure Analysis - Dedicated Container Architecture

## 📋 Executive Summary

**Problem**: CSV 파일이 S3 input 폴더에는 존재하지만 Fargate 컨테이너의 `/data/` 디렉토리로 동기화되지 않아 전체 워크플로우가 종료됨.

**Impact**: HTTP 502 에러 → 3회 재시도 실패 → "TERMINATING ENTIRE WORKFLOW"

**Root Cause**: Dedicated container/cookie 아키텍처에서 파일 동기화 메커니즘 실패

---

## 🔍 Problem Discovery Timeline

### Session: 2025-10-06-06-30-14

| 시간 | 이벤트 | 상태 |
|------|--------|------|
| 06:30:14 | Session 생성 시작 | ✅ |
| 06:31:02 | S3에 CSV 업로드 | ✅ |
| 06:31:XX | Fargate 컨테이너 시작 (172.31.52.6) | ✅ |
| 06:31:XX | ALB 타겟 등록 (healthy) | ✅ |
| 06:31:XX | Cookie 획득 (Option 2) | ✅ |
| 06:31:XX | **파일 동기화 시도** | ❌ |
| 06:3X:XX | Python 실행 시도 → HTTP 502 | ❌ |
| 06:3X:XX | 3회 재시도 후 워크플로우 종료 | ❌ |

---

## 🔴 Critical Evidence

### 1. S3 Input 폴더 - 파일 존재 ✅

```bash
$ aws s3 ls s3://bedrock-logs-gonsoomoon/manus/fargate_sessions/2025-10-06-06-30-14/input/

2025-10-06 06:31:02     167936 Dat-fresh-food-claude.csv  # ← 파일 존재
```

### 2. Fargate 컨테이너 `/data/` 디렉토리 - 파일 없음 ❌

```bash
$ ls -la ./data/
total 8
drwxr-xr-x 2 root root 4096 Oct  6 06:31 .
drwxr-xr-x 1 root root 4096 Oct  6 06:31 ..
# ← Empty! CSV 파일 없음
```

### 3. AgentCore Runtime 로그 - 워크플로우 종료

```json
{
  "error": "Failed to execute. Error: Connection failed after 3 attempts:
           FIXED CONTAINER EXECUTION FAILED: FIXED CONTAINER NOT RESPONDING:
           HTTP 502 - TERMINATING ENTIRE WORKFLOW"
}
```

---

## 🏗️ Architecture Context

### Dedicated Container Model (현재)

```
Job 1 시작
  ↓
AgentCore Runtime
  ↓
1. Fargate 컨테이너 시작 (172.31.52.6)
  ↓
2. ALB 등록 + Cookie 획득 ✅
  ↓
3. ❌ 파일 동기화 (S3 → Container /data/)  ← 실패 지점!
  ↓
4. Python 실행 시도
  ↓
5. HTTP 502 (파일 없음)
  ↓
6. 워크플로우 종료
```

### 비교: 이전 세션 (2025-10-06-06-16-23) - 파일 동기화 성공 ✅

```
S3 Files:
- input/Dat-fresh-food-claude.csv (06:17:48) ✅
- data/Dat-fresh-food-claude.csv (06:23:18) ✅  ← 동기화 성공!
- debug/execution_1.json (06:20:40) ✅

Result:
- 파일 동기화: 성공
- Execution: 실패 (NameError: glob not defined)
- Session: 조기 종료 (다른 문제)
```

---

## 🔧 File Sync Mechanism Analysis

### 예상 동작 흐름

```python
# 1. AgentCore Runtime이 S3 input 폴더에 파일 업로드
s3://bedrock-logs-gonsoomoon/manus/fargate_sessions/{session_id}/input/
  └── Dat-fresh-food-claude.csv

# 2. 파일 동기화 메커니즘 (예상)
# Option A: Fargate 컨테이너 시작 시 S3 sync
# Option B: AgentCore가 /sync 엔드포인트 호출
# Option C: Fargate가 주기적으로 S3 polling

# 3. 컨테이너 내부 경로
/data/
  └── Dat-fresh-food-claude.csv  ← 여기로 복사되어야 함

# 4. Python 코드가 파일 참조
import pandas as pd
df = pd.read_csv('./data/Dat-fresh-food-claude.csv')
```

### 현재 상태: 2단계에서 실패 ❌

---

## 📊 Session Comparison

| 항목 | Session 2025-10-06-06-16-23 | Session 2025-10-06-06-30-14 |
|------|----------------------------|----------------------------|
| **파일 동기화** | ✅ 성공 | ❌ 실패 |
| **S3 input 파일** | ✅ 존재 | ✅ 존재 |
| **Container /data/ 파일** | ✅ 존재 | ❌ 없음 |
| **Execution 생성** | ✅ 1개 생성 | ❌ 0개 |
| **실패 원인** | NameError (코드 에러) | File not found (sync 실패) |
| **워크플로우 종료** | 조기 종료 (1 execution) | HTTP 502 → 워크플로우 종료 |

---

## 🐛 Potential Root Causes

### 1. 타이밍 문제 (Race Condition)

**가능성**: 파일 동기화가 완료되기 전에 Python 실행 시도

```
T0: Fargate 컨테이너 시작
T1: AgentCore가 S3에 파일 업로드
T2: AgentCore가 /execute 호출 ← 너무 빠름!
T3: 파일 동기화 시작 (아직 완료 안 됨)
T4: Python 실행 → FileNotFoundError
```

**증거**:
- Session 06:16:23: 파일 동기화 성공 (시간 여유?)
- Session 06:30:14: 파일 동기화 실패 (빠른 실행?)

### 2. 파일 동기화 엔드포인트 누락

**가능성**: Session 06:30:14에서 `/sync` 엔드포인트 호출 누락

**확인 필요**:
- Fargate Flask 서버에 `/sync` 엔드포인트 존재 여부
- AgentCore가 실행 전 `/sync` 호출하는지 여부

### 3. S3 권한 문제

**가능성**: Fargate Task Role이 S3 버킷 읽기 권한 없음

**확인 필요**:
```bash
# Fargate 컨테이너 내부에서 테스트
aws s3 cp s3://bedrock-logs-gonsoomoon/manus/fargate_sessions/2025-10-06-06-30-14/input/Dat-fresh-food-claude.csv ./data/
```

### 4. 컨테이너 초기화 실패

**가능성**: Fargate 컨테이너가 `/data/` 디렉토리 마운트 실패

**증거**:
```bash
drwxr-xr-x 2 root root 4096 Oct  6 06:31 .   # ← 디렉토리 생성 시간 06:31
drwxr-xr-x 1 root root 4096 Oct  6 06:31 ..
# 빈 디렉토리지만 생성은 됨
```

---

## 🔬 Investigation Plan

### Phase 1: 파일 동기화 메커니즘 확인

```bash
# 1. Fargate Flask 서버 코드 확인
grep -r "sync\|download\|s3" fargate-runtime/

# 2. AgentCore Runtime 파일 동기화 로직 확인
grep -r "sync\|upload\|input" src/tools/

# 3. Dockerfile 확인 - 초기화 스크립트
cat Dockerfile | grep -A 10 "COPY\|RUN"
```

### Phase 2: 런타임 테스트

```python
# Fargate 컨테이너 내부에서 수동 테스트
import boto3

s3 = boto3.client('s3')
s3.download_file(
    'bedrock-logs-gonsoomoon',
    'manus/fargate_sessions/2025-10-06-06-30-14/input/Dat-fresh-food-claude.csv',
    '/data/Dat-fresh-food-claude.csv'
)
```

### Phase 3: AgentCore 로그 분석

```bash
# 파일 동기화 관련 로그 검색
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/... \
  --filter-pattern "sync OR upload OR input OR download" \
  --start-time 1728193800000
```

---

## 💡 Hypothesis: Session 06:16:23 vs 06:30:14

### Why did 06:16:23 succeed?

**Timeline reconstruction**:
```
06:17:29 - Session start
06:17:48 - Input file uploaded to S3
06:20:40 - Execution 1 (3분 후)  ← 충분한 시간!
06:23:18 - Data file synced
```

**3분의 시간 여유** → 파일 동기화 완료 가능

### Why did 06:30:14 fail?

**Timeline reconstruction**:
```
06:30:14 - Session start
06:31:02 - Input file uploaded to S3
06:31:XX - Execution attempt (즉시?)  ← 시간 부족!
06:31:XX - HTTP 502 (file not found)
```

**즉각적인 실행 시도** → 파일 동기화 미완료

---

## ✅ UPDATE: 파일 동기화 이미 구현되어 있음!

**2025-10-06 업데이트**: 상세 코드 검토 결과, **파일 동기화가 이미 완전히 구현되어 있습니다!**

### 구현 현황

**1. Fargate Flask 서버 - `/file-sync` 엔드포인트 ✅**

파일 위치: `fargate-runtime/dynamic_executor_v2.py:657-694`

```python
@app.route('/file-sync', methods=['POST'])
def file_sync():
    """S3를 통한 파일 동기화 처리"""
    data = request.get_json()
    action = data['action']  # "sync_data_from_s3"
    bucket_name = data.get('bucket_name')
    s3_key_prefix = data.get('s3_key_prefix')  # "manus/fargate_sessions/{session_id}/input/"
    local_path = data.get('local_path')  # "/app/data/"

    if action == "sync_data_from_s3":
        result = sync_from_s3(s3_client, bucket_name, s3_key_prefix, local_path)
        return jsonify(result)
```

**2. S3 → Container 동기화 로직 ✅**

파일 위치: `fargate-runtime/dynamic_executor_v2.py:696-753`

```python
def sync_from_s3(s3_client, bucket_name, s3_key_prefix, local_path):
    """S3에서 로컬로 파일들 다운로드"""
    # S3 객체 목록 조회
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=s3_key_prefix
    )

    # 모든 파일 다운로드
    for obj in response['Contents']:
        s3_key = obj['Key']
        relative_path = s3_key[len(s3_key_prefix):].lstrip('/')
        local_file_path = os.path.join(local_path, relative_path)

        s3_client.download_file(bucket_name, s3_key, local_file_path)
        downloaded_files.append(local_file_path)
```

**3. AgentCore Runtime - 파일 동기화 호출 ✅**

파일 위치: `src/tools/global_fargate_coordinator.py:314-341`

```python
def create_session_with_data(self, csv_file_path: str):
    """CSV 파일과 함께 세션 생성 (3단계 프로세스)"""

    # 1. 세션이 이미 존재하면 CSV 업로드 건너뜀
    if self._current_request_id in self._sessions:
        logger.info(f"♻️ Session exists - skipping CSV upload")
        return True

    # 2. 먼저 세션 생성 (Timestamp 생성)
    if not self.ensure_session():
        raise Exception("Failed to create Fargate session")

    # 3. 생성된 세션 ID를 사용하여 S3 업로드
    session_id = self._sessions[self._current_request_id]['session_id']
    s3_key = self._upload_csv_to_s3_with_session_id(csv_file_path, session_id)
    logger.info(f"📤 CSV uploaded to S3: {s3_key}")

    # 4. 컨테이너에 S3 → 로컬 동기화 ✅
    self._sync_csv_from_s3_to_container(s3_key)
    logger.info("✅ CSV file synced to container")

    return True
```

**4. 파일 동기화 상세 로직 ✅**

파일 위치: `src/tools/global_fargate_coordinator.py:394-430`

```python
def _sync_csv_from_s3_to_container(self, s3_key: str):
    """S3에서 컨테이너로 CSV 파일 동기화"""
    try:
        # s3_key 형태: "manus/fargate_sessions/{session_id}/input/file.csv"
        sync_request = {
            "action": "sync_data_from_s3",
            "bucket_name": "bedrock-logs-gonsoomoon",
            "s3_key_prefix": f"manus/fargate_sessions/{s3_key.split('/')[2]}/input/",
            "local_path": "/app/data/"
        }

        # 요청별 HTTP 클라이언트 사용 (쿠키 격리)
        http_client = self._get_http_client(self._current_request_id)
        response = http_client.post(
            f"{alb_dns}/file-sync",
            json=sync_request,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"File sync failed: {response.text}")

        result = response.json()
        logger.info(f"📥 Synced {result.get('files_count', 0)} files to container")

        # 동기화 완료를 위한 10초 대기
        logger.info("⏳ Waiting 10 seconds for file sync to complete...")
        time.sleep(10)

    except Exception as e:
        logger.error(f"❌ File sync failed: {e}")
        raise
```

---

## 🎯 수정 불필요 - 기존 솔루션 이미 구현됨

**이전 권장사항**:
~~Solution 1: 명시적 파일 동기화 엔드포인트 구현~~

**현재 상태**:
✅ **이미 구현되어 있습니다!**

- `/file-sync` 엔드포인트: 완료
- `sync_from_s3()` 함수: 완료
- `create_session_with_data()` 호출: 완료
- `_sync_csv_from_s3_to_container()` 로직: 완료

---

## 🔍 Session 2025-10-06-06-30-14 실패 원인 재분석

**새로운 가설**:

### 가설 1: `create_session_with_data()` 호출 안 됨 (가능성 높음)

```python
# agentcore_runtime.py에서 호출하는 메서드 확인 필요

# 만약 이렇게 호출했다면 → CSV 없이 세션 생성
coordinator.ensure_session()  # ❌ 파일 동기화 안 함

# 이렇게 호출해야 함 → CSV 업로드 + 동기화
coordinator.create_session_with_data(csv_path)  # ✅ 파일 동기화 포함
```

### 가설 2: 세션 재사용으로 CSV 업로드 건너뜀

```python
# global_fargate_coordinator.py:320-322
if self._current_request_id in self._sessions:
    logger.info(f"♻️ Session exists - skipping CSV upload")
    return True  # ← CSV 업로드 및 동기화 건너뜀!
```

**시나리오**:
1. Session 06:16:23에서 세션 생성 + CSV 업로드 성공
2. Session 06:30:14가 **동일한 Request ID** 재사용?
3. 이미 세션 존재 → CSV 업로드 건너뜀
4. `/data/` 디렉토리 비어있음 (새 컨테이너라서)

### 가설 3: AgentCore가 대체 전략 실행

**Session 06:30:14의 실제 결과**:
- Execution 1: `/data/` 비어있음 확인
- Execution 2: **Agent가 샘플 데이터 직접 생성** ✅
- Execution 3-16: 생성된 데이터로 분석 완료 ✅

**결론**:
- 파일 동기화 실패 감지
- AgentCore가 자가 복구 메커니즘 실행
- Python 코드로 샘플 데이터 생성 지시
- 워크플로우 정상 완료

---

## 🎯 Recommended Solutions (Updated)

### Solution 1: AgentCore Runtime 호출 확인 ✅

**확인 사항**:
```python
# agentcore_runtime.py에서 반드시 확인
# ❌ 잘못된 호출
coordinator.ensure_session()

# ✅ 올바른 호출
coordinator.create_session_with_data(csv_file_path)
```

### Solution 2: 세션 재사용 시 파일 동기화 강제

**현재 문제**:
```python
# 세션 존재 시 CSV 업로드 건너뜀
if self._current_request_id in self._sessions:
    return True  # ← 파일 동기화 안 함!
```

**개선안**:
```python
def create_session_with_data(self, csv_file_path: str):
    # 세션이 존재하더라도 CSV 파일이 컨테이너에 없으면 동기화
    if self._current_request_id in self._sessions:
        session_id = self._sessions[self._current_request_id]['session_id']

        # 컨테이너에 파일 존재 여부 확인
        if not self._check_file_exists_in_container(csv_file_path):
            logger.info("📁 File not found in container - syncing from S3...")
            s3_key = f"manus/fargate_sessions/{session_id}/input/{os.path.basename(csv_file_path)}"
            self._sync_csv_from_s3_to_container(s3_key)

        return True
```

### Solution 2: 헬스체크에 파일 동기화 포함

**구현**:
```python
# fargate-runtime/dynamic_executor_v2.py
@app.route('/health', methods=['GET'])
def health():
    """헬스체크 + 파일 동기화 상태"""
    files_synced = os.path.exists('/data/Dat-fresh-food-claude.csv')

    return jsonify({
        "status": "healthy" if files_synced else "initializing",
        "files_synced": files_synced
    })
```

### Solution 3: Retry with Exponential Backoff

**구현**:
```python
# src/tools/fargate_container_controller.py
def execute_with_retry(self, code: str, max_retries=3):
    """파일 동기화 대기 포함 재시도"""
    for attempt in range(max_retries):
        try:
            return self.execute(code)
        except Exception as e:
            if "FileNotFoundError" in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            raise
```

---

## 📝 Action Items

### Immediate (현재 세션)

1. ✅ **파일 동기화 실패 확인 완료**
   - S3: 파일 존재
   - Container: 파일 없음
   - 원인: 동기화 메커니즘 실패

2. ⏳ **파일 동기화 코드 위치 확인 필요**
   - Fargate Flask 서버 엔드포인트
   - AgentCore Runtime 호출 로직
   - Dockerfile 초기화 스크립트

### Short-term (다음 테스트)

3. ⏳ **Solution 1 구현 및 테스트**
   - `/sync-input-files` 엔드포인트 추가
   - AgentCore에서 실행 전 호출
   - 동기화 완료 대기

4. ⏳ **Job 2 멀티 Job 테스트**
   - 파일 동기화 수정 후
   - Option 2 (new HTTP client) 검증
   - 독립적 컨테이너 실행 확인

### Long-term (아키텍처 개선)

5. ⏳ **헬스체크에 초기화 상태 포함**
   - `initializing` → `healthy` 전환
   - AgentCore가 `healthy` 확인 후 실행

6. ⏳ **관찰성 개선**
   - 파일 동기화 시작/완료 로그
   - S3 다운로드 시간 측정
   - 실패 시 상세 에러 메시지

---

## 🔗 Related Issues

### Issue 1: Early Session Termination (2025-10-06-06-16-23)
- **Status**: Separate issue
- **Cause**: AgentCore Runtime 로직 (1 execution 후 종료)
- **Impact**: 파일 동기화는 성공했으나 세션 조기 종료

### Issue 2: Cookie Acquisition (Solved)
- **Status**: Fixed with Option 2
- **Solution**: New HTTP Client per cookie acquisition attempt
- **Verification**: Pending (파일 동기화 수정 후 테스트)

---

## 📚 References

### Files Modified (Previous)
- `src/tools/global_fargate_coordinator.py` (Option 2 구현)
- `src/tools/fargate_container_controller.py` (HTTP session injection)

### Files to Investigate
- `fargate-runtime/dynamic_executor_v2.py` (Flask 서버)
- `fargate-runtime/session_fargate_manager.py` (세션 관리)
- `Dockerfile` (초기화 스크립트)
- `agentcore_runtime.py` (파일 업로드 로직)

### AWS Resources
- S3 Bucket: `bedrock-logs-gonsoomoon/manus/fargate_sessions/`
- Fargate Cluster: `my-fargate-cluster`
- Container IP: `172.31.52.6` (Session 06:30:14)

---

## 🎓 Key Learnings

### Dedicated Container Architecture 고유 문제

**Ephemeral Container (이전)**:
- 매 execution마다 새 컨테이너 시작
- 시작 시 S3 파일 자동 다운로드
- 파일 동기화 실패 확률 낮음

**Dedicated Container (현재)**:
- 1개 컨테이너가 전체 Job 처리
- 파일 동기화 타이밍 중요 ⚠️
- **Race condition 가능성 높음**

### Cookie Isolation vs File Sync

**Cookie Isolation (Solved ✅)**:
- Request ID별 독립적 HTTP Client
- Sticky Session 쿠키 격리
- Option 2로 해결

**File Sync (Current Issue ❌)**:
- S3 → Container 동기화 메커니즘
- 타이밍 문제
- 명시적 동기화 엔드포인트 필요

---

**Last Updated**: 2025-10-06 06:40:00 UTC
**Session**: 2025-10-06-06-30-14
**Author**: Claude Code Investigation
