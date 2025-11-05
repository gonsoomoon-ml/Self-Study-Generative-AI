# 🎉 Bedrock AgentCore VPC Private 연결 완벽 솔루션

> **대박 소식!** AWS가 2025년 9월에 Bedrock AgentCore의 VPC 및 PrivateLink 지원을 발표했습니다!

**공식 발표**: [Amazon Bedrock AgentCore Runtime, Browser, and Code Interpreter add support for VPC, AWS PrivateLink, CloudFormation, and tagging](https://aws.amazon.com/about-aws/whats-new/2025/09/amazon-bedrock-agentcore-runtime-browser-code-interpreter-vpc-privatelink-cloudformation-tagging/)

---

## 📊 가능한 두 가지 접근 방식

### 방식 1: AgentCore Runtime을 사용자 VPC에서 실행 ⭐⭐⭐ (Best!)

**개요**: AgentCore Runtime을 사용자 VPC의 Private Subnet에서 실행하도록 구성

**아키텍처**:
```
AgentCore Runtime (Your VPC Private Subnet)
    ↓ (Private IP)
Internal ALB/NLB (Your VPC)
    ↓ (Private IP)
Fargate Tasks (Your VPC Private Subnet)
```

**구성 방법**:

#### 1. AWS CLI로 VPC 모드 Runtime 생성
```bash
aws bedrock-agentcore create-runtime \
  --runtime-name "MyPrivateAgentRuntime" \
  --region us-east-1 \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "subnets": [
        "subnet-0123456789abcdef0",
        "subnet-0123456789abcdef1"
      ],
      "securityGroups": ["sg-0123456789abcdef0"]
    }
  }'
```

#### 2. 사전 요구사항
- ✅ Amazon VPC with private subnets
- ✅ Multiple Availability Zones (고가용성)
- ✅ Security Groups configured
- ✅ IAM permissions for service-linked role `AWSServiceRoleForBedrockAgentCoreNetwork`

#### 3. ALB를 Internal로 변경
```bash
# 현재 internet-facing ALB를 internal로 변경하려면 새로 생성 필요
aws elbv2 create-load-balancer \
  --name fargate-alb-internal \
  --type application \
  --scheme internal \
  --subnets subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-groups sg-0123456789abcdef0
```

#### 4. Security Group 구성
```bash
# AgentCore Runtime Security Group
# Outbound: ALB로의 HTTP/HTTPS 허용
aws ec2 authorize-security-group-egress \
  --group-id sg-agentcore-runtime \
  --protocol tcp \
  --port 80 \
  --source-group sg-internal-alb

# Internal ALB Security Group
# Inbound: AgentCore Runtime에서만 허용
aws ec2 authorize-security-group-ingress \
  --group-id sg-internal-alb \
  --protocol tcp \
  --port 80 \
  --source-group sg-agentcore-runtime
```

#### 5. Runtime 업데이트 (기존 Runtime 있는 경우)
```python
import boto3

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

response = client.update_runtime(
    runtimeId='your-runtime-id',
    networkConfiguration={
        'networkMode': 'VPC',
        'networkModeConfig': {
            'subnets': [
                'subnet-0123456789abcdef0',
                'subnet-0123456789abcdef1'
            ],
            'securityGroups': ['sg-0123456789abcdef0']
        }
    }
)
```

**장점**:
- ✅ **완전한 Private 연결** - Public IP 불필요
- ✅ AgentCore와 Fargate가 같은 VPC에서 실행
- ✅ 인터넷 노출 없음
- ✅ 최고 수준의 보안

**단점**:
- ⚠️ 기존 Runtime 재구성 필요
- ⚠️ Internal ALB로 변경 (새로 생성 필요)

---

### 방식 2: VPC Endpoint (PrivateLink) 사용

**개요**: VPC Endpoint를 통해 Bedrock AgentCore 서비스에 Private 접근

**아키텍처**:
```
Your Resources (VPC Private Subnet)
    ↓ (Private IP)
VPC Endpoint (com.amazonaws.region.bedrock-agentcore)
    ↓ (AWS PrivateLink)
Bedrock AgentCore Service (AWS Managed)
```

**Service Names**:
- **Data Plane**: `com.amazonaws.us-east-1.bedrock-agentcore`
- **Gateway**: `com.amazonaws.us-east-1.bedrock-agentcore.gateway`

**구성 방법**:

#### 1. VPC Endpoint 생성 (AWS Console)
1. VPC Console → Endpoints → Create Endpoint
2. Service category: AWS services
3. Service name: `com.amazonaws.us-east-1.bedrock-agentcore`
4. VPC: 사용자 VPC 선택
5. Subnets: Private subnets 선택 (multiple AZs)
6. Security Groups: 적절한 SG 선택
7. Enable Private DNS: ✅ 체크

#### 2. VPC Endpoint 생성 (AWS CLI)
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.bedrock-agentcore \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0 \
  --private-dns-enabled
```

#### 3. Gateway용 VPC Endpoint 추가 생성
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.bedrock-agentcore.gateway \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0 \
  --private-dns-enabled
```

#### 4. Endpoint Policy 구성 (선택사항)
```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::057716757052:root"
      },
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime",
        "bedrock-agentcore:InvokeGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

**장점**:
- ✅ 간단한 구성
- ✅ 기존 Runtime 변경 불필요 (추가 옵션)
- ✅ Private DNS 지원

**단점**:
- ⚠️ AgentCore → Your ALB 연결은 여전히 Public (방식 1과 함께 사용 필요)
- ⚠️ VPC Endpoint 비용 추가

---

## 🎯 권장 구성: 방식 1 + 방식 2 조합 ⭐⭐⭐

**완벽한 Private 아키텍처**:

```
┌─────────────────────────────────────────────────────────────┐
│                        Your VPC                              │
│                                                               │
│  ┌─────────────────────┐                                    │
│  │ Private Subnet AZ-A │                                    │
│  │                     │                                    │
│  │  AgentCore Runtime  │ ──┐                               │
│  │  (VPC Mode)         │   │                               │
│  └─────────────────────┘   │                               │
│                             │ Private IP                     │
│  ┌─────────────────────┐   │                               │
│  │ Private Subnet AZ-B │   │                               │
│  │                     │   ↓                               │
│  │  ┌──────────────┐  │  ┌──────────────────┐            │
│  │  │ Fargate Task │←─┼──│ Internal ALB     │            │
│  │  └──────────────┘  │  └──────────────────┘            │
│  │                     │                                    │
│  └─────────────────────┘                                    │
│                                                               │
│  ┌────────────────────────────────────┐                     │
│  │ VPC Endpoint (PrivateLink)         │                     │
│  │ com.amazonaws.us-east-1.bedrock-   │                     │
│  │ agentcore                           │                     │
│  └────────────────────────────────────┘                     │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         │ AWS PrivateLink
                         ↓
        ┌─────────────────────────────┐
        │ Bedrock AgentCore Service   │
        │ (AWS Managed)                │
        └─────────────────────────────┘
```

**구성 단계**:

1. **VPC Endpoint 생성** (Bedrock 서비스 접근용)
2. **AgentCore Runtime을 VPC 모드로 생성/업데이트**
3. **Internal ALB 생성** (기존 internet-facing ALB 교체)
4. **Security Groups 구성** (AgentCore ↔ ALB ↔ Fargate)
5. **NAT Gateway** (선택, 인터넷 접근 필요 시)

---

## 📋 구현 체크리스트

### Phase 1: VPC 인프라 준비
- [ ] VPC와 Private Subnets 확인 (multiple AZs)
- [ ] Security Groups 생성 및 구성
- [ ] IAM 권한 확인 (AWSServiceRoleForBedrockAgentCoreNetwork)

### Phase 2: VPC Endpoint 생성
- [ ] Bedrock AgentCore Data Plane VPC Endpoint 생성
- [ ] Bedrock AgentCore Gateway VPC Endpoint 생성
- [ ] Private DNS 활성화
- [ ] Endpoint Policy 구성

### Phase 3: Internal ALB 생성
- [ ] Internal ALB 생성 (scheme: internal)
- [ ] Target Group 생성 (IP type)
- [ ] Listener 구성 (HTTP/HTTPS)
- [ ] Health Check 구성

### Phase 4: AgentCore Runtime VPC 구성
- [ ] 새 Runtime 생성 (VPC 모드) 또는 기존 Runtime 업데이트
- [ ] Network Configuration 적용 (subnets, security groups)
- [ ] Runtime 테스트 및 검증

### Phase 5: Fargate 업데이트
- [ ] `global_fargate_coordinator.py` 업데이트:
  - Public ALB URL → Internal ALB URL
  - `alb_dns` 변수 업데이트
- [ ] Security Group 업데이트 (Internal ALB에서 Fargate로)
- [ ] Session Manager 로직 검증

### Phase 6: 테스트 및 검증
- [ ] AgentCore Runtime → Internal ALB 연결 테스트
- [ ] Internal ALB → Fargate 연결 테스트
- [ ] End-to-end workflow 테스트
- [ ] 로그 확인 (Private IP 사용 확인)

---

## 🔧 코드 변경 사항

### 1. `src/tools/global_fargate_coordinator.py` 업데이트

```python
# Before (Public ALB)
ALB_DNS = "fargate-alb-057716757052.us-east-1.elb.amazonaws.com"
BASE_URL = f"http://{ALB_DNS}"

# After (Internal ALB)
INTERNAL_ALB_DNS = "fargate-alb-internal.us-east-1.elb.amazonaws.com"  # Internal ALB
BASE_URL = f"http://{INTERNAL_ALB_DNS}"

# 또는 HTTPS 사용
BASE_URL = f"https://{INTERNAL_ALB_DNS}"
```

### 2. Runtime 생성 스크립트

```python
# create_vpc_runtime.py
import boto3

def create_vpc_agentcore_runtime():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')

    response = client.create_runtime(
        runtimeName='InsightExtractorRuntime',
        networkConfiguration={
            'networkMode': 'VPC',
            'networkModeConfig': {
                'subnets': [
                    'subnet-0123456789abcdef0',  # Private Subnet AZ-A
                    'subnet-0123456789abcdef1'   # Private Subnet AZ-B
                ],
                'securityGroups': ['sg-agentcore-runtime']
            }
        },
        tags={
            'Environment': 'Production',
            'Project': 'InsightExtractor'
        }
    )

    print(f"Runtime created: {response['runtimeId']}")
    print(f"Runtime ARN: {response['runtimeArn']}")
    return response

if __name__ == '__main__':
    create_vpc_agentcore_runtime()
```

### 3. VPC Endpoint 생성 스크립트

```bash
#!/bin/bash
# create_vpc_endpoints.sh

VPC_ID="vpc-0123456789abcdef0"
SUBNET1="subnet-0123456789abcdef0"
SUBNET2="subnet-0123456789abcdef1"
SG_ID="sg-0123456789abcdef0"
REGION="us-east-1"

# Data Plane VPC Endpoint
aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore \
  --subnet-ids $SUBNET1 $SUBNET2 \
  --security-group-ids $SG_ID \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=bedrock-agentcore-data-plane}]'

