# 🔧 문제 해결 가이드

한국 패션/뷰티 이커머스 고객 지원 에이전트 실행 중 발생할 수 있는 문제들과 해결 방법입니다.

## 📋 일반적인 문제들

### 1. ParameterNotFound 오류

**오류 메시지:**
```
ParameterNotFound: An error occurred (ParameterNotFound) when calling the GetParameter operation: 
```

**원인:** SSM 파라미터가 생성되지 않았거나 잘못된 경로를 사용 중

**해결 방법:**

1. **인프라 배포 확인:**
   ```bash
   aws cloudformation describe-stacks --stack-name EcommerceCustomerSupportStackInfra
   aws cloudformation describe-stacks --stack-name EcommerceCustomerSupportStackCognito
   ```

2. **SSM 파라미터 확인:**
   ```bash
   aws ssm get-parameters-by-path --path "/app/ecommerce/agentcore" --output table
   ```

3. **노트북 재시작:** Kernel > Restart Kernel

### 2. Gateway 관련 오류

**오류 메시지:**
```
ConflictException: A target with name 'EcommerceLambdaTarget' already exists
```

**해결 방법:**
- 정상적인 메시지입니다. 기존 Gateway Target을 재사용합니다.

### 3. Lambda 함수 찾을 수 없음

**원인:** CloudFormation 인프라 스택이 제대로 배포되지 않음

**해결 방법:**
1. **스택 상태 확인:**
   ```bash
   aws cloudformation describe-stack-events --stack-name EcommerceCustomerSupportStackInfra
   ```

2. **인프라 재배포:**
   ```bash
   cd /home/ubuntu/Self-Study-Generative-AI/lab/18_ec-customer-support-agent-bedrock_agent_core/
   ./scripts/prereq.sh
   ```

### 4. Cognito 인증 실패

**오류 메시지:**
```
Cognito 클라이언트 시크릿 조회 실패
```

**해결 방법:**
1. **Cognito 스택 확인:**
   ```bash
   aws cloudformation describe-stacks --stack-name EcommerceCustomerSupportStackCognito
   ```

2. **User Pool 확인:**
   ```bash
   aws cognito-idp list-user-pools --max-items 10
   ```

### 5. 모델 액세스 권한 없음

**오류 메시지:**
```
AccessDeniedException: Your account is not authorized to invoke this API
```

**해결 방법:**
1. **Bedrock 콘솔에서 모델 활성화:**
   - [Amazon Bedrock Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
   - **Claude 3.7 Sonnet** 모델 활성화

2. **활성화 상태 확인:**
   ```bash
   aws bedrock list-foundation-models --query 'modelSummaries[?contains(modelName, `Claude`)]'
   ```

## 🚀 빠른 수정 방법

### 전체 리셋

모든 것을 처음부터 다시 시작하려면:

1. **기존 리소스 정리:**
   ```bash
   aws cloudformation delete-stack --stack-name EcommerceCustomerSupportStackCognito
   aws cloudformation delete-stack --stack-name EcommerceCustomerSupportStackInfra
   ```

2. **스택 삭제 대기:**
   ```bash
   aws cloudformation wait stack-delete-complete --stack-name EcommerceCustomerSupportStackCognito
   aws cloudformation wait stack-delete-complete --stack-name EcommerceCustomerSupportStackInfra
   ```

3. **노트북 재시작:** Kernel > Restart Kernel

4. **인프라 재배포:** 노트북의 "AWS 인프라 자동 배포" 셀 실행

### 노트북별 문제

#### Lab-03 Gateway
- **필수:** 인프라 배포 셀을 먼저 실행
- **중요:** 노트북 재시작 후 실행 (SSM 파라미터 경로 변경)

#### Lab-04 Runtime  
- **요구사항:** Lab-03 완료 후 실행
- **의존성:** Gateway와 Lambda 함수 필요

#### Lab-05 Frontend
- **요구사항:** Lab-03, Lab-04 완료 후 실행
- **추가 설치:** Streamlit 관련 패키지

## 📞 추가 지원

### AWS 상태 확인

```bash
# 1. 계정 및 리전 확인
aws sts get-caller-identity
aws configure get region

# 2. 권한 확인
aws iam get-user

# 3. 전체 리소스 상태
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
```

### 로그 확인

```bash
# CloudFormation 이벤트
aws cloudformation describe-stack-events --stack-name EcommerceCustomerSupportStackInfra

# Lambda 로그
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/EcommerceCustomer"
```

## ✅ 성공 확인

모든 것이 정상 작동하는지 확인:

1. **✅ 인프라:** CloudFormation 스택 2개 CREATE_COMPLETE
2. **✅ 파라미터:** SSM 파라미터 12-13개 존재
3. **✅ Lambda:** EcommerceCustomer 함수 1개 이상
4. **✅ Gateway:** ecommerce-gw 게이트웨이 생성
5. **✅ 에이전트:** 노트북에서 응답 성공

---

💡 **팁:** 대부분의 문제는 노트북 재시작과 인프라 재배포로 해결됩니다!