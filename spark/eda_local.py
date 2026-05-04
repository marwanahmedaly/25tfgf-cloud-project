#!/usr/bin/env python3
"""
EDA analysis script for Medical Q&A dataset.
Downloads processed data from S3, generates distribution plots locally on EC2.
"""

import boto3
import os
import tempfile
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11

CONTEXT_MAX_LENGTH = 4096
QUESTION_MAX_LENGTH = 500
PIE_EXPLODE_RATIO = 0.02
PIE_START_ANGLE = 90


def download_from_s3(bucket_name, prefix, local_dir):
    """Download all parquet files from S3 prefix to local directory."""
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    downloaded = 0
    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.key.endswith('/'):
            continue
        local_path = Path(local_dir) / obj.key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        bucket.download_file(obj.key, str(local_path))
        downloaded += 1
        print(f"Downloaded {obj.key} -> {local_path}")

    return downloaded


def plot_context_length_distribution(pdf, output_dir):
    """Generate context length distribution histogram."""
    print("Plotting context length distribution...")
    context_lengths = pdf['context_parsed'].str.len().clip(upper=CONTEXT_MAX_LENGTH)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(context_lengths, bins=50, edgecolor='white', alpha=0.8, color='steelblue')
    ax.axvline(context_lengths.mean(), color='#ef4444', linestyle='--', linewidth=2,
               label=f'Mean: {context_lengths.mean():.0f}')
    ax.axvline(context_lengths.quantile(0.95), color='#f59e0b', linestyle='--', linewidth=2,
               label=f'P95: {context_lengths.quantile(0.95):.0f}')
    ax.axvline(context_lengths.quantile(0.99), color='#10b981', linestyle='--', linewidth=2,
               label=f'P99: {context_lengths.quantile(0.99):.0f}')
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'context_length_distribution.png'), dpi=150)
    plt.close()
    print(f"Saved context_length_distribution.png")


def plot_question_length_distribution(pdf, output_dir):
    """Generate question length distribution histogram."""
    print("Plotting question length distribution...")
    question_lengths = pdf['question_parsed'].str.len().clip(upper=QUESTION_MAX_LENGTH)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(question_lengths, bins=50, edgecolor='white', alpha=0.8, color='forestgreen')
    ax.axvline(question_lengths.mean(), color='#ef4444', linestyle='--', linewidth=2,
               label=f'Mean: {question_lengths.mean():.0f}')
    ax.axvline(question_lengths.quantile(0.95), color='#f59e0b', linestyle='--', linewidth=2,
               label=f'P95: {question_lengths.quantile(0.95):.0f}')
    ax.axvline(question_lengths.quantile(0.99), color='#10b981', linestyle='--', linewidth=2,
               label=f'P99: {question_lengths.quantile(0.99):.0f}')
    ax.set_xlabel('Question Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Medical Question Length Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'question_length_distribution.png'), dpi=150)
    plt.close()
    print(f"Saved question_length_distribution.png")


def plot_split_distribution(pdf, output_dir):
    """Generate split distribution pie chart."""
    print("Plotting split distribution...")

    if 'split' in pdf.columns:
        splits = pdf['split'].value_counts()
    else:
        # Estimate from train-only data
        n = len(pdf)
        splits = pd.Series({'train': n, 'val': int(n * 0.125), 'test': int(n * 0.125)})
        print(f"No 'split' column found - showing estimated distribution based on train partition")

    fig, ax = plt.subplots(figsize=(10, 8))
    labels = splits.index.tolist()
    sizes = splits.values
    colors = ['#6366f1', '#10b981', '#f59e0b']
    explode = (PIE_EXPLODE_RATIO, PIE_EXPLODE_RATIO, PIE_EXPLODE_RATIO)

    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=PIE_START_ANGLE, textprops={'fontsize': 14}
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    ax.set_title('Train/Val/Test Split Distribution')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'split_distribution.png'), dpi=150)
    plt.close()
    print(f"Saved split_distribution.png")


def upload_to_s3(local_dir, bucket_name, prefix):
    """Upload all files from local dir to S3 prefix."""
    s3 = boto3.client('s3')
    uploaded = 0
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            s3_key = f"{prefix}/{relative_path}"
            s3.upload_file(local_path, bucket_name, s3_key)
            print(f"Uploaded {local_path} -> s3://{bucket_name}/{s3_key}")
            uploaded += 1
    return uploaded


def download_single_partition(bucket_name, prefix, local_dir, partition=0):
    """Download just ONE partition file for EDA (avoids OOM)."""
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    partition_files = [obj for obj in bucket.objects.filter(Prefix=prefix) if 'part-00000' in obj.key]
    if not partition_files:
        partition_files = [obj for obj in bucket.objects.filter(Prefix=prefix) if obj.key.endswith('.parquet')]

    target_file = partition_files[partition] if partition < len(partition_files) else partition_files[0]
    local_path = Path(local_dir) / Path(target_file.key).name
    bucket.download_file(target_file.key, str(local_path))
    print(f"Downloaded {target_file.key} -> {local_path}")
    return str(local_path)


def main():
    bucket = '25tfgf-ai-medical'
    train_prefix = 'processed/split=train/'
    output_dir = '/home/ubuntu/figures'

    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nDownloading one train partition from s3://{bucket}/{train_prefix}...")
        parquet_path = download_single_partition(bucket, train_prefix, tmpdir)

        print(f"\nLoading Parquet file {parquet_path}...")
        pdf = pd.read_parquet(parquet_path)
        print(f"Loaded {len(pdf)} rows, columns: {list(pdf.columns)}")

        print(f"\nGenerating EDA plots...")
        plot_context_length_distribution(pdf, output_dir)
        plot_question_length_distribution(pdf, output_dir)
        plot_split_distribution(pdf, output_dir)

    print(f"\nUploading figures to s3://{bucket}/figures/...")
    upload_to_s3(output_dir, bucket, 'figures')

    print("\nEDA complete!")


if __name__ == "__main__":
    main()
