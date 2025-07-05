resource "aws_security_group" "aurora_db" {
  name        = "dagster-db-sg-${var.environment_name}"
  description = "Allow ECS tasks to talk to DB"
  vpc_id      = aws_vpc.dagster.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.dagster_ecs.id]
  }
}

resource "aws_security_group" "dagster_alb" {
  name_prefix = "dagster-alb-sg-"
  vpc_id      = aws_vpc.dagster.id

  ingress {
    description = "Allow HTTP from my IP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "dagster_ecs" {
  name_prefix = "dagster-sg-"
  vpc_id      = aws_vpc.dagster.id

  # Allow traffic for webserver (HTTP) from ALB
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.dagster_alb.id]
  }

  # Allow traffic for gRPC services (from other containers)
  ingress {
    from_port   = 4000
    to_port     = 4000
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.dagster.cidr_block]
  }

  # Egress allows all outbound traffic (common default)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}