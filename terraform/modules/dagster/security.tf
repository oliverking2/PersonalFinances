resource "aws_security_group" "ecs_tasks" {
  name        = "dagster-ecs-sg-${var.environment_name}"
  description = "Allow all outbound"
  vpc_id      = aws_vpc.dagster.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "dagster-db-sg-${var.environment_name}"
  description = "Allow ECS tasks to talk to DB"
  vpc_id      = aws_vpc.dagster.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
