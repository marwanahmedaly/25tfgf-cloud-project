# =============================================================================
# EC2 Instance for Ollama
# =============================================================================

resource "aws_instance" "ollama" {
  ami           = var.ec2_ami_id
  instance_type = var.ec2_instance_type
  key_name      = var.key_name

  subnet_id = aws_subnet.public_1.id

  vpc_security_group_ids = [aws_security_group.ec2.id]

  iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name

  root_block_device {
    volume_type = "gp3"
    volume_size = 100
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update -y
              apt-get upgrade -y
              echo "Ollama EC2 instance initialized"
              EOF

  tags = {
    Name = "${var.net_id}-ollama-ec2"
    net_id = var.net_id
  }
}

resource "aws_iam_role" "ec2_instance_role" {
  name = "${var.net_id}-ec2-instance-role"

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
    Name = "${var.net_id}-ec2-instance-role"
  }
}

resource "aws_iam_role_policy_attachment" "ec2_s3_access" {
  role       = aws_iam_role.ec2_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "${var.net_id}-ec2-instance-profile"
  role = aws_iam_role.ec2_instance_role.name

  tags = {
    Name = "${var.net_id}-ec2-instance-profile"
  }
}