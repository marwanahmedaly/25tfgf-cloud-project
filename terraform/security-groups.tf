# =============================================================================
# Security Groups
# =============================================================================

# EC2 Security Group (Ollama + OpenWebUI)
resource "aws_security_group" "ec2" {
  name        = "${var.net_id}-ec2-sg"
  description = "Security group for EC2 instance running Ollama and OpenWebUI"
  vpc_id      = aws_vpc.main.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Ollama API (port 11434)
  ingress {
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Ollama API"
  }

  # OpenWebUI (port 8080)
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "OpenWebUI"
  }

  # All egress
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.net_id}-ec2-sg"
  }
}

# EMR Security Group
resource "aws_security_group" "emr" {
  name        = "${var.net_id}-emr-sg"
  description = "Security group for EMR cluster"
  vpc_id      = aws_vpc.main.id

  # SSH access to master node
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access to EMR master"
  }

  # Spark UI
  ingress {
    from_port   = 20888
    to_port     = 20888
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Spark UI"
  }

  # JupyterHub
  ingress {
    from_port   = 9443
    to_port     = 9443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "JupyterHub"
  }

  # EMR internal communication
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "EMR internal communication"
  }

  # All egress
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.net_id}-emr-sg"
  }
}