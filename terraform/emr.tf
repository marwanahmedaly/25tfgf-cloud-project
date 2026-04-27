# =============================================================================
# S3 Bucket for Data Storage
# =============================================================================

resource "aws_s3_bucket" "data" {
  bucket = var.s3_bucket_name

  tags = {
    Name = "${var.net_id}-ai-medical-bucket"
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# IAM Roles for EMR
# =============================================================================

# EMR Service Role
resource "aws_iam_role" "emr_service_role" {
  name = "${var.net_id}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "elasticmapreduce.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.net_id}-emr-service-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_service_role_policy" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMR-ServicePolicy"
}

# EMR Instance Profile Role
resource "aws_iam_role" "emr_instance_profile_role" {
  name = "${var.net_id}-emr-instance-profile-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.net_id}-emr-instance-profile-role"
  }
}

resource "aws_iam_role_policy_attachment" "emr_instance_profile_policy" {
  role       = aws_iam_role.emr_instance_profile_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMR_EC2_DefaultRole_v2"
}

# EMR Instance Profile
resource "aws_iam_instance_profile" "emr_instance_profile" {
  name = "${var.net_id}-emr-instance-profile"
  role = aws_iam_role.emr_instance_profile_role.name

  tags = {
    Name = "${var.net_id}-emr-instance-profile"
  }
}

# =============================================================================
# EMR Cluster
# =============================================================================

resource "aws_emr_cluster" "main" {
  name          = "${var.net_id}-emr-cluster"
  release_label = "emr-7.2.0"
  region        = var.region
  service_role  = aws_iam_role.emr_service_role.arn

  ec2_attributes {
    subnet_id                        = aws_subnet.public_1.id
    emr_managed_master_security_group = aws_security_group.emr.id
    emr_managed_slave_security_group  = aws_security_group.emr.id
    instance_profile                 = aws_iam_instance_profile.emr_instance_profile.arn
  }

  master_instance_group {
    instance_type = var.emr_master_instance_type
    instance_count = 1
    market        = "ON_DEMAND"
    name          = "Master"
  }

  core_instance_group {
    instance_type = var.emr_instance_type
    instance_count = var.emr_instance_count
    market        = "SPOT"
    bid_price     = "0.30"
    name          = "Core"
  }

  configuration {
    classification = "spark-env"
    properties = {
      PYSPARK_PYTHON = "/usr/bin/python3"
    }
  }

  applications = ["Spark", "JupyterHub"]

  bootstrap_action {
    path = "s3://${var.s3_bucket_name}/bootstrap_emr.sh"
    name = "Setup Hive"
  }

  tags = {
    Name = "${var.net_id}-emr-cluster"
    net_id = var.net_id
  }

  termination_protection = false
  visible_to_all_users   = true
  log_uri                = "s3://${var.s3_bucket_name}/emr-logs/"

  depends_on = [
    aws_subnet.public_1,
    aws_security_group.emr,
    aws_iam_role.emr_service_role,
    aws_iam_role.emr_instance_profile_role,
    aws_iam_instance_profile.emr_instance_profile
  ]
}