# =============================================================================
# VPC and Networking
# =============================================================================

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.net_id}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "${var.net_id}-igw"
  }
}

# Public Subnet 1 (us-east-1a)
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[0]
  availability_zone       = var.availability_zones[0]
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.net_id}-public-subnet-1"
  }
}

# Public Subnet 2 (us-east-1b)
resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[1]
  availability_zone       = var.availability_zones[1]
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.net_id}-public-subnet-2"
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = {
    Name = "${var.net_id}-public-rt"
  }
}

# Associate Public Subnet 1 with Route Table
resource "aws_route_table_association" "public_1" {
  subnet_id         = aws_subnet.public_1.id
  route_table_id    = aws_route_table.public.id
}

# Associate Public Subnet 2 with Route Table
resource "aws_route_table_association" "public_2" {
  subnet_id         = aws_subnet.public_2.id
  route_table_id    = aws_route_table.public.id
}