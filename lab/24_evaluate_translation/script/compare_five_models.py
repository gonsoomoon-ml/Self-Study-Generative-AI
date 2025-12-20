"""
Comprehensive Translation Quality Evaluation Comparison

This module compares five state-of-the-art translation evaluation methods:
1. MetricX-24 XXL - Google's multilingual translation metric (mT5-based)
2. COMET-KIWI - Unbabel's quality estimation model (InfoXLM-based)  
3. Claude Sonnet 4.5 - Anthropic's balanced LLM as judge
4. Claude Haiku 4.5 - Anthropic's fast LLM as judge
5. Claude Opus 4.5 - Anthropic's most advanced LLM as judge

The comparison evaluates each method's ability to correctly identify translation quality
across different error types including accuracy, fluency, terminology, style, and locale issues.

Usage:
    cd script
    uv run compare_five_models.py

Requirements:
    - CUDA-capable GPU for MetricX-24 and COMET-KIWI
    - HuggingFace authentication (huggingface-cli login)
    - AWS credentials with Bedrock access for Claude models
"""

import torch
from typing import List, Dict
from comet import download_model, load_from_checkpoint
from transformers import AutoTokenizer, MT5ForConditionalGeneration

from util import (
    check_hf_login, 
    get_quality_test_data,
    create_bedrock_client,
    evaluate_single_claude,
    print_detailed_results
)

# MetricX settings
METRICX_MODEL = "google/metricx-24-hybrid-xxl-v2p6"
METRICX_TOKENIZER = "google/mt5-xxl"
METRICX_TOKEN_ID = 250089

# COMET settings
COMET_MODEL = "Unbabel/wmt22-cometkiwi-da"

# Claude settings
CLAUDE_SONNET_MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
CLAUDE_HAIKU_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
CLAUDE_OPUS_MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"


def normalize_metricx(score: float) -> float:
    """
    Normalize MetricX score to 0-1 scale (higher = better).
    
    MetricX raw scores range from 0-25 where lower is better.
    This function inverts and normalizes to match other metrics.
    
    Args:
        score: Raw MetricX score (0-25, lower = better)
        
    Returns:
        Normalized score (0-1, higher = better)
    """
    return 1.0 - (score / 25.0)


def run_metricx(data: List[Dict[str, str]], verbose: bool = False) -> tuple[List[float], List[str]]:
    """
    Evaluate translations using MetricX-24 XXL model.
    
    Args:
        data: List of dicts with 'src' and 'mt' keys
        verbose: Whether to show detailed processing output
        
    Returns:
        Tuple of (raw MetricX scores (0-25, lower = better), justifications)
    """
    print("Loading MetricX-24 XXL...")
    print(f"Model: {METRICX_MODEL}")
    
    tokenizer = AutoTokenizer.from_pretrained(METRICX_TOKENIZER)
    model = MT5ForConditionalGeneration.from_pretrained(
        METRICX_MODEL, 
        torch_dtype=torch.float16,
        device_map="auto"  # Automatically distribute across GPUs
    )
    model.eval()

    scores = []
    justifications = ["No reasoning provided (MetricX-24 is a neural metric)"] * len(data)
    
    if verbose:
        print(f"Evaluating {len(data)} translations with MetricX-24...")
    
    with torch.no_grad():
        for i, item in enumerate(data):
            if verbose:
                print(f"Processing {i+1}/{len(data)}:")
                print(f"  Source (Korean): {item['src']}")
                print(f"  Translation (English): {item['mt']}")
            
            input_text = f"source: {item['src']} candidate: {item['mt']}"

            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                max_length=1536,
                truncation=True,
                padding=True,
            )

            # Get device from model's first parameter
            device = next(model.parameters()).device
            inputs = inputs.to(device)
            
            inputs["input_ids"] = inputs["input_ids"][:, :-1]
            inputs["attention_mask"] = inputs["attention_mask"][:, :-1]
            decoder_input_ids = torch.zeros((1, 1), dtype=torch.long, device=device)

            outputs = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=decoder_input_ids,
            )

            raw_score = outputs.logits[:, 0, METRICX_TOKEN_ID].item()
            raw_score = max(0.0, min(25.0, raw_score))
            scores.append(raw_score)
            
            if verbose:
                normalized_score = normalize_metricx(raw_score)
                expected_quality = item.get('quality', 'unknown')
                error_type = item.get('error_type') or 'none'
                
                if expected_quality == 'good':
                    status = "✓ Correct" if normalized_score >= 0.7 else "✗ Missed"
                else:  # expected_quality == 'bad'
                    status = "✓ Correct" if normalized_score < 0.7 else "✗ Missed"
                
                print(f"  Score: {normalized_score:.4f}")
                print(f"  Status: {status}")
                print(f"  Error Type: {error_type}")
                print(f"  Justification: Neural quality estimation score (no textual reasoning)")
                print()

    # Clear GPU memory
    del model
    del tokenizer
    torch.cuda.empty_cache()
    print("MetricX-24 evaluation completed.")

    return scores, justifications


