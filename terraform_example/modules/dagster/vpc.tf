locals {
  # take the first two AZ names
  azs        = slice(data.aws_availability_zones.azs.names, 0, 2)
  # for public subnets: index 0 & 1; for private: 2 & 3
  public_cidrs  = [
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 0),
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 1)
  ]
  private_cidrs = [
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 2),
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 3)
  ]
}

data "aws_availability_zones" "azs" {}

resource "aws_vpc" "dagster" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "dagster-vpc-${var.environment_name}" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.dagster.id
  tags   = { Name = "dagster-igw-${var.environment_name}" }
}
