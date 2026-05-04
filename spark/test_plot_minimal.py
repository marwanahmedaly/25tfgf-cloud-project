#!/usr/bin/env python3
import os
from pyspark.sql import SparkSession
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

output_dir = "/home/hadoop/figures"
os.makedirs(output_dir, exist_ok=True)

spark = SparkSession.builder.appName("EDA-Minimal").getOrCreate()
df = spark.read.parquet("s3://25tfgf-ai-medical/processed/")
pdf = df.toPandas()
print(f"Loaded {len(pdf)} rows")

print("Creating test plot...")
fig, ax = plt.subplots(figsize=(8, 6))
ax.hist([1, 2, 3, 4, 5], bins=5, color='steelblue')
ax.set_title('Test Plot')
ax.set_xlabel('X')
ax.set_ylabel('Y')
plt.tight_layout()
out_path = f"{output_dir}/test_plot.png"
plt.savefig(out_path, dpi=100)
plt.close()
print(f"Saved: {out_path}")

spark.stop()
print("Done!")
