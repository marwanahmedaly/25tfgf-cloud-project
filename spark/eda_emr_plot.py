#!/usr/bin/env python3
"""
EDA plot job - reads stats from S3 JSON, generates plots locally, uploads to S3.
Run on EMR master node after eda_emr_stats.py completes, or standalone on any machine with boto3.
"""

import json
import boto3
import os
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BUCKET = "25tfgf-ai-medical"
STATS_KEY = "eda_stats/results.json"

def download_stats():
    s3 = boto3.client('s3')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        s3.download_file(BUCKET, STATS_KEY, f.name)
        return f.name

def plot_context_histogram(stats, output_dir):
    ctx_hist = stats["context"]["histogram"]
    buckets = list(ctx_hist.keys())
    counts = list(ctx_hist.values())

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(buckets)), counts, color='steelblue', edgecolor='white', alpha=0.8)
    ax.set_xticks(range(len(buckets)))
    ax.set_xticklabels(buckets, rotation=45)
    median_bucket_idx = min(len(buckets)-1, int(stats["context"]["median"]) // 500)
    ax.axvline(median_bucket_idx, color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {stats["context"]["median"]:.0f}')
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution (Full 21M Dataset)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'context_length_distribution.png'), dpi=150)
    plt.close()

def plot_question_percentiles(stats, output_dir):
    q_stats = stats["question"]
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = ['Median', 'P95', 'P99']
    values = [q_stats['median'], q_stats['p95'], q_stats['p99']]
    ax.bar(labels, values, color='forestgreen', edgecolor='white', alpha=0.8)
    ax.axhline(q_stats['median'], color='#ef4444', linestyle='--', linewidth=2)
    ax.set_ylabel('Question Length (characters)')
    ax.set_title('Medical Question Length Percentiles (Full 21M Dataset)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'question_length_distribution.png'), dpi=150)
    plt.close()

def plot_split(stats, output_dir):
    pct = stats["split"]["percentages"]
    labels = list(pct.keys())
    sizes = [pct[k] for k in labels]
    colors = ['#6366f1', '#10b981', '#f59e0b']
    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(
        sizes, explode=(0.02, 0.02, 0.02), labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14}
    )
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
    ax.set_title('Train/Val/Test Split Distribution')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'split_distribution.png'), dpi=150)
    plt.close()

def main():
    output_dir = "/home/hadoop/figures"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading stats from s3://{BUCKET}/{STATS_KEY}...")
    stats_path = download_stats()

    with open(stats_path) as f:
        stats = json.load(f)

    print(f"Stats loaded: {stats['total_rows']} total rows")
    print(f"Context: median={stats['context']['median']}, p95={stats['context']['p95']}, p99={stats['context']['p99']}")
    print(f"Question: median={stats['question']['median']}, p95={stats['question']['p95']}, p99={stats['question']['p99']}")
    print(f"Split: {stats['split']['percentages']}")

    plot_context_histogram(stats, output_dir)
    plot_question_percentiles(stats, output_dir)
    plot_split(stats, output_dir)

    print(f"Saved 3 figures to {output_dir}")

    print(f"Uploading figures to s3://{BUCKET}/figures/...")
    s3 = boto3.client('s3')
    for fname in ['context_length_distribution.png', 'question_length_distribution.png', 'split_distribution.png']:
        s3.upload_file(os.path.join(output_dir, fname), BUCKET, f"figures/{fname}")
        print(f"Uploaded {fname}")

    print("EDA plot complete!")

if __name__ == "__main__":
    main()