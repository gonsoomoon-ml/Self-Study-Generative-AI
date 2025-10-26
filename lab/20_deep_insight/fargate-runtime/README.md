# Fargate Runtime Environment

이 폴더는 멀티에이전트 워크플로우를 AWS Fargate에서 실행하기 위한 런타임 환경을 포함합니다.

## 📂 파일 구조 및 용도

### 🚀 핵심 실행 파일

#### `dynamic_executor_v2.py`
- **용도**: Fargate 컨테이너 내에서 실행되는 메인 코드 실행기
- **기능**:
  - HTTP 서버로 코드 실행 요청 수신
  - Python/Bash 명령어 실행 및 결과 반환
  - 작업 디렉토리를 `/app`으로 고정하여 경로 문제 해결
  - 세션 완료 시 S3에 결과 업로드

#### `session_fargate_manager.py`
- **용도**: Fargate 태스크 세션 관리자
- **기능**:
  - ECS 태스크 생성 및 관리
  - 세션별 고유 ID 생성 및 추적
  - 헬스체크 (300초 타임아웃)
  - 태스크 종료 및 리소스 정리

### 📦 컨테이너 설정

#### `Dockerfile`
- **용도**: Fargate 컨테이너 이미지 빌드 설정
- **버전**: v7-workdir (최신 안정화 버전)
- **특징**:
  - Python 3.11 기반
  - 한글 폰트 지원 (NanumGothic)
  - weasyprint, matplotlib 등 시각화 라이브러리 포함
  - 작업 디렉토리 `/app` 설정

#### `requirements.txt`
- **용도**: Python 패키지 의존성 목록
- **포함 패키지**:
  - pandas, numpy - 데이터 분석
  - matplotlib, lovelyplots - 시각화
  - weasyprint - PDF 생성
  - boto3 - AWS SDK

### ⚙️ AWS 설정 파일

#### `task-definition-v7-workdir.json`
- **용도**: ECS 태스크 정의 (최신 버전)
- **설정**:
  - 이미지: v7-workdir 태그
  - 메모리: 2048 MB
  - CPU: 1024 units
  - 네트워크 모드: awsvpc

#### `s3-policy.json`
- **용도**: S3 버킷 접근 정책
- **권한**:
  - bedrock-logs-gonsoomoon 버킷에 대한 읽기/쓰기 권한
  - 파일 업로드/다운로드 및 동기화

#### `task-role-trust.json`
- **용도**: ECS 태스크 역할 신뢰 정책
- **기능**: ECS 서비스가 태스크 역할을 사용할 수 있도록 허용

#### `trust-policy.json`
- **용도**: IAM 역할 기본 신뢰 정책
- **기능**: ECS 태스크가 AWS 서비스에 접근할 수 있도록 허용

#### `alb-security-example.json`
- **용도**: ALB(Application Load Balancer) 보안 그룹 설정 예제
- **참고**: 로드 밸런서 사용 시 보안 그룹 구성 참고용

### 🔧 기타


## 🏗️ 인프라 정보

- **ECS 클러스터**: my-fargate-cluster
- **ECR 리포지토리**: my-python-app
- **현재 이미지 태그**: v7-workdir
- **S3 버킷**: bedrock-logs-gonsoomoon

## 📝 사용 방법

1. **Docker 이미지 빌드 및 푸시**:
```bash
docker build -t my-python-app:v7-workdir .
docker tag my-python-app:v7-workdir [ECR_URI]:v7-workdir
docker push [ECR_URI]:v7-workdir
```

2. **태스크 정의 등록**:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition-v7-workdir.json
```

3. **Python 코드에서 사용**:
```python
from fargate_runtime.session_fargate_manager import SessionBasedFargateManager

manager = SessionBasedFargateManager()
session_id = manager.start_session()
# 코드 실행...
manager.stop_session(session_id)
```

## ⚠️ 주의사항

- 모든 파일 경로는 `/app` 기준으로 사용
- 세션당 최대 5분 헬스체크 타임아웃 설정
- 태스크 종료 시 자동으로 S3에 결과 동기화