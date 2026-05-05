# CISC 886 Cloud-based Conversational Chatbot — Implementation Tutorial

**Course:** CISC 886 – Cloud Computing, Queen's University
**Project:** Cloud-based Medical Chatbot (Healthcare domain)
**Model:** unsloth/Llama-3.2-1B-Instruct (Meta Llama 3.2 1B, instruction-tuned via Unsloth)
**Dataset:** ruslanmv/ai-medical-dataset (21.2M medical Q&A pairs)
**Training:** Local workstation (RTX 5000 Ada, 16 GB VRAM) with Unsloth (`/colab/fine_tune.ipynb`)
**Inference:** EC2 m5.xlarge (Ubuntu 22.04) + Ollama + OpenWebUI (Docker)

---

## Overview

This document provides a complete step-by-step implementation tutorial aligned with the CISC 886 project deliverables. Each section maps to a deliverable section in `latex/main.tex`.

### Architecture Summary

```
HuggingFace Dataset → S3 (raw) → EMR/Spark → S3 (processed) → Local Workstation (Unsloth QLoRA, 50k sample) → S3 (model artifacts) → EC2/Ollama → Browser/OpenWebUI
```

> **50k Sample Strategy:** Model fine-tuning uses 50,000 training samples and 2,500 evaluation samples from the processed dataset. This cap fits comfortably within the RTX 5000 Ada's 16 GB VRAM while still achieving meaningful domain adaptation.

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
│                                                               │Local Workstn││
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
- **Local Workstation** (RTX 5000 Ada, for fine-tuning with Unsloth)
- **Browser** (for OpenWebUI)

### Data Flow Paragraph (copy and customize):

> Data flows from the HuggingFace Medical Dataset (ruslanmv/ai-medical-dataset) downloaded locally and uploaded to S3 as raw data. The EMR Spark cluster processes this data through a PySpark pipeline that applies length-based quality filtering (context: 200–4096 chars, question: ≥20 chars), parses question/context columns, and splits into train/val/test sets stored as Parquet in S3. The processed data is downloaded to a local workstation (RTX 5000 Ada, 16 GB VRAM) where QLoRA fine-tuning is performed on `unsloth/Llama-3.2-1B-Instruct` using Unsloth. The script applies a custom medical chat template with second-person rewriting and extracts relevant sentences from clinical context. The fine-tuned LoRA adapter and GGUF export are uploaded back to S3, then deployed to an EC2 m5.xlarge instance, where Ollama serves the model and OpenWebUI provides a browser-based chat interface.

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
  default = "YOUR_KEY_NAME"  # e.g., "lab6_key_pair"
}
```

### Step 2.3: Plan and Apply

```bash
terraform plan -var="net_id=25tfgf" -var="key_name=lab6_key_pair"
terraform apply -var="net_id=25tfgf" -var="key_name=lab6_key_pair"
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

### Model Selection: unsloth/Llama-3.2-1B-Instruct

| Attribute | Value |
|-----------|-------|
| **Model Name** | unsloth/Llama-3.2-1B-Instruct |
| **Base Model** | meta-llama/Llama-3.2-1B-Instruct |
| **Parameters** | 1 billion |
| **Source** | https://huggingface.co/unsloth/Llama-3.2-1B-Instruct |
| **License** | Llama 3.2 License (requires acceptance on HuggingFace) |
| **Format** | 4-bit quantized GGUF (Q4_K_M) for QLoRA |

**Why unsloth/Llama-3.2-1B-Instruct?**
- Under 10B parameters (project requirement)
- Unsloth's optimized variant provides 2x faster training and 70% less VRAM
- Instruction-tuned (`-Instruct`) variant provides better foundation for medical fine-tuning
- Suitable for local RTX 5000 Ada (16GB VRAM) with 4-bit QLoRA (~4-5GB VRAM)
- Pre-installed dependencies via `pip install unsloth`
- Strong general-knowledge base with safety tuning for medical Q&A
- Native chat-template format supports multi-turn conversational interactions

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
- **Train:** 80% → capped at 50,000 samples for fine-tuning
- **Validation:** 10% → capped at 2,500 samples for evaluation
- **Test:** 10% → held out

**Data Leakage Prevention:** The random split ensures no data from the test set is used during training or hyperparameter tuning. Since this is a text-generation task, no external test set is required.

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
aws s3 cp spark/bootstrap_eda.sh s3://25tfgf-ai-medical/
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
  --bootstrap-actions Path=s3://25tfgf-ai-medical/bootstrap_eda.sh,Name="Install EDA dependencies" \
  --applications Name=Spark Name=JupyterHub \
  --configurations '{"Classification":"spark-env","Properties":{"PYSPARK_PYTHON":"/usr/bin/python3"}}'
