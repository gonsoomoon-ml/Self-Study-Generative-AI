# K-Style 이커머스 환경 설정 가이드

이 디렉토리는 K-Style 이커머스 고객 지원 에이전트의 환경 설정을 위한 모든 파일들을 포함합니다.

## 📁 구성 파일들

### 🚀 **환경 설정 스크립트**
- **`create_kstyle_env.sh`** - 메인 환경 설정 스크립트 (가상환경 + 패키지 설치)
- **`setup_aws.sh`** - AWS 환경 확인 및 설정
- **`requirements.txt`** - 필수 Python 패키지 목록

### ⚙️ **프로젝트 설정**
- **`pyproject.toml`** - 현대적 Python 프로젝트 설정 (UV 패키지 매니저용)
- **`uv.lock`** - 정확한 의존성 버전 잠금 파일

## 🚀 빠른 시작

### 1️⃣ **기본 환경 설정** (필수)
```bash
# 실행 권한 부여
chmod +x setup/*.sh

# K-Style 가상환경 생성 및 패키지 설치
./setup/create_kstyle_env.sh
```

### 2️⃣ **AWS 환경 확인** (권장)
```bash
# AWS 설정 확인
./setup/setup_aws.sh
```

### 3️⃣ **애플리케이션 실행**
```bash
# 가상환경 활성화
source .venv/bin/activate

# Streamlit 앱 실행
streamlit run streamlit_app.py
```

## 📚 상세 가이드

### 🔧 **create_kstyle_env.sh 기능**
- **UV 패키지 매니저** 자동 설치
- **Python 3.12** 가상환경 생성
- **이커머스 특화 패키지** 자동 설치:
  - AI/ML: `strands-agents`, `boto3`, `bedrock_agentcore`
  - 웹앱: `streamlit`, `plotly`, `pandas`
  - 개발: `jupyter`, `ipykernel`
- **Jupyter 커널** 자동 등록
- **환경 변수 템플릿** 생성 (`.env.example`)

### ☁️ **setup_aws.sh 기능**
- **AWS CLI** 설치 확인
- **자격 증명** 상태 확인
- **필수 서비스 권한** 테스트
- **Bedrock 모델** 액세스 확인
- **기존 리소스** 스캔 (SSM Parameters, CloudFormation)

### 📦 **패키지 관리**
- **UV** 패키지 매니저 사용 (pip보다 빠름)
- **의존성 잠금** (uv.lock)으로 재현 가능한 환경
- **가상환경 격리**로 시스템 Python 보호

## 🔍 문제 해결

### ❓ **자주 묻는 질문**

#### Q: UV 설치가 실패합니다
```bash
# 수동 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

#### Q: AWS 자격 증명 오류
```bash
# AWS CLI 설정
aws configure

# 필요한 정보:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (예: us-east-1)
# - Output format (json)
```

#### Q: Bedrock 모델 액세스 오류
- AWS 콘솔 → Bedrock → Model access에서 Claude 모델 활성화
- IAM 권한에 `bedrock:InvokeModel` 포함 확인

#### Q: 가상환경 활성화 실패
```bash
# 가상환경 재생성
rm -rf .venv
./setup/create_kstyle_env.sh
```

### 🔧 **고급 설정**

#### 환경 변수 설정
```bash
# .env 파일 생성 (선택사항)
cp .env.example .env
# 필요한 값들 수정
```

#### 패키지 추가/제거
```bash
# 가상환경 활성화 후
source .venv/bin/activate

# 패키지 추가
uv add package_name

# 패키지 제거  
uv remove package_name

# 설치된 패키지 확인
uv pip list
```

#### 다른 Python 버전 사용
```bash
# Python 3.11 사용 예시
uv python install 3.11
uv venv --python 3.11
```

## 📊 시스템 요구사항

### 🖥️ **운영체제**
- Ubuntu 20.04+ (권장)
- macOS 10.15+
- Windows 10+ (WSL2 권장)

### 🐍 **Python**
- Python 3.12+ (자동 설치됨)
- pip는 불필요 (UV 사용)

### ☁️ **AWS**
- AWS CLI v2 (권장)
- 유효한 AWS 자격 증명
- Bedrock 서비스 액세스 권한

### 💾 **디스크 공간**
- 최소 2GB (가상환경 + 패키지)
- 권장 5GB (추가 모델 캐시)

## 🎯 다음 단계

환경 설정이 완료되면:

1. **📚 튜토리얼 시작**
   ```bash
   jupyter lab lab-01-create-ecommerce-agent.ipynb
   ```

2. **🛍️ 웹앱 실행**
   ```bash
   streamlit run streamlit_app.py
   ```

3. **🔍 리소스 확인**
   ```bash
   ./scripts/list_ssm_parameters.sh
   ```

4. **🏗️ 인프라 구성** (필요시)
   ```bash
   ./scripts/prereq.sh
   ```

---

**💡 도움이 필요하시면 메인 README.md를 참조하거나 이슈를 등록해 주세요!**