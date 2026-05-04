# Cloud-based Medical Chatbot

**Course:** CISC 886 – Cloud Computing, Queen's University

**Approach:** A — Cost-optimized hybrid (local training, minimal cloud)

A chatbot fine-tuned on medical Q&A data (ruslanmv/ai-medical-dataset), leveraging cloud infrastructure for scalable data processing and deployment while optimizing costs through local model training.

## Architecture

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
                           │   Local RTX   │      │    Browser     │
                           │   5000 (Train)│      │   (User UI)    │
                           └────────────────┘      └────────────────┘
```

Data flows from the HuggingFace AI Medical Dataset (ruslanmv/ai-medical-dataset) downloaded locally, uploaded to S3 as raw data, processed by EMR Spark into clean tokenized Parquet with length-based quality filtering, downloaded to local GPU for QLoRA fine-tuning with Gemma-4-2B, exported as GGUF to EC2, served via Ollama, and accessed through OpenWebUI in a browser.

## Pipeline

1. **Data Preparation (EMR/Spark):** Raw dataset → Spark preprocessing → Clean Parquet

2. **Model Fine-tuning (Local):** Processed Parquet → QLoRA fine-tuning → GGUF model

3. **Deployment (EC2):** GGUF model → Ollama → OpenWebUI

## Project Structure

```
cloud-project/
├── spark/                 # EMR/Spark preprocessing
│   ├── preprocess.py      # Main PySpark script
│   ├── requirements.txt   # Python dependencies
│   ├── bootstrap_emr.sh   # EMR bootstrap actions
│   └── eda_analysis.py    # EDA visualization script
├── colab/                 # Model fine-tuning
│   └── fine_tune.ipynb    # QLoRA training notebook
├── ec2/                   # EC2 deployment
│   ├── setup_ollama.sh    # Ollama installation
│   ├── setup_openwebui.sh # OpenWebUI installation
│   ├── ollama.service      # systemd service
│   └── openwebui.service   # systemd service
└── terraform/             # Infrastructure as Code
    ├── main.tf            # VPC, subnets, gateway
    ├── variables.tf       # Input variables
    ├── outputs.tf         # Output values
    ├── security-groups.tf # Security groups
    ├── emr.tf             # EMR cluster
    └── ec2.tf             # EC2 instance
```

## Quick Start

### 1. Initialize Infrastructure

```bash
cd terraform
terraform init
terraform plan -var="net_id=YOUR_NETID" -var="key_name=YOUR_KEY"
terraform apply -var="net_id=YOUR_NETID" -var="key_name=YOUR_KEY"
```

### 2. Upload Bootstrap Script to S3

```bash
aws s3 cp spark/bootstrap_emr.sh s3://YOUR_NETID-ai-medical/
```

### 3. Upload Raw Data to S3

```bash
aws s3 cp ./data/ai-medical-dataset/data/ s3://YOUR_NETID-ai-medical/raw/ --recursive
```

### 4. Create EMR Cluster

```bash
# Get values from Terraform output
VPC_ID=$(terraform output -raw vpc_id)
SUBNET_ID=$(terraform output -raw public_subnet_1_id)
S3_BUCKET="YOUR_NETID-ai-medical"
EMR_SERVICE_ROLE="YOUR_NETID-emr-service-role"
EMR_INSTANCE_PROFILE="YOUR_NETID-emr-instance-profile"

aws emr create-cluster \
  --name "YOUR_NETID-emr-cluster" \
  --release-label emr-7.2.0 \
  --instance-count 3 \
  --instance-type m5.xlarge \
  --ec2-attributes "SubnetId=${SUBNET_ID},InstanceProfile=${EMR_INSTANCE_PROFILE}" \
  --service-role "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/${EMR_SERVICE_ROLE}" \
  --bootstrap-actions "Path=s3://${S3_BUCKET}/bootstrap_emr.sh,Name=Install-dependencies" \
  --applications Name=Spark Name=JupyterHub \
  --configurations '{"Classification":"spark-env","Properties":{"PYSPARK_PYTHON":"/usr/bin/python3"}}' \
  --region us-east-1
```

### 5. Run PySpark Preprocessing

```bash
# Wait for cluster to be in WAITING state, then:
aws emr add-steps \
  --cluster-id j-XXXXXXXX \
  --steps Name=SparkPreprocessing,Type=Spark,Args=[\
    --deploy-mode,cluster,\
    --conf,spark.executor.memory=4g,\
    --conf,spark.executor.cores=2,\
    s3://YOUR_NETID-ai-medical/spark/preprocess.py,\
    --input,s3://YOUR_NETID-ai-medical/raw/,\
    --output,s3://YOUR_NETID-ai-medical/processed/,\
    --min-context-length,200,\
    --max-context-length,4096,\
    --min-question-length,20,\
    --train-ratio,0.8,\
    --val-ratio,0.1\
  ] \
  --region us-east-1
```

### 6. Terminate EMR Cluster (IMPORTANT)

```bash
# CRITICAL: Terminate immediately after preprocessing to avoid charges
aws emr terminate-clusters --cluster-ids j-XXXXXXXX --region us-east-1
```

### 7. Download Processed Data

```bash
aws s3 sync s3://YOUR_NETID-ai-medical/processed/ ./data/processed/
```

### 8. Fine-tune Model (Local RTX 5000)

```bash
cd colab
jupyter notebook fine_tune.ipynb
# Follow notebook instructions
```

### 9. Deploy to EC2

```bash
# SSH to EC2
ssh -i "YOUR_KEY.pem" ubuntu@<EC2_PUBLIC_IP>

# Run setup scripts
./setup_ollama.sh
./setup_openwebui.sh

# Transfer and load model
ollama create gemma-4-2b-medical -f /path/to/model.gguf
```

### 10. Access the Chatbot

Open browser: `http://<EC2_PUBLIC_IP>:8080`

## Cost Summary

| Service | Configuration | Estimated Cost | Duration |
|---------|--------------|----------------|----------|
| S3 | ~5GB storage | ~$0.10/month | Persistent |
| EMR | m5.xlarge (1+2 nodes, spot) | ~$0.30-0.50/hour | ~15-30 minutes |
| EC2 | m5.xlarge (4 vCPU, 16GB RAM) | ~$0.526/hour | Stop when not in use |

**Total project cost with credits:** ~$2-5 | **Tip:** Always terminate EMR after preprocessing to avoid idle charges.

## Security Considerations

- SSH key kept secure, never committed to git
- S3 bucket with versioning enabled
- EMR uses IAM instance profiles (no access keys on nodes)
- Security groups restrict traffic to necessary ports only
- Terminate EMR cluster immediately after preprocessing

## License

- **Model:** Gemma Terms — Before using Gemma, accept the license at https://huggingface.co/google/gemma-4-2b
- **Dataset:** [ruslanmv/ai-medical-dataset](https://huggingface.co/datasets/ruslanmv/ai-medical-dataset) (CC-BY 4.0)
