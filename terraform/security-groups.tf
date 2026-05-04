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

# EMR Block Public Access requires ports 22, 9443, 11434 to be explicitly permitted.
# Port 8080 (OpenWebUI) is allowed via block public access config below.