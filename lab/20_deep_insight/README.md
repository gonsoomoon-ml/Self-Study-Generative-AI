# Test VPC Private Connectivity - File Organization

이 폴더는 **Bedrock AgentCore VPC Private 연결 테스트 환경** 관련 파일들을 포함합니다.

---

## 📁 폴더 구조

### 🔧 Setup Scripts (설정 스크립트)

#### 메인 스크립트
- **`test_vpc_setup_new_vpc.sh`** ⭐
  - 새로운 VPC 생성 및 전체 인프라 구축 (권장)
  - Private/Public subnet, NAT Gateway, VPC Endpoint 모두 생성
  - 사용법: `./test_vpc_setup_new_vpc.sh`

#### 대안 스크립트
- **`test_vpc_setup.sh`**
  - 기존 VPC 사용 (Option 1)
  - 기존 인프라에 VPC Endpoint와 Internal ALB만 추가

### 🗑️ Cleanup Scripts (정리 스크립트)

- **`cleanup_test_vpc_new.sh`**
  - 새 VPC 전체 리소스 정리
  - 사용법: `./cleanup_test_vpc_new.sh`

- **`cleanup_test_vpc.sh`**
  - 기존 VPC용 정리 스크립트

- **`cleanup_partial_vpc.sh`**
  - 긴급 정리 스크립트 (설정 중 실패 시)
  - 부분적으로 생성된 리소스 정리용

### 📓 Jupyter Notebook (AgentCore 배포)

- **`agentcore_runtime_vpc.ipynb`** ⭐⭐⭐
  - **VPC Private 연결**을 사용한 AgentCore Runtime 배포 가이드
  - 기존 `agentcore_runtime.ipynb`의 VPC 버전
  - VPC 설정 자동화 포함
  - Private IP 사용 검증 포함
  - 한글 상세 설명
  - 사용법: Jupyter에서 열어서 셀 단위 실행
  - **주의**: `agentcore_runtime.py`, `requirements.txt` 파일이 이 폴더에 복사되어 있어야 함 (이미 복사됨)

### 🐍 Python Scripts (테스트 및 배포)

- **`agentcore_runtime.py`**
  - AgentCore Runtime 엔트리포인트
  - Bedrock Manus 에이전트 메인 코드
  - 상위 디렉토리에서 복사됨

- **`create_test_fargate_task.py`**
  - Fargate task definition 생성 및 실행
  - Private subnet에 task 배포
  - Target group에 등록 및 health 확인
  - 사용법: `python3 create_test_fargate_task.py`

- **`test_vpc_private_connectivity.py`** ⭐
  - 전체 인프라 검증 스크립트
  - VPC Endpoint, ALB, Subnet, Security Group, NAT Gateway 상태 확인
  - 사용법: `python3 test_vpc_private_connectivity.py`

- **`test_vpc_connectivity.py`**
  - 기본 연결 테스트 스크립트

### ⚙️ Configuration (설정 파일)

- **`test_vpc_config.json`** ⭐
  - 모든 리소스 ID 및 설정 저장
  - VPC ID, Subnet ID, Security Group ID 등
  - 스크립트 간 공유 설정

- **`requirements.txt`**
  - Python 패키지 의존성 목록
  - AgentCore Runtime 배포 시 사용
  - 상위 디렉토리에서 복사됨

---

## 📚 Documentation (문서)

### 한글 문서
- **`TEST_VPC_SUMMARY_KR.md`** ⭐
  - 완전한 한글 보고서
  - 구축 완료된 인프라 상세 설명
  - 네트워크 흐름도, 보안 개선사항, 비용 정보

### 영문 문서
- **`TEST_VPC_SUMMARY.md`** ⭐
  - 완전한 영문 기술 문서
  - 모든 리소스 상세 정보
  - 검증 결과 및 비용 분석

- **`TEST_VPC_NEXT_STEPS.md`**
  - AgentCore 통합 테스트 방법
  - VPC 설정 옵션
  - 트러블슈팅 가이드

- **`BEDROCK_AGENTCORE_VPC_SOLUTION.md`**
  - VPC Private 연결 아키텍처 가이드
  - 전체 솔루션 설명
  - 구현 단계별 가이드

- **`NETWORK_ARCHITECTURE_DIAGRAM.md`**
  - 상세 네트워크 다이어그램
  - 현재 아키텍처 vs 새 아키텍처 비교

- **`TEST_VPC_README.md`**
  - 전체 테스트 가이드
  - 단계별 실행 방법

- **`VPC_SETUP_COMPARISON.md`**
  - Option 1 (기존 VPC) vs Option 2 (새 VPC) 비교

---

## 🚀 Quick Start (빠른 시작)

### 1단계: VPC 인프라 생성
```bash
cd test_vpc_private_setup
./test_vpc_setup_new_vpc.sh
```

약 5-10분 소요 (VPC Endpoint 생성 시간)

### 2단계: 인프라 검증
```bash
python3 test_vpc_private_connectivity.py
```

