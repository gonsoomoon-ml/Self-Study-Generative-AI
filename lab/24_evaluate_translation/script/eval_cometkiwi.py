"""
Translation Evaluation using COMET-KIWI

Run:
    cd script
    uv run eval_cometkiwi.py
"""

from comet import download_model, load_from_checkpoint

from util import check_hf_login, get_quality_test_data, print_detailed_results

MODEL_NAME = "Unbabel/wmt22-cometkiwi-da"


def evaluate(data: list[dict], verbose: bool = True) -> tuple[list[float], float, list[str]]:
    """
    Evaluate translations using COMET-KIWI (reference-free).

    Args:
        data: List of dicts with 'src' and 'mt' keys
        verbose: Whether to show processing output

    Returns:
        Tuple of (scores list, system score, justifications list)
        Scores range 0-1 (higher = better)
    """
    model_path = download_model(MODEL_NAME)
    model = load_from_checkpoint(model_path)
    
    if verbose:
        print(f"Evaluating {len(data)} translations with COMET-KIWI...")
    
    output = model.predict(data, batch_size=8, gpus=1)
    scores = output.scores
    system_score = output.system_score
    
    # COMET-KIWI doesn't provide textual justifications, so create placeholder
    justifications = ["No reasoning provided (COMET-KIWI is a neural metric)"] * len(data)
    
    if verbose:
        for i, (item, score) in enumerate(zip(data, scores)):
            print(f"Processing {i+1}/{len(data)}:")
            print(f"  Source (Korean): {item['src']}")
            print(f"  Translation (English): {item['mt']}")
            print(f"  Score: {score:.4f}")
            
            # Determine status and get error type
            expected_quality = item.get('quality', 'unknown')
            error_type = item.get('error_type') or 'none'
            
            if expected_quality == 'good':
                status = "✓ Correct" if score >= 0.7 else "✗ Missed"
            else:  # expected_quality == 'bad'
                status = "✓ Correct" if score < 0.7 else "✗ Missed"
            
            print(f"  Status: {status}")
            print(f"  Error Type: {error_type}")
            print(f"  Justification: Neural quality estimation score (no textual reasoning)")
            print()
    
    return scores, system_score, justifications


def main():
    check_hf_login()

    print("=" * 80)
    print("COMET-KIWI Evaluation (Reference-free)")
    print("Score range: 0-1 (higher = better)")
    print("=" * 80)

    data = get_quality_test_data()
    scores, system_score, justifications = evaluate(data)

    # Display detailed results with all requested information
    print_detailed_results(data, scores, justifications, "COMET-KIWI")


if __name__ == "__main__":
    main()
