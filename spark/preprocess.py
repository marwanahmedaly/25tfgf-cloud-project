"""
PySpark preprocessing pipeline for StackOverflow Python Q&A dataset.
Filters, transforms, and splits data for LLM fine-tuning.
"""

import argparse
import json
import logging
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from pyspark.sql.window import Window

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = "### Question: {question}\n### Answer: {answer}\n"


def parse_json_string(col):
    """Parse JSON string if column contains JSON-formatted string."""
    return F.when(
        F.col(col).startswith('{'),
        F.from_json(F.col(col), schema='question_body STRING, answer_body STRING')
    ).otherwise(F.col(col))


def create_spark_session():
    """Create SparkSession with adaptive query execution enabled."""
    return (SparkSession.builder
            .appName("stackoverflow-preprocess")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.adaptive.skewJoin.enabled", "true")
            .getOrCreate())


def load_arrow_data(spark, input_path):
    """Load raw arrow files into Spark DataFrame."""
    logger.info(f"Loading arrow files from {input_path}")
    df = spark.read.format("arrow").load(input_path)
    logger.info(f"Loaded {df.count()} rows")
    return df


def filter_by_score(df, min_score):
    """Filter rows by minimum answer score."""
    logger.info(f"Filtering by answer_score >= {min_score}")
    filtered = df.filter(F.col("answer_score") >= min_score)
    logger.info(f"After filtering: {filtered.count()} rows")
    return filtered


def parse_bodies(df):
    """Parse question_body and answer_body (handle JSON string format)."""
    logger.info("Parsing question and answer bodies")

    # Check if column contains JSON string format
    parsed = df.withColumn(
        "question_parsed",
        F.when(
            F.col("question_body").startswith('{'),
            F.get_json_object(F.col("question_body"), "$.question_body")
        ).otherwise(F.col("question_body"))
    ).withColumn(
        "answer_parsed",
        F.when(
            F.col("answer_body").startswith('{'),
            F.get_json_object(F.col("answer_body"), "$.answer_body")
        ).otherwise(F.col("answer_body"))
    )

    return parsed


def remove_empty_rows(df):
    """Remove rows with empty question or answer."""
    logger.info("Removing empty question/answer rows")
    cleaned = df.filter(
        (F.trim(F.col("question_parsed")) != '') &
        (F.trim(F.col("answer_parsed")) != '')
    )
    logger.info(f"After removing empty rows: {cleaned.count()} rows")
    return cleaned


def create_prompt(df):
    """Create prompt template from question and answer."""
    logger.info("Creating prompt template")
    return df.withColumn(
        "prompt",
        F.concat(
            F.lit("### Question: "),
            F.col("question_parsed"),
            F.lit("\n### Answer: "),
            F.col("answer_parsed"),
            F.lit("\n")
        )
    )


def add_unique_id(df):
    """Add unique ID using monotonically increasing ID."""
    logger.info("Adding unique ID")
    return df.withColumn("id", F.monotonically_increasing_id())


def stratified_split(df, train_ratio, val_ratio, seed=42):
    """
    Perform stratified train/val/test split based on answer_score buckets.
    Returns DataFrame with 'split' column.
    """
    logger.info(f"Performing stratified split (train={train_ratio}, val={val_ratio})")

    # Create score buckets for stratification
    num_buckets = 100
    bucket_col = "score_bucket"

    df_with_bucket = df.withColumn(
        bucket_col,
        F.ntile(num_buckets).over(Window.partitionBy())
    )

    # Add random column for split assignment
    df_ranked = df_with_bucket.withColumn("rand", F.rand(seed))

    # Calculate cumulative probabilities
    test_ratio = 1.0 - train_ratio - val_ratio

    # Assign split based on stratified sampling
    df_split = df_ranked.withColumn(
        "split",
        F.when(F.col("rand") < train_ratio, "train")
        .when(F.col("rand") < train_ratio + val_ratio, "val")
        .otherwise("test")
    )

    # Clean up intermediate columns
    return df_split.drop(bucket_col, "rand")


def write_parquet_partitioned(df, output_path):
    """Write DataFrame as Parquet partitioned by split."""
    logger.info(f"Writing Parquet to {output_path} partitioned by split")
    df.write.mode("overwrite").partitionBy("split").parquet(output_path)
    logger.info("Write complete")


def main():
    parser = argparse.ArgumentParser(description="Preprocess StackOverflow Q&A for LLM fine-tuning")
    parser.add_argument("--input", required=True, help="Input path to arrow files (local or S3)")
    parser.add_argument("--output", required=True, help="Output path for Parquet files")
    parser.add_argument("--min-answer-score", type=int, default=5, help="Minimum answer score filter")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Maximum token length (for reference)")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")

    args = parser.parse_args()

    logger.info("Starting preprocessing pipeline")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")

    # Create Spark session
    spark = create_spark_session()

    try:
        # Load data
        df = load_arrow_data(spark, args.input)

        # Filter by score
        df = filter_by_score(df, args.min_answer_score)

        # Parse bodies
        df = parse_bodies(df)

        # Remove empty rows
        df = remove_empty_rows(df)

        # Create prompt
        df = create_prompt(df)

        # Add unique ID
        df = add_unique_id(df)

        # Stratified split
        df = stratified_split(df, args.train_ratio, args.val_ratio)

        # Select final columns
        output_df = df.select(
            "id",
            "question_id",
            "answer_id",
            "question_parsed",
            "answer_parsed",
            "prompt",
            "question_score",
            "answer_score",
            "split"
        )

        # Write output
        write_parquet_partitioned(output_df, args.output)

        # Log split distribution
        split_counts = output_df.groupBy("split").count().collect()
        for row in split_counts:
            logger.info(f"Split '{row['split']}': {row['count']} rows")

    finally:
        spark.stop()
        logger.info("Pipeline complete")


if __name__ == "__main__":
    main()