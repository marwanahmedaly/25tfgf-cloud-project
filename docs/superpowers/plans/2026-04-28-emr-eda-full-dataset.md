# EMR Full EDA Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run full EDA on all 21M rows of processed medical data using Spark on EMR, generating statistics and plots for the complete dataset.

**Architecture:** A Spark job submitted via `command-runner.jar` (CUSTOM_JAR step type) in cluster deploy mode computes only aggregate statistics — percentiles, histogram buckets, split counts — and writes JSON results to S3. No 21M rows are collected to the driver. Plots are generated locally on the EMR master node and uploaded to S3.

**Tech Stack:** Spark 3.5 on EMR 7.2.0, Python 3.10, matplotlib, pandas, boto3, AWS EMR steps

---

## File Map

**Created:**
- `spark/eda_emr_stats.py` — Spark job: computes statistics on 21M rows in parallel, writes JSON to S3
- `spark/eda_emr_plot.py` — Python script: reads stats from S3, generates plots, uploads to S3
- `spark/bootstrap_eda.sh` — Bootstrap action: installs `matplotlib pandas seaborn pyarrow boto3` on all nodes (already exists)

**Modified:**
- `terraform/emr.tf` — Add bootstrap action reference pointing to S3
- `terraform/outputs.tf` — Add output for EMR master public DNS

**Key Reference:**
- `terraform/emr.tf:270-326` — Current EMR cluster definition
- `spark/run_eda_emr.py` — Previous attempt (failed with exitCode 13 due to wrong step type)

---

## Task 1: Upload bootstrap script and EDA scripts to S3

**Files:**
- Upload: `spark/bootstrap_eda.sh` → `s3://25tfgf-ai-medical/bootstrap_eda.sh`
- Upload: `spark/eda_emr_stats.py` → `s3://25tfgf-ai-medical/eda_emr_stats.py`
- Upload: `spark/eda_emr_plot.py` → `s3://25tfgf-ai-medical/eda_emr_plot.py`

- [ ] **Step 1: Upload bootstrap action to S3**

```bash
aws s3 cp spark/bootstrap_eda.sh s3://25tfgf-ai-medical/ --region us-east-1
```

- [ ] **Step 2: Upload EDA stats script to S3**

```bash
aws s3 cp spark/eda_emr_stats.py s3://25tfgf-ai-medical/ --region us-east-1
```

- [ ] **Step 3: Upload EDA plot script to S3**

```bash
aws s3 cp spark/eda_emr_plot.py s3://25tfgf-ai-medical/ --region us-east-1
```

---

## Task 2: Write `eda_emr_stats.py`

This is the Spark job that computes statistics on all 21M rows using parallel aggregation.

**Files:**
- Create: `spark/eda_emr_stats.py`

- [ ] **Step 1: Write the stats computation script**

```python
#!/usr/bin/env python3
"""
EDA stats job for EMR - computes statistics on full 21M dataset.
Run with: spark-submit --master yarn --deploy-mode cluster s3://25tfgf-ai-medical/eda_emr_stats.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, percentile_approx
import json
import os

BUCKET = "25tfgf-ai-medical"
STATS_KEY = "eda_stats/results.json"

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
    ctx_stats = df.select(
        percentile_approx(ctx_len, 0.5).alias("ctx_median"),
        percentile_approx(ctx_len, 0.95).alias("ctx_p95"),
        percentile_approx(ctx_len, 0.99).alias("ctx_p99"),
    ).filter(col("context_parsed").isNotNull())

    median_ctx = ctx_stats.select("ctx_median").first()[0]
    p95_ctx = ctx_stats.select("ctx_p95").first()[0]
    p99_ctx = ctx_stats.select("ctx_p99").first()[0]

    print("Computing question length percentiles...")
    qry_stats = df.select(
        percentile_approx(qry_len, 0.5).alias("qry_median"),
        percentile_approx(qry_len, 0.95).alias("qry_p95"),
        percentile_approx(qry_len, 0.99).alias("qry_p99"),
    ).filter(col("question_parsed").isNotNull())

    median_qry = qry_stats.select("qry_median").first()[0]
    p95_qry = qry_stats.select("qry_p95").first()[0]
    p99_qry = qry_stats.select("qry_p99").first()[0]

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

    results = {
        "context": {"median": median_ctx, "p95": p95_ctx, "p99": p99_ctx, "histogram": ctx_hist},
        "question": {"median": median_qry, "p95": p95_qry, "p99": p99_qry},
        "split": {**split_counts, "percentages": split_pct},
        "total_rows": total
    }

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
    median_bucket = min(len(buckets)-1, int(median_ctx) // 500)
    ax.axvline(median_bucket, color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {median_ctx:.0f}')
    ax.set_xlabel('Context Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Clinical Context Length Distribution (Full 21M Dataset)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'context_length_distribution.png'), dpi=150)
    plt.close()

    # Question length histogram
    print("Generating question length histogram...")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist([median_qry, p95_qry, p99_qry], bins=10, color='forestgreen', edgecolor='white', alpha=0.8)
    ax.axvline(median_qry, color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {median_qry:.0f}')
    ax.set_xlabel('Question Length (characters)')
    ax.set_ylabel('Frequency')
    ax.set_title('Medical Question Length Distribution (Full 21M Dataset)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'question_length_distribution.png'), dpi=150)
    plt.close()

    # Split pie chart
    print("Generating split distribution...")
    labels = list(split_pct.keys())
    sizes = [split_counts[k] for k in labels]
    colors = ['#6366f1', '#10b981', '#f59e0b']
    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(sizes, explode=(0.02, 0.02, 0.02), labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
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
```