```

### Step 4.3: Monitor EMR Cluster

```bash
# Check cluster status
aws emr describe-cluster --cluster-id j-XXXXXXXX --query 'Cluster.Status'

# SSH to master node (if needed)
ssh -i lab6_key_pair.pem hadoop@master-public-dns
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
  --tokenizer unsloth/Llama-3.2-1B-Instruct

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
3. **Parse** and alias `question_parsed` and `context_parsed` columns
4. **Remove** empty rows
5. **Split** into train/val/test (80/10/10)
6. **Write** partitioned Parquet to S3

> **Note:** The chat template and second-person rewriting are applied at training time in `colab/fine_tune.ipynb`, not during Spark preprocessing. The Spark pipeline outputs raw parsed question/context pairs.

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

> **Training on Local Workstation with Unsloth** — Fine-tuning is performed on a local workstation (RTX 5000 Ada, 16 GB VRAM) using the `unsloth/Llama-3.2-1B-Instruct` model with QLoRA adapters. The training notebook is at `/colab/fine_tune.ipynb`.

### Prerequisites

```bash
# Install Unsloth and dependencies
pip install unsloth transformers peft trl accelerate bitsandbytes datasets scipy boto3
```

### What the Notebook Does (`/colab/fine_tune.ipynb`)

1. **Download from S3** — Fetches processed Parquet data from `25tfgf-ai-medical/processed/`
2. **Load dataset** — Loads train/val splits as HuggingFace Dataset (50k train / 2.5k eval)
3. **Text processing** — Extracts relevant sentences and rewrites third-person clinical text to second-person direct advice
4. **Prepare prompts** — Applies Llama-3.2 chat template with medical system prompt
5. **Load model** — `unsloth/Llama-3.2-1B-Instruct` with 4-bit QLoRA
6. **Fine-tune** — 50k sample, 1 epoch, effective batch size 16
7. **Save adapter** — `./model/final_lora/` directory
8. **Export GGUF** — `./model/medical_assistant_gguf_gguf/` for Ollama
9. **Plot loss curve** — Saves training log and loss figure

### Step 5.1: Download Processed Data

```bash
# Create data directory
mkdir -p ./data/processed

# Sync from S3
aws s3 sync s3://25tfgf-ai-medical/processed/ ./data/processed/
```

### Step 5.2: Run the Training Script

```bash
cd colab
jupyter notebook fine_tune.ipynb
```

The script implements two robust mechanisms:
- **Checkpoint resumption:** If interrupted, automatically resumes from the latest `checkpoint-*` folder
- **Idempotency guard:** If `final_lora/` already contains a saved adapter, training is skipped

### Hyperparameters

| Parameter | Value |
|-----------|-------|
| Learning Rate | 2e-5 |
| Batch Size (per device) | 4 |
| Gradient Accumulation Steps | 4 |
| Effective Batch Size | 16 |
| Epochs | 1 |
| LoRA Rank (r) | 16 |
| LoRA Alpha | 16 |
| LoRA Dropout | 0 |
| LoRA Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Max Sequence Length | 1024 (training) / 512 (model load) |
| Quantization | 4-bit NF4 |
| Optimizer | adamw_8bit |
| Warmup Ratio | 0.03 |
| LR Scheduler | cosine |
| Weight Decay | 0.01 |
| Max Grad Norm | 1.0 |
| Logging Steps | 50 |
| Eval Steps | 500 |
| Save Steps | 1000 |
| Save Total Limit | 2 |

### Fine-Tuning Code (`/colab/fine_tune.ipynb`)

```python
from unsloth import FastLanguageModel
import torch

# Load Llama-3.2-1B-Instruct via Unsloth
model, tokenizer = FastLanguageModel.from_pretrained(
    "unsloth/Llama-3.2-1B-Instruct",
    max_seq_length=512,
    dtype=None,
    load_in_4bit=True,
    device_map="cuda",
)

# Configure LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# Train with SFTTrainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_data,
    eval_dataset=eval_data,
    dataset_text_field="text",
    max_seq_length=1024,
    dataset_num_proc=2,
    packing=True,
    args=TrainingArguments(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        learning_rate=2e-5,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=1000,
        save_total_limit=2,
        optim="adamw_8bit",
        seed=3407,
        output_dir="./cloud_project/checkpoints",
        report_to="none",
    ),
)

# Resume from checkpoint if available
last_checkpoint = get_last_checkpoint("./cloud_project/checkpoints")
trainer.train(resume_from_checkpoint=last_checkpoint)

# Save adapter
trainer.save_model("./cloud_project/final_lora")
tokenizer.save_pretrained("./cloud_project/final_lora")

# Export GGUF for Ollama
model.save_pretrained_gguf(
    "./cloud_project/medical_assistant_gguf",
    tokenizer,
    quantization_method="q4_k_m"
)
```

### Step 5.3: Compare Base vs Fine-tuned

