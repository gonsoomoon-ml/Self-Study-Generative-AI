"""
Translation Evaluation using MetricX-24

Run:
    cd script
    uv run eval_metricx.py
"""

import torch
from transformers import AutoTokenizer, MT5ForConditionalGeneration

from util import check_hf_login, get_quality_test_data, print_detailed_results

MODEL_NAME = "google/metricx-24-hybrid-xxl-v2p6"
TOKENIZER_NAME = "google/mt5-xxl"
MAX_INPUT_LENGTH = 1536
PREDICTION_TOKEN_ID = 250089  # <extra_id_10> token


def normalize_score(score: float) -> float:
    """
    Normalize MetricX score to 0-1 scale (higher = better).

    MetricX: 0-25 (lower = better)
    Normalized: 0-1 (higher = better, comparable to COMET-KIWI)
    """
    return 1.0 - (score / 25.0)


def make_input(source: str, hypothesis: str, reference: str = "") -> str:
    """
    Create input string for MetricX model.

    For QE mode (reference-free), pass empty reference.
    """
    if reference:
        return f"source: {source} candidate: {hypothesis} reference: {reference}"
    else:
        return f"source: {source} candidate: {hypothesis}"


def evaluate(data: list[dict], use_reference: bool = False, verbose: bool = True) -> tuple[list[float], float, list[str]]:
    """
    Evaluate translations using MetricX-24 (reference-free by default).

    Args:
        data: List of dicts with 'src' and 'mt' keys
        use_reference: If True, use reference-based evaluation
        verbose: Whether to show processing output

    Returns:
        Tuple of (scores list, system score, justifications list)
        Scores range 0-25 (lower = better)
    """
    print(f"Loading tokenizer: {TOKENIZER_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

    print(f"Loading model: {MODEL_NAME} (XXL with multi-GPU support)")
    model = MT5ForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"  # Automatically distribute across GPUs
    )
    model.eval()

    if verbose:
        print(f"Evaluating {len(data)} translations with MetricX-24...")

    scores = []
    # MetricX doesn't provide textual justifications, so create placeholder
    justifications = ["No reasoning provided (MetricX-24 is a neural metric)"] * len(data)

    with torch.no_grad():
        for i, item in enumerate(data):
            ref = item.get("ref", "") if use_reference else ""
            input_text = make_input(item["src"], item["mt"], ref)

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                max_length=MAX_INPUT_LENGTH,
                truncation=True,
                padding=True,
            )

            # Get device from model's first parameter
            device = next(model.parameters()).device
            inputs = inputs.to(device)

            # Remove EOS token as per MetricX implementation
            inputs["input_ids"] = inputs["input_ids"][:, :-1]
            inputs["attention_mask"] = inputs["attention_mask"][:, :-1]

            # Create decoder input (single token: 0)
            decoder_input_ids = torch.zeros((1, 1), dtype=torch.long, device=device)

            # Forward pass
            outputs = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=decoder_input_ids,
            )

            # Extract score from logits at <extra_id_10> position
            logits = outputs.logits
            raw_score = logits[:, 0, PREDICTION_TOKEN_ID].item()

            # Clamp to valid range [0, 25]
            raw_score = max(0.0, min(25.0, raw_score))
            scores.append(raw_score)
            
            if verbose:
                # Normalize score for display (0-1, higher = better)
                normalized_score = normalize_score(raw_score)
                
                print(f"Processing {i+1}/{len(data)}:")
                print(f"  Source (Korean): {item['src']}")
                print(f"  Translation (English): {item['mt']}")
                print(f"  Score: {normalized_score:.4f}")
                
                # Determine status and get error type
                expected_quality = item.get('quality', 'unknown')
                error_type = item.get('error_type') or 'none'
                
                if expected_quality == 'good':
                    status = "✓ Correct" if normalized_score >= 0.7 else "✗ Missed"
                else:  # expected_quality == 'bad'
                    status = "✓ Correct" if normalized_score < 0.7 else "✗ Missed"
                
                print(f"  Status: {status}")
                print(f"  Error Type: {error_type}")
                print(f"  Justification: Neural quality estimation score (no textual reasoning)")
                print()

    system_score = sum(scores) / len(scores)
    return scores, system_score, justifications


def main():
    check_hf_login()

    print("=" * 80)
    print("MetricX-24 Evaluation (Reference-free / QE mode)")
    print("Score range: 0-25 (lower = better), normalized to 0-1 (higher = better)")
    print("=" * 80)

    data = get_quality_test_data()
    raw_scores, raw_system_score, justifications = evaluate(data)

    # Normalize scores for final display (0-1, higher = better)
    normalized_scores = [normalize_score(s) for s in raw_scores]
    
    # Display detailed results with normalized scores
    print_detailed_results(data, normalized_scores, justifications, "MetricX-24")


if __name__ == "__main__":
    main()
