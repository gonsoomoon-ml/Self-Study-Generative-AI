# VPC Setup Options Comparison

## 두 가지 테스트 환경 옵션

Bedrock AgentCore VPC Private 연결을 테스트하기 위한 두 가지 방법을 제공합니다.

---

## 📊 비교표

| 측면 | Option 1: 기존 VPC 사용 | Option 2: 새 VPC 생성 ⭐ |
|------|-------------------------|------------------------|
| **VPC** | Default VPC (vpc-ff5e1585) | 새 VPC (10.100.0.0/16) |
| **격리 수준** | 부분 격리 | 완전 격리 ✅ |
| **프로덕션 영향** | 동일 VPC (낮음) | 없음 ✅ |
| **설정 시간** | 5-7분 | 8-12분 |
| **비용** | ~$0.04/시간 | ~$0.09/시간 (+NAT Gateway) |
| **리소스 개수** | 8개 | 19개 |
| **Cleanup 난이도** | 쉬움 | 중간 (VPC 삭제 필요) |
| **추천 대상** | 빠른 테스트 | 완전 격리 선호 |

---

## Option 1: 기존 VPC 사용 (test_vpc_setup.sh)

### 📋 개요
Default VPC (vpc-ff5e1585)를 사용하여 테스트 환경을 구축합니다.

### 🏗️ 생성되는 리소스

```
기존 Default VPC (172.31.0.0/16)
├── Security Groups (3개) 🆕
│   ├── test-vpc-private-agentcore-sg
│   ├── test-vpc-private-alb-sg
│   └── test-vpc-private-fargate-sg
│
├── VPC Endpoints (2개) 🆕
│   ├── bedrock-agentcore (Data Plane)
│   └── bedrock-agentcore.gateway
│
├── Internal ALB 🆕
│   └── test-vpc-private-alb
│
└── Target Group 🆕
    └── test-vpc-private-tg
```

**총 리소스**: 8개 (모두 새로 생성)

### ✅ 장점

1. **빠른 구축**
   - VPC 생성 불필요
   - Subnets 이미 존재
   - 5-7분 완료

2. **비용 절감**
   - NAT Gateway 불필요
   - ~$0.04/시간 (~$1/일)

3. **간단한 Cleanup**
   - VPC는 그대로 유지
   - 생성한 리소스만 삭제
   - 2-3분 완료

4. **빠른 테스트**
   - 개념 증명용으로 적합
   - 기본 연결성 테스트 충분

### ⚠️ 단점

1. **부분 격리**
   - 프로덕션과 동일 VPC
   - 다른 리소스와 공존

2. **Security Group 복잡도**
   - 기존 SG와 혼재
   - 충돌 가능성 낮지만 존재

3. **Subnet 제한**
   - 기존 Public Subnets 사용
   - Private Subnet 설정 제한

### 💰 비용 (시간당)

```
VPC Endpoints (2개):     $0.02/hour
Internal ALB:            $0.0225/hour
─────────────────────────────────────
총계:                    ~$0.04/hour
```

**1일 테스트**: ~$1.00

### 🚀 실행 방법

```bash
# Setup
./test_vpc_setup.sh

# Test
python3 create_test_agentcore_runtime.py
python3 create_test_fargate_task.py
python3 test_vpc_connectivity.py

# Cleanup
./cleanup_test_vpc.sh
```

### 📝 적합한 경우

- ✅ 빠른 개념 증명 필요
- ✅ 비용 최소화
- ✅ 간단한 테스트만 수행
- ✅ VPC 생성/삭제 권한 없음

---

## Option 2: 새 VPC 생성 (test_vpc_setup_new_vpc.sh) ⭐ 추천

### 📋 개요
완전히 독립된 새 VPC (10.100.0.0/16)를 생성하여 격리된 테스트 환경을 구축합니다.

### 🏗️ 생성되는 리소스

```
새 VPC (10.100.0.0/16) 🆕
├── Subnets (4개) 🆕
│   ├── Private Subnet A (10.100.1.0/24, us-east-1a)
│   ├── Private Subnet B (10.100.2.0/24, us-east-1c)
│   ├── Public Subnet A (10.100.11.0/24, us-east-1a)
│   └── Public Subnet B (10.100.12.0/24, us-east-1c)
│
├── Network Components 🆕
│   ├── Internet Gateway
│   ├── NAT Gateway (in Public Subnet A)
│   ├── Elastic IP (for NAT)
│   ├── Public Route Table (0.0.0.0/0 → IGW)
│   └── Private Route Table (0.0.0.0/0 → NAT)
│
├── Security Groups (4개) 🆕
│   ├── test-vpc-private-agentcore-sg
│   ├── test-vpc-private-alb-sg
│   ├── test-vpc-private-fargate-sg
│   └── test-vpc-private-vpce-sg (VPC Endpoints용)
│
├── VPC Endpoints (2개) 🆕
│   ├── bedrock-agentcore (Data Plane)
│   └── bedrock-agentcore.gateway
│
├── Internal ALB 🆕
│   └── test-vpc-private-alb (Private Subnets에 배포)
│
└── Target Group 🆕
    └── test-vpc-private-tg
```

