# Cloud-based StackOverflow Python Chatbot — Design Spec

**Date:** 2026-04-27
**Project:** CISC 886 – Cloud Computing, Queen's University
**Approach:** A — Cost-optimized hybrid (local training, minimal cloud)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │     S3      │───▶│   EMR       │───▶│    S3        │    │   EC2       │ │
│  │ (raw data)  │    │ (Spark)     │    │ (processed)  │───▶│ (Ollama +   │ │
│  └─────────────┘    └─────────────┘    └──────────────┘    │  OpenWebUI) │ │
│                                                             └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │                      │
                                    ▼                      ▼
                           ┌────────────────┐      ┌────────────────┐
                           │   Local RTX    │      │    Browser     │
                           │   5000 (Train) │      │   (User UI)    │
                           └────────────────┘      └────────────────┘
```

**Pipeline:** Raw dataset (S3) → EMR Spark preprocessing → Processed data (S3) → Local QLoRA fine-tuning → GGUF model → EC2 Ollama + OpenWebUI

---

## Phase 1 — Data Preparation (Section 4: EMR + Spark)

**5 marks — must include screenshots of cluster running AND terminated**

### Infrastructure
- **S3 bucket:** `q1abc-so-python/` (replace q1abc with actual netID)
  - `raw/` — uploaded raw dataset
  - `processed/` — cleaned, tokenized output
- **EMR cluster:** `q1abc-emr-spark`
  - Instance type: m5.xlarge (1 master + 2 core nodes)
  - Region: us-east-1
  - EMR release: 7.x (latest stable)
  - Use spot instances for core nodes to reduce cost

### Preprocessing Pipeline (PySpark)
1. Read raw arrow files from S3 (`q1abc-so-python/raw/`)
2. Filter by answer_score (keep Q&A pairs with score >= 1)
3. Parse question_body and answer_body fields
4. Tokenize using HuggingFace tokenizers, truncate to 512 tokens
5. Add prompt template: `"### Question: {question}\n### Answer: {answer}\n"`
6. Split into train/val/test (80/10/10), stratified by tags
7. Save as Parquet to `q1abc-so-python/processed/`

### Deliverables (Section 4)
- [ ] PySpark script committed to GitHub with inline comments
- [ ] EMR console screenshot: cluster configuration visible
- [ ] EMR console screenshot: cluster in Terminated state (REQUIRED)
- [ ] S3 console screenshot: processed output files visible
- [ ] 3 EDA figures (token length distribution, answer score histogram, split distribution) with captions

### Data Flow
Raw arrow files (2.9 GB, ~987K examples) → EMR cluster → Cleaned Parquet (~500K examples after filtering) → S3

---

## Phase 2 — Model Fine-Tuning (Section 5)

**6 marks**

### Model
- **Base model:** Gemma-4-2B from HuggingFace
  - Link: https://huggingface.co/google/gemma-4-2b
  - Parameters: 2 billion
  - License: Gemma Terms (check HuggingFace for acceptance requirement)
  - Format: 4-bit GGUF for QLoRA

### Dataset
- **Source:** koutch/stackoverflow_python from HuggingFace
- **Split:** After Spark preprocessing — 80% train, 10% val, 10% test
- **Avoiding leakage:** No data from test set used during training or validation hyperparameter tuning

### Training (Local RTX 5000)
- **Library:** Unsloth (or direct transformers + peft)
- **Technique:** QLoRA (4-bit quantization, LoRA adapter)
- **Adapter config:** rank=16, alpha=32, target modules: q_proj, k_proj, v_proj, o_proj
- **Hardware:** RTX 5000 (8GB VRAM), 4-bit quantization, gradient accumulation

### Hyperparameters
| Parameter | Value |
|-----------|-------|
| Learning rate | 2e-4 |
| Batch size | 2 |
| Gradient accumulation steps | 16 |
| Epochs | 3 |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Quantization | 4-bit |
| Max sequence length | 512 |

### Deliverables (Section 5)
- [ ] Runnable Jupyter notebook (.ipynb) committed to GitHub with inline explanation
- [ ] Hyperparameter table in report
- [ ] 2 example prompts: base model response vs fine-tuned model response (side-by-side)
- [ ] Optional: training loss curve, side-by-side comparison screenshot

### Data Flow
Processed Parquet (S3) → Download to local → Gemma-4-2B QLoRA fine-tuning → Merged GGUF → Ready for Ollama

---

## Phase 3 — EC2 Deployment (Section 6)

**3 marks**

### EC2 Instance
- **Instance type:** g4dn.xlarge (T4 GPU, 16GB VRAM, 4 vCPU, 16GB RAM)
- **AMI:** Ubuntu 22.04 LTS (Ubuntu Server 22.04)
- **Region:** us-east-1
- **Resource naming:** q1abc-ollama, q1abc-ec2, q1abc-sg (replace q1abc with actual netID)

### Installation Commands
```bash
# SSH into EC2
ssh -i "25tfgf-key.pem" ubuntu@<ec2-public-ip>

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Create systemd service for auto-start
sudo nano /etc/systemd/system/ollama.service
# Add: [Unit], [Service], [Install] sections with ExecStart=/usr/local/bin/ollama serve

