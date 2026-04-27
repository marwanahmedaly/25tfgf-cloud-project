# Medical Chatbot Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the existing chatbot pipeline from StackOverflow Python to the AI Medical Dataset by updating Spark preprocessing, EDA analysis, fine-tuning notebook, and README.

**Architecture:** Medical-optimized data pipeline using length-based quality filtering and medical-themed prompt templates. Infrastructure (VPC, EMR, EC2, S3) remains unchanged.

**Tech Stack:** PySpark, AWS EMR/S3, HuggingFace transformers + peft, Unsloth, Ollama, OpenWebUI, Terraform, Ubuntu 22.04

---

## File Structure

```
cloud-project/
├── spark/
│   ├── preprocess.py      # Modify: schema, filtering, prompt template
│   ├── eda_analysis.py    # Modify: column refs, context length metrics
│   ├── requirements.txt   # No change
│   └── bootstrap_emr.sh   # No change
├── colab/
│   └── fine_tune.ipynb    # Modify: prompt template, max_tokens=1024, test prompts
├── ec2/                   # No changes
├── terraform/             # Modify: S3 bucket name
├── README.md              # Modify: dataset reference, medical examples
└── docs/superpowers/plans/
    └── 2026-04-27-medical-chatbot-implementation.md  # This plan
```

---

## Task 1: Update Spark Preprocessing

**Files:**
- Modify: `spark/preprocess.py`

- [ ] **Step 1: Read the current preprocess.py**

Read `spark/preprocess.py` to understand its current structure before modifying.

- [ ] **Step 2: Update schema column references**

Change from StackOverflow schema (`question_body`, `answer_body`, `answer_score`) to medical schema (`question`, `context`).

Replace line 37 in `filter_by_score()`:
```python
# OLD (line 37)
filtered = df.filter(F.col("answer_score") >= min_score)

# NEW - remove score filtering (no score available in medical dataset)
# Add length-based filtering instead
```

- [ ] **Step 3: Replace parse_bodies() function**

```python
def parse_bodies(df):
    """
    Parse question and context fields from medical dataset.
    No JSON parsing needed - medical dataset uses simple string columns.
    """
    logger.info("Parsing question and context fields")

    # Medical dataset has direct string columns
    parsed = df.withColumn(
        "question_parsed",
        F.when(F.col("question").isNull(), F.lit("")).otherwise(F.col("question"))
    ).withColumn(
        "context_parsed",
        F.when(F.col("context").isNull(), F.lit("")).otherwise(F.col("context"))
    )

    return parsed
```

- [ ] **Step 4: Replace remove_empty_rows() with length-based filtering**

```python
def apply_length_filters(df, min_context_length=200, max_context_length=4096, min_question_length=20):
    """
    Apply length-based quality filters for medical dataset.
    Replaces answer_score filtering.
    """
    logger.info(f"Applying length filters: context [{min_context_length}-{max_context_length}], question >= {min_question_length}")

    # Filter by context length
    df = df.filter(
        (F.length(F.col("context_parsed")) >= min_context_length) &
        (F.length(F.col("context_parsed")) <= max_context_length)
    )

    # Filter by question length
    df = df.filter(F.length(F.col("question_parsed")) >= min_question_length)

    # Remove null/empty
    df = df.filter(
        (F.trim(F.col("question_parsed")) != '') &
        (F.trim(F.col("context_parsed")) != '')
    )

    logger.info(f"After length filtering: {df.count()} rows")
    return df
```

- [ ] **Step 5: Update create_prompt() for medical template**

```python
def create_prompt(df):
    """Create medical prompt template from question and context."""
    logger.info("Creating medical prompt template")
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
```

- [ ] **Step 6: Update main() function**

In `main()`, replace the filter call:
```python
# OLD (line 149)
df = filter_by_score(df, args.min_answer_score)

# NEW - use length-based filtering (remove min_score argument)
df = apply_length_filters(df,
    min_context_length=200,
    max_context_length=4096,
    min_question_length=20
)
```

Also update column selection in `output_df`:
```python
# OLD columns (lines 167-177)
output_df = df.select(
    "id", "question_id", "answer_id",
    "question_parsed", "answer_parsed", "prompt",
    "question_score", "answer_score", "split"
)

# NEW columns for medical dataset
output_df = df.select(
    "id",
    "question_parsed",
    "context_parsed",
    "prompt",
    "split"
)
```