**총 리소스**: 19개 (모두 새로 생성)

### ✅ 장점

1. **완전한 격리** ⭐
   - 프로덕션 VPC와 100% 분리
   - 독립적인 네트워크 환경
   - 충돌 위험 없음

2. **프로덕션 유사 환경**
   - Private/Public Subnets
   - NAT Gateway 포함
   - 실제 프로덕션과 동일 구조

3. **자유로운 네트워크 설계**
   - CIDR 블록 선택 가능
   - Subnet 구성 커스터마이징
   - 라우팅 완전 제어

4. **완전한 Cleanup**
   - VPC 전체 삭제 가능
   - 흔적 없이 제거
   - 깨끗한 테스트

5. **프로덕션 마이그레이션 준비**
   - 실제 프로덕션 구조와 동일
   - 마이그레이션 시나리오 검증
   - 모범 사례 적용

### ⚠️ 단점

1. **더 긴 설정 시간**
   - VPC 생성: ~1분
   - NAT Gateway: ~2-3분
   - 총 8-12분 소요

2. **높은 비용**
   - NAT Gateway 추가: +$0.045/시간
   - ~$0.09/시간 (~$2/일)

3. **복잡한 Cleanup**
   - 리소스 의존성 순서 중요
   - NAT Gateway 삭제 대기 필요
   - 5-7분 소요

4. **더 많은 권한 필요**
   - VPC 생성/삭제
   - NAT Gateway 생성/삭제
   - Elastic IP 할당/해제

### 💰 비용 (시간당)

```
VPC:                     무료
Subnets:                 무료
Internet Gateway:        무료
NAT Gateway:             $0.045/hour  🆕
Elastic IP:              무료 (NAT에 연결 시)
Route Tables:            무료
VPC Endpoints (2개):     $0.02/hour
Internal ALB:            $0.0225/hour
─────────────────────────────────────
총계:                    ~$0.09/hour
```

**1일 테스트**: ~$2.16

### 🚀 실행 방법

```bash
# Setup (8-12분 소요)
./test_vpc_setup_new_vpc.sh

# Test
python3 create_test_agentcore_runtime.py
python3 create_test_fargate_task.py
python3 test_vpc_connectivity.py

# Cleanup (5-7분 소요)
./cleanup_test_vpc_new.sh
```

### 📝 적합한 경우

- ✅ **완전한 격리 필요** ⭐
- ✅ 프로덕션 유사 환경 검증
- ✅ 네트워크 구조 실험
- ✅ 마이그레이션 시뮬레이션
- ✅ 여러 번 반복 테스트
- ✅ 보안 컴플라이언스 검증

---

## 🎯 추천 시나리오별 선택

### Scenario 1: 빠른 개념 증명
**→ Option 1 (기존 VPC)**

```
목표: Bedrock AgentCore VPC 모드가 작동하는지 확인
시간: 1시간
비용: $0.04
```

### Scenario 2: 완전한 격리 테스트 ⭐
**→ Option 2 (새 VPC)**

```
목표: 프로덕션과 완전히 분리된 환경에서 테스트
시간: 2-3시간
비용: $0.18-0.27
```

### Scenario 3: 프로덕션 마이그레이션 준비 ⭐
**→ Option 2 (새 VPC)**

```
목표: 실제 프로덕션 구조 시뮬레이션
시간: 1-2일
비용: ~$4-5
```

### Scenario 4: 교육/워크샵
**→ Option 2 (새 VPC)**

```
목표: 완전한 VPC 아키텍처 이해
시간: 반나절
비용: ~$1
```

---

## 📋 상세 실행 타임라인

### Option 1: 기존 VPC (5-7분)

```
00:00 - Step 1: Security Groups 생성 (30초)
00:30 - Step 2: SG Rules 설정 (20초)
00:50 - Step 3: VPC Endpoints 생성 (3-5분) ⏳
05:50 - Step 4: Internal ALB 생성 (1분)
06:50 - Step 5-8: Target Group, Listener, Config (20초)
07:10 - ✅ 완료
```

### Option 2: 새 VPC (8-12분)

```
00:00 - Step 1: VPC 생성 (10초)
00:10 - Step 2: Internet Gateway 생성 (10초)
00:20 - Step 3: Subnets 생성 (20초)
00:40 - Step 4: Route Tables 생성 (20초)
01:00 - Step 5: NAT Gateway 생성 (2-3분) ⏳
04:00 - Step 6-7: Security Groups (40초)
04:40 - Step 8: VPC Endpoints 생성 (3-5분) ⏳
09:40 - Step 9-13: ALB, TG, Config (1분)
10:40 - ✅ 완료
```

---

## 🔄 마이그레이션 경로

### 테스트 → 프로덕션

**Option 1 사용 시:**
```
1. Option 1로 개념 증명 (1시간)
2. Option 2로 완전 테스트 (1일)
3. 프로덕션 VPC에 적용
```

