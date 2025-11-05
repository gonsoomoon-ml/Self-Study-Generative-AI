# 파일 동기화 실패 근본 원인 분석 (Root Cause Analysis)

## 📋 Executive Summary

**Session**: 2025-10-06-06-30-14
**Problem**: CSV 파일이 S3에 업로드되었지만 Fargate 컨테이너의 `/data/` 디렉토리에 동기화되지 않음
**Root Cause**: `ensure_session_with_data()` 메서드의 조기 반환 로직 (Line 320-322)
**Impact**: 파일 동기화 건너뜀 → Agent가 대체 전략으로 샘플 데이터 생성

---

## 🔍 Detailed Timeline

| 시간 | 이벤트 | 증거 | 상태 |
|------|--------|------|------|
| 06:30:14 | Session 생성 시작 | Session ID: `2025-10-06-06-30-14` | ✅ |
| 06:31:02 | **S3에 CSV 업로드 완료** | `s3://.../input/Dat-fresh-food-claude.csv` (112KB) | ✅ |
| 06:31:XX | Fargate 컨테이너 시작 | Container IP: `172.31.52.6` | ✅ |
| 06:31:XX | **파일 동기화 건너뜀** | `♻️ Session exists - skipping CSV upload` | ❌ |
| 06:36:19 | **Execution 1**: `ls -la ./data/` | `total 8` (빈 디렉토리) | ❌ |
| 06:36:38 | **Execution 2**: Agent가 샘플 데이터 생성 | 1000행 CSV 생성 | ✅ |
| 06:37:27 | 데이터 분석 완료 | 총 매출액: 27,712,337원 | ✅ |
| 06:42:26 | Session 완료 | 16 executions | ✅ |

**Key Observation**: S3 업로드 (06:31:02)와 Execution 1 (06:36:19) 사이 **5분 간격** 존재

---

## 🐛 Root Cause: Early Return Logic

### 문제 코드 위치

**파일**: `src/tools/global_fargate_coordinator.py`
**라인**: 320-322

```python
def ensure_session_with_data(self, csv_file_path: str):
    """CSV 파일과 함께 세션 생성 (세션 확인 → S3 업로드 → 컨테이너 동기화)"""
    try:
        logger.info(f"🚀 Creating session with data: {csv_file_path}")

        # 🔴 문제 발생 지점!
        if self._current_request_id in self._sessions:
            logger.info(f"♻️ Session exists for request {self._current_request_id} - skipping CSV upload")
            return True  # ← CSV 업로드 및 동기화 건너뜀!

        # 2. 세션 생성
        if not self.ensure_session():
            raise Exception("Failed to create Fargate session")

        # 3. S3 업로드
        session_id = self._sessions[self._current_request_id]['session_id']
        s3_key = self._upload_csv_to_s3_with_session_id(csv_file_path, session_id)
        logger.info(f"📤 CSV uploaded to S3: {s3_key}")

        # 4. 컨테이너에 동기화 ← 실행되지 않음!
        self._sync_csv_from_s3_to_container(s3_key)
        logger.info("✅ CSV file synced to container")

        return True
```

### 문제 시나리오

**정상 시나리오 (첫 번째 호출)**:
1. `ensure_session_with_data()` 호출
2. `self._current_request_id not in self._sessions` → 진행
3. 세션 생성 → S3 업로드 → 파일 동기화 ✅

**문제 시나리오 (두 번째 호출)**:
1. `ensure_session_with_data()` 호출
2. `self._current_request_id in self._sessions` → **조기 반환** ❌
3. CSV 업로드 건너뜀
4. 파일 동기화 건너뜀
5. 컨테이너 `/data/` 디렉토리 비어있음

---

## 💡 Why This Happens

### Scenario 1: 세션 재사용 (가장 가능성 높음)

```python
# Agent 워크플로우
1. Coder Agent 시작 → ensure_session_with_data(csv_path) 호출
   - 세션 생성 → CSV 업로드 → 파일 동기화 ✅

2. Validator Agent 시작 → ensure_session_with_data(csv_path) 호출
   - 세션 존재 → 조기 반환 ❌
   - 파일 동기화 건너뜀

3. Reporter Agent 시작 → ensure_session_with_data(csv_path) 호출
   - 세션 존재 → 조기 반환 ❌
   - 파일 동기화 건너뜀
```

### Scenario 2: 새 컨테이너에서 세션 재사용

```python
# 이전 컨테이너 (172.31.X.X)에서 세션 생성
_sessions = {
    "request_123": {
        "session_id": "2025-10-06-06-30-14",
        "container_ip": "172.31.X.X",  # 이전 컨테이너
        "http_client": <session with cookie>
    }
}

# 새 컨테이너 (172.31.52.6) 시작
# Request ID는 동일하지만 컨테이너는 다름!
# ensure_session_with_data() 호출
# → 세션 존재 확인 → 조기 반환
# → 새 컨테이너에는 파일 없음!
```

