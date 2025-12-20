# Translation Evaluation Project

## Overview
This project evaluates machine translation quality using two state-of-the-art metrics:

1. **MetricX-24 Hybrid XL** (Google)
2. **COMET-KIWI** (Unbabel)

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

## Setup

```bash
cd setup
./create_env.sh eval_translation
```

## Run

```bash
# Login to HuggingFace (required)
huggingface-cli login

# Run individual evaluations
cd script
uv run eval_cometkiwi.py
uv run eval_metricx.py

# Run comparison on quality test data
uv run compare_models.py
```

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

## Project Structure

```
24_evaluate_translation/
├── script/
│   ├── util.py              # Common utilities
│   ├── eval_cometkiwi.py    # COMET-KIWI evaluation
│   ├── eval_metricx.py      # MetricX-24 evaluation
│   └── compare_models.py    # Side-by-side comparison
├── setup/
│   ├── pyproject.toml
│   └── create_env.sh
├── .gitignore
├── claude.md
├── README.md
├── pyproject.toml -> setup/pyproject.toml
└── uv.lock -> setup/uv.lock
```

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
