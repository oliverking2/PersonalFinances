locals {
  public_subnet_ids  = [ for sb in aws_subnet.public  : sb.id ]
}

resource "aws_subnet" "public" {
  for_each = { for idx, az in local.azs : az => idx }
  vpc_id                  = aws_vpc.dagster.id
  cidr_block              = local.public_cidrs[each.value]
  availability_zone       = each.key
  map_public_ip_on_launch = true
  tags = { Name = "dagster-public-${each.key}" }
}

# 2 subnets (2 AZ) assigned the route table
resource "aws_route_table_association" "public_assoc" {
  for_each       = aws_subnet.public          # maps AZ → subnet resource
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public_rt.id
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "dagster-nat-${var.environment_name}"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[local.azs[0]].id
  tags = {
    Name = "dagster-nat-${var.environment_name}"
  }
}

# Public Subnet Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.dagster.id
  tags = { Name = "dagster-public-rt-${var.environment_name}" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

