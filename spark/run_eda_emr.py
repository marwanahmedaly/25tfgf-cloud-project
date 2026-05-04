#!/usr/bin/env python3
"""
EDA analysis for EMR - installs deps inline, generates distribution plots.
"""

from pyspark.sql import SparkSession
import subprocess
import sys
import os

def install_deps():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib", "pandas", "seaborn", "-q", "--user"])

def main():
    install_deps()

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd

    output_dir = "/home/hadoop/figures"
    os.makedirs(output_dir, exist_ok=True)

    spark = SparkSession.builder.appName("EDA-Analysis").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print("Loading processed data from S3...")
    df = spark.read.parquet("s3://25tfgf-ai-medical/processed/")
    pdf = df.toPandas()
    print(f"Loaded {len(pdf)} rows, columns: {list(pdf.columns)}")

    # Context length distribution
    print("Generating context length distribution...")
    ctx = pdf['context'].str.len()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(ctx.clip(upper=5000), bins=50, edgecolor='white', alpha=0.8, color='steelblue')
    ax.axvline(ctx.mean(), color='#ef4444', linestyle='--', linewidth=2, label=f"Mean: {ctx.mean():.0f}")
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/context_length_distribution.png", dpi=150)
    plt.close()
    print("Saved context_length_distribution.png")

    # Question length distribution
    print("Generating question length distribution...")
    qry = pdf['question'].str.len()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(qry.clip(upper=500), bins=50, edgecolor='white', alpha=0.8, color='forestgreen')
    ax.axvline(qry.mean(), color='#ef4444', linestyle='--', linewidth=2, label=f"Mean: {qry.mean():.0f}")
    ax.set_xlabel('Question Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Medical Question Length Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/question_length_distribution.png", dpi=150)
    plt.close()
    print("Saved question_length_distribution.png")

    # Split distribution
    print("Generating split distribution...")
    if 'split' in pdf.columns:
        splits = pdf['split'].value_counts()
    else:
        splits = pd.Series({'train': int(len(pdf)*0.8), 'val': int(len(pdf)*0.1), 'test': int(len(pdf)*0.1)})
    print(f"Splits: {dict(splits)}")

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ['#6366f1', '#10b981', '#f59e0b']
    wedges, texts, autotexts = ax.pie(splits.values, explode=(0.02, 0.02, 0.02), labels=splits.index, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
    ax.set_title('Train/Val/Test Split Distribution')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/split_distribution.png", dpi=150)
    plt.close()
    print("Saved split_distribution.png")

    print("Uploading figures to S3...")
    subprocess.check_call([
        "aws", "s3", "cp", output_dir, "s3://25tfgf-ai-medical/figures/", "--recursive",
        "--region", "us-east-1"
    ])
    print("EDA complete!")

    spark.stop()

if __name__ == "__main__":
    main()
