# Medical Chatbot Pipeline — Design Specification

**Date:** 2026-04-27
**Project:** CISC 886 – Cloud-based Conversational Chatbot
**Dataset:** ruslanmv/ai-medical-dataset (changed from StackOverflow Python)
**Approach:** Medical-Optimized Pipeline (Approach B)

---

## 1. Overview

Adapt the existing cloud chatbot pipeline from StackOverflow Python to the AI Medical Dataset. The infrastructure (VPC, EMR, EC2, S3) remains unchanged — only the data layer and preprocessing are modified for the medical domain.

**Key changes:**
- Schema adaptation: `question_body/answer_body` → `question/context`
- Quality filtering: Length-based heuristics (no answer_score available)
- Prompt template: Medical-focused format
- Token limit: 1024 (up from 512)

---

## 2. Architecture

No infrastructure changes. Same pipeline flow:

```
HuggingFace → S3 (raw) → EMR/Spark → S3 (processed) → Local Fine-tuning → EC2/Ollama → OpenWebUI
     │                                                         ↑
     └───────────────── Download ───────────────────────────────┘
```

**Infrastructure components:**
- VPC with public subnets, Internet Gateway, route tables
- EMR cluster (Spark + JupyterHub) for preprocessing
- EC2 instance (g4dn.xlarge) for Ollama + OpenWebUI
- S3 bucket for raw and processed data

---

## 3. Schema Comparison

| Aspect | StackOverflow (old) | Medical (new) |
|--------|---------------------|---------------|
| Question field | `question_body` | `question` |
| Answer field | `answer_body` | `context` |
| Quality metric | `answer_score` | None available |
| Rows | ~smaller subset | ~21.2M |
| Format | Q&A pairs | Question + clinical context |

---

## 4. Spark Preprocessing

### 4.1 Input Data

- **Source:** HuggingFace `ruslanmv/ai-medical-dataset` (downloaded locally to `data/ai-medical-dataset/`)
- **Format:** Parquet (18 files, ~4.36 GB)
- **Schema:** `question` (string), `context` (string)

### 4.2 Filtering Rules

| Filter | Threshold | Rationale |
|--------|-----------|-----------|
| Minimum context length | 200 characters | Remove trivial/empty/single-word contexts |
| Maximum context length | 4096 characters | Prevent truncation issues before 1024 token limit |
| Minimum question length | 20 characters | Remove malformed or degenerate questions |
| Non-null check | Both fields | Remove any null/None entries |

### 4.3 Pipeline Steps

1. Load raw parquet files from S3
2. Apply length-based quality filters
3. Create medical prompt template
4. Add unique ID
5. Train/val/test split (80/10/10)
6. Write partitioned parquet to S3

### 4.4 Prompt Template

```
### Medical Question: {question}

### Clinical Context: {context}

### Answer:
```

**Rationale:** "Clinical Context" is more accurate than "Answer" since the context is supporting information rather than a direct answer. "Answer:" is left empty for the model to generate.

---

## 5. Fine-Tuning Configuration

### 5.1 Model

| Parameter | Value |
|-----------|-------|
| Model | google/gemma-4-2b |
| Parameters | ~2B |
| License | Gemma Terms |
| Quantization | 4-bit (QLoRA) |

### 5.2 Hyperparameters

| Hyperparameter | Value |
|----------------|-------|
| Max sequence length | 1024 tokens |
| Learning rate | 2e-4 |
| Batch size (per device) | 2 |
| Gradient accumulation steps | 16 |
| Epochs | 3 |
| LoRA rank (r) | 16 |
| LoRA alpha | 32 |
| Target modules | q_proj, k_proj, v_proj, o_proj |
| Warmup steps | 50 |

### 5.3 Test Prompts (for inference comparison)

Example medical questions for evaluating fine-tuning:

1. "### Medical Question: What is the mechanism of action of ibuprofen?\n\n### Clinical Context:\n\n### Answer:"
2. "### Medical Question: Describe the pathophysiology of type 2 diabetes\n\n### Clinical Context:\n\n### Answer:"

---

## 6. EDA Metrics

Replace `answer_score` metrics with context-based metrics:

| Metric | Description |
|--------|-------------|
| Context length distribution | Histogram of context character lengths |
| Question length distribution | Histogram of question character lengths |
| Split distribution | Train/val/test pie chart |
| Records filtered | Count before/after length filtering |

---

## 7. File Changes Summary

| File | Action | Changes |
|------|--------|---------|
| `spark/preprocess.py` | Modify | Schema columns, length filtering, prompt template |
| `spark/eda_analysis.py` | Modify | Column references, context length metrics |
| `colab/fine_tune.ipynb` | Modify | Prompt template, max_tokens=1024, test prompts |
| `README.md` | Modify | Dataset reference, medical examples |
| `terraform/*.tf` | No change | Infrastructure unchanged |
| `ec2/*.sh` | No change | Deployment unchanged |
| `ec2/*.service` | No change | Services unchanged |

---

## 8. S3 Bucket Structure

```
q1abc-ai-medical/
├── raw/
│   └── (parquet files from HuggingFace)
├── processed/
│   ├── split=train/
│   ├── split=val/
│   └── split=test/
└── models/
    └── gemma-4-2b-medical.gguf
```

---

## 9. Out of Scope

- Dataset source change (already downloaded to `data/ai-medical-dataset/`)
- Model change (Gemma-4-2B remains appropriate)
- Infrastructure changes
- Web interface changes (OpenWebUI unchanged)
