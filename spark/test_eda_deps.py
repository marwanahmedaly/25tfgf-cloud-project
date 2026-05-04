#!/usr/bin/env python3
"""
Simple test script to verify EDA deps and S3 access.
"""

import sys
import os

print("Python version:", sys.version)

# Test matplotlib import
try:
    import matplotlib
    matplotlib.use('Agg')
    print("matplotlib OK:", matplotlib.__version__)
except Exception as e:
    print("matplotlib FAILED:", e)

# Test pandas import
try:
    import pandas as pd
    print("pandas OK:", pd.__version__)
except Exception as e:
    print("pandas FAILED:", e)

# Test seaborn import
try:
    import seaborn as sns
    print("seaborn OK:", sns.__version__)
except Exception as e:
    print("seaborn FAILED:", e)

# Test PySpark
try:
    from pyspark.sql import SparkSession
    print("PySpark OK")
    spark = SparkSession.builder.appName("test").getOrCreate()
    print("SparkContext version:", spark.sparkContext.version)
    spark.stop()
except Exception as e:
    print("PySpark FAILED:", e)

# Test reading from S3
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("test-s3").getOrCreate()
    df = spark.read.parquet("s3://25tfgf-ai-medical/processed/")
    count = df.count()
    print(f"S3 read OK, row count: {count}")
    spark.stop()
except Exception as e:
    print("S3 read FAILED:", e)

print("Test script completed successfully")
