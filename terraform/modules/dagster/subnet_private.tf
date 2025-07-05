locals {
  private_subnet_ids = [ for sb in aws_subnet.private : sb.id ]
}

resource "aws_subnet" "private" {
  for_each = { for idx, az in local.azs : az => idx }
  vpc_id            = aws_vpc.dagster.id
  cidr_block        = local.private_cidrs[each.value]
  availability_zone = each.key
  tags = { Name = "dagster-private-${each.key}" }
}

# 2 subnets (2 AZ) assigned the route table
resource "aws_route_table_association" "private_assoc" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_rt.id
}

# Private Subnet Route Table
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.dagster.id
  tags = { Name = "dagster-private-rt-${var.environment_name}" }
}

# route for 0.0.0.0/0 to the NAT gateway
resource "aws_route" "private_to_nat" {
  route_table_id         = aws_route_table.private_rt.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}