# Gateway VPC Endpoint
aws ec2 create-vpc-endpoint \
  --region $REGION \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.$REGION.bedrock-agentcore.gateway \
  --subnet-ids $SUBNET1 $SUBNET2 \
  --security-group-ids $SG_ID \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=bedrock-agentcore-gateway}]'

echo "VPC Endpoints created successfully!"
```

---

## 💰 비용 고려사항

### VPC Endpoint 비용 (us-east-1)
- **Endpoint 시간당 비용**: $0.01/시간/AZ × 2 AZ = $0.02/시간
- **데이터 처리 비용**: $0.01/GB
- **월간 예상 비용**: ~$15-20 (endpoint 비용) + 데이터 전송

### NAT Gateway 비용 (선택사항)
- **시간당 비용**: $0.045/시간
- **데이터 처리 비용**: $0.045/GB
- **월간 예상 비용**: ~$33 (NAT) + 데이터 전송

### 절감 효과
- ❌ **제거 가능**: NAT Gateway (AgentCore가 VPC 내부에서 실행되면 불필요)
- ✅ **유지 필요**: VPC Endpoint (Bedrock 서비스 접근용)
- ✅ **보안 향상** + **컴플라이언스 요구사항 충족**

---

## 🚨 중요 제한사항

### Region 지원
현재 지원 Region (2025년 기준):
- ✅ US East (N. Virginia) - `us-east-1`
- ✅ US West (Oregon) - `us-west-2`
- ✅ Asia Pacific (Sydney) - `ap-southeast-2`
- ✅ Europe (Frankfurt) - `eu-central-1`

**주의**: 사용자의 현재 Region (`us-east-1`)은 지원됩니다! ✅

### 네트워크 제한
- **Inbound 트래픽**: VPC를 통해 라우팅되지 않음
- **Outbound 트래픽**: VPC를 통해 라우팅됨
- **Public Subnets**: 인터넷 연결 제공 안 함 (NAT Gateway 필요)

### Control Plane
- ⚠️ **Control Plane Endpoints는 PrivateLink 미지원**
- Management 작업은 여전히 Public Endpoint 사용

---

## 📚 참고 문서

### AWS 공식 문서
1. [VPC connectivity for Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)
2. [VPC interface endpoints (AWS PrivateLink)](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/vpc-interface-endpoints.html)
3. [AWS Blog: Secure ingress connectivity to Amazon Bedrock AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/secure-ingress-connectivity-to-amazon-bedrock-agentcore-gateway-using-interface-vpc-endpoints/)

### GitHub 샘플
- [aws-samples/amazon-bedrock-vpc-endpoints](https://github.com/aws-samples/amazon-bedrock-vpc-endpoints)

---

## 🎯 다음 단계

1. **즉시 시작 가능**: VPC와 Private Subnets 확인
2. **Phase 1 구현**: VPC Endpoint 생성 (15분)
3. **Phase 2 구현**: Internal ALB 생성 (30분)
4. **Phase 3 구현**: AgentCore Runtime VPC 모드 구성 (30분)
5. **Phase 4 테스트**: End-to-end Private 연결 검증

**총 예상 시간**: 2-3시간

---

## ✅ 결론

**네, 가능합니다!** AWS가 2025년 9월에 발표한 VPC 지원 덕분에 Bedrock AgentCore를 완전히 Private 환경에서 실행할 수 있습니다.

**최상의 아키텍처**:
1. AgentCore Runtime을 VPC 모드로 구성
2. Internal ALB 사용
3. VPC Endpoint로 Bedrock 서비스 접근
4. 완전한 Private 연결 (Public IP 불필요)

**보안 효과**:
- ✅ 인터넷 노출 제거
- ✅ VPC 레벨 격리
- ✅ Security Group으로 세밀한 제어
- ✅ 컴플라이언스 요구사항 충족

지금 바로 구현 가능합니다! 🚀
