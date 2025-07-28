# Amazon Bedrock Agent Core - UV 가상환경 설정

이 디렉토리는 Amazon Bedrock Agent Core 샘플을 위한 UV 기반 Python 가상환경을 설정하는 스크립트를 포함합니다.

## 📋 목차

- [개요](#개요)
- [사전 요구사항](#사전-요구사항)
- [설치 및 설정](#설치-및-설정)
- [사용법](#사용법)
- [주요 명령어](#주요-명령어)
- [문제 해결](#문제-해결)

## 🎯 개요

이 프로젝트는 **UV**를 사용하여 Python 가상환경을 관리합니다. UV는 Python 패키지 관리와 가상환경 관리를 위한 빠르고 현대적인 도구입니다.

### UV의 장점

- ⚡ **빠른 속도**: Rust로 작성되어 매우 빠름
- 🔒 **의존성 잠금**: 정확한 패키지 버전 관리
- 🛠️ **통합 도구**: 가상환경, 패키지 관리, 프로젝트 초기화를 하나의 도구로
- 📦 **최신 표준**: PEP 621, PEP 660 등 최신 Python 표준 지원

## 🔧 사전 요구사항

- Linux/macOS/Windows (WSL)
- curl (UV 설치용)
- 인터넷 연결

## 🚀 설치 및 설정

### 1. 스크립트 실행

```bash
# 스크립트에 실행 권한 부여
chmod +x create_uv_virtual_env.sh

# 가상환경 생성 (환경 이름 지정)
./create_uv_virtual_env.sh MyEnv
```

### 2. 자동 설치 과정

스크립트가 실행되면 다음 작업들이 자동으로 수행됩니다:

1. **UV 설치 확인**: UV가 설치되어 있지 않으면 자동 설치
2. **Python 3.10 설치**: UV를 통해 Python 3.10 설치
3. **가상환경 생성**: `.venv` 디렉토리에 가상환경 생성
4. **프로젝트 초기화**: `uv init`으로 프로젝트 설정
5. **패키지 설치**: `requirements.txt`의 모든 패키지 설치

## 📖 사용법

### 가상환경 활성화

```bash
# 가상환경 활성화
source .venv/bin/activate

# 활성화 확인
which python
python --version
```

### 가상환경 비활성화

```bash
deactivate
```

### Jupyter Lab 실행

```bash
# UV를 통해 Jupyter Lab 실행
uv run --with jupyter jupyter lab

# 또는 가상환경 활성화 후 실행
source .venv/bin/activate
jupyter lab
```

### Jupyter 노트북에서 커널 사용하기

스크립트 실행 시 자동으로 Jupyter 커널이 생성됩니다. Jupyter Lab에서 노트북을 열 때:

1. **노트북 파일 열기**: `.ipynb` 파일을 클릭
2. **커널 선택**: 우상단의 커널 선택 드롭다운에서 생성된 커널 선택
   - 커널 이름: 스크립트 실행 시 지정한 환경 이름 (예: `MyEnv`)
3. **코드 실행**: 이제 해당 가상환경의 패키지들을 사용할 수 있습니다

#### 커널 확인 및 관리

```bash
# 설치된 Jupyter 커널 목록 확인
jupyter kernelspec list

# 특정 커널 제거
jupyter kernelspec uninstall -y MyEnv
```

## 🛠️ 주요 명령어

### 패키지 관리

```bash
# 새 패키지 추가
uv add package_name

# 특정 버전의 패키지 추가
uv add package_name==1.2.3

# 개발 의존성으로 패키지 추가
uv add --dev package_name

# 패키지 제거
uv remove package_name

# requirements.txt에서 패키지 설치
uv add -r requirements.txt
```

### Python 스크립트 실행

```bash
# UV를 통해 스크립트 실행
uv run python your_script.py

# 가상환경 활성화 후 실행
source .venv/bin/activate
python your_script.py
```

### 프로젝트 관리

```bash
# 새 UV 프로젝트 초기화
uv init

# Python 버전 설치
uv python install 3.10

# 가상환경 생성
uv venv --python 3.10
```

## 🔍 문제 해결

### UV가 설치되지 않는 경우

```bash
# 수동으로 UV 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 가상환경 활성화 오류

```bash
# .venv 디렉토리 확인
ls -la .venv/

# 가상환경 재생성
rm -rf .venv
uv venv --python 3.10
```

### 패키지 설치 오류

```bash
# 캐시 정리
uv cache clean

# 패키지 재설치
uv add -r requirements.txt --force-reinstall
```

## 📁 프로젝트 구조

```
01_setup/
├── README.md                    # 이 파일
├── create_uv_virtual_env.sh     # UV 가상환경 생성 스크립트
├── requirements.txt             # Python 패키지 의존성
└── .venv/                       # UV 가상환경 (스크립트 실행 후 생성)
```

## 🔗 유용한 링크

- [UV 공식 문서](https://docs.astral.sh/uv/)
- [Amazon Bedrock Agent Core](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Python 가상환경 가이드](https://docs.python.org/3/tutorial/venv.html)

## 📝 참고사항

- UV는 Python 3.8 이상을 지원합니다
- 가상환경은 `.venv` 디렉토리에 생성됩니다
- `requirements.txt` 파일이 자동으로 설치됩니다
- Jupyter Lab을 사용하려면 `uv run --with jupyter jupyter lab` 명령어를 사용하세요

---

**💡 팁**: UV는 매우 빠르므로 대규모 프로젝트에서도 효율적으로 작동합니다. 기존의 pip/conda보다 훨씬 빠른 패키지 설치 속도를 경험할 수 있습니다!






