"""
Claude 4.5 Family Model Comparison

This module compares three Claude 4.5 models for translation quality evaluation:
1. Claude Sonnet 4.5 - Balanced performance 
2. Claude Haiku 4.5 - Fast and efficient
3. Claude Opus 4.5 - Most advanced model

Usage:
    cd script
    uv run compare_claude_models.py

Requirements:
    - AWS credentials with Bedrock access for Claude models
"""

from util import (
    check_hf_login, 
    get_quality_test_data,
    create_bedrock_client,
    evaluate_single_claude,
    print_detailed_results
)

# Claude settings
CLAUDE_MODELS = {
    'sonnet4.5': {
        'id': 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'name': 'Claude Sonnet 4.5',
        'description': 'Balanced performance for comprehensive evaluation'
    },
    'haiku4.5': {
        'id': 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
        'name': 'Claude Haiku 4.5',
        'description': 'Fast and efficient for basic translation quality checking'
    },
    'opus4.5': {
        'id': 'global.anthropic.claude-opus-4-5-20251101-v1:0',
        'name': 'Claude Opus 4.5',
        'description': 'Most advanced model for nuanced translation assessment'
    }
}


def run_claude_evaluation(data, model_id: str, model_name: str, verbose: bool = True):
    """Evaluate translations using Claude model via Bedrock."""
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
        if not verbose:
            print(f"Evaluating {i+1}/{len(data)} with {model_name}: ", end="", flush=True)
        
        score, justification = evaluate_single_claude(bedrock_client, model_id, item['src'], item['mt'])
        scores.append(score)
        justifications.append(justification)
        
        if not verbose:
            print(f"Score {score:.4f}")
        elif verbose:
            print(f"Processing {i+1}/{len(data)}:")
            print(f"  Source (Korean): {item['src']}")
            print(f"  Translation (English): {item['mt']}")
            
            expected_quality = item.get('quality', 'unknown')
            error_type = item.get('error_type') or 'none'
            
            if expected_quality == 'good':
                status = "✓ Correct" if score >= 0.7 else "✗ Missed"
            else:
                status = "✓ Correct" if score < 0.7 else "✗ Missed"
            
            print(f"  Score: {score:.4f}")
            print(f"  Status: {status}")
            print(f"  Error Type: {error_type}")
            print(f"  Justification: {justification}")
            print()
    
    print(f"{model_name} evaluation completed.")
    return scores, justifications


def main():
    """Main comparison function for Claude 4.5 family models."""
    check_hf_login()

    print("=" * 100)
    print("CLAUDE 4.5 FAMILY MODEL COMPARISON")
    print("Claude Sonnet 4.5 | Claude Haiku 4.5 | Claude Opus 4.5")
    print("=" * 100)
    print("Evaluating across error types: accuracy, fluency, terminology, style/register, locale")
    print("=" * 100)

    data = get_quality_test_data()

    # Run all three Claude models (with brief output for comparison mode)
    print("\n1. Running Claude Sonnet 4.5...")
    sonnet_scores, sonnet_justifications = run_claude_evaluation(
        data, CLAUDE_MODELS['sonnet4.5']['id'], CLAUDE_MODELS['sonnet4.5']['name'], verbose=False
    )
    
    print("\n2. Running Claude Haiku 4.5...")
    haiku_scores, haiku_justifications = run_claude_evaluation(
        data, CLAUDE_MODELS['haiku4.5']['id'], CLAUDE_MODELS['haiku4.5']['name'], verbose=False
    )
    
    print("\n3. Running Claude Opus 4.5...")
    opus_scores, opus_justifications = run_claude_evaluation(
        data, CLAUDE_MODELS['opus4.5']['id'], CLAUDE_MODELS['opus4.5']['name'], verbose=False
    )

    # Show detailed results for each model
    print("\n" + "=" * 120)
    print("DETAILED RESULTS FOR EACH CLAUDE MODEL")
    print("=" * 120)
    
    print_detailed_results(data, sonnet_scores, sonnet_justifications, "Claude Sonnet 4.5")
    print_detailed_results(data, haiku_scores, haiku_justifications, "Claude Haiku 4.5")
    print_detailed_results(data, opus_scores, opus_justifications, "Claude Opus 4.5")

    # Comparison summary
    print("\n" + "=" * 100)
    print("CLAUDE MODEL COMPARISON SUMMARY")
    print("=" * 100)
    
    threshold = 0.7
    total = len(data)
    
    # Calculate accuracy for each model
    sonnet_correct = sum(1 for i, item in enumerate(data) if (
        (item.get('quality') == 'good' and sonnet_scores[i] >= threshold) or
        (item.get('quality') == 'bad' and sonnet_scores[i] < threshold)
    ))
    
    haiku_correct = sum(1 for i, item in enumerate(data) if (
        (item.get('quality') == 'good' and haiku_scores[i] >= threshold) or
        (item.get('quality') == 'bad' and haiku_scores[i] < threshold)
    ))
    
    opus_correct = sum(1 for i, item in enumerate(data) if (
        (item.get('quality') == 'good' and opus_scores[i] >= threshold) or
        (item.get('quality') == 'bad' and opus_scores[i] < threshold)
    ))
    
    print(f"Model Performance (threshold={threshold}):")
    print(f"  Sonnet 4.5: {sonnet_correct}/{total} ({100*sonnet_correct/total:.1f}%) - {CLAUDE_MODELS['sonnet4.5']['description']}")
    print(f"  Haiku 4.5:  {haiku_correct}/{total} ({100*haiku_correct/total:.1f}%) - {CLAUDE_MODELS['haiku4.5']['description']}")
    print(f"  Opus 4.5:   {opus_correct}/{total} ({100*opus_correct/total:.1f}%) - {CLAUDE_MODELS['opus4.5']['description']}")
    
    # Average scores
    sonnet_avg = sum(sonnet_scores) / len(sonnet_scores)
    haiku_avg = sum(haiku_scores) / len(haiku_scores)
    opus_avg = sum(opus_scores) / len(opus_scores)
    
    print(f"\nAverage Scores:")
    print(f"  Sonnet 4.5: {sonnet_avg:.4f}")
    print(f"  Haiku 4.5:  {haiku_avg:.4f}")
    print(f"  Opus 4.5:   {opus_avg:.4f}")
    
    # Best model recommendation
    best_accuracy = max(sonnet_correct, haiku_correct, opus_correct)
    if sonnet_correct == best_accuracy:
        best_model = "Sonnet 4.5"
    elif haiku_correct == best_accuracy:
        best_model = "Haiku 4.5" 
    else:
        best_model = "Opus 4.5"
    
    print(f"\n🏆 Recommended Model: Claude {best_model}")
    print(f"✅ Best balance of accuracy, speed, and cost for translation quality evaluation")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()