Run the test cell at the end of the script to generate comparison responses:

```
BASE MODEL RESPONSE:
Question: I have a severe headache, sensitivity to light, and nausea. What could this be?
Response: [generic answer]

FINE-TUNED MODEL RESPONSE:
Question: I have a severe headache, sensitivity to light, and nausea. What could this be?
Response: [concise medical advice in second person]
```

### Step 5.4: Upload Model Artifacts to S3

```bash
# Upload LoRA adapter
aws s3 sync ./model/final_lora/ s3://25tfgf-ai-medical/models/final_lora/

# Upload GGUF for Ollama
aws s3 sync ./model/medical_assistant_gguf_gguf/ s3://25tfgf-ai-medical/models/medical_assistant_gguf_gguf/

# Upload logs and figures
aws s3 cp ./model/training_log.csv s3://25tfgf-ai-medical/models/
aws s3 cp ./model/training_loss_curve.png s3://25tfgf-ai-medical/models/
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
ssh -i lab6_key_pair.pem ubuntu@<EC2_PUBLIC_IP>
```

### Step 6.2: Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 6.3: Configure Ollama to Listen on All Interfaces

By default Ollama binds to `127.0.0.1`. OpenWebUI (running in Docker) needs to reach it.

Edit the systemd service:
```bash
sudo nano /etc/systemd/system/ollama.service
```

Add under `[Service]`:
```ini
Environment="OLLAMA_HOST=0.0.0.0"
```

Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Step 6.4: Create Ollama systemd Service (Auto-start)

```bash
sudo tee /etc/systemd/system/ollama.service > /dev/null <<'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ubuntu
Group=ubuntu
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=default.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Step 6.5: Download Model from S3

```bash
mkdir -p /home/ubuntu/model
aws s3 sync s3://25tfgf-ai-medical/models/medical_assistant_gguf_gguf/ /home/ubuntu/model/
```

### Step 6.6: Create Ollama Modelfile

Copy the committed Modelfile from the repo to the EC2 instance:

```bash
aws s3 cp s3://25tfgf-ai-medical/models/medical_assistant_gguf_gguf/Modelfile /home/ubuntu/model/Modelfile
```

The Modelfile configures the Llama 3.2 chat template, stop tokens, and generation parameters:

```dockerfile
FROM llama-3.2-1b-instruct.Q4_K_M.gguf

TEMPLATE """{{ if .Messages }}
{{- if or .System .Tools }}<|start_header_id|>system<|end_header_id|>
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

You are a helpful assistant with tool calling capabilities...
{{- end }}
{{- end }}<|eot_id|>
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if eq .Role "user" }}<|start_header_id|>user<|end_header_id|>

{{ .Content }}<|eot_id|>{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- else if eq .Role "assistant" }}<|start_header_id|>assistant<|end_header_id|>
{{- if .ToolCalls }}

{{- range .ToolCalls }}{"name": "{{ .Function.Name }}", "parameters": {{ .Function.Arguments }}}{{ end }}
{{- else }}

{{ .Content }}{{ if not $last }}<|eot_id|>{{ end }}
{{- end }}
{{- else if eq .Role "tool" }}<|start_header_id|>ipython<|end_header_id|>

{{ .Content }}<|eot_id|>{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- end }}
{{- end }}
{{- else }}
{{- if .System }}<|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|>{{ end }}{{ if .Prompt }}<|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|>{{ end }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}{{ .Response }}{{ if .Response }}<|eot_id|>{{ end }}"""

PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|eom_id|>"
PARAMETER temperature 1.5
PARAMETER min_p 0.1
```

### Step 6.7: Create and Verify Model

```bash
cd /home/ubuntu/model
ollama create medical-assistant -f Modelfile
ollama list
```

### Step 6.8: Test Ollama API

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "medical-assistant",
  "prompt": "I have a severe headache, sensitivity to light, and nausea. What could this be?",
  "stream": false
}'
```

### Step 6.9: Fix Security Group (if needed)

Ensure the EC2 security group allows:
- Port 22 (SSH) from `0.0.0.0/0`
- Port 11434 (Ollama) from `0.0.0.0/0`
- Port 8080 (OpenWebUI) from `0.0.0.0/0`

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR_SG_ID \
  --protocol tcp --port 11434 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR_SG_ID \
  --protocol tcp --port 8080 --cidr 0.0.0.0/0
```

### Deliverables for Section 6
- [ ] All commands copy-pasted verbatim in README and report
- [ ] Screenshot: Terminal showing Ollama serving `medical-assistant` model
- [ ] Screenshot: curl API response

---

## Section 7: Web Interface (2 marks)

### Step 7.1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu
```

### Step 7.2: Run OpenWebUI (Docker)