---

## 📊 Evidence

### S3 Evidence

```bash
$ aws s3 ls s3://bedrock-logs-gonsoomoon/manus/fargate_sessions/2025-10-06-06-30-14/input/
2025-10-06 06:31:02  112391 Dat-fresh-food-claude.csv  # ✅ S3에 파일 존재
```

### Container Evidence (Execution 1)

```json
{
  "execution_num": 1,
  "timestamp": "2025-10-06 06:36:19.810530",
  "code": "BASH: ls -la ./data/",
  "stdout": "total 8\ndrwxr-xr-x 2 root root 4096 Oct  6 06:31 .\ndrwxr-xr-x 1 root root 4096 Oct  6 06:31 ..\n",
  "container_ip": "172.31.52.6"
}
```

**빈 디렉토리** - 파일 동기화 실행되지 않음 ❌

### Code Evidence

```python
# coder_agent_fargate_tool.py:88-95
if csv_file_path and os.path.exists(csv_file_path):
    logger.info(f"📂 Creating Fargate session with CSV data: {csv_file_path}")
    if not fargate_manager.ensure_session_with_data(csv_file_path):  # ← 호출됨
        return "Error: Failed to create Fargate session with CSV data"
```

---

## 🎯 Root Cause Summary

**문제**:
```python
# 조기 반환 조건이 너무 단순함
if self._current_request_id in self._sessions:
    return True  # ← 파일 동기화 상태 확인 안 함!
```

**근본 원인**:
1. **세션 존재 여부만 확인** (파일 동기화 상태 확인 안 함)
2. **컨테이너 변경 감지 안 됨** (새 컨테이너에 파일 없을 수 있음)
3. **Agent 재호출 시 파일 동기화 건너뜀** (Validator/Reporter)

---

## ✅ Solution: File Existence Check

### Fix 1: 컨테이너 파일 존재 여부 확인 (Best)

```python
def ensure_session_with_data(self, csv_file_path: str):
    """CSV 파일과 함께 세션 생성 (파일 존재 확인 포함)"""
    try:
        logger.info(f"🚀 Creating session with data: {csv_file_path}")

        # 1. 세션이 이미 있으면 파일 존재 확인
        if self._current_request_id in self._sessions:
            logger.info(f"♻️ Session exists - checking if file sync needed...")

            # 컨테이너에 파일 존재 여부 확인
            filename = os.path.basename(csv_file_path)
            if self._check_file_exists_in_container(filename):
                logger.info(f"✅ File already exists in container: {filename}")
                return True

            # 파일 없으면 동기화 실행
            logger.info(f"📁 File not found in container - syncing from S3...")
            session_id = self._sessions[self._current_request_id]['session_id']
            s3_key = f"manus/fargate_sessions/{session_id}/input/{filename}"
            self._sync_csv_from_s3_to_container(s3_key)
            logger.info("✅ CSV file synced to container")
            return True

        # 2-4. 기존 로직 (세션 생성 → S3 업로드 → 동기화)
        ...

def _check_file_exists_in_container(self, filename: str) -> bool:
    """컨테이너에 파일이 존재하는지 확인"""
    try:
        http_client = self._get_http_client(self._current_request_id)
        alb_dns = self._session_manager.alb_dns

        # ls 명령으로 파일 확인
        check_code = f"import os; print('exists' if os.path.exists('/app/data/{filename}') else 'not_found')"

        response = http_client.post(
            f"{alb_dns}/execute",
            json={"code": check_code},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return 'exists' in result.get('stdout', '')

        return False

    except Exception as e:
        logger.warning(f"⚠️ Failed to check file existence: {e}")
        return False  # 확인 실패 시 동기화 실행
```

### Fix 2: 무조건 파일 동기화 (Simple)

```python
def ensure_session_with_data(self, csv_file_path: str):
    """CSV 파일과 함께 세션 생성 (항상 동기화)"""
    try:
        logger.info(f"🚀 Creating session with data: {csv_file_path}")

        # 1. 세션 생성 (없으면)
        if self._current_request_id not in self._sessions:
            if not self.ensure_session():
                raise Exception("Failed to create Fargate session")

        # 2. 항상 S3 업로드 + 동기화 실행
        session_id = self._sessions[self._current_request_id]['session_id']

        # S3에 파일이 없으면 업로드
        filename = os.path.basename(csv_file_path)
        s3_key = f"manus/fargate_sessions/{session_id}/input/{filename}"

        # 항상 동기화 (이미 있어도 덮어쓰기)
        self._upload_csv_to_s3_with_session_id(csv_file_path, session_id)
        self._sync_csv_from_s3_to_container(s3_key)
        logger.info("✅ CSV file synced to container")

        return True
```