**Option 2 사용 시:**
```
1. Option 2로 완전 테스트 (1일)
2. 프로덕션 VPC에 직접 적용
   (구조가 동일하므로 바로 적용 가능)
```

---

## 🎓 학습 목적별 선택

### 초보자 (VPC 처음 접함)
**→ Option 1**
- 기본 개념 이해
- 빠른 성공 경험
- 이후 Option 2로 진행

### 중급자 (VPC 경험 있음)
**→ Option 2**
- 완전한 VPC 구조 이해
- NAT Gateway 개념 학습
- 프로덕션 준비

### 고급자 (프로덕션 배포 예정)
**→ Option 2**
- 프로덕션 시뮬레이션
- 보안 검증
- 성능 테스트

---

## 💡 팁 및 권장사항

### Option 1을 선택했다면

```bash
# 빠른 테스트에 집중
./test_vpc_setup.sh
python3 create_test_agentcore_runtime.py
python3 test_vpc_connectivity.py

# 기본 연결성만 확인
# 필요 시 Option 2로 업그레이드
```

### Option 2를 선택했다면

```bash
# 완전한 환경 구축
./test_vpc_setup_new_vpc.sh

# NAT Gateway 대기 중 문서 읽기
# - NETWORK_ARCHITECTURE_DIAGRAM.md
# - TEST_VPC_README.md

# 완료 후 철저한 테스트
python3 create_test_agentcore_runtime.py
python3 create_test_fargate_task.py
python3 test_vpc_connectivity.py

# 네트워크 플로우 검증
# VPC Flow Logs 활성화 권장
```

---

## 🔍 의사결정 플로우차트

```
시작
  │
  ├─ 빠른 테스트만 필요? ─ YES → Option 1
  │                      └ NO ↓
  │
  ├─ 프로덕션과 완전 격리 필요? ─ YES → Option 2
  │                            └ NO ↓
  │
  ├─ 비용 민감? ─ YES → Option 1
  │             └ NO ↓
  │
  ├─ NAT Gateway 필요? ─ YES → Option 2
  │                     └ NO → Option 1
  │
  └─ 마이그레이션 준비 중? ─ YES → Option 2
                          └ NO → Option 1
```

---

## 📞 FAQ

### Q1: Option 1에서 Option 2로 전환 가능한가요?
**A:** 네! 언제든지 가능합니다.
```bash
# Option 1 cleanup
./cleanup_test_vpc.sh

# Option 2 setup
./test_vpc_setup_new_vpc.sh
```

### Q2: 두 환경을 동시에 실행 가능한가요?
**A:** 아니요. `test_vpc_config.json` 파일이 덮어씌워집니다.
하나를 완료하고 cleanup 후 다른 것을 실행하세요.

### Q3: 프로덕션에는 어떤 것을 권장하나요?
**A:** Option 2 구조를 권장합니다.
- 완전한 격리
- Private Subnets 사용
- NAT Gateway로 아웃바운드 제어
- 프로덕션 베스트 프랙티스

### Q4: NAT Gateway 없이 Option 2 가능한가요?
**A:** 가능하지만 비권장.
- Fargate가 ECR 이미지 pull 불가
- S3 접근 불가 (VPC Endpoint 필요)
- 테스트 제약 발생

### Q5: 비용을 더 줄일 수 있나요?
**A:** 예:
- Option 1 사용
- NAT Gateway 대신 VPC Endpoints 추가 (S3, ECR)
- 짧은 테스트 (1-2시간)
- 즉시 cleanup

---

## 🎯 최종 권장사항

### 대부분의 경우: Option 2 (새 VPC) ⭐⭐⭐

**이유:**
1. **완전한 격리** - 프로덕션 영향 없음
2. **프로덕션 유사** - 실제 환경 시뮬레이션
3. **안전한 실험** - 자유로운 테스트
4. **깨끗한 Cleanup** - 흔적 없이 제거

**추가 비용**:
- +$1.16/일 (NAT Gateway)
- 완전한 격리와 안전성을 고려하면 합리적

### 빠른 검증만 필요: Option 1 (기존 VPC) ⭐

**이유:**
1. **빠른 설정** - 5-7분
2. **저렴한 비용** - ~$1/일
3. **간단한 Cleanup** - 2-3분

**제한사항**:
- 부분 격리
- 프로덕션과 동일 VPC

---

## 📚 관련 문서

- `TEST_VPC_README.md` - 상세 사용 가이드
- `NETWORK_ARCHITECTURE_DIAGRAM.md` - 네트워크 다이어그램
- `BEDROCK_AGENTCORE_VPC_SOLUTION.md` - VPC 솔루션 가이드

---

**준비되셨나요?**

새 VPC로 시작하려면:
```bash
./test_vpc_setup_new_vpc.sh
```

기존 VPC로 시작하려면:
```bash
./test_vpc_setup.sh
```

**Happy Testing! 🚀**
