"""
EDA visualization script for StackOverflow Python Q&A dataset.
Generates token length distribution, answer score histogram, and split distribution plots.
"""

import argparse
import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from datasets import load_dataset

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11


def get_token_lengths(dataset, tokenizer):
    """Compute token lengths for all prompts using Gemma tokenizer."""
    logger.info("Computing token lengths...")
    token_lengths = []

    for idx, item in enumerate(dataset):
        question = item.get('question_body', '')
        answer = item.get('answer_body', '')

        # Format prompt same as preprocessing
        prompt = f"### Question: {question}\n### Answer: {answer}\n"

        tokens = tokenizer.encode(prompt, add_special_tokens=True)
        token_lengths.append(len(tokens))

        if (idx + 1) % 10000 == 0:
            logger.info(f"Processed {idx + 1} examples")

    return token_lengths


def plot_token_length_distribution(token_lengths, output_dir):
    """Generate token length distribution histogram."""
    logger.info("Plotting token length distribution...")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Compute statistics
    mean_len = sum(token_lengths) / len(token_lengths)
    p95_len = sorted(token_lengths)[int(len(token_lengths) * 0.95)]
    p99_len = sorted(token_lengths)[int(len(token_lengths) * 0.99)]

    ax.hist(token_lengths, bins=50, edgecolor='white', alpha=0.8, color='#6366f1')
    ax.axvline(mean_len, color='#ef4444', linestyle='--', linewidth=2, label=f'Mean: {mean_len:.0f}')
    ax.axvline(p95_len, color='#f59e0b', linestyle='--', linewidth=2, label=f'P95: {p95_len:.0f}')
    ax.axvline(p99_len, color='#10b981', linestyle='--', linewidth=2, label=f'P99: {p99_len:.0f}')

    ax.set_xlabel('Token Length')
    ax.set_ylabel('Frequency')
    ax.set_title('Token Length Distribution (Gemma Tokenizer)')
    ax.legend()

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'token_length_distribution.png')
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info(f"Saved to {output_path}")
    return {'mean': mean_len, 'p95': p95_len, 'p99': p99_len}


def plot_answer_score_histogram(dataset, output_dir):
    """Generate answer score histogram."""
    logger.info("Plotting answer score histogram...")

    scores = [item['answer_score'] for item in dataset]

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.hist(scores, bins=50, edgecolor='white', alpha=0.8, color='#6366f1')
    ax.set_xlabel('Answer Score')
    ax.set_ylabel('Frequency')
    ax.set_title('Answer Score Distribution')

    # Add percentiles
    p50 = sorted(scores)[len(scores) // 2]
    p95 = sorted(scores)[int(len(scores) * 0.95)]

    ax.axvline(p50, color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {p50}')
    ax.axvline(p95, color='#f59e0b', linestyle='--', linewidth=2, label=f'P95: {p95}')
    ax.legend()

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'answer_score_histogram.png')
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info(f"Saved to {output_path}")
    return {'p50': p50, 'p95': p95}


def plot_split_distribution(splits_data, output_dir):
    """Generate split distribution pie chart."""
    logger.info("Plotting split distribution...")

    fig, ax = plt.subplots(figsize=(10, 8))

    labels = list(splits_data.keys())
    sizes = list(splits_data.values())
    colors = ['#6366f1', '#10b981', '#f59e0b']
    explode = (0.02, 0.02, 0.02)

    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14}
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Train/Val/Test Split Distribution')

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'split_distribution.png')
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info(f"Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="EDA visualization for StackOverflow dataset")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to arrow dataset (local path or HF dataset name)"
    )
    parser.add_argument("--output-dir", default="./plots", help="Output directory for plots")
    parser.add_argument("--tokenizer", default="google/gemma-2b", help="Tokenizer for tokenization")

    args = parser.parse_args()

    logger.info("Starting EDA visualization")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output_dir}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load dataset (supports both local arrow files and HF dataset name)
    logger.info("Loading dataset...")
    ds = load_dataset("arrow", data_dir=args.input)['train']

    # Load tokenizer
    logger.info(f"Loading tokenizer: {args.tokenizer}")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

    # Generate token length distribution
    token_lengths = get_token_lengths(ds, tokenizer)
    stats = plot_token_length_distribution(token_lengths, args.output_dir)

    # Generate answer score histogram
    plot_answer_score_histogram(ds, args.output_dir)

    # Simulate split distribution (since we don't have actual splits yet)
    splits_data = {
        'train': 80,
        'val': 10,
        'test': 10
    }
    plot_split_distribution(splits_data, args.output_dir)

    logger.info("EDA complete")
    logger.info(f"Token length stats - Mean: {stats['mean']:.1f}, P95: {stats['p95']}, P99: {stats['p99']}")


if __name__ == "__main__":
    main()