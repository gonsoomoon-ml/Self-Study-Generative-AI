# Bedrock Manus

Amazon Bedrock 기반 AI 에이전트 워크플로우 프로젝트

## 환경 설정

### 1. Conda 가상 환경 생성

```bash
cd setup/
./create_conda_virtual_env.sh bedrock-manus-clean
```

### 2. 가상 환경 활성화

```bash
conda activate bedrock-manus-clean
```

### 3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성해야 합니다:

```bash
touch .env
```

`.env` 파일에 필요한 환경 변수를 설정하세요.

## 실행

Jupyter Notebook을 통해 프로젝트를 시작합니다:

```bash
jupyter notebook main.ipynb
```

## 주요 구성

- `main.ipynb`: 메인 실행 노트북
- `setup/`: 환경 설정 스크립트
- `src/`: 소스 코드
- `data/`: 데이터 파일
- `artifacts/`: 생성된 결과물 (자동 생성)