# Translation Evaluation: MetricX-24 vs COMET-KIWI

This project compares two state-of-the-art translation quality evaluation models.

## Models

| Model | Provider | Type | Score Range | Interpretation |
|-------|----------|------|-------------|----------------|
| [MetricX-24 Hybrid XL](https://huggingface.co/google/metricx-24-hybrid-xl-v2p6) | Google | Reference-free | 0-25 | Lower = Better |
| [COMET-KIWI](https://huggingface.co/Unbabel/wmt22-cometkiwi-da) | Unbabel | Reference-free | 0-1 | Higher = Better |

## Setup

```bash
cd setup
./create_env.sh eval_translation
```

## Run

```bash
# Login to HuggingFace (required)
huggingface-cli login

# Run evaluations
cd script
uv run eval_cometkiwi.py
uv run eval_metricx.py
```

## Comparison Results

Test data: Korean → English translations (5 samples)

### Normalized Scores (0-1, higher = better)

| # | Topic | Length | COMET-KIWI | MetricX-24 |
|---|-------|--------|------------|------------|
| 1 | Weather | Short | 0.87 | 0.95 |
| 2 | Greeting | Short | 0.88 | 0.94 |
| 3 | Project description | Short | 0.89 | 0.97 |
| 4 | Agentic AI | Long (~500 tokens) | 0.77 | 0.92 |
| 5 | Korean food culture | Long (~500 tokens) | 0.70 | 0.91 |
| **System** | **Average** | | **0.82** | **0.94** |

### Raw MetricX-24 Scores (0-25, lower = better)

| # | Topic | Raw Score |
|---|-------|-----------|
| 1 | Weather | 1.37 |
| 2 | Greeting | 1.55 |
| 3 | Project description | 0.83 |
| 4 | Agentic AI | 2.09 |
| 5 | Korean food culture | 2.21 |
| **System** | **Average** | **1.61** |

## Key Observations

1. **MetricX-24 gives higher scores overall** - More optimistic about translation quality
2. **Both models agree on ranking** - Short sentences score better than long ones
3. **MetricX-24 is more consistent** - Smaller variance between short and long texts
4. **COMET-KIWI is more conservative** - Gives lower scores especially for long texts

## Normalization

MetricX-24 scores are normalized to match COMET-KIWI scale:

```python
normalized = 1.0 - (raw_score / 25.0)
```

## Project Structure

```
24_evaluate_translation/
├── script/
│   ├── util.py              # Common utilities
│   ├── eval_cometkiwi.py    # COMET-KIWI evaluation
│   └── eval_metricx.py      # MetricX-24 evaluation
├── setup/
│   ├── pyproject.toml       # Dependencies
│   └── create_env.sh        # Environment setup
├── README.md
├── claude.md
└── .gitignore
```

## References

- [MetricX-24 Paper](https://aclanthology.org/2024.wmt-1.35)
- [MetricX GitHub](https://github.com/google-research/metricx)
- [COMET-KIWI Paper](https://aclanthology.org/2022.wmt-1.60)
