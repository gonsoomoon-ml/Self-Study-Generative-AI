# Bedrock Manus


# 2025.09.01 업데이트
### 제목: 보고서에 숫자에 대한 "인용" 추가


### 1. Graph 노드 확장
* validator_node 추가로 워크플로우에 검증 단계 통합
* 기존: coordinator → planner → supervisor → coder → reporter
* 신규: coordinator → planner → supervisor → coder --> validator → reporter

### 2. 기존 모듈 개선사항
#### 2.1. Agent 시스템 변경
- 이전 버전 (agents.py line 6)
```
    from src.tools.research_tools import research_tool_config, process_search_tool
```    
- 업그레이드 버전 (agents.py line 6-10)
```
  from src.tools.research_tools import research_tool_config, process_search_tool
  from src.tools.validator_tools import validator_tool_config, process_validator_tool
```

#### 2.2. 파일 관리 도구 강화
* file_management.py 대폭 개선:
    * 이전: 10줄의 기본 구현
    * 신규: 50줄 이상의 확장된 기능
    * JSON 자동 변환 지원
    * 향상된 에러 처리 및 로깅
    * 컬러 출력 지원

#### 2.3. Reporter 도구 개선
* Citation 시스템 통합
* PDF 생성 기능 추가
* 검증 리포트 연동

### 3. 인프라 및 설정 변경
- LLM 모델 매핑 업데이트
```
  "coordinator": "reasoning",  # basic → reasoning
  "planner": "advanced",       # reasoning → advanced  
  "validator": "reasoning",    # 신규 추가
```  

#### 3.1  출력 파일 구조
* 신규 artifacts:
    * calculation_metadata.json: 계산 추적 메타데이터
    * citations.json: Citation 매핑 데이터
    * validation_report.txt: 검증 결과 리포트
    * final_report.pdf: PDF 리포트 생성
    * 다양한 시각화 차트 (PNG 파일들)

### 4. 코드 품질 개선
#### 4.1. 모듈화 및 재사용성
* @log_io 데코레이터 활용 확대
* OptimizedValidator 클래스로 성능 최적화
* 캐싱 메커니즘 도입 (data_cache)

### 5. 성능 최적화
- Validator의 스마트 처리
* 대규모 데이터셋 처리 최적화:
    * 우선순위 기반 필터링
    * 배치 처리
    * 데이터 캐싱
    * 선택적 재검증

### 6.학습 포인트
1. 검증 시스템 도입: 데이터 무결성과 정확성 보장
2. Citation 시스템: 투명성과 추적 가능성 향상
3. 모듈화 강화: 각 컴포넌트의 독립성과 재사용성 증가
4. 성능 최적화: 대규모 데이터 처리를 위한 실용적 접근
5. 문서화 자동화: PDF 생성 등 리포팅 기능 강화

이 업그레이드는 특히 데이터 검증, 추적 가능성, 성능 최적화에 중점을 둔 엔터프라이즈급 개선사항입니다.


# 2025.08.01 업데이트
##  [중요] 아래 설정시 Admin 에게 문의하고 하시기 바랍니다.

## 1. 환경 설정

### 1.1 Conda 가상 환경 생성

```bash
cd setup/
./create_conda_virtual_env.sh bedrock-manus-clean
```

### 1.2. 가상 환경 활성화

```bash
conda activate bedrock-manus-clean
```

### 1.3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성해야 합니다:

```bash
touch .env
```

`.env` 파일에 필요한 환경 변수를 설정하세요.
```
TAVILY_API_KEY=<Placehloder> # 그냥 두셔도 됩니다.
JINA_API_KEY=<Placehloder> # 그냥 두셔도 됩니다.
LANGFUSE_SECRET_KEY=<> # 입력 필요
LANGFUSE_PUBLIC_KEY=<> # 입력 필요
LANGFUSE_HOST=<> # 입력 필요
# 기상 관련 MCP 서버 주소 환경변수 추가
MCP_SERVER_URL=<Placehloder> # 그냥 두셔도 됩니다.

# 콘다 환경 설정 - 
CONDA_ENV_NAME=bedrock-manus-clean
CONDA_PREFIX=/home/ubuntu/miniconda3/envs/bedrock-manus-clean # 경로가 다를시 필요
PYTHON_EXECUTABLE=/home/ubuntu/miniconda3/envs/bedrock-manus-clean/bin/python # 경로가 다를시 필요
```

## 쥬피터 노트북 실행 (커널 bedrock-manus-clean 선택)

```bash
main.ipynb
```

## 주요 구성

- `main.ipynb`: 메인 실행 노트북
- `setup/`: 환경 설정 스크립트
- `src/`: 소스 코드
- `data/`: 데이터 파일
- `artifacts/`: 생성된 결과물 (자동 생성)