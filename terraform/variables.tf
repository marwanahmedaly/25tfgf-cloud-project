# =============================================================================
# Terraform Variables
# =============================================================================

variable "net_id" {
  description = "Queen's netID for resource prefix"
  type        = string
  default     = "25tfgf"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "ec2_instance_type" {
  description = "EC2 instance type for Ollama"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_instance_type" {
  description = "EMR core node instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_master_instance_type" {
  description = "EMR master node instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_instance_count" {
  description = "Number of EMR core nodes"
  type        = number
  default     = 2
}

variable "emr_spot_bid_price" {
  description = "Bid price for EMR spot instances (as a percentage of on-demand)"
  type        = string
  default     = "0.30"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for medical dataset storage"
  type        = string
  default     = "25tfgf-ai-medical"
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
  default     = "lab6_key_pair"
}

variable "ec2_ami_id" {
  description = "EC2 AMI ID for Ollama instance (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0b89099a7c0cba64a"
}

variable "db_subnet_cidrs" {
  description = "CIDR blocks for database subnets (for future use)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "db_subnet_availability_zones" {
  description = "Availability zones for database subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}