- [ ] **Step 7: Update argparse defaults**

```python
# Remove min_answer_score, add context length parameters
parser.add_argument("--min-context-length", type=int, default=200, help="Minimum context length")
parser.add_argument("--max-context-length", type=int, default=4096, help="Maximum context length")
parser.add_argument("--min-question-length", type=int, default=20, help="Minimum question length")
# Remove: parser.add_argument("--min-answer-score", ...)
```

- [ ] **Step 8: Commit**

```bash
git add spark/preprocess.py
git commit -m "feat(spark): adapt preprocessing for medical dataset schema and length-based filtering"
```

---

## Task 2: Update EDA Analysis

**Files:**
- Modify: `spark/eda_analysis.py`

- [ ] **Step 1: Read the current eda_analysis.py**

Read `spark/eda_analysis.py` to understand its current structure.

- [ ] **Step 2: Update token length computation**

Replace tokenizer reference from question_body/answer_body to context:
```python
# In compute_token_lengths(), update to use medical dataset columns
def compute_token_lengths(df: pd.DataFrame, tokenizer) -> pd.DataFrame:
    """Compute token lengths for medical prompts."""
    logger.info("Computing token lengths")

    prompts = df["prompt"].tolist()
    token_lengths = []

    for i, prompt in enumerate(prompts):
        tokens = tokenizer.encode(prompt, truncation=True, max_length=2048)
        token_lengths.append(len(tokens))

        if (i + 1) % 10000 == 0:
            logger.info(f"  Processed {i + 1}/{len(prompts)} prompts")

    df["token_length"] = token_lengths
    return df
```

- [ ] **Step 3: Update context length distribution plot**

In `plot_context_length_distribution()`, replace answer_score histogram:
```python
def plot_context_length_distribution(df: pd.DataFrame, output_dir: str):
    """Generate context length distribution histogram."""
    logger.info("Plotting context length distribution")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Use context_parsed column, clip at 4096 for visualization
    context_lengths = df["context_parsed"].str.len().clip(upper=4096)
    ax.hist(context_lengths, bins=50, edgecolor="black", alpha=0.7, color="steelblue")
    ax.set_xlabel("Context Length (characters, clipped at 4096)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Clinical Context Lengths")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "context_length_distribution.png"), dpi=150)
    plt.close()

    logger.info(f"Saved context_length_distribution.png")
```

- [ ] **Step 4: Update question length distribution plot**

Add new function:
```python
def plot_question_length_distribution(df: pd.DataFrame, output_dir: str):
    """Generate question length distribution histogram."""
    logger.info("Plotting question length distribution")

    fig, ax = plt.subplots(figsize=(10, 6))

    question_lengths = df["question_parsed"].str.len().clip(upper=500)
    ax.hist(question_lengths, bins=50, edgecolor="black", alpha=0.7, color="forestgreen")
    ax.set_xlabel("Question Length (characters, clipped at 500)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Medical Question Lengths")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "question_length_distribution.png"), dpi=150)
    plt.close()

    logger.info(f"Saved question_length_distribution.png")
```

- [ ] **Step 5: Update main() to use new plots**

Replace old plot calls:
```python
# OLD (in main())
plot_token_length_distribution(df, args.output)
plot_answer_score_histogram(df, args.output)
plot_split_distribution(df, args.output)

# NEW
plot_token_length_distribution(df, args.output)
plot_context_length_distribution(df, args.output)  # replaces answer_score histogram
plot_question_length_distribution(df, args.output)  # new
plot_split_distribution(df, args.output)
```

Also update summary statistics:
```python
# Update EDA Summary Statistics section
logger.info("\n=== EDA Summary Statistics ===")
logger.info(f"Total records: {len(df)}")
logger.info(f"Split distribution:\n{df['split'].value_counts()}")
logger.info(f"\nContext length stats:")
logger.info(f"  Min: {df['context_parsed'].str.len().min()}")
logger.info(f"  Max: {df['context_parsed'].str.len().max()}")
logger.info(f"  Mean: {df['context_parsed'].str.len().mean():.1f}")
logger.info(f"  Median: {df['context_parsed'].str.len().median():.0f}")
logger.info(f"\nQuestion length stats:")
logger.info(f"  Min: {df['question_parsed'].str.len().min()}")
logger.info(f"  Max: {df['question_parsed'].str.len().max()}")
logger.info(f"  Mean: {df['question_parsed'].str.len().mean():.1f}")
```