```bash
# Create volume for persistent data
docker volume create open-webui

# Run OpenWebUI container
docker run -d \
  --name openwebui \
  --restart always \
  -p 8080:8080 \
  -e OLLAMA_BASE_URL=http://172.31.84.231:11434 \
  -e ANONYMIZED_TELEMETRY=False \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
```

> **Note:** Replace `172.31.84.231` with your EC2 instance's **private IP** (check with `hostname -I`).

### Step 7.3: Verify OpenWebUI is Running

```bash
docker ps
docker logs --tail 20 openwebui
```

### Step 7.4: Access Web Interface

Open browser: `http://<EC2_PUBLIC_IP>:8080`

### Step 7.5: Configure Model

1. Create an admin account on first visit
2. Click settings → Models
3. Select `medical-assistant`
4. Start chatting

### OpenWebUI systemd Service (Optional)

For auto-start without Docker's built-in restart:

```bash
sudo tee /etc/systemd/system/openwebui.service > /dev/null <<'EOF'
[Unit]
Description=OpenWebUI Service
After=network-online.target ollama.service
Requires=ollama.service

[Service]
Type=simple
ExecStart=/usr/bin/docker run --rm --name openwebui -p 8080:8080 \
  -e OLLAMA_BASE_URL=http://172.31.84.231:11434/api \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
ExecStop=/usr/bin/docker stop openwebui
ExecStopPost=/usr/bin/docker rm openwebui
User=ubuntu
Group=ubuntu
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openwebui
sudo systemctl start openwebui
```

### Deliverables for Section 7
- [ ] Screenshot: OpenWebUI running in browser with fine-tuned model name visible
- [ ] Screenshot: Sample conversation with model through the interface

---

## Repository Structure

```
cloud-project/
├── README.md                      # This file (implementation tutorial)
├── latex/
│   └── main.tex                   # Project deliverable report (LaTeX)
├── spark/                         # Section 4: EMR preprocessing
│   ├── preprocess.py              # PySpark pipeline
│   ├── eda_analysis.py            # EDA visualizations
│   ├── bootstrap_eda.sh           # EMR bootstrap
│   └── requirements.txt           # Python dependencies
├── colab/                         # Section 5: Fine-tuning
│   └── fine_tune.ipynb            # QLoRA training notebook
├── model/                         # Exported model artifacts
│   ├── final_lora/                # LoRA adapter weights
│   ├── medical_assistant_gguf_gguf/  # GGUF export for Ollama
│   │   ├── llama-3.2-1b-instruct.Q4_K_M.gguf
│   │   └── Modelfile
│   ├── training_log.csv           # Training loss log
│   └── training_loss_curve.png    # Loss curve visualization
└── terraform/                     # Section 2: Infrastructure
    ├── main.tf                    # VPC, subnets, IGW
    ├── variables.tf               # Input variables
    ├── outputs.tf                 # Output values
    ├── provider.tf                # AWS provider
    ├── security-groups.tf         # Security groups
    ├── emr.tf                     # EMR cluster
    └── ec2.tf                     # EC2 instance
```

---

## Quick Reference: Terraform vs Operational Commands

| Component | Terraform (`terraform/`) | Operational Commands (`README.md`) |
|-----------|--------------------------|-----------------------------------|
| **VPC/Network** | Creates VPC, subnets, routing | — |
| **EMR** | Provisions EMR cluster | `aws emr create-cluster`, `spark-submit` |
| **EC2** | Provisions EC2 instance | `ssh`, `curl` install scripts, `docker run` |
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
- Reduce batch size (currently 4 per device)
- Increase gradient accumulation steps (currently 4)
- Use 4-bit quantization (already configured)
- Reduce max sequence length

### Ollama Model Not Loading
- Check model file exists and is valid GGUF format: `ollama list`
- Verify sufficient disk space on EC2: `df -h`
- Check Ollama is bound to 0.0.0.0: `sudo ss -tlnp | grep 11434`
- Check Ollama logs: `journalctl -u ollama -f`

### OpenWebUI Cannot Connect to Ollama
- Ensure Ollama is running: `sudo systemctl status ollama`
- Verify `OLLAMA_HOST=0.0.0.0` is set in the systemd service
- Use EC2 **private IP** in `OLLAMA_BASE_URL`, not localhost
- Check security group allows port 11434 from EC2's own security group
- Check security group allows port 8080 from `0.0.0.0/0`

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
- [x] Jupyter notebook committed (`colab/fine_tune.ipynb`)
- [x] Hyperparameter table
- [x] Base vs Fine-tuned comparison (3 examples)
- [x] Training loss curve

### Section 6 — EC2 Deployment (3 marks)
- [x] Commands in README/report
- [ ] Ollama terminal screenshot
- [ ] curl API screenshot

### Section 7 — Web Interface (2 marks)
- [ ] Browser screenshot with model name
- [ ] Sample conversation screenshot

---

*Last Updated: 2026-05-04*
