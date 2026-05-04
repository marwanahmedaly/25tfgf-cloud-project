# CISC 886 Cloud-based Conversational Chatbot — Implementation Tutorial

**Course:** CISC 886 – Cloud Computing, Queen's University
**Project:** Cloud-based Medical Chatbot (Healthcare domain)
**Model:** unsloth/gemma-2-2b-it (Google Gemma-2-2B, instruction-tuned via Unsloth)
**Dataset:** ruslanmv/ai-medical-dataset (21.2M medical Q&A pairs)
**Training:** Google Colab with Unsloth (`/colab/fine_tune_4.py`)
**Inference:** EC2 m5.xlarge (Ubuntu 22.04) + Ollama + OpenWebUI

---

## Overview

This document provides a complete step-by-step implementation tutorial aligned with the CISC 886 project deliverables. Each section maps to a deliverable section in `CISC-886-Project-Deliverable.md`.

### Architecture Summary

```
HuggingFace Dataset → S3 (raw) → EMR/Spark → S3 (processed) → Google Colab (Unsloth, 100k sample) → EC2/Ollama → Browser/OpenWebUI
```

> **100k Sample Strategy:** Both EDA analysis and model fine-tuning use a 100k random sample from the processed dataset for computational efficiency while maintaining representative results.

### Deliverable Mark Breakdown

| Section | Deliverable | Marks |
|---------|-------------|-------|
| 1 | System Architecture Diagram + Paragraph | 2 |
| 2 | VPC & Networking (Terraform) | 4 |
| 3 | Model & Dataset Selection | 3 |
| 4 | EMR + Spark Preprocessing | 5 |
| 5 | Model Fine-Tuning | 6 |
| 6 | EC2 Deployment | 3 |
| 7 | Web Interface | 2 |
| **Total** | | **25** |

---

## Section 1: System Architecture (2 marks)

### What You Need

1. **Architecture Diagram** — Create using draw.io, Lucidchart, or similar
2. **Data Flow Paragraph** — Written description of data movement

### Components to Include in Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────┐ │
│  │   HuggingFace│    │      S3      │    │      EMR      │    │    S3    │ │
│  │   (Dataset)  │───▶│(25tfgf-ai-   │───▶│  (Spark)     │───▶│(processed│ │
│  │              │    │   medical)   │    │  m5.xlarge   │    │  )       │ │
│  └──────────────┘    └──────────────┘    └───────────────┘    └────┬─────┘ │
│                                                                      │       │
│                                                                      ▼       │
│                                                               ┌──────────────┐│
│                                                               │ Google Colab ││
│                                                               │(Unsloth QLoRA││
│                                                               │  Fine-tune)  ││
│                                                               └──────┬───────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                                    │                              │
                                    │                              ▼
                           ┌────────┴────────┐      ┌──────────────────────┐
                           │   S3 Bucket    │      │      EC2 m5.xlarge    │
                           │(upload model)  │      │ (Ollama + OpenWebUI)  │
                           └────────────────┘      └──────────────────────┘
```

### Required Components:
- **VPC** with CIDR block
- **Public Subnets** (2 subnets in different AZs)
- **Internet Gateway**
- **EMR Cluster** (master + core nodes)
- **S3 Bucket** (raw + processed folders)
- **EC2 Instance** (m5.xlarge for inference)
- **Google Colab** (for fine-tuning with Unsloth)
- **Browser** (for OpenWebUI)

### Data Flow Paragraph (copy and customize):

> Data flows from the HuggingFace Medical Dataset (ruslanmv/ai-medical-dataset) downloaded locally and uploaded to S3 as raw data. The EMR Spark cluster processes this data through a PySpark pipeline that applies length-based quality filtering, creates a medical prompt template, and splits into train/val/test sets stored as Parquet in S3. The processed data is downloaded to a local GPU machine where QLoRA fine-tuning is performed on Gemma-4-2B. The fine-tuned model is exported to GGUF format and deployed to an EC2 g4dn.xlarge instance, where Ollama serves the model and OpenWebUI provides a browser-based chat interface.

---

## Section 2: VPC & Networking (4 marks)

### Step 2.1: Initialize Terraform

```bash
cd terraform
terraform init
```

### Step 2.2: Configure Variables

Edit `terraform/variables.tf` with your netID:

```hcl
variable "net_id" {
  default = "YOUR_NETID"  # e.g., "25tfgf"
}