# Transfer GGUF model (from local or S3)
# Option A: scp
scp -i "25tfgf-key.pem" gemma-4-2b.gguf ubuntu@<ec2-public-ip>:/home/ubuntu/
# Option B: aws s3 cp
aws s3 cp s3://q1abc-so-python/models/gemma-4-2b.gguf /home/ubuntu/

# Load model in Ollama
ollama create gemma-4-2b -f /home/ubuntu/gemma-4-2b.gguf

# Test API
curl http://localhost:11434/api/generate -d '{"model":"gemma-4-2b","prompt":"How do I sort a list in Python?"}'
```

### Deliverables (Section 6)
- [ ] All commands copy-pasted verbatim in README and report
- [ ] Terminal screenshot: Ollama serving Gemma-4-2B with model name visible
- [ ] Screenshot: curl call to API with response shown

---

## Phase 4 — Web Interface (Section 7)

**2 marks**

### OpenWebUI Setup
- Install via Docker: `docker run -d -p 8080:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main`
- Or pip: `pip install open-webui`
- Configure to connect to Ollama at `http://localhost:11434`
- Create systemd service for auto-start on reboot

### Access
- Browser: `http://<ec2-public-ip>:8080`
- Security group must allow port 8080 from 0.0.0.0/0

### Deliverables (Section 7)
- [ ] Screenshot: OpenWebUI running in browser with fine-tuned model name visible
- [ ] Screenshot: Sample conversation with model through the interface

---

## Section 2 — VPC & Networking

**4 marks**

### VPC Configuration
- **Name:** q1abc-vpc
- **CIDR:** 10.0.0.0/16
- **Region:** us-east-1

### Subnets
| Subnet | CIDR | AZ | Purpose |
|--------|------|-----|---------|
| q1abc-public-subnet-1 | 10.0.1.0/24 | us-east-1a | EC2, EMR master |
| q1abc-public-subnet-2 | 10.0.2.0/24 | us-east-1b | EMR core (HA) |

### Internet Gateway
- **Name:** q1abc-igw
- Attached to q1abc-vpc
- Route table: 0.0.0.0/0 → igw-xxxxx

### Route Tables
- **Public route table:** 10.0.0.0/16 → local, 0.0.0.0/0 → igw-xxxxx
- **Enable:** Auto-assign public IP for instances in public subnets

### Security Groups
**q1abc-sg (EC2/Ollama):**
| Port | Source | Purpose |
|------|--------|---------|
| 22 | 0.0.0.0/0 | SSH |
| 80 | 0.0.0.0/0 | HTTP |
| 443 | 0.0.0.0/0 | HTTPS |
| 11434 | 0.0.0.0/0 | Ollama API |
| 8080 | 0.0.0.0/0 | OpenWebUI |

**q1abc-sg-emr (EMR):**
| Port | Source | Purpose |
|------|--------|---------|
| 22 | 0.0.0.0/0 | SSH |
| 9443 | 0.0.0.0/0 | EMR console |

### Justification
- Port 22 open for SSH access (required for setup and debugging)
- Ports 80/443 open for web traffic (OpenWebUI)
- Port 11434 for Ollama API (internal access, but open for simplicity)
- Port 8080 for OpenWebUI browser access

---

## Section 1 — System Architecture Diagram

Create a draw.io/Lucidchart diagram showing:
1. VPC boundary containing all AWS resources
2. S3 bucket with raw and processed folders
3. EMR cluster (master + 2 core nodes)
4. EC2 instance with Ollama + OpenWebUI
5. Local RTX 5000 for training
6. Browser arrow pointing to EC2

**Data flow paragraph:**
Data flows from the HuggingFace dataset (koutch/stackoverflow_python) downloaded locally, uploaded to S3 as raw data, processed by EMR Spark into clean tokenized Parquet, downloaded to local RTX 5000 for QLoRA fine-tuning with Gemma-4-2B, exported as GGUF to EC2, served via Ollama, and accessed through OpenWebUI in a browser.

---

## Cost Summary

| Service | Instance/Config | Cost (approx.) |
|---------|----------------|----------------|
| S3 | ~5GB storage | ~$0.10/month |
| EMR | m5.xlarge 1 master + 2 core, spot | ~$0.30-0.50/hour |
| EC2 | g4dn.xlarge | ~$0.526/hour |
| **Total ( EMR ~2hrs + EC2 ~3hrs)** | | ~$2-3 total |

With AWS credits this is very affordable. EMR should be terminated immediately after preprocessing.

---

## GitHub Repository Structure

```
cloud-project/
├── CISC-886-Project-Deliverable.md
├── Project-Resource-Guide.md
├── README.md
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-27-chatbot-design.md
├── spark/
│   ├── preprocess.py
│   ├── requirements.txt
│   └── bootstrap_emr.sh
├── colab/
│   └── fine_tune.ipynb
├── ec2/
│   ├── setup_ollama.sh
│   ├── setup_openwebui.sh
│   ├── ollama.service
│   └── openwebui.service
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── security-groups.tf
```