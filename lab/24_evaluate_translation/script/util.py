"""
Common utilities for translation evaluation
"""

import boto3
import json
import os
import sys
import time
from typing import Tuple, Optional

from huggingface_hub import HfFolder


def check_hf_login():
    """Check if user is logged in to HuggingFace Hub."""
    token = HfFolder.get_token()
    if token is None:
        print("ERROR: HuggingFace login required.")
        print()
        print("Please run:")
        print("  uv run huggingface-cli login")
        print()
        print("Or set token:")
        print("  uv run huggingface-cli login --token YOUR_TOKEN")
        sys.exit(1)
    print("HuggingFace login: OK")




def get_quality_test_data() -> list[dict]:
    """
    Return test data with various quality levels for model comparison.
    Loads from JSON file for better maintainability.
    """
    # Get the project root directory (parent of script folder)
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    json_path = os.path.join(project_root, "data", "quality_test_data.json")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["test_examples"]
    except FileNotFoundError:
        print(f"ERROR: Test data file not found: {json_path}")
        sys.exit(1)


def create_bedrock_client(region_name: str = "us-west-2"):
    """
    Create and return a configured Bedrock runtime client.
    
    Args:
        region_name: AWS region for Bedrock service
        
    Returns:
        Boto3 Bedrock runtime client
        
    Raises:
        Exception: If client initialization fails
    """
    try:
        client = boto3.client(service_name="bedrock-runtime", region_name=region_name)
        return client
    except Exception as e:
        print(f"Error initializing Bedrock client: {e}")
        print("Make sure AWS credentials are configured")
        raise


def create_claude_evaluation_prompt(source: str, translation: str) -> str:
    """
    Create standardized evaluation prompt for Claude LLM as judge.
    
    Args:
        source: Korean source text
        translation: English translation to evaluate
        
    Returns:
        Formatted prompt string for Claude evaluation (requests Korean justification)
    """
    return f"""당신은 전문 번역 품질 평가자입니다. 모바일 앱 인터페이스의 한국어에서 영어로 번역된 텍스트의 품질을 평가해주세요.

다음 기준으로 번역을 평가하세요:
1. 정확성: 번역이 올바른 의미를 전달하는가?
2. 유창성: 영어가 자연스럽고 문법적으로 올바른가?
3. 용어: 기술 용어가 올바르게 번역되었는가?
4. 문체/격식: 격식 수준이 적절한가?
5. 지역화: 문화적, 형식적 관례가 올바른가?

원문 (한국어): {source}
번역문 (영어): {translation}

정확성이 사용자 안전과 경험에 중요한 모바일 앱 UI 텍스트 맥락에서 이 번역을 고려하세요.

0.0에서 1.0 사이의 점수로 평가해주세요:
- 0.0 = 매우 나쁜 품질 (주요 오류, 오해의 소지, 안전하지 않음)
- 0.3 = 나쁜 품질 (사용성에 영향을 주는 심각한 오류)
- 0.5 = 적절한 품질 (일부 오류가 있지만 일반적으로 사용 가능)
- 0.7 = 좋은 품질 (사소한 오류, 대부분 정확함)
- 0.9 = 우수한 품질 (최소한의 문제, 전문적 수준)
- 1.0 = 완벽한 품질 (오류 없음, 이상적 번역)

숫자 점수(예: 0.75)와 함께 한국어로 간결한 정당화를 제공해주세요 (1-2문장)."""