---

## Task 3: Write `eda_emr_plot.py`

If we want to separate stats computation from plot generation (for debugging), use this script.

**Files:**
- Create: `spark/eda_emr_plot.py`

- [ ] **Step 1: Write the plot-only script**

```python
#!/usr/bin/env python3
"""
EDA plot job - reads stats from S3 JSON, generates plots locally on master node.
Run via SSH or inline after eda_emr_stats.py completes.
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
    ax.axvline(buckets[min(len(buckets)-1, int(stats["context"]["median"]) // 500)], color='#ef4444', linestyle='--', linewidth=2, label=f'Median: {stats["context"]["median"]:.0f}')
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
    wedges, texts, autotexts = ax.pie(sizes, explode=(0.02, 0.02, 0.02), labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
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
```

---

## Task 4: Update Terraform EMR cluster

Add bootstrap action to EMR cluster and add outputs for master public DNS (needed for SSH).

**Files:**
- Modify: `terraform/emr.tf` — add `bootstrap_actions` block and `log_uri`
- Modify: `terraform/outputs.tf` — add master public DNS output

- [ ] **Step 1: Update emr.tf to add bootstrap action and logging**

The current `aws_emr_cluster` block (lines 270-326) needs these additions:

After the `core_instance_group` block and before `configurations_json`, add:

```hcl
  bootstrap_actions {
    name = "Install EDA dependencies"
    path = "s3://${var.s3_bucket_name}/bootstrap_eda.sh"
  }
```

And add after `configurations_json`:

```hcl
  log_uri = "s3://${var.s3_bucket_name}/emr-logs/"
  termination_protection = false
```

The full `aws_emr_cluster` resource should end up like:

```hcl
resource "aws_emr_cluster" "main" {
  name          = "${var.net_id}-emr-cluster"
  release_label = "emr-7.2.0"
  service_role  = aws_iam_role.emr_service_role.arn

  ec2_attributes {
    subnet_id                          = aws_subnet.public_1.id
    emr_managed_master_security_group   = aws_security_group.emr_master.id
    emr_managed_slave_security_group   = aws_security_group.emr_slave.id
    instance_profile                   = aws_iam_instance_profile.emr_instance_profile.arn
  }

  master_instance_group {
    instance_type  = var.emr_master_instance_type
    instance_count = 1
    name           = "Master"
  }

  core_instance_group {
    instance_type  = var.emr_instance_type
    instance_count = var.emr_instance_count
    bid_price      = "0.30"
    name           = "Core"
  }

  configurations_json = jsonencode([
    {
      Classification = "spark-env"
      Properties = {
        PYSPARK_PYTHON = "/usr/bin/python3"
      }
    }
  ])

  bootstrap_actions {
    name = "Install EDA dependencies"
    path = "s3://${var.s3_bucket_name}/bootstrap_eda.sh"
  }

  log_uri = "s3://${var.s3_bucket_name}/emr-logs/"
  termination_protection = false

  applications = ["Spark", "JupyterHub"]

  tags = {
    Name = "${var.net_id}-emr-cluster"
    net_id = var.net_id
  }

  depends_on = [
    aws_subnet.public_1,
    aws_security_group.emr_master,
    aws_security_group.emr_slave,
    aws_iam_role.emr_service_role,
    aws_iam_role_policy.emr_service_role_ec2,
    aws_iam_role.emr_instance_profile_role,
    aws_iam_instance_profile.emr_instance_profile,
    aws_iam_service_linked_role.emr_spot
  ]
}
```

