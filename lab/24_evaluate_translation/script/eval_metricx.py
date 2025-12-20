"""
Translation Evaluation using MetricX-24

Run:
    cd script
    uv run eval_metricx.py
"""

import torch
from transformers import AutoTokenizer, MT5ForConditionalGeneration

from util import check_hf_login, get_sample_data, print_results

MODEL_NAME = "google/metricx-24-hybrid-xl-v2p6"
TOKENIZER_NAME = "google/mt5-xl"
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


def evaluate(data: list[dict], use_reference: bool = False) -> tuple[list[float], float]:
    """
    Evaluate translations using MetricX-24 (reference-free by default).

    Args:
        data: List of dicts with 'src' and 'mt' keys
        use_reference: If True, use reference-based evaluation

    Returns:
        Tuple of (scores list, system score)
        Scores range 0-25 (lower = better)
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print(f"Loading tokenizer: {TOKENIZER_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

    print(f"Loading model: {MODEL_NAME}")
    model = MT5ForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
    )
    model.to(device)
    model.eval()

    scores = []

    with torch.no_grad():
        for item in data:
            ref = item.get("ref", "") if use_reference else ""
            input_text = make_input(item["src"], item["mt"], ref)

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                max_length=MAX_INPUT_LENGTH,
                truncation=True,
                padding=True,
            ).to(device)

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
            score = logits[:, 0, PREDICTION_TOKEN_ID].item()

            # Clamp to valid range [0, 25]
            score = max(0.0, min(25.0, score))
            scores.append(score)

    system_score = sum(scores) / len(scores)
    return scores, system_score


def main():
    check_hf_login()

    print("=" * 60)
    print("MetricX-24 Evaluation (Reference-free / QE mode)")
    print("Score range: 0-25 (lower = better)")
    print("=" * 60)

    data = get_sample_data()
    scores, system_score = evaluate(data)

    # Print raw scores
    print_results(data, scores, system_score, "MetricX-24 (Raw)")

    # Print normalized scores (comparable to COMET-KIWI)
    normalized_scores = [normalize_score(s) for s in scores]
    normalized_system = normalize_score(system_score)

    print("\n" + "=" * 60)
    print("Normalized scores (0-1, higher = better)")
    print("Comparable to COMET-KIWI scale")
    print("=" * 60)

    print_results(data, normalized_scores, normalized_system, "MetricX-24 (Normalized)")


if __name__ == "__main__":
    main()