variable "key_name" {
  default = "YOUR_KEY_NAME"  # e.g., "25tfgf-key"
}
```

### Step 2.3: Plan and Apply

```bash
terraform plan -var="net_id=25tfgf" -var="key_name=25tfgf-key"
terraform apply -var="net_id=25tfgf" -var="key_name=25tfgf-key"
```

### What Terraform Creates

| Resource | Name | Purpose |
|----------|------|---------|
| VPC | `{net_id}-vpc` | Network isolation |
| Internet Gateway | `{net_id}-igw` | Internet access |
| Public Subnet 1 | `{net_id}-public-subnet-1` | us-east-1a |
| Public Subnet 2 | `{net_id}-public-subnet-2` | us-east-1b |
| Route Table | `{net_id}-public-rt` | Routing |
| EC2 Security Group | `{net_id}-ec2-sg` | Ollama + OpenWebUI |
| EMR Master SG | `{net_id}-emr-master-sg` | EMR master node |
| EMR Slave SG | `{net_id}-emr-slave-sg` | EMR slave nodes |

### Security Group Rules Explained

**EC2 Security Group (`{net_id}-ec2-sg`):**
| Port | Source | Purpose |
|------|--------|---------|
| 22 | 0.0.0.0/0 | SSH access |
| 11434 | 0.0.0.0/0 | Ollama API |
| 8080 | 0.0.0.0/0 | OpenWebUI |

**EMR Master Security Group (`{net_id}-emr-master-sg`):**
| Port | Source | Purpose |
|------|--------|---------|
| 22 | 0.0.0.0/0 | SSH |
| 9443 | 0.0.0.0/0 | JupyterHub |
| 0-65535 | 10.0.0.0/16 | EMR internal |

**EMR Slave Security Group (`{net_id}-emr-slave-sg`):**
| Port | Source | Purpose |
|------|--------|---------|
| 22 | 0.0.0.0/0 | SSH |
| 0-65535 | 10.0.0.0/16 | EMR internal |

### Deliverables for Section 2
- [ ] Terraform `.tf` files committed to GitHub
- [ ] Document CIDR blocks and subnet design
- [ ] Document security group rules with justification
- [ ] Explain route table configuration

---

## Section 3: Model & Dataset Selection (3 marks)

### Model Selection: unsloth/gemma-2-2b-it

| Attribute | Value |
|-----------|-------|
| **Model Name** | unsloth/gemma-2-2b-it |
| **Base Model** | google/gemma-2-2b |
| **Parameters** | 2 billion |
| **Source** | https://huggingface.co/unsloth/gemma-2-2b-it |
| **License** | Gemma Terms (requires acceptance on HuggingFace) |
| **Format** | 4-bit quantized GGUF for QLoRA |

**Why unsloth/gemma-2-2b-it?**
- Under 10B parameters (project requirement)
- Unsloth's optimized variant provides 2x faster training and 70% less VRAM
- Instruction-tuned (`-it`) variant provides better foundation for medical fine-tuning
- Suitable for Colab T4 GPU (16GB VRAM) with 4-bit QLoRA (~6GB VRAM)
- Pre-installed dependencies via `pip install unsloth`

### Dataset Selection: AI Medical Dataset

| Attribute | Value |
|-----------|-------|
| **Dataset Name** | ruslanmv/ai-medical-dataset |
| **Source** | https://huggingface.co/datasets/ruslanmv/ai-medical-dataset |
| **License** | CC-BY 4.0 |
| **Samples** | 21,210,000 (21.2M) |
| **Split** | Train only (you will split) |
| **Columns** | `question`, `context` |

**Data Sources:**
| Source | Words |
|--------|-------|
| ClinicalTrials | 127.4M |
| EMEA | 12M |
| PubMed | 968.4M |

### Train/Val/Test Split Strategy

After Spark preprocessing:
- **Train:** 80%
- **Validation:** 10%
- **Test:** 10%

**Data Leakage Prevention:** The random split ensures no data from the test set is used during training or hyperparameter tuning.

### Deliverables for Section 3
- [ ] Document model name, parameters, source link
- [ ] Document model license
- [ ] Explain domain fit and hardware requirements
- [ ] Document dataset name, source, license
- [ ] Document split strategy
- [ ] Show sample data verbatim
- [ ] Provide summary statistics (token length, etc.)

---

## Section 4: EMR + Spark Preprocessing (5 marks)

> ⚠️ **CRITICAL:** You MUST terminate EMR cluster after preprocessing to avoid excessive costs.

### Step 4.1: Upload Bootstrap Script to S3

```bash
# Upload before creating cluster
aws s3 cp spark/bootstrap_emr.sh s3://25tfgf-ai-medical/
```

### Step 4.2: Create EMR Cluster

```bash
aws emr create-cluster \
  --name "25tfgf-emr-cluster" \
  --release-label emr-7.2.0 \
  --instance-count 3 \
  --instance-type m5.xlarge \
  --ec2-attributes SubnetId=subnet-XXXXXX,InstanceProfile=25tfgf-emr-instance-profile \
  --service-role arn:aws:iam::XXXXXXXXXXXX:role/25tfgf-emr-service-role \
  --bootstrap-actions Path=s3://25tfgf-ai-medical/bootstrap_emr.sh,Name="Install dependencies" \
  --applications Name=Spark Name=JupyterHub \
  --configurations '{"Classification":"spark-env","Properties":{"PYSPARK_PYTHON":"/usr/bin/python3"}}'