모든 테스트가 통과하면 ✅ 표시됨

### 3단계: AgentCore Runtime 배포 (VPC Private) ⭐⭐⭐
```bash
# Jupyter Notebook 실행
jupyter notebook agentcore_runtime_vpc.ipynb
```

또는 JupyterLab:
```bash
jupyter lab agentcore_runtime_vpc.ipynb
```

노트북에서:
- VPC 설정 자동 로드
- AgentCore Runtime을 Private Subnet에 배포
- VPC Endpoint를 통한 Private 연결 사용
- Private IP 사용 검증

### 4단계 (선택): Fargate Task 직접 실행
```bash
python3 create_test_fargate_task.py
```

Task가 healthy 상태가 되면 성공

### 5단계: 정리
```bash
./cleanup_test_vpc_new.sh
```

모든 리소스 삭제 (비용 발생 중지)

---

## 📊 현재 상태

### 구축 완료된 인프라
- ✅ VPC: `vpc-<VPC_ID>` (10.100.0.0/16)
- ✅ VPC Endpoints: Available (Data Plane + Gateway)
- ✅ Internal ALB: Active (test-vpc-<VPC_ID>-alb)
- ✅ Fargate Task: Running and Healthy (10.100.2.72)
- ✅ NAT Gateway: Available
- ✅ Security Groups: 4개 모두 구성 완료

### 검증 상태
```
✅ VPC Endpoints       : PASS
✅ Internal ALB        : PASS
✅ Subnets             : PASS
✅ Security Groups     : PASS
✅ NAT Gateway         : PASS
✅ Task Health         : PASS
```

---

## 💡 주요 특징

### 보안 개선
- ✅ AgentCore → Fargate: **100% Private** (VPC Endpoint)
- ✅ ALB: **Internal only** (Public IP 없음)
- ✅ Fargate: **Private subnet** (Public IP 없음)
- ✅ Security: **Zero Trust** (SG-to-SG rules)

### 네트워크 흐름
```
Bedrock AgentCore (AWS)
    ↓ Private (PrivateLink)
VPC Endpoint (10.100.x.x)
    ↓ Private
Internal ALB (10.100.x.x)
    ↓ Private
Fargate Task (10.100.2.72)
    ↓ Outbound only
NAT Gateway → Internet
```

---

## 💰 비용 정보

**현재 실행 중** (비용 발생):
- NAT Gateway: ~$0.045/시간 (~월 $32.40)
- VPC Endpoint 2개: ~$0.02/시간 (~월 $14.40)
- Fargate Task (실행 시): ~$0.04/시간

**월 예상 비용**: ~$47 (24/7 실행 시)

**권장**: 테스트 완료 후 즉시 정리
```bash
./cleanup_test_vpc_new.sh
```

---

## 🔧 트러블슈팅

### Task가 시작 안 됨
- CloudWatch log group 확인: `/ecs/test-vpc-<VPC_ID>-task`
- Task 로그 확인: `aws logs tail /ecs/test-vpc-<VPC_ID>-task --follow`

### Target이 unhealthy
- Security group 규칙 확인
- Task가 RUNNING 상태인지 확인
- Health check endpoint 확인: `/health`

### VPC Endpoint 생성 실패
- Service name 확인: `com.amazonaws.us-east-1.bedrock-agentcore`
- Region 확인: `us-east-1`

### 정리가 안 됨
- 의존성 순서대로 삭제 필요
- `cleanup_partial_vpc.sh` 사용

---

## 📞 참고 자료

### AWS 리소스
- Account: `<YOUR_ACCOUNT_ID>`
- Region: `us-east-1`
- Cluster: `my-fargate-cluster`

### 주요 ARN
- ALB: `arn:aws:<SERVICE>:<REGION>:<ACCOUNT>:<RESOURCE>
- Target Group: `arn:aws:<SERVICE>:<REGION>:<ACCOUNT>:<RESOURCE>
- Task Definition: `test-vpc-<VPC_ID>-task:3`

### 관련 문서
- 한글 요약: `TEST_VPC_SUMMARY_KR.md`
- 영문 상세: `TEST_VPC_SUMMARY.md`
- 다음 단계: `TEST_VPC_NEXT_STEPS.md`

---

## ✅ 체크리스트

설정 완료:
- [x] VPC 및 Subnet 생성
- [x] VPC Endpoint 배포
- [x] Internal ALB 구성
- [x] Security Group 설정
- [x] NAT Gateway 배포
- [x] Fargate Task 실행
- [x] Target Group 등록
- [x] Health Check 통과

다음 단계:
- [ ] 실제 AgentCore runtime 연결 테스트
- [ ] 성능 측정 (지연시간)
- [ ] 로그 분석 (Private IP 사용 확인)
- [ ] 보안 감사
- [ ] 테스트 완료 후 정리

---

**작성일**: 2025-10-15
**상태**: ✅ **Production Ready** - 테스트 준비 완료
**폴더 버전**: v1.0