def parse_claude_response(response_text: str) -> Tuple[float, Optional[str]]:
    """
    Parse Claude's response to extract score and justification.
    
    Args:
        response_text: Raw response text from Claude
        
    Returns:
        Tuple of (score from 0.0 to 1.0, justification text or None)
    """
    try:
        # Handle different response formats
        response_text = response_text.strip()
        
        # Try to find a score (decimal number) at the beginning
        lines = response_text.split('\n')
        score_line = lines[0].strip()
        
        # Handle cases like "0.85 This translation is..." or just "0.85"
        if ' ' in score_line:
            parts = score_line.split(' ', 1)
            score_str = parts[0]
            justification = parts[1] + (' ' + '\n'.join(lines[1:]) if len(lines) > 1 else '')
        else:
            # Score is on its own line
            score_str = score_line
            justification = '\n'.join(lines[1:]).strip() if len(lines) > 1 else None
        
        score = float(score_str)
        score = max(0.0, min(1.0, score))  # Clamp to [0,1]
        
        # Clean up justification by removing markdown formatting
        if justification:
            import re
            # Remove markdown bold formatting
            justification = re.sub(r'\*\*([^*]+)\*\*', r'\1', justification)
            # Remove any remaining asterisks at the beginning/end and throughout text
            justification = justification.strip('* \n')
            justification = justification.replace('**', '').replace('*', '')
            # Remove Korean "정당화:" prefix to avoid duplication with English label
            if justification.startswith('정당화:'):
                justification = justification[4:].strip()  # Remove "정당화:" (4 characters)
            # Clean up multiple spaces and newlines
            justification = ' '.join(justification.split())
        
        return score, justification if justification and justification.strip() else None
        
    except (ValueError, IndexError) as e:
        # Try to extract any decimal number from the response
        import re
        score_match = re.search(r'(\d+\.?\d*)', response_text)
        if score_match:
            try:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))
                # Extract text after the score
                justification = response_text[score_match.end():].strip()
                # Clean up justification
                if justification:
                    justification = re.sub(r'\*\*([^*]+)\*\*', r'\1', justification)
                    justification = justification.strip('* \n')
                    justification = justification.replace('**', '').replace('*', '')
                    # Remove Korean "정당화:" prefix to avoid duplication
                    if justification.startswith('정당화:'):
                        justification = justification[4:].strip()  # Remove "정당화:" (4 characters)
                    justification = ' '.join(justification.split())
                return score, justification if justification else None
            except ValueError:
                pass
        
        return 0.5, f"Parse error ({e}): {response_text[:50]}..."