```

### Step 4.3: Monitor EMR Cluster

```bash
# Check cluster status
aws emr describe-cluster --cluster-id j-XXXXXXXX --query 'Cluster.Status'

# SSH to master node (if needed)
ssh -i 25tfgf-key.pem hadoop@master-public-dns
```

### Step 4.4: Run PySpark Preprocessing

```bash
# Submit Spark job
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --conf spark.executor.memory=4g \
  --conf spark.executor.cores=2 \
  s3://25tfgf-ai-medical/spark/preprocess.py \
  --input s3://25tfgf-ai-medical/raw/ \
  --output s3://25tfgf-ai-medical/processed/ \
  --min-context-length 200 \
  --max-context-length 4096 \
  --min-question-length 20 \
  --train-ratio 0.8 \
  --val-ratio 0.1
```

### Step 4.5: Run EDA Analysis

> **Note:** EDA is performed on a 100k random sample of the processed data for computational efficiency while still providing representative statistics.

```bash
python spark/eda_analysis.py \
  --input s3://25tfgf-ai-medical/processed/ \
  --output ./figures/ \
  --tokenizer google/gemma-4-2b

# Download figures
aws s3 sync ./figures/ s3://25tfgf-ai-medical/figures/
```

### Step 4.6: **TERMINATE EMR CLUSTER**

```bash
# CRITICAL: Terminate immediately after preprocessing
aws emr terminate-clusters --cluster-ids j-XXXXXXXX
```

### PySpark Pipeline Details (`spark/preprocess.py`)

The preprocessing pipeline performs:

1. **Load** raw Parquet files from S3
2. **Filter** by context length (200-4096 chars) and question length (≥20 chars)
3. **Parse** question and context columns
4. **Create prompt template:**
   ```
   ### Medical Question: {question}

   ### Clinical Context: {context}

   ### Answer:
   ```
5. **Split** into train/val/test (80/10/10)
6. **Write** partitioned Parquet to S3

### Deliverables for Section 4
- [ ] PySpark script committed to GitHub with inline explanation
- [ ] Screenshot: EMR console showing cluster configuration
- [ ] Screenshot: EMR console showing cluster in **Terminated** state
- [ ] Screenshot: S3 showing processed output files
- [ ] EDA Figure 1: Token length distribution (with caption)
- [ ] EDA Figure 2: Context length distribution (with caption)
- [ ] EDA Figure 3: Question length distribution OR split distribution (with caption)

---

## Section 5: Model Fine-Tuning (6 marks)

> **Training on Google Colab with Unsloth** — Fine-tuning is performed on Google Colab using the `unsloth/gemma-2-2b-it` model with QLoRA adapters. The training script is at `/colab/fine_tune_4.py`.

### Option A: Google Colab (Recommended)

The training script `/colab/fine_tune_4.py` performs the following:

1. **Install dependencies** — `pip install unsloth transformers peft trl accelerate bitsandbytes datasets scipy boto3`
2. **Download from S3** — Fetches processed data from `25tfgf-ai-medical/processed/`
3. **Load dataset** — Loads train/val/test splits as HuggingFace Dataset
4. **Prepare prompts** — Applies medical chat template with system prompt
5. **Load model** — `unsloth/gemma-2-2b-it` with 4-bit QLoRA
6. **Fine-tune** — 100k sample, 1 epoch, batch size 16
7. **Save adapter** — `gemma_lora_medical/` directory

### Option B: Unsloth Docker Container

```bash
# Run Unsloth container with GPU support
docker run -d -e JUPYTER_PASSWORD="mypassword" \
  -p 8888:8888 -p 8000:8000 -p 2222:22 \
  -v $(pwd)/work:/workspace/work \
  --gpus all \
  unsloth/unsloth

