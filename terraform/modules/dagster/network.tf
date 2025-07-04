locals {
  public_subnet_ids  = [ for sb in aws_subnet.public  : sb.id ]
  private_subnet_ids = [ for sb in aws_subnet.private : sb.id ]
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Application = "dagster-test"
    }
  }
}

data "aws_availability_zones" "azs" {}

resource "aws_vpc" "dagster" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "dagster-vpc-${var.environment_name}" }
}

locals {
  # take the first two AZ names
  azs        = slice(data.aws_availability_zones.azs.names, 0, 2)
  # for public subnets: index 0 & 1; for private: same
  public_cidrs  = [
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 0),
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 1)
  ]
  private_cidrs = [
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 2),
    cidrsubnet(aws_vpc.dagster.cidr_block, 8, 3)
  ]
}


resource "aws_subnet" "public" {
  for_each = { for idx, az in local.azs : az => idx }
  vpc_id                  = aws_vpc.dagster.id
  cidr_block              = local.public_cidrs[each.value]
  availability_zone       = each.key
  map_public_ip_on_launch = true
  tags = { Name = "dagster-public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each = { for idx, az in local.azs : az => idx }
  vpc_id            = aws_vpc.dagster.id
  cidr_block        = local.private_cidrs[each.value]
  availability_zone = each.key
  tags = { Name = "dagster-private-${each.key}" }
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
  for_each       = aws_subnet.public          # maps AZ → subnet resource
  subnet_id      = each.value.id
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
  subnet_id     = aws_subnet.public[local.azs[0]].id
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
  for_each       = aws_subnet.private          # maps AZ → subnet resource
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_rt.id
}