def run_cometkiwi(data: List[Dict[str, str]], verbose: bool = False) -> tuple[List[float], List[str]]:
    """
    Evaluate translations using COMET-KIWI model.
    
    Args:
        data: List of dicts with 'src' and 'mt' keys
        verbose: Whether to show detailed processing output
        
    Returns:
        Tuple of (COMET scores (0-1, higher = better), justifications)
    """
    print("Loading COMET-KIWI...")
    print(f"Model: {COMET_MODEL}")
    
    model_path = download_model(COMET_MODEL)
    model = load_from_checkpoint(model_path)

    comet_data = [{"src": item["src"], "mt": item["mt"]} for item in data]
    
    if verbose:
        print(f"Evaluating {len(data)} translations with COMET-KIWI...")
    else:
        print(f"Evaluating {len(data)} translations with batch_size=8...")
    
    output = model.predict(comet_data, batch_size=8, gpus=1)
    scores = output.scores
    justifications = ["No reasoning provided (COMET-KIWI is a neural metric)"] * len(data)
    
    if verbose:
        for i, (item, score) in enumerate(zip(data, scores)):
            print(f"Processing {i+1}/{len(data)}:")
            print(f"  Source (Korean): {item['src']}")
            print(f"  Translation (English): {item['mt']}")
            print(f"  Score: {score:.4f}")
            
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
    
    print("COMET-KIWI evaluation completed.")
    return scores, justifications


def run_claude_judge(data: List[Dict[str, str]], model_id: str, model_name: str, verbose: bool = False) -> tuple[List[float], List[str]]:
    """
    Evaluate translations using Claude LLM as Judge via Amazon Bedrock.
    Uses shared utilities for consistent behavior across all Claude evaluations.
    
    Args:
        data: List of dicts with 'src' and 'mt' keys
        model_id: Bedrock model ID for Claude
        model_name: Human-readable model name for logging
        verbose: Whether to show detailed processing output
        
    Returns:
        Tuple of (scores (0-1, higher = better), justifications)
    """
    print(f"Loading {model_name} via Bedrock...")
    print(f"Model ID: {model_id}")
    
    try:
        bedrock_client = create_bedrock_client("us-west-2")
        print("Bedrock client initialized successfully.")
    except Exception as e:
        neutral_scores = [0.5] * len(data)
        error_justifications = [f"API Error: {str(e)}"] * len(data)
        return neutral_scores, error_justifications

    scores = []
    justifications = []
    
    if verbose:
        print(f"Evaluating {len(data)} translations with {model_name}...")
    
    for i, item in enumerate(data):
        if verbose:
            print(f"Processing {i+1}/{len(data)}:")
            print(f"  Source (Korean): {item['src']}")
            print(f"  Translation (English): {item['mt']}")
        
        # Use shared evaluation function for consistency
        score, justification = evaluate_single_claude(bedrock_client, model_id, item['src'], item['mt'])
        scores.append(score)
        justifications.append(justification)
        
        if verbose:
            expected_quality = item.get('quality', 'unknown')
            error_type = item.get('error_type') or 'none'
            
            if expected_quality == 'good':
                status = "✓ Correct" if score >= 0.7 else "✗ Missed"
            else:  # expected_quality == 'bad'
                status = "✓ Correct" if score < 0.7 else "✗ Missed"
            
            print(f"  Score: {score:.4f}")
            print(f"  Status: {status}")
            print(f"  Error Type: {error_type}")
            print(f"  Justification: {justification}")
            print()
        else:
            print(f"Evaluating {i+1}/{len(data)} with {model_name}: Score {score:.4f}")
    
    print(f"{model_name} evaluation completed.")
    return scores, justifications


