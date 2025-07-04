resource "random_password" "postgres_master" {
  length  = 16
  special = true
}

resource "aws_db_subnet_group" "aurora" {
  name       = "dagster-db-subnet-group-${var.environment_name}"
  subnet_ids = local.private_subnet_ids
  tags = { Name = "dagster-db-subnets-${var.environment_name}" }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier   = "dagster-aurora-${var.environment_name}"
  engine               = "aurora-postgresql"
  engine_mode          = "provisioned"        # v2
  master_username      = var.db_username
  master_password      = random_password.postgres_master.result
  db_subnet_group_name = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.db.id]
  database_name        = "dagster"

  serverlessv2_scaling_configuration {
    min_capacity             = 0           # when active, scales down to 0 ACUs
    max_capacity             = 1
    seconds_until_auto_pause = 300
  }

  tags = { Environment = var.environment_name }
}

resource "aws_rds_cluster_instance" "writer" {
  cluster_identifier  = aws_rds_cluster.aurora.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora.engine
  publicly_accessible = true
  tags = { Name = "dagster-aurora-${var.environment_name}" }
}