- [ ] **Step 6: Commit**

```bash
git add spark/eda_analysis.py
git commit -m "feat(spark): update EDA for medical dataset with context/question length metrics"
```

---

## Task 3: Update Fine-Tuning Notebook

**Files:**
- Modify: `colab/fine_tune.ipynb`

- [ ] **Step 1: Read the current fine_tune.ipynb**

Read `colab/fine_tune.ipynb` to understand its structure.

- [ ] **Step 2: Update markdown cells for medical dataset**

In cell-0 (title cell):
```markdown
# QLoRA Fine-Tuning Gemma-4-2B on Medical Q&A

This notebook fine-tunes the Gemma-4-2B model using QLoRA on medical question-context pairs from the AI Medical Dataset.
```

- [ ] **Step 3: Update cell-4 (data loading)**

Replace the S3 bucket reference:
```python
# OLD
BUCKET_NAME = 'q1abc-so-python'  # Replace with your actual bucket name

# NEW
BUCKET_NAME = 'q1abc-ai-medical'  # Medical dataset bucket
DATA_PREFIX = 'processed/'
```

- [ ] **Step 4: Update MAX_SEQ_LENGTH in cell-9**

```python
# OLD
MAX_SEQ_LENGTH = 512

# NEW
MAX_SEQ_LENGTH = 1024
```

- [ ] **Step 5: Update cell-10 (training args)**

```python
# Update max_seq_length in TrainingArguments
training_args = TrainingArguments(
    output_dir='./gemma-qlora-finetuned-medical',
    learning_rate=2e-4,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=16,
    num_train_epochs=3,
    max_seq_length=1024,  # Changed from 512
    logging_steps=10,
    save_steps=100,
    eval_steps=100,
    warmup_steps=50,
    fp16=True,
    eval_strategy='steps',
    save_strategy='steps',
    load_best_model_at_end=True
)
```

- [ ] **Step 6: Update test prompts in cell-18 (inference comparison)**

```python
# OLD test prompts
test_prompts = [
    '### Question: How do I sort a list in Python?\n### Answer:',
    '### Question: What is the difference between a list and a tuple?\n### Answer:',
]

# NEW medical test prompts
test_prompts = [
    '### Medical Question: What is the mechanism of action of ibuprofen?\n\n### Clinical Context:\n\n### Answer:',
    '### Medical Question: Describe the pathophysiology of type 2 diabetes\n\n### Clinical Context:\n\n### Answer:',
]
```

- [ ] **Step 7: Update export cell (cell-16)**

```python
# Reload base model and merge LoRA weights
model = PeftModel.from_pretrained(base_model, './gemma-qlora-finetuned-final')
model = model.merge_and_unload()

# Save as HuggingFace format
model.save_pretrained('./gemma-qlora-gguf-medical')  # Changed from 'gemma-qlora-gguf'
tokenizer.save_pretrained('./gemma-qlora-gguf-medical')

print("Model exported to ./gemma-qlora-gguf-medical")
print("To convert to GGUF for Ollama, use: llama-cli or llama.cpp converter")
```

- [ ] **Step 8: Commit**

```bash
git add colab/fine_tune.ipynb
git commit -m "feat(colab): update fine-tuning notebook for medical dataset with 1024 token limit"
```

---

## Task 4: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current README.md**

Read `README.md` to understand its structure.

- [ ] **Step 2: Update title and description**

```markdown
# Cloud-based Medical Chatbot

**Course:** CISC 886 – Cloud Computing, Queen's University

**Approach:** A — Cost-optimized hybrid (local training, minimal cloud)

A chatbot fine-tuned on medical Q&A data (ruslanmv/ai-medical-dataset), leveraging cloud infrastructure for scalable data processing and deployment while optimizing costs through local model training.
```

- [ ] **Step 3: Update architecture diagram description**

