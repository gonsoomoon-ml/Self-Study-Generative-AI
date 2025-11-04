# Phase 3: AgentCore Runtime 빠른 시작 가이드

## 📋 전제 조건

✅ **Phase 1/2가 이미 완료되어 있어야 합니다**:
- Phase 1: VPC, ALB, Security Groups, VPC Endpoints, IAM Roles 배포됨
- Phase 2: ECR, Docker Image, ECS Cluster, Task Definition 배포됨
- `production_deployment/.env` 파일이 자동 생성되어 있음

## 🚀 Phase 3 배포 (10-15분)

### 1단계: 프로젝트 Clone
```bash
git clone https://github.com/hyeonsangjeon/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/05_insight_extractor_strands_sdk_workshop_phase_2
```

### 2단계: uv 환경 설정 (완전 설정)
```bash
cd setup
./create-uv-env.sh deep-insight
```

**이 스크립트는 다음을 자동으로 수행합니다**:
- UV 설치 확인/자동 설치
- Python 3.12 설정 (프로젝트 요구사항)
- 의존성 설치 (pyproject.toml 기반)
- **한글 폰트 설치** (PDF 생성에 필수!)
- **시스템 패키지 설치** (pandoc, texlive, poppler-utils)
- Jupyter 커널 등록
- 루트 디렉토리에 심링크 생성

**예상 출력**:
```
[INFO] 환경 설정을 시작합니다...
[INFO] 환경 이름: deep-insight
[INFO] Python 버전: 3.12
...
[SUCCESS] 환경 설정이 완료되었습니다!
```

**또는 간단 설정** (의존성만 동기화):
```bash
cd setup
uv sync  # 이미 환경이 구성되어 있다면
```

### 3단계: 패치 스크립트 실행 (필수!)
```bash
./patch_dockerignore_template.sh
```

**예상 출력**:
```
✅ Patch applied successfully!
Modified section:
*.md
!README.md
!src/prompts/*.md
```

**검증**:
```bash
grep "!src/prompts/\*.md" .venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template
```

### 4단계: .env 파일 확인
```bash
cd ../production_deployment
cat .env
```

**필수 환경 변수** (Phase 1/2에서 자동 생성됨):
```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=057716757052  # 예시
VPC_ID=vpc-xxxxx
PRIVATE_SUBNET_ID=subnet-xxxxx
SG_AGENTCORE_ID=sg-xxxxx
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::ACCOUNT:role/...
```

⚠️ **만약 .env 파일이 없거나 값이 비어있다면**:
- Phase 1/2를 먼저 배포해야 합니다
- `./scripts/phase1/deploy.sh prod` 실행
- `./scripts/phase2/deploy.sh prod` 실행

### 5단계: Runtime 배포
```bash
cd ..
python3 01_create_agentcore_runtime.py
```

**예상 출력** (10-15분 소요):
```
============================================================
AgentCore Runtime 생성 - Native launch() 메서드
============================================================

[1/5] 환경 설정 로드...
✅ 환경 설정 로드 완료
  - Region: us-east-1
  - VPC: vpc-xxxxx
  - Subnet: subnet-xxxxx
  - Security Group: sg-xxxxx

[2/5] IAM Role 설정...
✅ 기존 IAM Role 재사용: arn:aws:iam::...

[3/5] AgentCore Runtime 설정...
✅ Configuration 완료
✅ ✅ VPC 설정이 YAML에 저장되었습니다!

[4/5] Runtime 배포 (launch)...
⚠️  이 단계는 5-10분 소요됩니다
🐳 Docker 이미지 빌드 중...
📦 ECR 푸시 중...
🚀 Runtime 생성 중...

🎉 CodeBuild completed successfully in 1m 36s
✅ launch() 완료!

[5/5] Runtime 상태 확인...
✅ Runtime이 READY 상태입니다!
✅ .env 파일 업데이트 완료

✅ 🎉 VPC Runtime 배포 성공!
```

### 6단계: 검증

