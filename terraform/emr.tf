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
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
}

resource "aws_iam_role_policy" "emr_service_role_ec2" {
  name = "${var.net_id}-emr-service-role-ec2-policy"
  role = aws_iam_role.emr_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:AuthorizeSecurityGroupEgress",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:CancelSpotInstanceRequests",
          "ec2:CreateNetworkInterface",
          "ec2:CreateSecurityGroup",
          "ec2:CreateTags",
          "ec2:DeleteNetworkInterface",
          "ec2:DeleteSecurityGroup",
          "ec2:DeleteTags",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeAccountAttributes",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeInstances",
          "ec2:DescribeKeyPairs",
          "ec2:DescribeNetworkAcls",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeRouteTables",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSpotInstanceRequests",
          "ec2:DescribeSpotPriceHistory",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcAttribute",
          "ec2:DescribeVpcEndpoints",
          "ec2:DescribeVpcs",
          "ec2:DetachNetworkInterface",
          "ec2:ModifyImageAttribute",
          "ec2:ModifyInstanceAttribute",
          "ec2:RequestSpotInstances",
          "ec2:RevokeSecurityGroupEgress",
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "ec2:DeleteVolume",
          "ec2:DescribeVolumeStatus",
          "ec2:DescribeVolumes",
          "ec2:DetachVolume",
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListInstanceProfiles",
          "iam:ListRolePolicies",
          "iam:PassRole",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = "*"
      }
    ]
  })
}

# Create service-linked role for EC2 Spot Instances (required for EMR with spot instances)
resource "aws_iam_service_linked_role" "emr_spot" {
  aws_service_name = "spot.amazonaws.com"
  description      = "Service-linked role for EC2 Spot Instances used by EMR"
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
  policy_arn = "arn:aws:iam::aws:policy/AmazonEMRFullAccessPolicy_v2"
}

resource "aws_iam_role_policy_attachment" "emr_instance_s3_access" {
  role       = aws_iam_role.emr_instance_profile_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
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
# EMR Block Public Access Configuration
# =============================================================================

# EMR Block Public Access is enabled by default in each region.
# By default, it blocks public access on all ports except 22.
# We must explicitly permit JupyterHub (9443) and Ollama API (11434) for public access.
resource "aws_emr_block_public_access_configuration" "main" {
  block_public_security_group_rules = true

  permitted_public_security_group_rule_range {
    min_range = 22
    max_range = 22
  }

  permitted_public_security_group_rule_range {
    min_range = 9443
    max_range = 9443
  }

  permitted_public_security_group_rule_range {
    min_range = 11434
    max_range = 11434
  }
}

# =============================================================================
# EMR Security Groups (Separate for Master and Slave)
# =============================================================================

resource "aws_security_group" "emr_master" {
  name        = "${var.net_id}-emr-master-sg"
  description = "Security group for EMR master node"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 9443
    to_port     = 9443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "JupyterHub"
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "EMR internal"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = {
    Name = "${var.net_id}-emr-master-sg"
    for-use-with-amazon-emr-managed-policies = "true"
  }
}

resource "aws_security_group" "emr_slave" {
  name        = "${var.net_id}-emr-slave-sg"
  description = "Security group for EMR slave nodes"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "EMR internal"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = {
    Name = "${var.net_id}-emr-slave-sg"
    for-use-with-amazon-emr-managed-policies = "true"
  }
}

# =============================================================================
# EMR Cluster
# =============================================================================

resource "aws_emr_cluster" "main" {
  name          = "${var.net_id}-emr-cluster"
  release_label = "emr-7.2.0"
  service_role  = aws_iam_role.emr_service_role.arn

  ec2_attributes {
    subnet_id                          = aws_subnet.public_1.id
    emr_managed_master_security_group   = aws_security_group.emr_master.id
    emr_managed_slave_security_group   = aws_security_group.emr_slave.id
    instance_profile                   = aws_iam_instance_profile.emr_instance_profile.arn
    key_name                           = var.key_name
  }

  master_instance_group {
    instance_type  = var.emr_master_instance_type
    instance_count = 1
    name           = "Master"
  }

  core_instance_group {
    instance_type  = var.emr_instance_type
    instance_count = var.emr_instance_count
    name           = "Core"
  }

  configurations_json = jsonencode([
    {
      Classification = "spark-env"
      Properties = {
        PYSPARK_PYTHON = "/usr/bin/python3"
      }
    }
  ])

  bootstrap_action {
    name = "Install EDA dependencies"
    path = "s3://${var.s3_bucket_name}/bootstrap_eda.sh"
  }

  applications = ["Spark", "JupyterHub"]

  # Bootstrap action removed - no bootstrap_emr.sh in S3 bucket yet

  tags = {
    Name = "${var.net_id}-emr-cluster"
    net_id = var.net_id
  }

  termination_protection = false
  log_uri                 = "s3://${var.s3_bucket_name}/emr-logs/"

  depends_on = [
    aws_subnet.public_1,
    aws_security_group.emr_master,
    aws_security_group.emr_slave,
    aws_iam_role.emr_service_role,
    aws_iam_role_policy.emr_service_role_ec2,
    aws_iam_role.emr_instance_profile_role,
    aws_iam_instance_profile.emr_instance_profile,
    aws_iam_service_linked_role.emr_spot
  ]
}