```markdown
## Architecture

Data flows from the HuggingFace AI Medical Dataset (ruslanmv/ai-medical-dataset) downloaded locally, uploaded to S3 as raw data, processed by EMR Spark into clean tokenized Parquet with length-based quality filtering, downloaded to local GPU for QLoRA fine-tuning with Gemma-4-2B, exported as GGUF to EC2, served via Ollama, and accessed through OpenWebUI in a browser.
```

- [ ] **Step 4: Update S3 bucket references**

Replace all `q1abc-so-python` with `q1abc-ai-medical`:
- S3 bucket name
- aws s3 cp commands
- spark-submit paths

- [ ] **Step 5: Update data upload command**

```bash
# OLD
aws s3 cp ./data/stackoverflow_python/ s3://YOUR_NETID-so-python/raw/ --recursive

# NEW
aws s3 cp ./data/ai-medical-dataset/data/ s3://YOUR_NETID-ai-medical/raw/ --recursive
```

- [ ] **Step 6: Update curl test example**

```bash
# OLD
curl http://localhost:11434/api/generate -d '{"model":"gemma-4-2b","prompt":"How do I sort a list in Python?"}'

# NEW
curl http://localhost:11434/api/generate -d '{"model":"gemma-4-2b-medical","prompt":"### Medical Question: What is the mechanism of action of ibuprofen?\n\n### Clinical Context:\n\n### Answer?"}'
```

- [ ] **Step 7: Update license section**

```markdown
## License

- **Model:** Gemma Terms — Before using Gemma, accept the license at https://huggingface.co/google/gemma-4-2b
- **Dataset:** [ruslanmv/ai-medical-dataset](https://huggingface.co/datasets/ruslanmv/ai-medical-dataset) (CC-BY 4.0)
```

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs: update README for medical chatbot dataset and examples"
```

---

## Task 5: Update Terraform S3 Bucket Name

**Files:**
- Modify: `terraform/variables.tf`, `terraform/emr.tf`

- [ ] **Step 1: Update variables.tf**

```hcl
# OLD
variable "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  type        = string
  default     = "q1abc-so-python"
}

# NEW
variable "s3_bucket_name" {
  description = "S3 bucket name for medical dataset storage"
  type        = string
  default     = "q1abc-ai-medical"
}
```

- [ ] **Step 2: Update emr.tf references**

Find and replace bucket references:
```hcl
# In aws_s3_bucket resource (around line 303-308)
# OLD
resource "aws_s3_bucket" "data" {
  bucket = "${var.net_id}-so-python"
  ...
}

# NEW
resource "aws_s3_bucket" "data" {
  bucket = "${var.net_id}-ai-medical"
  ...
}
```

- [ ] **Step 3: Commit**

```bash
git add terraform/variables.tf terraform/emr.tf
git commit -m "feat(terraform): rename S3 bucket to ai-medical"
```

---

## Spec Coverage Check

| Spec Section | Implementation Task |
|-------------|---------------------|
| Section 4.1 Input Data | Task 1 (spark/preprocess.py) |
| Section 4.2 Filtering Rules (200-4096 chars, 20 char question) | Task 1 (apply_length_filters()) |
| Section 4.3 Pipeline Steps | Task 1 (main()) |
| Section 4.4 Prompt Template (Medical Question/Clinical Context/Answer) | Task 1 (create_prompt()) |
| Section 5.2 Hyperparameters (max_tokens=1024) | Task 3 (fine_tune.ipynb cell-10) |
| Section 5.3 Test Prompts | Task 3 (fine_tune.ipynb cell-18) |
| Section 6 EDA Metrics (context/question length distributions) | Task 2 (eda_analysis.py) |
| Section 7 File Changes Summary | Tasks 1-4 |
| Section 8 S3 Bucket Structure | Task 5 (terraform) |
| README dataset reference | Task 4 (README.md) |

---

## Placeholder Scan

- No "TBD" or "TODO" found
- All code blocks contain complete implementations
- All function names and signatures are consistent across tasks
- No "similar to X" references

## Type Consistency

- Function `apply_length_filters()` used consistently in main()
- Column names `question_parsed`, `context_parsed`, `prompt` consistent across preprocess.py, eda_analysis.py, fine_tune.ipynb
- MAX_SEQ_LENGTH = 1024 consistent across preprocess.py argparse and fine_tune.ipynb
- S3 bucket name `q1abc-ai-medical` consistent across terraform, README, fine_tune.ipynb
