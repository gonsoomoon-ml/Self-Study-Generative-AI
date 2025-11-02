# Phase 2: Fargate Runtime 배포

> **소요 시간**: 15-20분
> **난이도**: 중급
> **사전 요구사항**: Phase 1 완료 ([STEP_BY_STEP_GUIDE.md](../STEP_BY_STEP_GUIDE.md))

---

## 📋 목차

1. [개요](#개요)
2. [Step 1: 환경 준비](#step-1-환경-준비)
3. [Step 2: Docker 이미지 빌드](#step-2-docker-이미지-빌드)
4. [Step 3: ECR 푸시](#step-3-ecr-푸시)
5. [Step 4: ECS Task Definition 등록](#step-4-ecs-task-definition-등록)
6. [Step 5: 테스트 Task 실행](#step-5-테스트-task-실행)
7. [트러블슈팅](#트러블슈팅)

---

## 🎯 개요

이 단계에서는 Python 코드를 실행하는 Fargate Runtime을 Docker 컨테이너로 패키징하고 배포합니다.

### 주요 작업

- ✅ Docker 이미지 빌드 (Python 3.12 + 필수 패키지)
- ✅ ECR Repository 생성
- ✅ Docker 이미지를 ECR에 푸시
- ✅ ECS Task Definition 등록
- ✅ 테스트 Fargate Task 실행
- ✅ ALB Health Check 통과 확인

---

## Step 1: 환경 준비

### 1.1 환경 변수 로드

```bash
# 프로젝트 루트로 이동
cd production_deployment

# Phase 1에서 생성한 환경 변수 로드
source deployment.env

# 확인
echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "ECS Cluster: $ECS_CLUSTER_NAME"
```

### 1.2 ECR Repository 생성

```bash
# ECR Repository 이름
ECR_REPO_NAME="fargate-runtime-${ENVIRONMENT}"

# ECR Repository 생성
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  --tags Key=Environment,Value=$ENVIRONMENT Key=Project,Value=bedrock-manus

# ECR URI 가져오기
ECR_URI=$(aws ecr describe-repositories \
  --repository-names $ECR_REPO_NAME \
  --region $AWS_REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "✅ ECR Repository 생성 완료: $ECR_URI"

# 환경 변수에 추가
echo "ECR_REPO_NAME=$ECR_REPO_NAME" >> deployment.env
echo "ECR_URI=$ECR_URI" >> deployment.env
```

**참고**: Repository가 이미 존재하면 에러가 발생하지만 무시해도 됩니다.

---

## Step 2: Docker 이미지 빌드

### 2.1 Fargate Runtime 파일 확인

```bash
# 필요한 파일 확인
ls -lh ../fargate-runtime/

# 예상 파일:
# - Dockerfile
# - dynamic_executor_v2.py
# - requirements.txt (선택 사항, Dockerfile에 포함됨)
```

### 2.2 Dockerfile 검증

```bash
# Dockerfile 내용 미리보기
head -20 ../fargate-runtime/Dockerfile
```

**주요 내용 확인**:
- ✅ Base Image: `python:3.12-slim`
- ✅ 한글 폰트 설치 (`fonts-nanum`)
- ✅ Python 패키지: pandas, matplotlib, flask, boto3, weasyprint 등
- ✅ Port 8080 노출
- ✅ CMD: `python -u dynamic_executor_v2.py`

### 2.3 Docker 이미지 빌드

```bash
# fargate-runtime 디렉토리로 이동
cd ../fargate-runtime

# Docker 이미지 빌드
docker build \
  --platform linux/amd64 \
  -t $ECR_REPO_NAME:latest \
  -t $ECR_REPO_NAME:v$(date +%Y%m%d-%H%M%S) \
  .

echo "✅ Docker 이미지 빌드 완료"

# 이미지 확인
docker images | grep $ECR_REPO_NAME
```

**예상 소요 시간**: 5-10분 (첫 빌드 시)

**예상 출력**:
```
REPOSITORY                    TAG                   IMAGE ID       SIZE
fargate-runtime-prod          latest                abc123def456   465MB
fargate-runtime-prod          v20251020-150530      abc123def456   465MB
```

### 2.4 로컬 테스트 (선택 사항)

```bash
# 로컬에서 컨테이너 실행 테스트
docker run -d \
  -p 8080:8080 \
  --name fargate-test \
  $ECR_REPO_NAME:latest

# Health check 테스트
sleep 5
curl http://localhost:8080/health

# 예상 출력: {"status": "healthy", ...}

# 컨테이너 중지 및 삭제
docker stop fargate-test
docker rm fargate-test
```

---

## Step 3: ECR 푸시

### 3.1 ECR 로그인

```bash
# 프로젝트 루트로 돌아가기
cd ../production_deployment

# 환경 변수 재로드
source deployment.env

# ECR 로그인
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URI

echo "✅ ECR 로그인 완료"
```

### 3.2 Docker 이미지 태그 및 푸시

```bash
# 이미지 태그
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker tag $ECR_REPO_NAME:latest $ECR_URI:v$(date +%Y%m%d-%H%M%S)

# ECR에 푸시
docker push $ECR_URI:latest
docker push $ECR_URI:v$(date +%Y%m%d-%H%M%S)

echo "✅ Docker 이미지 ECR 푸시 완료"
```

**예상 소요 시간**: 3-5분

### 3.3 ECR 이미지 확인

```bash
# ECR에 푸시된 이미지 확인
aws ecr list-images \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --query 'imageIds[*].[imageTag]' \
  --output table
```

**예상 출력**:
```
-----------------------
|     ListImages      |
+---------------------+
|  latest             |
|  v20251020-150530   |
+---------------------+
```

---

## Step 4: ECS Task Definition 등록

### 4.1 Task Definition JSON 생성

```bash
# Task Definition 파일 생성
cat > task-definition-prod.json <<EOF
{
  "family": "fargate-runtime-${ENVIRONMENT}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "${FARGATE_EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${FARGATE_TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "fargate-runtime",
      "image": "${ECR_URI}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENV_NAME", "value": "${ENVIRONMENT}"},
        {"name": "AWS_DEFAULT_REGION", "value": "${AWS_REGION}"},
        {"name": "S3_BUCKET_NAME", "value": "${S3_BUCKET_NAME}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/fargate-runtime-${ENVIRONMENT}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

echo "✅ Task Definition JSON 생성 완료"
cat task-definition-prod.json
```

### 4.2 Task Definition 등록

```bash
# Task Definition 등록
aws ecs register-task-definition \
  --cli-input-json file://task-definition-prod.json \
  --region $AWS_REGION

# Task Definition ARN 가져오기
TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition fargate-runtime-${ENVIRONMENT} \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "✅ Task Definition 등록 완료: $TASK_DEF_ARN"

# 환경 변수에 추가
echo "TASK_DEF_ARN=$TASK_DEF_ARN" >> deployment.env
```

---

## Step 5: 테스트 Task 실행

### 5.1 Fargate Task 수동 실행

```bash
# 환경 변수 재로드
source deployment.env

# Subnet ID 추출 (첫 번째 Private Subnet 사용)
PRIVATE_SUBNET_ID=$(echo $PRIVATE_SUBNET_IDS | cut -d',' -f1)

# Fargate Task 실행
TASK_ARN=$(aws ecs run-task \
  --cluster $ECS_CLUSTER_NAME \
  --task-definition fargate-runtime-${ENVIRONMENT} \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_ID],securityGroups=[$FARGATE_SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --region $AWS_REGION \
  --query 'tasks[0].taskArn' \
  --output text)

echo "✅ Fargate Task 실행 시작: $TASK_ARN"
```

### 5.2 Task 상태 모니터링

```bash
# Task 상태 확인 (30초마다)
watch -n 30 "aws ecs describe-tasks \
  --cluster $ECS_CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region $AWS_REGION \
  --query 'tasks[0].[lastStatus,healthStatus,containers[0].lastStatus]' \
  --output table"
```

**예상 진행 과정**:
1. `PROVISIONING` → `PENDING` (1-2분): ENI 생성, IP 할당
2. `PENDING` → `RUNNING` (30초): 컨테이너 시작
3. Health Status: `UNKNOWN` → `HEALTHY` (1-2분): Health check 통과

**최종 예상 출력**:
```
-----------------------------
|      DescribeTasks        |
+---------------------------+
|  RUNNING                  |
|  HEALTHY                  |
|  RUNNING                  |
+---------------------------+
```

### 5.3 Task Logs 확인

```bash
# CloudWatch Logs 스트림 확인
aws logs tail /ecs/fargate-runtime-${ENVIRONMENT} \
  --follow \
  --format short \
  --region $AWS_REGION
```

**예상 로그**:
```
2025-10-20T15:30:45 Starting Flask server on port 8080
2025-10-20T15:30:46 Session manager initialized
2025-10-20T15:30:47 Health check endpoint ready
```

### 5.4 ALB Target 등록 및 Health Check

```bash
# Task의 Private IP 가져오기
TASK_IP=$(aws ecs describe-tasks \
  --cluster $ECS_CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region $AWS_REGION \
  --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
  --output text)

echo "Task Private IP: $TASK_IP"

# ALB Target Group에 등록
aws elbv2 register-targets \
  --target-group-arn $ALB_TARGET_GROUP_ARN \
  --targets Id=$TASK_IP,Port=8080 \
  --region $AWS_REGION

echo "✅ Task를 ALB Target Group에 등록 완료"

# Health Check 상태 확인 (60초 대기)
sleep 60

aws elbv2 describe-target-health \
  --target-group-arn $ALB_TARGET_GROUP_ARN \
  --targets Id=$TASK_IP,Port=8080 \
  --region $AWS_REGION \
  --query 'TargetHealthDescriptions[0].TargetHealth' \
  --output table
```

**예상 출력**:
```
-------------------------------------------------------
|              DescribeTargetHealth                   |
+-------------+---------------------------------------+
|  State      |  healthy                              |
|  Reason     |  -                                    |
+-------------+---------------------------------------+
```

**참고**: Health Check가 `unhealthy`인 경우 5.5 섹션을 참조하세요.

### 5.5 Health Check 트러블슈팅

Health Check가 실패하는 경우:

```bash
# 1. Target Health 상세 확인
aws elbv2 describe-target-health \
  --target-group-arn $ALB_TARGET_GROUP_ARN \
  --targets Id=$TASK_IP,Port=8080 \
  --query 'TargetHealthDescriptions[0]' \
  --output json

# 2. Task 로그 확인
aws logs tail /ecs/fargate-runtime-${ENVIRONMENT} \
  --since 5m \
  --format short

# 3. Security Group 규칙 확인
aws ec2 describe-security-groups \
  --group-ids $FARGATE_SECURITY_GROUP \
  --query 'SecurityGroups[0].IpPermissions' \
  --output table

# 4. Task가 실행 중인지 확인
aws ecs describe-tasks \
  --cluster $ECS_CLUSTER_NAME \
  --tasks $TASK_ARN \
  --query 'tasks[0].[lastStatus,containers[0].exitCode]'
```

**일반적인 원인**:
- Container가 Port 8080을 리스닝하지 않음
- Security Group에서 ALB → Fargate (8080) 트래픽 차단
- Container가 crash 또는 재시작 중
- Health check endpoint (`/health`) 응답 없음

---

## Step 6: 검증 및 정리

### 6.1 체크리스트

- [ ] ECR Repository 생성 완료
- [ ] Docker 이미지 빌드 성공
- [ ] ECR에 이미지 푸시 완료
- [ ] ECS Task Definition 등록 완료
- [ ] Fargate Task `RUNNING` 상태
- [ ] Task Health Status: `HEALTHY`
- [ ] ALB Target Health: `healthy`
- [ ] CloudWatch Logs 정상 수집

### 6.2 Task 정리 (테스트 완료 후)

```bash
# ALB Target Group에서 제거
aws elbv2 deregister-targets \
  --target-group-arn $ALB_TARGET_GROUP_ARN \
  --targets Id=$TASK_IP,Port=8080 \
  --region $AWS_REGION

echo "✅ Task를 ALB에서 제거 완료"

# Task 중지
aws ecs stop-task \
  --cluster $ECS_CLUSTER_NAME \
  --task $TASK_ARN \
  --region $AWS_REGION

echo "✅ 테스트 Task 중지 완료"
```

**참고**: Phase 3에서 AgentCore Runtime이 자동으로 Task를 생성하므로 지금은 정리합니다.

---

## 🔧 트러블슈팅

### 문제 1: Docker 빌드 실패

**증상**:
```
ERROR: failed to solve: failed to fetch ...
```

**해결 방법**:
```bash
# Docker daemon 재시작
sudo systemctl restart docker

# BuildKit 캐시 정리
docker builder prune -a

# 재시도
docker build --no-cache -t $ECR_REPO_NAME:latest .
```

### 문제 2: ECR 푸시 권한 에러

**증상**:
```
denied: User is not authorized to perform: ecr:PutImage
```

**해결 방법**:
```bash
# IAM 권한 확인
aws sts get-caller-identity

# ECR Repository 정책 확인
aws ecr get-repository-policy \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION
```

**필요한 IAM 권한**:
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:PutImage`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`

### 문제 3: Task가 PROVISIONING에서 멈춤

**증상**:
```
Task LastStatus: PROVISIONING (5분 이상)
```

**해결 방법**:
```bash
# Task 이벤트 확인
aws ecs describe-tasks \
  --cluster $ECS_CLUSTER_NAME \
  --tasks $TASK_ARN \
  --query 'tasks[0].stoppedReason'

# Subnet에 사용 가능한 IP가 있는지 확인
aws ec2 describe-subnets \
  --subnet-ids $PRIVATE_SUBNET_ID \
  --query 'Subnets[0].AvailableIpAddressCount'
```

**일반적인 원인**:
- Subnet에 사용 가능한 IP 부족
- Security Group 설정 오류
- ECR 이미지를 Pull할 수 없음 (VPC Endpoint 문제)

### 문제 4: Task가 즉시 종료됨

**증상**:
```
Task LastStatus: STOPPED
ExitCode: 1
```

**해결 방법**:
```bash
# Task 종료 이유 확인
aws ecs describe-tasks \
  --cluster $ECS_CLUSTER_NAME \
  --tasks $TASK_ARN \
  --query 'tasks[0].[stoppedReason,containers[0].exitCode,containers[0].reason]'

# CloudWatch Logs 확인
aws logs tail /ecs/fargate-runtime-${ENVIRONMENT} \
  --since 10m \
  --format short
```

**일반적인 원인**:
- Python 스크립트 에러
- 환경 변수 누락
- S3 버킷 접근 권한 부족

---

## ✅ 완료 확인

다음이 모두 완료되었으면 Phase 2가 성공적으로 완료되었습니다:

- [x] ECR Repository 생성 완료
- [x] Docker 이미지 빌드 및 푸시 성공
- [x] ECS Task Definition 등록 완료
- [x] 테스트 Fargate Task 실행 및 `HEALTHY` 상태 확인
- [x] ALB Health Check 통과 확인
- [x] `deployment.env` 업데이트 (ECR_URI, TASK_DEF_ARN 추가)

**STATUS.md 업데이트**:
```bash
# production_deployment/STATUS.md 파일을 편집하여 Phase 2 체크박스를 완료로 표시하세요
```

---

## 📚 다음 단계

Phase 2 완료를 축하합니다! 🎉

다음 단계로 진행하세요:

→ **[03_AGENTCORE_RUNTIME.md](./03_AGENTCORE_RUNTIME.md)** - AgentCore Runtime 생성

---

**작성일**: 2025-10-20
**마지막 업데이트**: 2025-10-20
