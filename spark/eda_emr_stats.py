#!/usr/bin/env python3
"""
EDA stats job for EMR - computes statistics on full 21M dataset.
Run with: spark-submit --master yarn --deploy-mode cluster s3://25tfgf-ai-medical/eda_emr_stats.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, percentile_approx
import os
import json

import boto3

BUCKET = "25tfgf-ai-medical"

def main():
    spark = SparkSession.builder \
        .appName("EDA-Stats-Full") \
        .config("spark.executor.memory", "4g") \
        .config("spark.executor.cores", 2) \
        .getOrCreate()

    print("Loading processed data from S3...")
    df = spark.read.parquet(f"s3://{BUCKET}/processed/")
    total = df.count()
    print(f"Total rows: {total}")

    ctx_len = length(col("context_parsed"))
    qry_len = length(col("question_parsed"))

    print("Computing context length percentiles...")
    ctx_stats_df = df.select(
        percentile_approx(ctx_len, 0.5).alias("ctx_median"),
        percentile_approx(ctx_len, 0.95).alias("ctx_p95"),
        percentile_approx(ctx_len, 0.99).alias("ctx_p99"),
    ).filter(col("context_parsed").isNotNull())

    median_ctx = ctx_stats_df.select("ctx_median").first()[0]
    p95_ctx = ctx_stats_df.select("ctx_p95").first()[0]
    p99_ctx = ctx_stats_df.select("ctx_p99").first()[0]

    print("Computing question length percentiles...")
    qry_stats_df = df.select(
        percentile_approx(qry_len, 0.5).alias("qry_median"),
        percentile_approx(qry_len, 0.95).alias("qry_p95"),
        percentile_approx(qry_len, 0.99).alias("qry_p99"),
    ).filter(col("question_parsed").isNotNull())

    median_qry = qry_stats_df.select("qry_median").first()[0]
    p95_qry = qry_stats_df.select("qry_p95").first()[0]
    p99_qry = qry_stats_df.select("qry_p99").first()[0]

    print("Computing context histogram buckets...")
    ctx_hist = {}
    bucket_edges = list(range(0, 5001, 500))
    for i in range(len(bucket_edges) - 1):
        low, high = bucket_edges[i], bucket_edges[i+1]
        count = df.filter((ctx_len >= low) & (ctx_len < high)).count()
        ctx_hist[f"{low}-{high}"] = count

    print("Computing split distribution...")
    split_counts = {}
    for row in df.groupBy("split").count().collect():
        split_counts[row.split] = row.count

    total = sum(split_counts.values())
    split_pct = {k: round(v/total*100, 2) for k, v in split_counts.items()}

    print(f"Context stats: median={median_ctx}, p95={p95_ctx}, p99={p99_ctx}")
    print(f"Question stats: median={median_qry}, p95={p95_qry}, p99={p99_qry}")
    print(f"Split distribution: {split_pct}")

    results = {
        "context": {"median": median_ctx, "p95": p95_ctx, "p99": p99_ctx, "histogram": ctx_hist},
        "question": {"median": median_qry, "p95": p95_qry, "p99": p99_qry},
        "split": {**split_counts, "percentages": split_pct},
        "total_rows": total
    }

    print("Writing stats JSON to S3...")
    s3 = boto3.client('s3')
    s3.put_object(Bucket=BUCKET, Key="eda_stats/results.json", Body=json.dumps(results, indent=2))
    print(f"Stats JSON written to s3://{BUCKET}/eda_stats/results.json")

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output_dir = "/home/hadoop/figures"
    os.makedirs(output_dir, exist_ok=True)

    # Context length histogram
    print("Generating context length histogram...")
    buckets = list(ctx_hist.keys())
    counts = list(ctx_hist.values())
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(buckets)), counts, color='steelblue', edgecolor='white', alpha=0.8)
    ax.set_xticks(range(len(buckets)))
    ax.set_xticklabels(buckets, rotation=45)
    median_bucket_idx = min(len(buckets)-1, int(median_ctx) // 500)
    ax.axvline(median_bucket_idx, color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {median_ctx:.0f}')
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution (Full 21M Dataset)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'context_length_distribution.png'), dpi=150)
    plt.close()

    # Question length bar chart (percentiles)
    print("Generating question length chart...")
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = ['Median', 'P95', 'P99']
    values = [median_qry, p95_qry, p99_qry]
    ax.bar(labels, values, color='forestgreen', edgecolor='white', alpha=0.8)
    ax.axhline(median_qry, color='#ef4440', linestyle='--', linewidth=2)
    ax.set_ylabel('Question Length (characters)')
    ax.set_title('Medical Question Length Percentiles (Full 21M Dataset)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'question_length_distribution.png'), dpi=150)
    plt.close()

    # Split pie chart
    print("Generating split distribution...")
    labels = list(split_pct.keys())
    sizes = [split_counts[k] for k in labels]
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

    print(f"Saved 3 figures to {output_dir}")
    spark.stop()
    print("EDA stats job complete!")

if __name__ == "__main__":
    main()