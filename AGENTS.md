# AGENTS.md — Cloud-based Medical Chatbot

Course project (CISC 886, Queen's University). Not a production service — no CI, no test suite, no root-level package manager.

## Repository Layout

| Directory | Purpose |
|-----------|---------|
| `terraform/` | AWS infrastructure (VPC, EMR, EC2, S3, IAM). Entry point: `main.tf` + `provider.tf`. |
| `spark/` | PySpark preprocessing scripts for EMR. `preprocess.py` is the main pipeline. `requirements.txt` is **only** for EMR bootstrap deps. |
| `colab/` | Fine-tuning script (`fine_tune.py`). Originally a Colab notebook; contains hardcoded paths and `!` shell commands. |
| `ec2/` | Deployment shell scripts and systemd services for Ollama + OpenWebUI. |
| `model/` | Checkpoints, LoRA adapters, and GGUF exports. Large binaries — **do not commit** new checkpoints without updating `.gitignore`. |
| `data/` | Raw and processed medical dataset (ai-medical-dataset). |

## Infrastructure

- **Tool:** Terraform >= 1.0, AWS provider ~> 5.0
- **Region:** `us-east-1` (hardcoded default)
- **Resource naming:** Every AWS resource is prefixed with `net_id` (default: `25tfgf`). Change `terraform/variables.tf` if you are not the original owner.
- **S3 bucket:** `25tfgf-ai-medical` is hardcoded in `terraform/variables.tf`, `colab/fine_tune.py`, and `README.md`. Update all three if replicating for a different netID.

### Common Terraform Commands

```bash
cd terraform
terraform init
terraform plan -var="net_id=YOUR_NETID" -var="key_name=YOUR_KEY"
terraform apply -var="net_id=YOUR_NETID" -var="key_name=YOUR_KEY"
```

## Data Pipeline

1. **Upload bootstrap script to S3** before creating the EMR cluster:
   ```bash
   aws s3 cp spark/bootstrap_emr.sh s3://YOUR_NETID-ai-medical/
   aws s3 cp spark/bootstrap_eda.sh s3://YOUR_NETID-ai-medical/   # referenced by emr.tf
   ```

2. **Upload raw data**:
   ```bash
   aws s3 cp data/ai-medical-dataset/data/ s3://YOUR_NETID-ai-medical/raw/ --recursive
   ```

3. **Run preprocessing** via EMR step (see `README.md` for full `aws emr add-steps` command with flags).

4. **Terminate EMR immediately after preprocessing** to avoid charges:
   ```bash
   aws emr terminate-clusters --cluster-ids j-XXXXXXXX --region us-east-1
   ```
   > The course deliverable **requires** a screenshot of the cluster in Terminated state.

5. **Download processed data**:
   ```bash
   aws s3 sync s3://YOUR_NETID-ai-medical/processed/ ./data/processed/
   ```

## Fine-Tuning

- **Script:** `colab/fine_tune.py`
- **Model:** `unsloth/Llama-3.2-1B-Instruct` (note: README mentions Gemma in some places; the actual script uses Llama-3.2-1B-Instruct)
- **Dataset:** expects local Parquet files at `./data/processed/split={train,val,test}/*.parquet`
- **GPU required:** CUDA-only (`torch.cuda.is_available()` assertion at top of script)
- **Quirks:**
  - Contains a Windows-style `!dir` command near the end (`!dir ".\\cloud_project\\medical_assistant_gguf"`). Replace with `ls` or remove on Linux.
  - Hardcodes `BUCKET_NAME = '25tfgf-ai-medical'` for S3 download. Update if using a different bucket.
  - Uses `UNSIGNED` S3 config; bucket must have public access or appropriate bucket policy.
  - Idempotent: checks if final LoRA adapter already exists and skips training if found.

## Deployment

- **EC2 instance type:** `m5.xlarge` (default in `terraform/variables.tf`)
- **AMI:** Ubuntu 22.04 LTS (`ami-0b89099a7c0cba64a`)
- **Post-SSH setup:**
  ```bash
  ./ec2/setup_ollama.sh
  ./ec2/setup_openwebui.sh
  ```
- **Services:** `ollama.service` and `openwebui.service` are copied to `/etc/systemd/system/` by the setup scripts.
- **Access:** OpenWebUI at `http://<EC2_PUBLIC_IP>:8080`

## Local Development Environment

- A `venv/` directory exists locally but is **not** committed. There is no root `requirements.txt`.
- To run EDA scripts locally, install deps from `spark/requirements.txt` into your own venv.

## MCP / Agent Tooling

- `.mcp.json` configures two MCP servers: **Context7** (documentation) and **AWS MCP** (region `us-east-1`).
- `.claude/settings.local.json` contains a long permission allow-list for AWS and Terraform CLI operations.

## Git Hygiene

- **No `.gitignore` exists.** The repo currently contains large model binaries (`model/checkpoints/`, `model/final_lora/`, `model/medical_assistant_gguf/`). If you add new checkpoints, create a `.gitignore` or use `git lfs` — do not push multi-GB files to GitHub.
- SSH keys and AWS credentials are **never** committed (course security requirement).

## Documentation References

- `README.md` — high-level architecture and quick-start commands
- `IMPLEMENTATION-TUTORIAL.md` — step-by-step replication guide aligned with course deliverables
- `CISC-886-Project-Deliverable.md` — official rubric and submission requirements
- `docs/superpowers/specs/2026-04-27-medical-chatbot-design.md` — design spec explaining medical schema migration from StackOverflow Python dataset
