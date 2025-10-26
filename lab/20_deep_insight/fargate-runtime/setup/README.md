# Fargate Runtime Setup Files

Fargate Runtime 초기 설정을 위한 파일들 (한 번만 사용)

## 📁 폴더 구조

```
setup/
├── iam-policies/      # IAM 정책 파일
├── config/            # ECS Task Definition
└── examples/          # 참고 예제
```

## 🔐 IAM Policies

### trust-policy.json
**용도**: ECS Task Execution Role의 신뢰 정책

**사용법**:
```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://iam-policies/trust-policy.json
```

### task-role-trust.json
**용도**: ECS Task Role의 신뢰 정책

**사용법**:
```bash
aws iam create-role \
  --role-name fargate-task-role \
  --assume-role-policy-document file://iam-policies/task-role-trust.json
```

### s3-policy.json
**용도**: S3 버킷 접근 권한

**사용법**:
```bash
aws iam put-role-policy \
  --role-name fargate-task-role \
  --policy-name S3AccessPolicy \
  --policy-document file://iam-policies/s3-policy.json
```

## ⚙️ Config

### task-definition-v7-workdir.json
**용도**: ECS Task Definition (v7 - workdir 설정 포함)

**주요 설정**:
- Image: ECR repository URI
- CPU/Memory: 1024/2048
- Port: 8080 (Flask)
- WorkingDirectory: /app

**사용법**:
```bash
aws ecs register-task-definition \
  --cli-input-json file://config/task-definition-v7-workdir.json
```

**업데이트 방법**:
1. JSON 파일 수정 (이미지 URI 등)
2. 새 버전으로 등록
3. ECS 서비스 업데이트

## 📚 Examples

### alb-security-example.json
**용도**: ALB Security Group 설정 참고

**포함 내용**:
- Inbound: Port 80 (HTTP)
- Outbound: All traffic

**사용 시나리오**:
- ALB 생성 시 Security Group 참고
- Fargate와 ALB 간 통신 설정

## 🚀 초기 설정 순서

### 1️⃣ IAM Roles 생성
```bash
cd setup

# Execution Role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://iam-policies/trust-policy.json

# Task Role
aws iam create-role \
  --role-name fargate-task-role \
  --assume-role-policy-document file://iam-policies/task-role-trust.json

# S3 Policy 연결
aws iam put-role-policy \
  --role-name fargate-task-role \
  --policy-name S3AccessPolicy \
  --policy-document file://iam-policies/s3-policy.json
```

### 2️⃣ Docker 이미지 빌드 & 푸시
```bash
cd ..  # fargate-runtime 루트로

# ECR 로그인
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 이미지 빌드
docker build -t dynamic-executor:v19 .

# 태그
docker tag dynamic-executor:v19 \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/dynamic-executor:v19

# 푸시
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/dynamic-executor:v19
```

### 3️⃣ Task Definition 등록
```bash
cd setup

# config/task-definition-v7-workdir.json 파일의 image URI 업데이트
# 그 후 등록

aws ecs register-task-definition \
  --cli-input-json file://config/task-definition-v7-workdir.json
```

### 4️⃣ ECS Service 생성
```bash
aws ecs create-service \
  --cluster my-fargate-cluster \
  --service-name dynamic-executor-service \
  --task-definition fargate-dynamic-task:7 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "..."
```

## ⚠️ 주의사항

1. **IAM Roles**: 이미 생성된 경우 스킵
2. **ECR Repository**: 미리 생성 필요
3. **Task Definition**: 버전 관리 주의 (v7이 최신)
4. **Security Groups**: ALB와 Fargate 간 통신 허용 필요

## 🔄 업데이트

**코드 업데이트 시**:
1. 상위 폴더에서 코드 수정
2. Docker 이미지 재빌드 (새 버전 태그)
3. Task Definition 재등록 (image URI 업데이트)
4. ECS Service 업데이트

**Setup 파일은 변경 불필요** (한 번만 사용)

## 📖 참고

- 메인 README: `../README.md`
- Source Code: `../dynamic_executor_v2.py`
- Dockerfile: `../Dockerfile`
