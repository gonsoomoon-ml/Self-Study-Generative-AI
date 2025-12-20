# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This project evaluates machine translation quality using five different approaches:

1. **MetricX-24 Hybrid XXL** (Google) - Hybrid reference-free metric (0-25 scale, lower = better)
2. **COMET-KIWI** (Unbabel) - Reference-free quality estimation (0-1 scale, higher = better)  
3. **LLM as Judge** (Claude Sonnet 4.5) - Balanced performance, human-like evaluation (0-1 scale, higher = better)
4. **LLM as Judge** (Claude Haiku 4.5) - Fast and efficient evaluation (0-1 scale, higher = better)
5. **LLM as Judge** (Claude Opus 4.5) - Most advanced evaluation model (0-1 scale, higher = better)

## Models

### MetricX-24 Hybrid XL
- **HuggingFace**: `google/metricx-24-hybrid-xl-v2p6`
- **Type**: Hybrid (reference-based & reference-free)
- **Score Range**: 0-25 (lower = better)
- **Architecture**: mT5-based
- **GitHub**: https://github.com/google-research/metricx

### COMET-KIWI (wmt22-cometkiwi-da)
- **HuggingFace**: `Unbabel/wmt22-cometkiwi-da`
- **Type**: Reference-free (quality estimation)
- **Score Range**: 0-1 (higher = better)
- **Architecture**: InfoXLM-based
- **Languages**: 94 languages supported

### LLM as Judge - Claude 4.5 Family
All Claude 4.5 models use Amazon Bedrock Converse API with identical evaluation criteria.

#### Claude Sonnet 4.5 (Balanced)
- **Model**: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Characteristics**: Optimal balance of performance, speed, and cost
- **Best for**: General-purpose translation evaluation

#### Claude Haiku 4.5 (Fast)
- **Model**: `global.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Characteristics**: Fastest response times, cost-effective
- **Best for**: High-volume evaluation, rapid prototyping

#### Claude Opus 4.5 (Advanced)
- **Model**: `global.anthropic.claude-opus-4-5-20251101-v1:0`
- **Characteristics**: Most sophisticated reasoning and accuracy
- **Best for**: Critical applications requiring highest precision

**Common Evaluation Criteria**: Accuracy, Fluency, Terminology, Style/Register, Locale

## Common Commands

### Environment Setup
```bash
cd setup
./create_env.sh eval_translation
```

### Required Authentication
```bash
# HuggingFace login required before running any evaluations
huggingface-cli login

# AWS credentials required for LLM as judge (Claude via Bedrock)
aws configure
# or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
```

### Running Evaluations
```bash
# Run individual model evaluations
cd script
uv run eval_cometkiwi.py      # COMET-KIWI on sample data
uv run eval_metricx.py        # MetricX-24 on sample data

# Run two-model comparison on quality test data
uv run compare_models.py      # Compare MetricX-24 vs COMET-KIWI

# Run three-model comparison including LLM as judge
uv run compare_three_models.py  # Compare MetricX vs COMET vs Sonnet 4.5

# Run five-model comparison with all Claude 4.5 models
uv run compare_five_models.py   # Compare all five methods
```

### Testing
No specific test framework is configured. Evaluation scripts serve as the primary validation method.

## Quality Test Results

Tested on 14 samples with various error types (Korean -> English).

### Scores by Error Type (Normalized 0-1, higher = better)

| Error Type | COMET-KIWI | MetricX-24 | Better Detector |
|------------|------------|------------|-----------------|
| good | 0.87 | 0.95 | Both |
| mistranslation | 0.67 | 0.63 | MetricX |
| undertranslation | 0.76 | 0.70 | MetricX |
| overtranslation | 0.62 | 0.92 | COMET |
| grammar | 0.84 | 0.91 | COMET |
| literal | 0.58 | 0.89 | COMET |
| unrelated | 0.52 | 0.58 | Both |
| empty | 0.84 | 0.86 | Neither |
| gibberish | 0.38 | 0.73 | COMET |

### Accuracy (threshold=0.7)
- **COMET-KIWI: 57.1%** (8/14)
- **MetricX-24: 35.7%** (5/14)

### Model Strengths & Weaknesses

| Model | Strengths | Weaknesses |
|-------|-----------|------------|
| COMET-KIWI | Detects gibberish, literal, overtranslation | Misses empty translations |
| MetricX-24 | Good on semantic errors (mistranslation) | Misses stylistic errors (grammar, literal) |

### Recommendation
- **COMET-KIWI** is more conservative and better at detecting various error types
- **MetricX-24** tends to give high scores even for problematic translations
- Use both models together for best results

## Normalization

MetricX-24 scores normalized to match COMET-KIWI scale:
```python
normalized = 1.0 - (raw_score / 25.0)
```

## Key Architecture

### Core Components
- **util.py** - Common utilities including HuggingFace authentication check and test data
- **eval_cometkiwi.py** - COMET-KIWI model evaluation script 
- **eval_metricx.py** - MetricX-24 model evaluation script
- **compare_models.py** - Two-model comparison (MetricX vs COMET-KIWI)
- **compare_three_models.py** - Three-model comparison (adds Claude Sonnet 4.5)
- **compare_five_models.py** - Five-model comparison (all methods including Claude family)

### Data Management
- Sample data is hardcoded in `util.py` with Korean→English translation pairs
- Quality test data includes various error types: mistranslation, undertranslation, overtranslation, grammar, literal, unrelated, empty, gibberish
- Score normalization: MetricX-24 scores (0-25) are normalized to COMET-KIWI scale (0-1) using `1.0 - (score / 25.0)`

### Dependencies
- `torch` for GPU acceleration
- `transformers` for MetricX-24 model loading
- `unbabel-comet` for COMET-KIWI evaluation
- `boto3` for Amazon Bedrock API access
- `uv` for package management and script execution

## Using XXL Model (Multi-GPU)

For better accuracy, use MetricX-24 XXL on a multi-GPU machine.

### Requirements
- **4x GPU** with 24GB+ VRAM each (e.g., 4x L4, 4x A10G, 4x A100)
- **Model**: `google/metricx-24-hybrid-xxl-v2p6-bfloat16` (~22GB)

### Code Changes in `eval_metricx.py`

```python
# Change model name
MODEL_NAME = "google/metricx-24-hybrid-xxl-v2p6-bfloat16"

# Use device_map for multi-GPU
model = MT5ForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",  # Automatically distribute across GPUs
)
# Remove: model.to(device)
```

### Model Size Comparison

| Model | Parameters | VRAM Required | Accuracy |
|-------|------------|---------------|----------|
| Large | ~580M | ~3GB | Good |
| XL | ~3.7B | ~8GB | Better |
| XXL | ~11B | ~22GB (bfloat16) | Best |

### Check Available GPUs

```bash
nvidia-smi --query-gpu=index,name,memory.total --format=csv
```

### Expected Output (4x L4)
```
index, name, memory.total [MiB]
0, NVIDIA L4, 23034 MiB
1, NVIDIA L4, 23034 MiB
2, NVIDIA L4, 23034 MiB
3, NVIDIA L4, 23034 MiB
```

## References

- [MetricX-24 Paper](https://aclanthology.org/2024.wmt-1.35)
- [MetricX GitHub](https://github.com/google-research/metricx)
- [COMET-KIWI Paper](https://aclanthology.org/2022.wmt-1.60)
- [WMT24 Metrics Task](https://www2.statmt.org/wmt24/metrics-task.html)
