"""
Translation Evaluation using LLM as Judge (Claude 4.5 Family)

This module provides standalone evaluation of translation quality using Claude 4.5 models
as an LLM judge through Amazon Bedrock. It evaluates translations based on accuracy,
fluency, terminology, style/register, and locale considerations.

Usage:
    cd script
    uv run eval_llm_judge.py [--model MODEL_NAME]
    
    Available models:
    - sonnet4.5 (default): Balanced performance
    - opus4.5: Most advanced, best for nuanced evaluation  
    - haiku4.5: Fastest, good for basic evaluation

Examples:
    uv run eval_llm_judge.py                    # Uses Sonnet 4.5 (default)
    uv run eval_llm_judge.py --model opus4.5   # Uses Opus 4.5
    uv run eval_llm_judge.py --model haiku4.5  # Uses Haiku 4.5

Requirements:
    - AWS credentials configured with Bedrock access
    - boto3 package installed
"""

import argparse
import json
import sys
from typing import Tuple

from util import (
    check_hf_login, 
    get_quality_test_data, 
    print_detailed_results,
    create_bedrock_client,
    evaluate_single_claude
)

# Model configurations
CLAUDE_MODELS = {
    'sonnet4.5': {
        'id': 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'name': 'Claude Sonnet 4.5',
        'description': 'Balanced performance for comprehensive evaluation'
    },
    'opus4.5': {
        'id': 'global.anthropic.claude-opus-4-5-20251101-v1:0', 
        'name': 'Claude Opus 4.5',
        'description': 'Most advanced model for nuanced translation assessment'
    },
    'haiku4.5': {
        'id': 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
        'name': 'Claude Haiku 4.5', 
        'description': 'Fast and efficient for basic translation quality checking'
    }
}

REGION_NAME = "us-west-2"


# All Claude evaluation functionality has been moved to util.py for reuse


def evaluate(data: list[dict], model_id: str, model_name: str, verbose: bool = True) -> Tuple[list[float], float, list[str]]:
    """
    Evaluate translations using Claude 4.5 family as LLM judge.
    
    Args:
        data: List of dicts with 'src' and 'mt' keys
        model_id: Bedrock model ID for Claude
        model_name: Human-readable model name for display
        verbose: Whether to print progress and justifications
        
    Returns:
        Tuple of (scores list, system score, justifications list)
        Scores range 0-1 (higher = better)
    """
    # Initialize Bedrock client using shared utility
    try:
        bedrock_client = create_bedrock_client(REGION_NAME)
        if verbose:
            print(f"Bedrock client initialized for region: {REGION_NAME}")
    except Exception as e:
        # Return neutral scores on error
        return [0.5] * len(data), 0.5, ["Error: Failed to initialize client"] * len(data)

    scores = []
    justifications = []
    
    if verbose:
        print(f"Evaluating {len(data)} translations with {model_name}...")
    
    for i, item in enumerate(data):
        if verbose:
            print(f"Processing {i+1}/{len(data)}:")
            print(f"  Source (Korean): {item['src']}")
            print(f"  Translation (English): {item['mt']}")
        
        score, justification = evaluate_single_claude(bedrock_client, model_id, item['src'], item['mt'])
        scores.append(score)
        justifications.append(justification)
        
        if verbose:
            # Determine status and get error type
            expected_quality = item.get('quality', 'unknown')
            error_type = item.get('error_type') or 'none'
            
            if expected_quality == 'good':
                status = "✓ Correct" if score >= 0.7 else "✗ Missed"
            else:  # expected_quality == 'bad'
                status = "✓ Correct" if score < 0.7 else "✗ Missed"
            
            print(f"  Score: {score:.4f}")
            print(f"  Status: {status}")
            print(f"  Error Type: {error_type}")
            # Show justification for all scores
            print(f"  Justification: {justification}")
            print()  # Add blank line for readability
    
    system_score = sum(scores) / len(scores) if scores else 0.0
    
    return scores, system_score, justifications


def parse_arguments():
    """Parse command line arguments for model selection."""
    parser = argparse.ArgumentParser(
        description="Translation Quality Evaluation using Claude 4.5 Family as LLM Judge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Models:
  sonnet4.5   Claude Sonnet 4.5 - Balanced performance (default)
  opus4.5     Claude Opus 4.5 - Most advanced, best for nuanced evaluation  
  haiku4.5    Claude Haiku 4.5 - Fastest, good for basic evaluation

Examples:
  python eval_llm_judge.py                    # Uses Sonnet 4.5
  python eval_llm_judge.py --model opus4.5   # Uses Opus 4.5
  python eval_llm_judge.py --model haiku4.5  # Uses Haiku 4.5
        """
    )
    
    parser.add_argument(
        '--model', 
        choices=list(CLAUDE_MODELS.keys()),
        default='sonnet4.5',
        help='Claude model to use for evaluation (default: sonnet4.5)'
    )
    
    return parser.parse_args()


def main():
    """Main evaluation function with model selection and detailed results display."""
    args = parse_arguments()
    
    # Get selected model configuration
    model_config = CLAUDE_MODELS[args.model]
    model_id = model_config['id']
    model_name = model_config['name']
    model_description = model_config['description']
    
    check_hf_login()

    print("=" * 80)
    print(f"LLM as Judge Evaluation using {model_name}")
    print(f"Description: {model_description}")
    print("Score range: 0-1 (higher = better)")
    print("=" * 80)

    # Use quality test data instead of sample data
    data = get_quality_test_data()
    scores, system_score, justifications = evaluate(data, model_id, model_name)

    # Display detailed results with all requested information
    print_detailed_results(data, scores, justifications, f"{model_name} (LLM Judge)")
    
    print(f"\nModel Details:")
    print(f"  Model: {args.model}")
    print(f"  Model ID: {model_id}")
    print(f"  Region: {REGION_NAME}")
    print(f"  Description: {model_description}")
    print(f"  Evaluation Criteria: Accuracy, Fluency, Terminology, Style/Register, Locale")
    print(f"  Test Examples: {len(data)} diverse translation scenarios")


if __name__ == "__main__":
    main()