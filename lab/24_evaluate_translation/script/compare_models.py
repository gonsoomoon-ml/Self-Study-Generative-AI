"""
Compare MetricX-24 and COMET-KIWI on various translation quality levels.

Run:
    cd script
    uv run compare_models.py
"""

import torch
from comet import download_model, load_from_checkpoint
from transformers import AutoTokenizer, MT5ForConditionalGeneration

from util import check_hf_login, get_quality_test_data

# MetricX settings
METRICX_MODEL = "google/metricx-24-hybrid-xl-v2p6"
METRICX_TOKENIZER = "google/mt5-xl"
METRICX_TOKEN_ID = 250089

# COMET settings
COMET_MODEL = "Unbabel/wmt22-cometkiwi-da"


def normalize_metricx(score: float) -> float:
    """Normalize MetricX score to 0-1 (higher = better)."""
    return 1.0 - (score / 25.0)


def run_metricx(data: list[dict]) -> list[float]:
    """Run MetricX-24 evaluation."""
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("Loading MetricX-24...")
    tokenizer = AutoTokenizer.from_pretrained(METRICX_TOKENIZER)
    model = MT5ForConditionalGeneration.from_pretrained(
        METRICX_MODEL, torch_dtype=torch.float16
    )
    model.to(device)
    model.eval()

    scores = []
    with torch.no_grad():
        for item in data:
            input_text = f"source: {item['src']} candidate: {item['mt']}"

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                max_length=1536,
                truncation=True,
                padding=True,
            ).to(device)

            inputs["input_ids"] = inputs["input_ids"][:, :-1]
            inputs["attention_mask"] = inputs["attention_mask"][:, :-1]
            decoder_input_ids = torch.zeros((1, 1), dtype=torch.long, device=device)

            outputs = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=decoder_input_ids,
            )

            score = outputs.logits[:, 0, METRICX_TOKEN_ID].item()
            score = max(0.0, min(25.0, score))
            scores.append(score)

    # Clear GPU memory
    del model
    torch.cuda.empty_cache()

    return scores


def run_cometkiwi(data: list[dict]) -> list[float]:
    """Run COMET-KIWI evaluation."""
    print("Loading COMET-KIWI...")
    model_path = download_model(COMET_MODEL)
    model = load_from_checkpoint(model_path)

    comet_data = [{"src": item["src"], "mt": item["mt"]} for item in data]
    output = model.predict(comet_data, batch_size=8, gpus=1)

    return output.scores


def main():
    check_hf_login()

    print("=" * 80)
    print("Translation Quality Comparison: MetricX-24 vs COMET-KIWI")
    print("=" * 80)

    data = get_quality_test_data()

    # Run both models
    metricx_raw = run_metricx(data)
    metricx_norm = [normalize_metricx(s) for s in metricx_raw]
    comet_scores = run_cometkiwi(data)

    # Print comparison table
    print("\n" + "=" * 80)
    print("RESULTS (Normalized 0-1, higher = better)")
    print("=" * 80)
    print(f"{'#':<3} {'Quality':<6} {'Error Type':<16} {'COMET':<8} {'MetricX':<8} {'Agree?':<6}")
    print("-" * 80)

    correct_comet = 0
    correct_metricx = 0
    threshold = 0.7  # Below this = bad translation

    for i, item in enumerate(data):
        quality = item["quality"]
        error_type = item["error_type"] or "-"
        comet = comet_scores[i]
        metricx = metricx_norm[i]

        # Check if model correctly identifies quality
        comet_pred = "good" if comet >= threshold else "bad"
        metricx_pred = "good" if metricx >= threshold else "bad"

        comet_correct = comet_pred == quality
        metricx_correct = metricx_pred == quality

        if comet_correct:
            correct_comet += 1
        if metricx_correct:
            correct_metricx += 1

        agree = "✓" if comet_correct and metricx_correct else "✗"

        print(f"{i+1:<3} {quality:<6} {error_type:<16} {comet:<8.4f} {metricx:<8.4f} {agree:<6}")

    # Summary
    total = len(data)
    print("-" * 80)
    print(f"\nAccuracy (threshold={threshold}):")
    print(f"  COMET-KIWI: {correct_comet}/{total} ({100*correct_comet/total:.1f}%)")
    print(f"  MetricX-24: {correct_metricx}/{total} ({100*correct_metricx/total:.1f}%)")

    # Group by error type
    print("\n" + "=" * 80)
    print("SCORES BY ERROR TYPE")
    print("=" * 80)

    error_types = {}
    for i, item in enumerate(data):
        et = item["error_type"] or "good"
        if et not in error_types:
            error_types[et] = {"comet": [], "metricx": []}
        error_types[et]["comet"].append(comet_scores[i])
        error_types[et]["metricx"].append(metricx_norm[i])

    print(f"{'Error Type':<20} {'COMET (avg)':<15} {'MetricX (avg)':<15}")
    print("-" * 50)
    for et in ["good", "mistranslation", "undertranslation", "overtranslation",
               "grammar", "literal", "unrelated", "empty", "gibberish"]:
        if et in error_types:
            comet_avg = sum(error_types[et]["comet"]) / len(error_types[et]["comet"])
            metricx_avg = sum(error_types[et]["metricx"]) / len(error_types[et]["metricx"])
            print(f"{et:<20} {comet_avg:<15.4f} {metricx_avg:<15.4f}")


if __name__ == "__main__":
    main()