def call_claude_with_retry(bedrock_client, model_id: str, prompt: str, max_retries: int = 3, debug: bool = False) -> Tuple[float, Optional[str]]:
    """
    Call Claude via Bedrock with retry logic and exponential backoff.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        model_id: Bedrock model ID for Claude
        prompt: Evaluation prompt
        max_retries: Maximum retry attempts
        debug: Whether to print debug information
        
    Returns:
        Tuple of (score from 0.0 to 1.0, justification text or None)
    """
    messages = [{
        'role': 'user',
        'content': [{'text': prompt}]
    }]

    for attempt in range(max_retries):
        try:
            if debug:
                print(f"  Debug: Calling Bedrock API with model {model_id}")
            
            response = bedrock_client.converse(
                modelId=model_id,
                messages=messages,
                inferenceConfig={
                    'maxTokens': 300,  # Increased for longer Korean justifications
                    'temperature': 0.1
                }
            )
            
            response_text = response['output']['message']['content'][0]['text'].strip()
            
            if debug:
                print(f"  Debug: Raw response: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
            
            score, justification = parse_claude_response(response_text)
            
            if debug:
                print(f"  Debug: Parsed score: {score}, justification: '{justification[:50] if justification else 'None'}{'...' if justification and len(justification) > 50 else ''}'")
            
            return score, justification
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed. Last error: {e}")
                return 0.5, f"API Error after {max_retries} attempts"


def evaluate_single_claude(bedrock_client, model_id: str, source: str, translation: str, debug: bool = False) -> Tuple[float, Optional[str]]:
    """
    Evaluate a single translation using Claude with standardized prompt and retry logic.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        model_id: Bedrock model ID for Claude
        source: Korean source text
        translation: English translation
        debug: Whether to enable debug logging
        
    Returns:
        Tuple of (score from 0.0 to 1.0, justification text or None)
    """
    prompt = create_claude_evaluation_prompt(source, translation)
    return call_claude_with_retry(bedrock_client, model_id, prompt, debug=debug)


def print_results(data: list[dict], scores: list[float], system_score: float, model_name: str):
    """Print evaluation results."""
    print(f"\n{'=' * 60}")
    print(f"{model_name} Evaluation Results")
    print("=" * 60)

    for i, (item, score) in enumerate(zip(data, scores)):
        print(f"\n[{i+1}] Source: {item['src']}")
        print(f"    Translation: {item['mt']}")
        print(f"    Score: {score:.4f}")

    print(f"\n{'=' * 60}")
    print(f"System Score (average): {system_score:.4f}")
    print("=" * 60)


def print_detailed_results(data: list[dict], scores: list[float], justifications: list[str], model_name: str):
    """
    Print detailed evaluation results with example_id, score, error type, and clear analysis.
    
    Args:
        data: List of test examples with metadata
        scores: List of evaluation scores
        justifications: List of justification text from the model
        model_name: Name of the evaluation model
    """
    print(f"\n{'=' * 150}")
    print(f"{model_name} - DETAILED EVALUATION RESULTS")
    print("=" * 150)
    print(f"{'ID':<4} {'Expected':<8} {'Score':<8} {'Status':<10} {'Error Type':<20} {'Claude Reasoning':<100}")
    print("-" * 150)
    
    for i, (item, score, justification) in enumerate(zip(data, scores, justifications)):
        example_id = item.get('id', i+1)
        expected_quality = item.get('quality', 'unknown')
        error_type = item.get('error_type') or 'none'
        error_description = item.get('error_description', '')
        
        # Determine if Claude's assessment matches expected quality
        if expected_quality == 'good':
            status = "✓ Correct" if score >= 0.7 else "✗ Missed"
        else:  # expected_quality == 'bad'
            status = "✓ Correct" if score < 0.7 else "✗ Missed"
        
        # Clean and truncate text for display (keep Korean for better understanding)
        reason = (justification or 'No reasoning provided')
        reason_display = (reason[:100] + '...') if len(reason) > 100 else reason
        
        print(f"{example_id:<4} {expected_quality:<8} {score:<8.4f} {status:<10} {error_type:<20} {reason_display:<100}")
    
    # Summary statistics
    print("-" * 150)
    system_score = sum(scores) / len(scores) if scores else 0.0
    print(f"System Average Score: {system_score:.4f}")
    
    # Calculate accuracy (how often Claude agrees with expected quality)
    correct_assessments = 0
    for item, score in zip(data, scores):
        expected = item.get('quality', 'unknown')
        if expected == 'good' and score >= 0.7:
            correct_assessments += 1
        elif expected == 'bad' and score < 0.7:
            correct_assessments += 1
    
    accuracy = (correct_assessments / len(data)) * 100 if data else 0
    print(f"Assessment Accuracy: {correct_assessments}/{len(data)} ({accuracy:.1f}%) - How often Claude agrees with expected quality")
    
    # Score distribution
    excellent = sum(1 for s in scores if s >= 0.9)
    good = sum(1 for s in scores if 0.7 <= s < 0.9)
    adequate = sum(1 for s in scores if 0.5 <= s < 0.7)
    poor = sum(1 for s in scores if s < 0.5)
    total = len(scores)
    
    print(f"Score Distribution: Excellent: {excellent}/{total} ({100*excellent/total:.1f}%), "
          f"Good: {good}/{total} ({100*good/total:.1f}%), "
          f"Adequate: {adequate}/{total} ({100*adequate/total:.1f}%), "
          f"Poor: {poor}/{total} ({100*poor/total:.1f}%)")
    
    # Error type performance analysis
    print(f"\nError Type Performance Analysis:")
    print(f"{'Error Type':<25} {'Count':<8} {'Avg Score':<12} {'Detection Rate':<15} {'Notes'}")
    print("-" * 80)
    
    error_types = {}
    for item, score in zip(data, scores):
        error_type = item.get('error_type') or 'none'
        expected = item.get('quality', 'unknown')
        if error_type not in error_types:
            error_types[error_type] = {'scores': [], 'detected': 0, 'total': 0}
        error_types[error_type]['scores'].append(score)
        error_types[error_type]['total'] += 1
        # For bad translations, detection means score < 0.7
        if expected == 'bad' and score < 0.7:
            error_types[error_type]['detected'] += 1
        elif expected == 'good' and score >= 0.7:
            error_types[error_type]['detected'] += 1
    
    for error_type, info in sorted(error_types.items()):
        avg_score = sum(info['scores']) / len(info['scores'])
        detection_rate = (info['detected'] / info['total']) * 100 if info['total'] > 0 else 0
        
        # Add contextual notes
        if error_type == 'none':
            notes = "(Good translations)"
        elif avg_score < 0.3:
            notes = "(Critical errors - well detected)"
        elif avg_score > 0.7:
            notes = "(Claude may be too lenient)"
        else:
            notes = "(Moderate severity)"
            
        print(f"{error_type:<25} {info['total']:<8} {avg_score:<12.4f} {detection_rate:<15.1f}% {notes}")
    
    print("=" * 150)
    print(f"Note: System Average Score of {system_score:.3f} suggests Claude appropriately penalizes poor translations while rewarding good ones.")
