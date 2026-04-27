"""
EDA visualization script for Medical Q&A dataset.
Generates token length distribution, context/question length histograms, and split distribution plots.
"""

import argparse
import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

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
        question = item.get('question', '')
        context = item.get('context', '')

        # Format prompt same as preprocessing
        prompt = f"### Medical Question: {question}\n\n### Clinical Context: {context}\n\n### Answer: "

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


def plot_context_length_distribution(dataset, output_dir):
    """Generate context length distribution histogram."""
    logger.info("Plotting context length distribution...")

    context_lengths = dataset['context'].str.len().clip(upper=4096)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.hist(context_lengths, bins=50, edgecolor='white', alpha=0.8, color='steelblue')
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution')

    # Add percentiles
    mean_len = context_lengths.mean()
    p95_len = context_lengths.quantile(0.95)
    p99_len = context_lengths.quantile(0.99)

    ax.axvline(mean_len, color='#ef4444', linestyle='--', linewidth=2, label=f'Mean: {mean_len:.0f}')
    ax.axvline(p95_len, color='#f59e0b', linestyle='--', linewidth=2, label=f'P95: {p95_len:.0f}')
    ax.axvline(p99_len, color='#10b981', linestyle='--', linewidth=2, label=f'P99: {p99_len:.0f}')
    ax.legend()

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'context_length_distribution.png')
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info(f"Saved to {output_path}")
    return {'mean': mean_len, 'p95': p95_len, 'p99': p99_len}


def plot_question_length_distribution(dataset, output_dir):
    """Generate question length distribution histogram."""
    logger.info("Plotting question length distribution...")

    question_lengths = dataset['question'].str.len().clip(upper=500)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.hist(question_lengths, bins=50, edgecolor='white', alpha=0.8, color='forestgreen')
    ax.set_xlabel('Question Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Medical Question Length Distribution')

    # Add percentiles
    mean_len = question_lengths.mean()
    p95_len = question_lengths.quantile(0.95)
    p99_len = question_lengths.quantile(0.99)

    ax.axvline(mean_len, color='#ef4444', linestyle='--', linewidth=2, label=f'Mean: {mean_len:.0f}')
    ax.axvline(p95_len, color='#f59e0b', linestyle='--', linewidth=2, label=f'P95: {p95_len:.0f}')
    ax.axvline(p99_len, color='#10b981', linestyle='--', linewidth=2, label=f'P99: {p99_len:.0f}')
    ax.legend()

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'question_length_distribution.png')
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info(f"Saved to {output_path}")
    return {'mean': mean_len, 'p95': p95_len, 'p99': p99_len}


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
    parser = argparse.ArgumentParser(description="EDA visualization for Medical dataset")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to Parquet dataset (output from preprocess.py)"
    )
    parser.add_argument("--output-dir", default="./plots", help="Output directory for plots")
    parser.add_argument("--tokenizer", default="google/gemma-4-2b", help="Tokenizer for tokenization")

    args = parser.parse_args()

    logger.info("Starting EDA visualization")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output_dir}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load dataset (Parquet format from preprocess.py)
    logger.info("Loading dataset...")
    ds = pd.read_parquet(args.input)

    # Load tokenizer
    logger.info(f"Loading tokenizer: {args.tokenizer}")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

    # Generate token length distribution
    token_lengths = get_token_lengths(ds, tokenizer)
    stats = plot_token_length_distribution(token_lengths, args.output_dir)

    # Generate context length distribution
    context_stats = plot_context_length_distribution(ds, args.output_dir)

    # Generate question length distribution
    question_stats = plot_question_length_distribution(ds, args.output_dir)

    # Use actual split data if available
    if 'split' in ds.columns:
        splits_data = ds['split'].value_counts().to_dict()
    else:
        splits_data = {
            'train': 80,
            'val': 10,
            'test': 10
        }
    plot_split_distribution(splits_data, args.output_dir)

    logger.info("EDA complete")
    logger.info(f"Token length stats - Mean: {stats['mean']:.1f}, P95: {stats['p95']}, P99: {stats['p99']}")
    logger.info(f"Context length stats - Mean: {context_stats['mean']:.1f}, P95: {context_stats['p95']:.0f}, P99: {context_stats['p99']:.0f}")
    logger.info(f"Question length stats - Mean: {question_stats['mean']:.1f}, P95: {question_stats['p95']:.0f}, P99: {question_stats['p99']:.0f}")


if __name__ == "__main__":
    main()