# Access Jupyter Lab at http://localhost:8888
```

**Unsloth Benefits:**
- 2-5x faster training
- 70% less VRAM consumption
- Pre-installed dependencies (transformers, peft, trl, bitsandbytes)
- Native Gemma 2B support

### Step 5.1: Download Processed Data

```bash
# Create data directory
mkdir -p ./data/processed

# Sync from S3
aws s3 sync s3://25tfgf-ai-medical/processed/ ./data/processed/
```

### Step 5.2: Open and Run Jupyter Notebook

> **Note:** Fine-tuning is performed on a 100k sample of the processed data to enable training within Colab's GPU time limits while still achieving meaningful domain adaptation.

```bash
cd colab
jupyter notebook fine_tune.ipynb
```

### Step 5.3: Follow Notebook Sections

1. **Setup** — Install transformers, peft, bitsandbytes, accelerate
2. **Load Data** — Download from S3 or load local processed data
3. **Prepare Dataset** — Convert to HuggingFace Dataset format
4. **Load Model** — Gemma-4-2B with 4-bit QLoRA configuration
5. **Configure Training** — Set hyperparameters
6. **Train** — Fine-tune with LoRA adapter
7. **Export** — Merge adapter and export to GGUF

### Hyperparameters

| Parameter | Value |
|-----------|-------|
| Learning Rate | 2e-4 |
| Batch Size | 16 |
| Gradient Accumulation Steps | 2 |
| Epochs | 1 |
| LoRA Rank | 32 |
| LoRA Alpha | 32 |
| Max Sequence Length | 1024 |
| Quantization | 4-bit NF4 |
| Optimizer | adamw_8bit |
| Warmup Steps | 50 |
| LR Scheduler | cosine |

### Fine-Tuning Code (`/colab/fine_tune_4.py`)

```python
from unsloth import FastLanguageModel
import torch

# Load Gemma 2B instruction-tuned via Unsloth
model, tokenizer = FastLanguageModel.from_pretrained(
    "unsloth/gemma-2-2b-it",
    max_seq_length=1024,
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
)

# Configure LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    lora_alpha=32,
    lora_dropout=0,
    bias="none",
    random_state=3407,
)

# Load dataset and train
trainer.train()

