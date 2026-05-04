# =============================================================================
# Terraform Outputs
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_1_id" {
  description = "Public Subnet 1 ID (us-east-1a)"
  value       = aws_subnet.public_1.id
}

output "public_subnet_2_id" {
  description = "Public Subnet 2 ID (us-east-1b)"
  value       = aws_subnet.public_2.id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}

output "route_table_id" {
  description = "Public Route Table ID"
  value       = aws_route_table.public.id
}

output "ec2_security_group_id" {
  description = "EC2 Security Group ID"
  value       = aws_security_group.ec2.id
}

output "emr_master_security_group_id" {
  description = "EMR Master Node Security Group ID"
  value       = aws_security_group.emr_master.id
}

output "emr_slave_security_group_id" {
  description = "EMR Slave Nodes Security Group ID"
  value       = aws_security_group.emr_slave.id
}

output "ec2_instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.ollama.id
}

output "ec2_public_ip" {
  description = "EC2 Instance Public IP"
  value       = aws_instance.ollama.public_ip
}

output "ec2_private_ip" {
  description = "EC2 Instance Private IP"
  value       = aws_instance.ollama.private_ip
}

output "emr_cluster_id" {
  description = "EMR Cluster ID"
  value       = aws_emr_cluster.main.id
}

output "emr_cluster_endpoint" {
  description = "EMR Cluster Master Node Endpoint"
  value       = aws_emr_cluster.main.master_public_dns
}

output "emr_master_public_dns" {
  description = "EMR master node public DNS hostname"
  value       = aws_emr_cluster.main.master_public_dns
}

output "s3_bucket_name" {
  description = "S3 Bucket Name for Data Storage"
  value       = aws_s3_bucket.data.bucket
}

output "s3_bucket_arn" {
  description = "S3 Bucket ARN"
  value       = aws_s3_bucket.data.arn
}

output "emr_service_role_arn" {
  description = "EMR Service Role ARN"
  value       = aws_iam_role.emr_service_role.arn
}

output "emr_instance_profile_arn" {
  description = "EMR Instance Profile ARN"
  value       = aws_iam_instance_profile.emr_instance_profile.arn
}

output "ec2_instance_profile_arn" {
  description = "EC2 Instance Profile ARN"
  value       = aws_iam_instance_profile.ec2_instance_profile.arn
}