# Bedrock AgentCore VPC 모드 배포 - 최종 정리

**날짜**: 2025-10-18
**Runtime ID**: bedrock_manus_runtime_vpc-cRZMLaFTr6
**최종 상태**: UPDATE_FAILED (Version 8)

---

## 📋 요약

가이드 문서 (https://claude.ai/public/artifacts/6a6d3bc2-7612-4399-a173-e43b731ad5da)를 기반으로 모든 필수 인프라를 구축했으나, 기존 PUBLIC 모드 Runtime을 VPC 모드로 마이그레이션하는데 실패했습니다.

---

## ✅ 완료된 작업

### 1. 가용 영역(AZ) 검증
```bash
✅ subnet-0b2fb367d6e823a79: us-east-1a (use1-az2) - 지원됨
✅ subnet-0ed3a6040386768cf: us-east-1c (use1-az6) - 지원됨
```
- 가이드의 지원 AZ 목록 (use1-az1, use1-az2, use1-az4, use1-az6)에 포함
- IP 주소 충분 (248, 246개 available)

### 2. VPC DNS 설정
```bash
✅ DNS Hostnames: Enabled
✅ DNS Support: Enabled
```

### 3. Service-Linked Role
```bash
✅ Role exists: AWSServiceRoleForBedrockAgentCoreNetwork
```
- 서비스: `network.bedrock-agentcore.amazonaws.com`

### 4. 필수 VPC 엔드포인트 생성

모든 필수 엔드포인트를 생성하고 `available` 상태로 확인:

| 엔드포인트 | ID | 상태 | 타입 |
|-----------|-----|------|------|
| ECR API | vpce-039416a0eccab0c78 | available | Interface |
| ECR Docker | vpce-08bd4278d0dd8779d | available | Interface |
| CloudWatch Logs | vpce-0d55a82f7b038ae04 | available | Interface |
| S3 Gateway | vpce-06d422d1c6e63afac | available | Gateway |
| AgentCore | vpce-0b1c05f284838d951 | available | Interface |
| AgentCore Gateway | vpce-00259de820f493d28 | available | Interface |

모든 Interface 엔드포인트 설정:
- Security Group: `sg-0affaea9ac4dc26b1` (AgentCore SG)
- Subnets: Private subnets (us-east-1a, us-east-1c)
- Private DNS: Enabled

### 5. 네트워크 인프라

✅ **Route Tables**:
```bash
# Private Route Table (rtb-03f767343ef0bfe88)
10.100.0.0/16 → local
0.0.0.0/0 → nat-084c84d8f7ab9ac5c (NAT Gateway)
```

✅ **Security Groups**:
- Inbound: VPC Endpoint SG + Self-referencing
- Outbound: HTTP 80, HTTPS 443, All traffic (0.0.0.0/0)

✅ **NAT Gateway**:
- ID: nat-084c84d8f7ab9ac5c
- State: available

---

## ❌ 여전히 실패하는 이유

### 시도한 업데이트 (8번째 버전)
```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id bedrock_manus_runtime_vpc-cRZMLaFTr6 \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": ["subnet-0b2fb367d6e823a79", "subnet-0ed3a6040386768cf"]
    }
  }'
```

**결과**: 즉시 `UPDATE_FAILED`

### 가능한 원인 분석

#### 1. **PUBLIC → VPC 마이그레이션 미지원** (가장 가능성 높음)
- 가이드의 모든 예제가 `create-agent-runtime` 사용 (신규 생성)
- `update-agent-runtime`으로 네트워크 모드 변경 불가능할 수 있음
- AWS 문서에서 명시적으로 확인 필요

#### 2. **Hidden Prerequisites**
- 계정 레벨 feature flag 필요
- AWS Support 케이스를 통한 활성화 필요
- 서비스 쿼터 문제

#### 3. **Beta/Limited Availability**
- VPC 지원이 2025년 9월 발표된 신기능
- us-east-1에서 제한적 가용성
- 특정 AWS 계정만 지원

#### 4. **Container Image 접근 불가**
- VPC 모드에서 ECR 이미지를 가져오는 과정에서 실패
- 엔드포인트는 있지만 실제 연결 안 됨
- 하지만 CloudWatch 로그 전혀 없음 (이상함)

---

## 🎯 권장 조치

### Option 1: 새로운 Runtime을 VPC 모드로 생성 (권장)

기존 Runtime 업데이트 대신 **새로운 Runtime을 처음부터 VPC 모드로 생성**:

```bash
# test_vpc_private_setup 폴더에서 실행
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "bedrock_manus_runtime_vpc_new" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "057716757052.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-bedrock_manus_runtime_vpc:latest"
    }
  }' \
  --role-arn "arn:aws:iam::057716757052:role/agentcore-bedrock_manus_runtime-role" \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "securityGroups": ["sg-0affaea9ac4dc26b1"],
      "subnets": ["subnet-0b2fb367d6e823a79", "subnet-0ed3a6040386768cf"]
    }
  }' \
  --region us-east-1
```

**장점**:
- 가이드의 모든 예제가 이 방법 사용
- PUBLIC → VPC 마이그레이션 문제 회피
- 기존 PUBLIC Runtime은 유지 (롤백 가능)

**단점**:
- 새로운 Runtime ID 생성됨
- 기존 세션/로그 히스토리 없음

### Option 2: AWS Support 문의

**주제**: "Bedrock AgentCore PUBLIC to VPC migration UPDATE_FAILED"

**포함 내용**:
- Runtime ID: `bedrock_manus_runtime_vpc-cRZMLaFTr6`
- 시도한 업데이트: 8번 (모두 UPDATE_FAILED)
- 완료된 인프라:
  - ✅ 지원되는 AZ (use1-az2, use1-az6)
  - ✅ VPC DNS 활성화
  - ✅ Service-Linked Role 존재
  - ✅ 모든 필수 VPC 엔드포인트 (ECR, S3, Logs, AgentCore)
  - ✅ NAT Gateway, Route Tables
  - ✅ Security Groups
- 질문:
  1. PUBLIC → VPC 마이그레이션이 지원되는가?
  2. UPDATE_FAILED에 에러 상세가 없는 이유는?
  3. CloudWatch 로그가 비어있는 이유는?
  4. 계정에서 VPC 모드가 활성화되어 있는가?

### Option 3: PUBLIC 모드 유지 (임시 해결책)

- 현재 프로덕션 Runtime (`bedrock_manus_runtime-E8I6oFGlTA`) 정상 작동 중
- VPC 모드가 기능적으로 필수는 아님
- VPC 지원 성숙될 때까지 대기

---

## 📊 생성된 VPC 리소스

### VPC 엔드포인트 (6개)
```bash
# 새로 생성 (2025-10-18)
vpce-039416a0eccab0c78  # ECR API
vpce-08bd4278d0dd8779d  # ECR Docker
vpce-0d55a82f7b038ae04  # CloudWatch Logs
vpce-06d422d1c6e63afac  # S3 Gateway

# 기존 (2025-10-15)
vpce-0b1c05f284838d951  # Bedrock AgentCore
vpce-00259de820f493d28  # Bedrock AgentCore Gateway
```

### 월간 비용 예상
- NAT Gateway: ~$32.40/월
- VPC Endpoint 6개: ~$43.20/월 (Interface 5개)
- **총 ~$76/월**

**참고**: 테스트 완료 후 cleanup 스크립트 실행 권장

---

## 📝 학습 내용

### 1. AZ Name vs AZ ID
- AZ 이름 (us-east-1a)과 AZ ID (use1-az1)는 다름
- AgentCore는 특정 AZ ID만 지원
- 계정마다 AZ 매핑이 다를 수 있음

### 2. 필수 VPC 엔드포인트
VPC 모드 Runtime에 다음 엔드포인트 필수:
- ECR API & Docker (컨테이너 이미지 가져오기)
- S3 (ECR 레이어 다운로드)
- CloudWatch Logs (로깅)
- AgentCore Gateway (제어 플레인)

### 3. Service-Linked Role
- Role 이름: `AWSServiceRoleForBedrockAgentCoreNetwork`
- 서비스: `network.bedrock-agentcore.amazonaws.com`
- 자동 생성되지만 수동 생성 가능

### 4. 마이그레이션 vs 신규 생성
- 가이드는 모두 `create-agent-runtime` 사용
- `update-agent-runtime`으로 네트워크 모드 변경은 문서화되지 않음
- 신규 생성이 더 안전한 접근일 수 있음

---

## 🔗 참고 자료

- **완벽 가이드**: https://claude.ai/public/artifacts/6a6d3bc2-7612-4399-a173-e43b731ad5da
- **VPC 지원 발표**: https://aws.amazon.com/about-aws/whats-new/2025/09/bedrock-agentcore-vpc-privatelink/
- **이전 분석**: `VPC_MODE_UPDATE_FAILED_ANALYSIS.md`
- **Test VPC 문서**: `test_vpc_private_setup/TEST_VPC_SUMMARY_KR.md`

---

## ✅ 다음 단계

1. **새로운 Runtime 생성 시도** (VPC 모드로)
   ```bash
   cd test_vpc_private_setup
   # create-agent-runtime 명령 실행
   ```

2. **성공 시**:
   - 기존 PUBLIC Runtime 삭제 또는 유지
   - Production 트래픽 점진적 이동

3. **실패 시**:
   - AWS Support 케이스 생성
   - PUBLIC 모드로 계속 운영

4. **Cleanup** (테스트 완료 후):
   ```bash
   cd test_vpc_private_setup
   ./cleanup_test_vpc_new.sh
   ```

---

**최종 상태**: 모든 필수 인프라 준비 완료, 하지만 PUBLIC → VPC 마이그레이션 실패
**권장 사항**: 새로운 Runtime을 VPC 모드로 생성 시도
**대안**: PUBLIC 모드 유지 (안정적 작동 중)