#### CloudWatch Logs 확인
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/deep_insight_runtime_vpc --follow --region us-east-1
```

**성공 확인 사항**:
```
INFO:src.graph.nodes:[92m===== Coordinator started =====[0m
INFO:src.graph.nodes:[92m===== Coordinator completed =====[0m
```

**실패 시 나타나는 에러** (없어야 함):
```
❌ FileNotFoundError: [Errno 2] No such file or directory: '/app/src/prompts/coordinator.md'
```

#### Runtime ARN 확인
```bash
cd production_deployment
cat .env | grep RUNTIME_ARN
```

**출력**:
```
RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/deep_insight_runtime_vpc-XXXXX
```

### 7단계: 테스트 (선택 사항)
```bash
cd ..
python3 03_invoke_agentcore_job_vpc.py
```

**예상 실행 시간**: 15-20분 (Multi-Agent workflow)

---

## ✅ 성공 체크리스트

배포가 성공했다면 다음 항목들이 모두 체크되어야 합니다:

- [ ] **patch script 실행됨**: `!src/prompts/*.md` 확인
- [ ] **boto3 버전**: 1.40.65 이상
- [ ] **toolkit 버전**: 0.1.28 이상
- [ ] **.env 파일 존재**: Phase 1/2 값 포함
- [ ] **Docker 빌드 성공**: CodeBuild 완료 (1-2분)
- [ ] **ECR 푸시 성공**: Image URI 생성
- [ ] **Runtime READY**: 상태 확인 완료
- [ ] **CloudWatch Logs**: "Coordinator started" 메시지
- [ ] **FileNotFoundError 없음**: coordinator.md 정상 로드

---

## 🆘 트러블슈팅

### 문제 1: patch script 실행 안 됨
**증상**:
```
FileNotFoundError: coordinator.md
```

**해결**:
```bash
cd setup
./patch_dockerignore_template.sh
grep "!src/prompts/\*.md" .venv/.../dockerignore.template
```

### 문제 2: .env 파일 없음
**증상**:
```
❌ .env 파일이 없습니다
```

**해결**:
Phase 1/2를 먼저 배포:
```bash
cd production_deployment
./scripts/phase1/deploy.sh prod
./scripts/phase2/deploy.sh prod
```

### 문제 3: boto3 버전 낮음
**증상**:
```
TypeError: configure() got an unexpected keyword argument 'vpc_enabled'
```

**해결**:
```bash
cd setup
uv sync
uv pip show boto3 | grep Version  # 1.40.65 이상이어야 함
```

### 문제 4: CodeBuild 실패
**증상**:
```
CodeBuild build failed
```

**해결**:
1. IAM 권한 확인: CodeBuild Role에 ECR, S3 권한
2. VPC Endpoints 확인: ECR API, ECR Docker endpoints available
3. CodeBuild 로그 확인:
   ```bash
   aws codebuild batch-get-builds --ids <BUILD_ID>
   ```

---

## 📊 예상 소요 시간

| 단계 | 소요 시간 | 누적 |
|------|----------|------|
| 1. Git Clone | 1분 | 1분 |
| 2. uv sync | 1분 | 2분 |
| 3. Patch | 10초 | 2분 |
| 4. .env 확인 | 10초 | 2분 |
| 5. Runtime 배포 | 10-12분 | 12-14분 |
| 6. 검증 | 1분 | 13-15분 |

**총 소요 시간**: **13-15분**

---

## 💡 주요 참고사항

### CodeBuild Role 자동 생성
- **첫 실행**: Toolkit이 자동으로 CodeBuild Role 생성
- **두 번째 실행**: 기존 Role 재사용
- **Role 이름**: `AmazonBedrockAgentCoreSDKCodeBuild-{region}-{hash}`

### VPC 모드 특징
- ✅ Private Subnet에서 실행
- ✅ VPC Endpoint 통한 안전한 통신
- ✅ Public IP 불필요
- ✅ Security Group으로 접근 제어

### coordinator.md 포함
- ✅ Patch script가 toolkit의 dockerignore.template 수정
- ✅ `src/prompts/*.md` 파일들이 Docker 이미지에 포함됨
- ✅ Runtime 시작 시 coordinator.md 정상 로드

---

## 📞 다음 단계

**배포 성공 후**:
1. Phase 4: End-to-End 테스트
2. 모니터링 설정
3. Production 롤아웃

**관련 문서**:
- [production_deployment/README.md](./README.md) - 전체 가이드
- [docs/03_AGENTCORE_RUNTIME.md](./docs/03_AGENTCORE_RUNTIME.md) - 상세 가이드
- [UPDATE_PHASE1_IAM.md](./UPDATE_PHASE1_IAM.md) - IAM 업데이트 (선택 사항)

---

**작성일**: 2025-11-04
**버전**: 1.0.0
**상태**: ✅ Production Ready
