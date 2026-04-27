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
  default     = "g4dn.xlarge"
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
  description = "Number of EMR core nodes (spot)"
  type        = number
  default     = 2
}

variable "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  type        = string
  default     = "25tfgf-emr-data-bucket"
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
  default     = "25tfgf-key"
}

variable "ec2_ami_id" {
  description = "EC2 AMI ID for Ollama instance (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0c7217a1c57d5bd80"
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