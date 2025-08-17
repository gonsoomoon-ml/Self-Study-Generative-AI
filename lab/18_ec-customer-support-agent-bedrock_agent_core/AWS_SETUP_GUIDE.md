# 🚀 AWS 인프라 설정 가이드

한국 패션/뷰티 이커머스 고객 지원 에이전트를 실행하기 위해 필요한 AWS 인프라를 설정하는 방법입니다.

## 📋 사전 요구사항

### AWS 설정
- AWS CLI 구성 완료 (`aws configure`)
- 다음 AWS 서비스에 대한 권한:
  - CloudFormation (스택 생성/삭제)
  - S3 (버킷 생성, 객체 업로드)
  - Lambda (함수 생성)
  - DynamoDB (테이블 생성)
  - Cognito (User Pool 생성)
  - IAM (역할 생성)
  - SSM (파라미터 생성)

### 모델 액세스
- Amazon Bedrock에서 **Claude 3.7 Sonnet** 모델 활성화 필요
- 모델 액세스: [Bedrock Console > Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)

## 🛠️ 자동 배포 방법

### 방법 1: Jupyter 노트북에서 실행 (권장)

1. **노트북 실행**:
   ```bash
   cd /home/ubuntu/Self-Study-Generative-AI/lab/18_ec-customer-support-agent-bedrock_agent_core/use_cases/customer_support/notebooks/
   jupyter lab
   ```

2. **lab-03-agentcore-gateway.ipynb** 노트북 열기

3. **인프라 배포 셀 실행**: 노트북 상단의 "AWS 인프라 자동 배포" 셀 실행

### 방법 2: 터미널에서 직접 실행

```bash
cd /home/ubuntu/Self-Study-Generative-AI/lab/18_ec-customer-support-agent-bedrock_agent_core/
./scripts/prereq.sh
```

## 📦 생성되는 AWS 리소스

### CloudFormation 스택 (2개)
- `EcommerceCustomerSupportStackInfra`: 기본 인프라
- `EcommerceCustomerSupportStackCognito`: 인증 시스템

### 주요 리소스
| 리소스 타입 | 개수 | 용도 |
|------------|------|------|
| S3 버킷 | 1개 | Lambda 코드 저장 |
| Lambda 함수 | 1개 | 반품 자격 검증 API |
| DynamoDB 테이블 | 2개 | 고객 프로필, 주문 데이터 |
| Cognito User Pool | 1개 | OAuth 인증 |
| IAM 역할 | 3개 | Lambda, Gateway, Runtime 권한 |
| SSM 파라미터 | 12개 | 구성 정보 저장 |

## 🔍 배포 확인

### 1. CloudFormation 스택 상태 확인
```bash
aws cloudformation describe-stacks --stack-name EcommerceCustomerSupportStackInfra
aws cloudformation describe-stacks --stack-name EcommerceCustomerSupportStackCognito
```

### 2. SSM 파라미터 확인
```bash
aws ssm get-parameters-by-path --path "/app/ecommerce/agentcore" --output table
```

### 3. Lambda 함수 확인
```bash
aws lambda list-functions --query 'Functions[?contains(FunctionName, `EcommerceCustomer`)]'
```

## 📋 생성된 SSM 파라미터 목록

```
/app/ecommerce/agentcore/cognito_auth_scope      # OAuth 스코프
/app/ecommerce/agentcore/cognito_auth_url        # OAuth 인증 URL
/app/ecommerce/agentcore/cognito_discovery_url   # OpenID 구성 URL
/app/ecommerce/agentcore/cognito_domain          # Cognito 도메인
/app/ecommerce/agentcore/cognito_token_url       # OAuth 토큰 URL
/app/ecommerce/agentcore/gateway_iam_role        # Gateway IAM 역할
/app/ecommerce/agentcore/lambda_arn              # Lambda 함수 ARN
/app/ecommerce/agentcore/machine_client_id       # 머신 클라이언트 ID
/app/ecommerce/agentcore/runtime_iam_role        # Runtime IAM 역할
/app/ecommerce/agentcore/userpool_id             # Cognito User Pool ID
/app/ecommerce/agentcore/web_client_id           # 웹 클라이언트 ID
```

## 🧹 리소스 정리

실습 완료 후 AWS 리소스를 정리하려면:

```bash
# CloudFormation 스택 삭제
aws cloudformation delete-stack --stack-name EcommerceCustomerSupportStackCognito
aws cloudformation delete-stack --stack-name EcommerceCustomerSupportStackInfra

# S3 버킷 정리 (버킷 이름은 실제 생성된 이름으로 변경)
aws s3 rm s3://ecommercesupport112-[ACCOUNT-ID]-[REGION] --recursive
aws s3 rb s3://ecommercesupport112-[ACCOUNT-ID]-[REGION]
```

## ❓ 문제 해결

### 배포 실패 시
1. **AWS 자격 증명 확인**: `aws sts get-caller-identity`
2. **권한 확인**: CloudFormation, Lambda, DynamoDB 등 필요 권한 보유
3. **모델 액세스 확인**: Bedrock에서 Claude 모델 활성화 상태
4. **스택 이벤트 확인**: 
   ```bash
   aws cloudformation describe-stack-events --stack-name [STACK-NAME]
   ```

### 일반적인 오류
- **ParameterNotFound**: SSM 파라미터가 생성되지 않음 → 인프라 스택 재배포
- **AccessDenied**: IAM 권한 부족 → AWS 관리자에게 권한 요청
- **ModelNotFound**: Bedrock 모델 미활성화 → 모델 액세스 설정

## 📞 지원

문제가 지속되면 다음을 확인하세요:
- AWS 콘솔에서 CloudFormation 스택 상태
- CloudWatch 로그에서 Lambda 함수 오류
- IAM 역할 및 정책 설정

---

🎯 **준비 완료!** 이제 `lab-03-agentcore-gateway.ipynb` 노트북을 실행할 수 있습니다.