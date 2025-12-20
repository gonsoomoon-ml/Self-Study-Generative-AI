# 번역 품질 평가 프레임워크

한국어-영어 모바일 앱 번역에 대한 최신 번역 품질 평가 모델들을 종합적으로 비교하는 프레임워크입니다. 

이 프로젝트는 **번역 품질 평가의 패러다임 시프트**를 보여줍니다. 전통적인 신경망 메트릭(COMET-KIWI, MetricX-24)이 40-47%의 낮은 정확도를 보이는 반면, **Claude 4.5 패밀리 모델들은 76-80%의 높은 정확도**를 달성하여 실무에서 활용 가능한 수준의 성능을 제공합니다.

특히 **치명적 오류 감지**에서 두드러진 차이를 보입니다. "24시간"을 "24일"로 번역하는 등 사용자에게 심각한 피해를 줄 수 있는 오류를 Claude 모델들은 0.0-0.2 점수로 정확히 탐지하는 반면, 신경망 메트릭들은 0.88-0.98의 위험할 정도로 높은 점수를 부여합니다. 

또한 Claude 모델들은 **한국어 사용자를 위한 상세한 정당화**를 제공하여 번역 품질 판단 근거를 명확히 이해할 수 있게 합니다. GPU가 필요하지 않아 접근성이 뛰어나며, 실무 번역 품질 관리에 즉시 활용할 수 있는 실용적인 솔루션을 제공합니다.

## 🎯 요약

| 모델 | 정확도 | 한국어 설명 | 치명적 오류 감지 | 속도 | 비용 | 권장사항 |
|------|--------|------------|-----------------|------|------|----------|
| **Claude Sonnet 4.5** ⭐ | **80.0%** | **제공** | **우수** | 중간 | 중간 | **주요 선택** |
| **Claude Opus 4.5** | **80.0%** | **제공** | **우수** | 느림 | 높음 | 전문적 용도 |
| **Claude Haiku 4.5** | 76.7% | **제공** | **우수** | **빠름** | **낮음** | 대량 스크리닝 |
| COMET-KIWI | 46.7% | 미제공 | 부족 | 빠름 | 낮음 | 연구용만 |
| MetricX-24 | 40.0% | 미제공 | 매우 부족 | 중간 | 낮음 | 권장하지 않음 |

### 🚨 주요 발견사항
- **Claude 모델들이 우수함** - 사용자에게 해를 끼칠 수 있는 치명적 오류 감지에서 뛰어남 (0.0-0.2 점수)
- **신경망 메트릭의 실패** - 심각한 오역에도 높은 점수(0.8+)를 부여하는 문제
- **비용 효과적 선택**: Claude Haiku 4.5가 Sonnet 정확도의 96%를 낮은 비용으로 제공
- **실용 가능**: Claude 모델들이 번역 판단에 대한 한국어 정당화 제공

## 📋 지원 모델