# Save adapter
model.save_pretrained("gemma_lora_medical")
tokenizer.save_pretrained("gemma_lora_medical")
```

### Step 5.4: Compare Base vs Fine-tuned

Run Cell 9 in the notebook to generate comparison responses:

```
BASE MODEL RESPONSE:
Question: What is the mechanism of action of ibuprofen?
Response: [generic answer]

FINE-TUNED MODEL RESPONSE:
Question: What is the mechanism of action of ibuprofen?
Response: [medical-domain enhanced answer]
```

### Step 5.5: Export Model for Ollama

```bash
# After training, merge and save
merged_model = model.merge_and_unload()
merged_model.save_pretrained('./gemma-qlora-medical')
tokenizer.save_pretrained('./gemma-qlora-medical')

# Convert to GGUF (requires llama.cpp)
# Upload to S3
aws s3 cp ./gemma-qlora-medical/ s3://25tfgf-ai-medical/models/ --recursive
```

### Deliverables for Section 5
- [ ] Runnable Jupyter notebook (.ipynb) committed to GitHub
- [ ] Hyperparameter table in report
- [ ] Example 1: Base model response vs Fine-tuned response
- [ ] Example 2: Base model response vs Fine-tuned response
- [ ] Optional: Training loss curve

---

## Section 6: EC2 Deployment (3 marks)

### Step 6.1: SSH to EC2 Instance

```bash
ssh -i 25tfgf-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### Step 6.2: Run Ollama Setup

```bash
# Copy service files
sudo cp ollama.service /etc/systemd/system/
sudo cp openwebui.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start Ollama
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify
sudo systemctl status ollama --no-pager
```

### Step 6.3: Transfer and Load Model

```bash
# Option A: Download from S3
aws s3 cp s3://25tfgf-ai-medical/models/gemma-qlora-medical /home/ubuntu/model/

# Option B: Create from GGUF (if converted locally)
ollama create gemma-4-2b-medical -f /path/to/model.gguf
```

### Step 6.4: Test Ollama API

```bash
# Test API endpoint
curl http://localhost:11434/api/generate -d '{
  "model": "gemma-4-2b-medical",
  "prompt": "What is the mechanism of action of ibuprofen?",
  "stream": false
}'
```

### EC2 Setup Scripts

| Script | Purpose |
|--------|---------|
| `ec2/setup_ollama.sh` | Installs Ollama and creates systemd service |
| `ec2/setup_openwebui.sh` | Installs OpenWebUI (Docker or pip) |
| `ec2/ollama.service` | Auto-start Ollama on boot |
| `ec2/openwebui.service` | Auto-start OpenWebUI on boot |

### Deliverables for Section 6
- [ ] All commands copy-pasted verbatim in README and report
- [ ] Screenshot: Terminal showing Ollama serving Gemma model with model name visible
- [ ] Screenshot: curl call to API with response shown

---

## Section 7: Web Interface (2 marks)

### Step 7.1: Run OpenWebUI Setup

```bash
# On EC2 instance
./setup_openwebui.sh
```

### Step 7.2: Access Web Interface

Open browser: `http://<EC2_PUBLIC_IP>:8080`

### Step 7.3: Configure Model

1. Click settings → Models
2. Select `gemma-4-2b-medical` (or whichever model name you used)
3. Start chatting

### Deliverables for Section 7
- [ ] Screenshot: OpenWebUI running in browser with fine-tuned model name visible
- [ ] Screenshot: Sample conversation with model through the interface

---

## Repository Structure

