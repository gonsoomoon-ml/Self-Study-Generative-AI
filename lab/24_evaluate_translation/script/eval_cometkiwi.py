"""
Translation Evaluation using COMET-KIWI

Run:
    cd script
    uv run eval_cometkiwi.py
"""

from comet import download_model, load_from_checkpoint

from util import check_hf_login, get_sample_data, print_results

MODEL_NAME = "Unbabel/wmt22-cometkiwi-da"


def evaluate(data: list[dict]) -> dict:
    """
    Evaluate translations using COMET-KIWI (reference-free).

    Args:
        data: List of dicts with 'src' and 'mt' keys
              e.g., [{"src": "Hello", "mt": "Bonjour"}]

    Returns:
        Model output with scores (0-1, higher = better)
    """
    model_path = download_model(MODEL_NAME)
    model = load_from_checkpoint(model_path)
    output = model.predict(data, batch_size=8, gpus=1)
    return output


def main():
    check_hf_login()

    print("=" * 60)
    print("COMET-KIWI Evaluation (Reference-free)")
    print("Score range: 0-1 (higher = better)")
    print("=" * 60)

    data = get_sample_data()
    output = evaluate(data)

    print_results(data, output.scores, output.system_score, "COMET-KIWI")


if __name__ == "__main__":
    main()