### Fix 3: 플래그 기반 추적 (Robust)

```python
class GlobalFargateCoordinator:
    def __init__(self):
        self._sessions = {}
        self._file_synced = {}  # {request_id: {filename: True/False}}
        ...

    def ensure_session_with_data(self, csv_file_path: str):
        """CSV 파일과 함께 세션 생성 (플래그 기반)"""
        try:
            filename = os.path.basename(csv_file_path)

            # 1. 세션 생성
            if self._current_request_id not in self._sessions:
                if not self.ensure_session():
                    raise Exception("Failed to create Fargate session")
                # 새 세션이므로 파일 동기화 플래그 초기화
                self._file_synced[self._current_request_id] = {}

            # 2. 파일 동기화 확인
            if self._file_synced.get(self._current_request_id, {}).get(filename):
                logger.info(f"✅ File already synced: {filename}")
                return True

            # 3. S3 업로드 + 동기화
            session_id = self._sessions[self._current_request_id]['session_id']
            s3_key = self._upload_csv_to_s3_with_session_id(csv_file_path, session_id)
            self._sync_csv_from_s3_to_container(s3_key)

            # 4. 플래그 설정
            self._file_synced[self._current_request_id][filename] = True
            logger.info("✅ CSV file synced and flagged")

            return True
```

---

## 🧪 Testing Plan

### Test 1: 단일 Agent 호출

```python
# Coder Agent만 실행
coordinator.ensure_session_with_data(csv_path)

# 검증
# 1. S3에 CSV 파일 존재
# 2. 컨테이너 /data/에 파일 존재
# 3. Execution에서 파일 읽기 성공
```

### Test 2: 다중 Agent 호출 (중요!)

```python
# Coder → Validator → Reporter 순차 실행
# 각 Agent에서 ensure_session_with_data() 호출

# 검증
# 1. 첫 번째 호출: 파일 동기화 실행 ✅
# 2. 두 번째 호출: 파일 존재 확인 → 동기화 건너뜀 (Fix 1) ✅
# 3. 세 번째 호출: 파일 존재 확인 → 동기화 건너뜀 (Fix 1) ✅
```

### Test 3: 컨테이너 재시작 (Edge Case)

```python
# 1. 세션 생성 + 파일 동기화
# 2. 컨테이너 강제 종료
# 3. 새 컨테이너 시작
# 4. ensure_session_with_data() 재호출

# 검증 (Fix 1 전용)
# - 파일 존재 확인 → 없음 → 재동기화 ✅
```

---

## 📝 Recommendations

### Immediate (Fix 1 구현)

1. **`_check_file_exists_in_container()` 메서드 추가**
   - Python 코드로 파일 존재 확인
   - 10초 타임아웃

2. **`ensure_session_with_data()` 수정**
   - 세션 존재 시 파일 확인
   - 파일 없으면 재동기화

3. **테스트**
   - Validator, Reporter Agent에서 검증

### Short-term (관찰성 개선)

1. **로깅 강화**
   ```python
   logger.info(f"📁 Checking file: {filename}")
   logger.info(f"✅ File found in container")
   logger.info(f"📥 Re-syncing file from S3")
   ```

2. **메트릭 추가**
   - 파일 동기화 횟수
   - 파일 확인 실패 횟수
   - 재동기화 횟수

### Long-term (아키텍처 개선)

1. **컨테이너 상태 추적**
   - 컨테이너 IP 변경 감지
   - 새 컨테이너 시작 시 자동 재동기화

2. **파일 캐싱 메커니즘**
   - 컨테이너 재시작 시 자동 복원
   - Persistent volume 사용 고려

---

## 🎓 Key Learnings

1. **조기 반환 로직의 위험성**
   - 상태 확인 없이 조기 반환하면 부작용 발생
   - 항상 필요한 전제 조건 검증 필요

2. **Dedicated Container 아키텍처의 복잡성**
   - 세션 재사용은 좋지만 파일 상태 관리 필요
   - 컨테이너 변경 시 파일 동기화 상태 초기화 필요

3. **Agent 워크플로우의 멱등성**
   - 같은 메서드를 여러 번 호출해도 안전해야 함
   - 상태 기반 조건부 실행 필요

4. **AgentCore 자가 복구의 강력함**
   - 파일 동기화 실패에도 불구하고 워크플로우 완료
   - 대체 전략으로 샘플 데이터 생성

---

**Last Updated**: 2025-10-06 07:00:00 UTC
**Session**: 2025-10-06-06-30-14
**Author**: Claude Code Investigation (Detailed Root Cause Analysis)
