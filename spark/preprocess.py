"""
PySpark preprocessing pipeline for Medical Q&A dataset.
Filters, transforms, and splits data for LLM fine-tuning.
"""

import argparse
import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_spark_session() -> SparkSession:
    """Create SparkSession with adaptive query execution enabled."""
    return (SparkSession.builder
            .appName("medical-preprocess")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.adaptive.skewJoin.enabled", "true")
            .getOrCreate())


def load_arrow_data(spark: SparkSession, input_path: str) -> DataFrame:
    """Load raw parquet files into Spark DataFrame."""
    logger.info(f"Loading parquet files from {input_path}")
    df = spark.read.format("parquet").load(input_path)
    logger.info(f"Loaded data from {input_path}")
    return df


def apply_length_filters(df: DataFrame, min_context_length: int, max_context_length: int, min_question_length: int) -> DataFrame:
    """Filter rows by context and question length constraints."""
    logger.info(f"Filtering by length (context: {min_context_length}-{max_context_length}, question: >={min_question_length})")
    filtered = df.filter(
        (F.length(F.col("context")) >= min_context_length) &
        (F.length(F.col("context")) <= max_context_length) &
        (F.length(F.col("question")) >= min_question_length)
    )
    return filtered


def alias_columns(df: DataFrame) -> DataFrame:
    """Create parsed aliases for question and context columns for downstream consistency."""
    logger.info("Aliasing question and context columns")
    parsed = df.withColumn(
        "question_parsed",
        F.col("question")
    ).withColumn(
        "context_parsed",
        F.col("context")
    )
    return parsed


def remove_empty_rows(df: DataFrame) -> DataFrame:
    """Remove rows with empty question or context."""
    logger.info("Removing empty question/context rows")
    cleaned = df.filter(
        (F.trim(F.col("question_parsed")) != '') &
        (F.trim(F.col("context_parsed")) != '')
    )
    return cleaned


def create_prompt(df: DataFrame) -> DataFrame:
    """Create prompt template from question and context."""
    logger.info("Creating prompt template")
    return df.withColumn(
        "prompt",
        F.concat(
            F.lit("### Medical Question: "),
            F.col("question_parsed"),
            F.lit("\n\n### Clinical Context: "),
            F.col("context_parsed"),
            F.lit("\n\n### Answer:\n")
        )
    )


def add_unique_id(df: DataFrame) -> DataFrame:
    """Add unique ID using monotonically increasing ID."""
    logger.info("Adding unique ID")
    return df.withColumn("id", F.monotonically_increasing_id())


def random_split(df: DataFrame, train_ratio: float, val_ratio: float, seed: int = 42) -> DataFrame:
    """
    Perform random train/val/test split.
    Returns DataFrame with 'split' column.
    """
    logger.info(f"Performing random split (train={train_ratio}, val={val_ratio})")

    # Add random column for split assignment
    df_ranked = df.withColumn("rand", F.rand(seed))

    # Assign split based on random sampling
    df_split = df_ranked.withColumn(
        "split",
        F.when(F.col("rand") < train_ratio, "train")
        .when(F.col("rand") < train_ratio + val_ratio, "val")
        .otherwise("test")
    )

    # Clean up intermediate column
    return df_split.drop("rand")


def write_parquet_partitioned(df: DataFrame, output_path: str) -> None:
    """Write DataFrame as Parquet partitioned by split."""
    logger.info(f"Writing Parquet to {output_path} partitioned by split")
    df.write.mode("overwrite").partitionBy("split").parquet(output_path)
    logger.info("Write complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess Medical Q&A for LLM fine-tuning")
    parser.add_argument("--input", required=True, help="Input path to parquet files (local or S3)")
    parser.add_argument("--output", required=True, help="Output path for Parquet files")
    parser.add_argument("--min-context-length", type=int, default=200, help="Minimum context length")
    parser.add_argument("--max-context-length", type=int, default=4096, help="Maximum context length")
    parser.add_argument("--min-question-length", type=int, default=20, help="Minimum question length")
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

        # Apply length filters
        df = apply_length_filters(df, args.min_context_length, args.max_context_length, args.min_question_length)

        # Alias columns
        df = alias_columns(df)

        # Remove empty rows
        df = remove_empty_rows(df)

        # Create prompt
        df = create_prompt(df)

        # Add unique ID
        df = add_unique_id(df)

        # Random split
        df = random_split(df, args.train_ratio, args.val_ratio)

        # Select final columns
        output_df = df.select(
            "id",
            "question_parsed",
            "context_parsed",
            "prompt",
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