- [ ] **Step 2: Add EMR master public DNS output to outputs.tf**

Add to `terraform/outputs.tf`:

```hcl
output "emr_master_public_dns" {
  description = "EMR master node public DNS hostname"
  value       = aws_emr_cluster.main.master_instance_group[*].public_dns
}

output "emr_cluster_id" {
  description = "EMR cluster ID"
  value       = aws_emr_cluster.main.id
}
```

---

## Task 5: Apply Terraform and create EMR cluster

- [ ] **Step 1: Plan Terraform**

```bash
cd terraform
terraform plan -var="net_id=25tfgf" -var="key_name=25tfgf-key" -out=emr_eda.tfplan
```

- [ ] **Step 2: Apply Terraform**

```bash
terraform apply emr_eda.tfplan
```

- [ ] **Step 3: Wait for cluster to be WAITING**

```bash
CLUSTER_ID=$(terraform output -raw emr_cluster_id)
aws emr wait cluster-running --cluster-id $CLUSTER_ID --region us-east-1
aws emr describe-cluster --cluster-id $CLUSTER_ID --query 'Cluster.Status' --output text
# Expected: WAITING
```

---

## Task 6: Submit EDA stats step via `command-runner.jar` CUSTOM_JAR step type

**Critical fix vs previous attempts:** Use `Type=CUSTOM_JAR` with `command-runner.jar` and explicitly invoke `spark-submit --deploy-mode cluster`. Previous attempts used `Type=SPARK` which failed with exitCode 13 because it uses a different executor environment that lacks `matplotlib`.

**Files:**
- No file changes — this is a CLI command

- [ ] **Step 1: Submit the EDA stats Spark job as a CUSTOM_JAR step**

```bash
CLUSTER_ID=$(terraform output -raw emr_cluster_id)
aws emr add-steps \
  --cluster-id $CLUSTER_ID \
  --steps 'Type=CUSTOM_JAR,Name=EDA Stats Full Dataset,ActionOnFailure=CONTINUE,Jar=s3://elasticmapreduce/libs/script-runner/script-runner.jar,Args=["spark-submit","--deploy-mode","cluster","--conf","spark.executor.memory=4g","--conf","spark.executor.cores=2","s3://25tfgf-ai-medical/eda_emr_stats.py"]' \
  --region us-east-1
```

- [ ] **Step 2: Get step ID from output**

Note the `StepId` from the command output (format: `s-XXXXXXXX`).

- [ ] **Step 3: Monitor step status**

```bash
STEP_ID="s-XXXXXXXX"  # Replace with actual step ID
aws emr describe-step --cluster-id $CLUSTER_ID --step-id $STEP_ID --query 'Step.Status' --output text
```

- [ ] **Step 4: Check for figures in S3**

```bash
aws s3 ls s3://25tfgf-ai-medical/figures/ --region us-east-1
```

---

## Task 7: Terminate EMR cluster

**CRITICAL:** Must terminate after EDA to avoid excessive costs.

- [ ] **Step 1: Terminate EMR cluster**

```bash
CLUSTER_ID=$(terraform output -raw emr_cluster_id)
aws emr terminate-clusters --cluster-ids $CLUSTER_ID --region us-east-1
```

- [ ] **Step 2: Verify termination**

```bash
aws emr describe-cluster --cluster-id $CLUSTER_ID --query 'Cluster.Status.State' --output text
# Expected: TERMINATED
```

---

## Root Cause of Previous Failure

The earlier attempts used `Type=SPARK` step type, which uses `spark-submit` internally but with a different executor environment that lacks `matplotlib`. The fix is to use `Type=CUSTOM_JAR` with `command-runner.jar` and explicitly invoke `spark-submit --deploy-mode cluster` — this runs the Python script in the same YARN container environment as the bootstrap, which has all packages installed.

---

## Spec Coverage Checklist

- [ ] Full 21M row EDA statistics computed (context/question lengths, percentiles, histogram)
- [ ] Full 21M row split distribution (train/val/test counts + percentages)
- [ ] 3 EDA figures generated: context length histogram, question length histogram, split pie chart
- [ ] Figures uploaded to `s3://25tfgf-ai-medical/figures/`
- [ ] EMR cluster created via Terraform with bootstrap action
- [ ] EMR cluster terminated after EDA (cost control)
- [ ] All scripts committed to GitHub