def main():
    """
    Main evaluation function that runs all five translation quality assessment methods
    and provides comprehensive comparison results.
    """
    check_hf_login()

    print("=" * 120)
    print("COMPREHENSIVE TRANSLATION QUALITY EVALUATION COMPARISON")
    print("MetricX-24 XXL | COMET-KIWI | Claude Sonnet 4.5 | Claude Haiku 4.5 | Claude Opus 4.5")
    print("=" * 120)
    print("Evaluating across error types: accuracy, fluency, terminology, style/register, locale")
    print("=" * 120)

    data = get_quality_test_data()

    # Run all five methods (without verbose output for comparison mode)
    print("\n1. Running MetricX-24...")
    metricx_raw, metricx_justifications = run_metricx(data, verbose=False)
    metricx_norm = [normalize_metricx(s) for s in metricx_raw]
    
    print("\n2. Running COMET-KIWI...")
    comet_scores, comet_justifications = run_cometkiwi(data, verbose=False)
    
    print("\n3. Running Claude Sonnet 4.5...")
    sonnet_scores, sonnet_justifications = run_claude_judge(data, CLAUDE_SONNET_MODEL_ID, "Claude Sonnet 4.5", verbose=False)
    
    print("\n4. Running Claude Haiku 4.5...")
    haiku_scores, haiku_justifications = run_claude_judge(data, CLAUDE_HAIKU_MODEL_ID, "Claude Haiku 4.5", verbose=False)
    
    print("\n5. Running Claude Opus 4.5...")
    opus_scores, opus_justifications = run_claude_judge(data, CLAUDE_OPUS_MODEL_ID, "Claude Opus 4.5", verbose=False)

    # Show detailed results for each model
    print("\n" + "=" * 120)
    print("DETAILED RESULTS FOR EACH MODEL")
    print("=" * 120)
    
    print_detailed_results(data, metricx_norm, metricx_justifications, "MetricX-24")
    print_detailed_results(data, comet_scores, comet_justifications, "COMET-KIWI") 
    print_detailed_results(data, sonnet_scores, sonnet_justifications, "Claude Sonnet 4.5")
    print_detailed_results(data, haiku_scores, haiku_justifications, "Claude Haiku 4.5")
    print_detailed_results(data, opus_scores, opus_justifications, "Claude Opus 4.5")

    # Print comparison table
    print("\n" + "=" * 140)
    print("RESULTS (All normalized 0-1, higher = better)")
    print("=" * 140)
    print(f"{'#':<3} {'Quality':<6} {'Error Type':<20} {'COMET':<8} {'MetricX':<8} {'Sonnet':<8} {'Haiku':<8} {'Opus':<8} {'Best':<8} {'Description':<30}")
    print("-" * 140)

    correct_comet = 0
    correct_metricx = 0
    correct_sonnet = 0
    correct_haiku = 0
    correct_opus = 0
    threshold = 0.7  # Below this = bad translation

    for i, item in enumerate(data):
        quality = item["quality"]
        error_type = (item.get("error_type") or "good")[:20]
        comet = comet_scores[i]
        metricx = metricx_norm[i]
        sonnet = sonnet_scores[i]
        haiku = haiku_scores[i]
        opus = opus_scores[i]

        # Check if model correctly identifies quality
        comet_correct = (comet >= threshold) if quality == "good" else (comet < threshold)
        metricx_correct = (metricx >= threshold) if quality == "good" else (metricx < threshold)
        sonnet_correct = (sonnet >= threshold) if quality == "good" else (sonnet < threshold)
        haiku_correct = (haiku >= threshold) if quality == "good" else (haiku < threshold)
        opus_correct = (opus >= threshold) if quality == "good" else (opus < threshold)

        if comet_correct:
            correct_comet += 1
        if metricx_correct:
            correct_metricx += 1
        if sonnet_correct:
            correct_sonnet += 1
        if haiku_correct:
            correct_haiku += 1
        if opus_correct:
            correct_opus += 1

        # Determine best performing model for this example
        scores_dict = {"COMET": comet, "MetricX": metricx, "Sonnet": sonnet, "Haiku": haiku, "Opus": opus}
        if quality == "good":
            best = max(scores_dict, key=scores_dict.get)
        else:
            best = min(scores_dict, key=scores_dict.get)
        
        # Truncate description if too long
        desc = item.get("error_description", "")[:30] + "..." if len(item.get("error_description", "")) > 30 else item.get("error_description", "")

        print(f"{i+1:<3} {quality:<6} {error_type:<20} {comet:<8.4f} {metricx:<8.4f} {sonnet:<8.4f} {haiku:<8.4f} {opus:<8.4f} {best:<8} {desc:<30}")

    # Summary
    total = len(data)
    print("-" * 140)
    print(f"\nAccuracy (threshold={threshold}):")
    print(f"  COMET-KIWI:     {correct_comet}/{total} ({100*correct_comet/total:.1f}%)")
    print(f"  MetricX-24:     {correct_metricx}/{total} ({100*correct_metricx/total:.1f}%)")
    print(f"  Claude Sonnet:  {correct_sonnet}/{total} ({100*correct_sonnet/total:.1f}%)")
    print(f"  Claude Haiku:   {correct_haiku}/{total} ({100*correct_haiku/total:.1f}%)")
    print(f"  Claude Opus:    {correct_opus}/{total} ({100*correct_opus/total:.1f}%)")

    # Group by error type
    print("\n" + "=" * 140)
    print("AVERAGE SCORES BY ERROR TYPE")
    print("=" * 140)

    error_types = {}
    for i, item in enumerate(data):
        et = item.get("error_type") or "good"
        if et not in error_types:
            error_types[et] = {"comet": [], "metricx": [], "sonnet": [], "haiku": [], "opus": []}
        error_types[et]["comet"].append(comet_scores[i])
        error_types[et]["metricx"].append(metricx_norm[i])
        error_types[et]["sonnet"].append(sonnet_scores[i])
        error_types[et]["haiku"].append(haiku_scores[i])
        error_types[et]["opus"].append(opus_scores[i])

    print(f"{'Error Type':<30} {'COMET':<10} {'MetricX':<10} {'Sonnet':<10} {'Haiku':<10} {'Opus':<10}")
    print("-" * 80)
    
    for et in sorted(error_types.keys()):
        comet_avg = sum(error_types[et]["comet"]) / len(error_types[et]["comet"])
        metricx_avg = sum(error_types[et]["metricx"]) / len(error_types[et]["metricx"])
        sonnet_avg = sum(error_types[et]["sonnet"]) / len(error_types[et]["sonnet"])
        haiku_avg = sum(error_types[et]["haiku"]) / len(error_types[et]["haiku"])
        opus_avg = sum(error_types[et]["opus"]) / len(error_types[et]["opus"])
        print(f"{et:<30} {comet_avg:<10.4f} {metricx_avg:<10.4f} {sonnet_avg:<10.4f} {haiku_avg:<10.4f} {opus_avg:<10.4f}")

    # Claude model comparison
    print("\n" + "=" * 80)
    print("CLAUDE 4.5 MODEL COMPARISON")
    print("=" * 80)
    print(f"Model Performance Summary:")
    print(f"  Sonnet 4.5: {100*correct_sonnet/total:.1f}% accuracy - Balanced performance")
    print(f"  Haiku 4.5:  {100*correct_haiku/total:.1f}% accuracy - Fast and efficient") 
    print(f"  Opus 4.5:   {100*correct_opus/total:.1f}% accuracy - Most advanced model")


if __name__ == "__main__":
    main()