```
cloud-project/
├── IMPLEMENTATION-TUTORIAL.md      # This file
├── CISC-886-Project-Deliverable.md # Project requirements
├── Project-Resource-Guide.md      # Resource guide
├── README.md                      # Main documentation
├── spark/                         # Section 4: EMR preprocessing
│   ├── preprocess.py              # PySpark pipeline
│   ├── eda_analysis.py            # EDA visualizations
│   ├── bootstrap_emr.sh            # EMR bootstrap
│   └── requirements.txt           # Python dependencies
├── colab/                         # Section 5: Fine-tuning
│   └── fine_tune.ipynb            # QLoRA training notebook
├── ec2/                          # Sections 6 & 7: Deployment
│   ├── setup_ollama.sh           # Ollama installation
│   ├── setup_openwebui.sh        # OpenWebUI installation
│   ├── ollama.service            # Ollama systemd
│   └── openwebui.service         # OpenWebUI systemd
└── terraform/                    # Section 2: Infrastructure
    ├── main.tf                   # VPC, subnets, IGW
    ├── variables.tf              # Input variables
    ├── outputs.tf                # Output values
    ├── provider.tf                # AWS provider
    ├── security-groups.tf        # Security groups
    ├── emr.tf                    # EMR cluster
    └── ec2.tf                    # EC2 instance
```

---

## Quick Reference: Terraform vs Operational Commands

| Component | Terraform (`terraform/`) | Operational Commands (`README.md`) |
|-----------|--------------------------|-----------------------------------|
| **VPC/Network** | Creates VPC, subnets, routing | — |
| **EMR** | Provisions EMR cluster | `aws emr create-cluster`, `spark-submit` |
| **EC2** | Provisions EC2 instance | `ssh`, `./setup_ollama.sh`, `./setup_openwebui.sh` |
| **S3** | Creates S3 bucket | `aws s3 cp`, `aws s3 sync` |

**Terraform** = Infrastructure provisioning (creates resources)
**Operational Commands** = Runtime management (uses resources)

---

## Cost Summary

| Service | Configuration | Cost |
|---------|--------------|------|
| S3 | 5GB storage | ~$0.10/month |
| EMR | m5.xlarge (1 master + 2 core, spot) | ~$0.30-0.50/hour |
| EC2 | m5.xlarge (CPU inference) | ~$0.192/hour |

**Total estimated:** ~$2-3 for entire project with proper teardown

---

## Common Issues and Solutions

### EMR Cluster Fails to Start
- Check IAM roles are correctly attached
- Verify security group allows internal communication
- Ensure bootstrap script is in S3 before cluster creation

### Out of Memory During Fine-tuning
- Reduce batch size
- Increase gradient accumulation steps
- Use 4-bit quantization (already configured)

### Ollama Model Not Loading
- Check model file exists and is valid GGUF format
- Verify sufficient disk space on EC2
- Check Ollama logs: `journalctl -u ollama -f`

### OpenWebUI Cannot Connect to Ollama
- Ensure Ollama is running: `sudo systemctl status ollama`
- Verify OLLAMA_BASE_URL environment variable
- Check security group allows port 11434

---

## Checklist: All Deliverables

### Section 1 — System Architecture (2 marks)
- [ ] Architecture diagram
- [ ] Data flow paragraph

### Section 2 — VPC & Networking (4 marks)
- [ ] Terraform files committed
- [ ] CIDR block and subnet design documented
- [ ] Security group rules documented
- [ ] Route table configuration documented

### Section 3 — Model & Dataset Selection (3 marks)
- [ ] Model name, parameters, source documented
- [ ] License documented
- [ ] Hardware requirements documented
- [ ] Dataset information documented
- [ ] Split strategy documented
- [ ] Sample data shown
- [ ] Summary statistics provided

### Section 4 — EMR + Spark (5 marks)
- [ ] PySpark script committed
- [ ] EMR cluster configuration screenshot
- [ ] EMR terminated screenshot (REQUIRED)
- [ ] S3 output files screenshot
- [ ] 3 EDA figures with captions

### Section 5 — Fine-Tuning (6 marks)
- [ ] Jupyter notebook committed
- [ ] Hyperparameter table
- [ ] Base vs Fine-tuned comparison (2 examples)

### Section 6 — EC2 Deployment (3 marks)
- [ ] Commands in README/report
- [ ] Ollama terminal screenshot
- [ ] curl API screenshot

### Section 7 — Web Interface (2 marks)
- [ ] Browser screenshot with model name
- [ ] Sample conversation screenshot

---

*Last Updated: 2026-04-29*
