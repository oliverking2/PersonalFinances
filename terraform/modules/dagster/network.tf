provider "aws" {
  region = var.region
}

data "aws_availability_zones" "azs" {}

resource "aws_vpc" "dagster" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "dagster-vpc-${var.environment_name}" }
}

# Use only the first AZ
locals {
  az = data.aws_availability_zones.azs.names[0]
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.dagster.id
  cidr_block              = cidrsubnet(aws_vpc.dagster.cidr_block, 8, 0)
  availability_zone       = local.az
  map_public_ip_on_launch = true
  tags = { Name = "dagster-public-${local.az}" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.dagster.id
  cidr_block        = cidrsubnet(aws_vpc.dagster.cidr_block, 8, 1)
  availability_zone = local.az
  tags = { Name = "dagster-private-${local.az}" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.dagster.id
  tags   = { Name = "dagster-igw-${var.environment_name}" }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.dagster.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "dagster-public-rt-${var.environment_name}" }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "dagster-nat-${var.environment_name}"
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  tags = {
    Name = "dagster-nat-${var.environment_name}"
  }
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.dagster.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
  tags = { Name = "dagster-private-rt-${var.environment_name}" }
}

resource "aws_route_table_association" "private_assoc" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private_rt.id
}