| 모델 | 제공사 | 유형 | 점수 범위 | 해석 |
|------|--------|------|-----------|------|
| **Claude Sonnet 4.5** | Anthropic | LLM 판단자 | 0-1 | 높을수록 좋음 |
| **Claude Haiku 4.5** | Anthropic | LLM 판단자 | 0-1 | 높을수록 좋음 |
| **Claude Opus 4.5** | Anthropic | LLM 판단자 | 0-1 | 높을수록 좋음 |
| [MetricX-24 XXL](https://huggingface.co/google/metricx-24-hybrid-xxl-v2p6) | Google | 신경망 메트릭 | 0-25 | 낮을수록 좋음 |
| [COMET-KIWI](https://huggingface.co/Unbabel/wmt22-cometkiwi-da) | Unbabel | 신경망 메트릭 | 0-1 | 높을수록 좋음 |

## 🚀 빠른 시작

### 사전 요구사항

**Claude 모델만 사용 (권장)**
- Python 3.11+
- AWS Bedrock 접근 권한이 있는 AWS 자격 증명
- GPU 불필요 ✅

**전체 비교용 (선택사항)**
- CUDA 지원 GPU (MetricX/COMET용 16GB+ VRAM)
- HuggingFace 계정

### 설치

```bash
# 환경 및 의존성 설정
./setup/create_env.sh

# AWS 자격 증명 구성 (필수)
aws configure

# HuggingFace 구성 (선택사항 - MetricX/COMET용만)
uv run huggingface-cli login
```

### 기본 사용법

```bash
# 🚀 빠른 시작: Claude 모델만 (GPU 불필요)
uv run script/eval_llm_judge.py --model sonnet4.5  # 전체적으로 최고
uv run script/eval_llm_judge.py --model haiku4.5   # 가장 빠름
uv run script/eval_llm_judge.py --model opus4.5    # 가장 정밀함

# Claude 패밀리 비교 (대부분 사용자에게 권장)
uv run script/compare_claude_models.py

# 🔬 전체 비교 (GPU 필요)
uv run script/eval_cometkiwi.py    # GPU 필요
uv run script/eval_metricx.py      # GPU 필요  
uv run script/compare_five_models.py  # 종합적이지만 느림
```

## 📁 프로젝트 구조

```
24_evaluate_translation/
├── script/
│   ├── eval_llm_judge.py          # Claude 모델 평가
│   ├── eval_cometkiwi.py          # COMET-KIWI 평가  
│   ├── eval_metricx.py            # MetricX-24 평가
│   ├── compare_five_models.py     # 종합 비교
│   ├── compare_claude_models.py   # Claude만 비교
│   └── util.py                    # 공유 유틸리티
├── data/
│   └── quality_test_data.json     # 31개 테스트 예시
├── detail_evaluation.md           # 상세 분석 (한국어)
└── README.md                      # 영문 문서
```

## 💡 모델 선택 가이드

### 실무 번역 품질 평가용
- **주력**: Claude Sonnet 4.5 (최고 정확도 + 비용 균형)
- **대량 처리**: Claude Haiku 4.5 (빠름, Sonnet 정확도의 96%)  
- **중요 콘텐츠**: Claude Opus 4.5 (최대 정밀도)

### 연구/벤치마킹용
- **상대적 순위**: COMET-KIWI (MetricX보다 나음)
- **피해야 할**: 절대 품질 평가용 MetricX-24

## 📊 평가 기준

### 테스트된 오류 유형
- **정확성**: 오역, 누락, 추가, 미번역
- **유창성**: 문법, 철자, 어순
- **용어**: 잘못된 용어, 일관성 부족
- **문체**: 격식 불일치, 존댓말 문제  
- **지역화**: 문화적 적응, 형식 관례

### 점수 체계
- **0-1 척도** (높을수록 좋은 품질)
- **임계값**: 0.7 (좋은 vs 나쁜 번역 경계)
- **한국어 정당화** Claude 모델에서 제공

## 🔍 결과 예시

### 처리 예시
```bash
$ uv run eval_llm_judge.py 
HuggingFace login: OK
================================================================================
Claude Sonnet 4.5를 사용한 LLM 판단자 평가
설명: 종합적 평가를 위한 균형잡힌 성능
점수 범위: 0-1 (높을수록 좋음)
================================================================================
us-west-2 지역에 대해 Bedrock 클라이언트가 초기화되었습니다
Claude Sonnet 4.5로 30개 번역을 평가 중...
처리 중 1/30:
  원문 (한국어): 앱을 실행하려면 홈 화면에서 아이콘을 탭하세요.
  번역 (영어): To launch the app, tap the icon on the home screen.
  점수: 1.0000
  상태: ✓ 정확
  오류 유형: none
  정당화: 번역이 원문의 의미를 완벽하게 전달하며, 모바일 UI에서 표준적으로 사용되는 자연스러운 영어 표현입니다. "launch", "tap", "icon", "home screen" 등 모든 기술 용어가 정확하고, 문법과 격식 수준도 앱 인터페이스에 완전히 적합합니다.
```

### 치명적 오류 감지
```
원문: "24시간 내에 설치하세요"
잘못된 번역: "Please install within 24 days"

Claude 점수: 0.0-0.2 ✅ (치명적으로 정확히 표시)
신경망 점수: 0.88-0.98 ❌ (위험할 정도로 높은 점수)
```

### 완벽한 번역
```
원문: "앱을 실행하려면 홈 화면에서 아이콘을 탭하세요"  
번역: "To launch the app, tap the icon on the home screen"

모든 모델: 0.85+ ✅ (적절히 높은 점수)
```

## 🛠 고급 사용법

### 맞춤 모델 선택

```bash
# 특정 Claude 모델 선택
uv run script/eval_llm_judge.py --model opus4.5
uv run script/eval_llm_judge.py --model haiku4.5
```

### 상세 출력
모든 평가 스크립트는 다음을 보여주는 상세 모드를 지원합니다:
- 원문과 번역 텍스트
- 점수와 신뢰도
- 상태 (✓ 정확 / ✗ 놓침)  
- 오류 유형 분류
- 상세한 정당화 (Claude 모델의 경우 한국어)

## 📊 상세 결과 및 분석

종합적인 평가 결과, 오류 분석, 한국어 문서는 다음을 참조하세요:
**[📋 상세 평가 분석 (한국어)](detail_evaluation.md)**


**AWS Bedrock 접근**  
```bash
aws configure  # 자격 증명 설정
aws bedrock list-foundation-models --region us-west-2  # 접근 테스트
```


## 📈 성능 벤치마크

### 평가 속도 (30개 예시)
- **Claude Haiku**: ~2-3분
- **Claude Sonnet**: ~3-4분  
- **Claude Opus**: ~4-5분
- **COMET-KIWI**: ~30초
- **MetricX-24**: ~2-3분

### 리소스 요구사항
- **GPU 메모리**: 16GB+ (MetricX/COMET용)
- **CPU**: 8+ 코어 권장
- **RAM**: 대형 모델용 32GB+

## 📚 문서

- **[상세 분석](detail_evaluation.md)** - 종합적인 한국어 분석
- **[테스트 데이터](data/quality_test_data.json)** - 31개 선별된 예시
- **[모델 유틸리티](script/util.py)** - 공유 함수

## 📋 검증 데이터

프로젝트는 31개의 신중하게 선별된 테스트 예시를 사용하여 모델 성능을 평가합니다. 다음은 데이터셋의 샘플 예시입니다:

### 좋은 번역 예시
```json
{
  "id": 1,
  "src": "앱을 실행하려면 홈 화면에서 아이콘을 탭하세요.",
  "mt": "To launch the app, tap the icon on the home screen.",
  "quality": "good",
  "error_type": null,
  "error_description": "Perfect translation: Accurate terminology, natural word order, appropriate formality level for UI instructions. Tests basic competency across all models."
}
```

### 데이터셋 구성
- **총 31개 예시**: 모바일 앱 UI 번역 시나리오
- **품질 분류**: "good" (좋음) vs "bad" (나쁨)
- **오류 유형**: 정확성, 유창성, 용어, 문체, 지역화
- **설명**: 각 예시가 테스트하는 번역 능력에 대한 상세 설명
- **실제 시나리오**: 앱 실행, 권한 요청, 설정 변경 등 실무 상황


## 📄 라이선스

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다. 자세한 내용은 LICENSE 파일을 참조하세요.

## 📚 중요 정보

### 1. COMET-KIWI (Unbabel)

- **GitHub**: https://github.com/Unbabel/COMET
- **논문**: Scaling up CometKiwi (WMT 2023)
- **AWS Marketplace** (COMET-KIWI) - 512 토큰 (A4 반장 정도)
  - **마켓플레이스**: https://aws.amazon.com/marketplace/pp/prodview-k5lgwkzc62j5u
  - **정확한 모델**: Unbabel/wmt22-cometkiwi-da
    - https://huggingface.co/Unbabel/wmt22-cometkiwi-da
  - **예제 코드**:
    - **실시간**: https://github.com/widn-ai/aws-marketplace/blob/865885a2e66333008c76b7ca39d31c0fbfcb1b7a/widn-comet-wmt22-cometkiwi-da.ipynb
    - **배치**: https://github.com/widn-ai/aws-marketplace/blob/865885a2e66333008c76b7ca39d31c0fbfcb1b7a/widn-comet-wmt22-cometkiwi-da.ipynb

### 2. MetricX-24 (Google Research) ⭐⭐⭐⭐⭐

**하이브리드 모델 - WMT 2024 최상위 성능**

**기본 정보**
- **GitHub**: https://github.com/google-research/metricx
- **HuggingFace**: https://huggingface.co/google

**주요 모델**:
- **google/metricx-24-hybrid-xxl-v2p6** (1536 토큰)
  - https://huggingface.co/google/metricx-24-hybrid-xxl-v2p6

**논문**: MetricX-24 (WMT 2024)
- **번역 품질 평가 조사**: https://claude.ai/public/artifacts/e5641ebc-1ed5-4afe-b926-e5de79982a3e

## 📚 참고문헌

- [MetricX-24 논문](https://aclanthology.org/2024.wmt-1.35)
- [MetricX GitHub](https://github.com/google-research/metricx)
- [COMET-KIWI 논문](https://aclanthology.org/2022.wmt-1.60)
- [Claude 4.5 모델](https://www.anthropic.com/claude)

---

*상세한 기술 분석과 한국어 문서는 [detail_evaluation.md](detail_evaluation.md)를 참조하세요*