# New ECS cluster for Dagster
resource "aws_ecs_cluster" "dagster_cluster" {
  name = "dagster_cluster"
}

resource "aws_ecs_task_definition" "dagster_daemon" {
  family                   = "dagster-daemon"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = local.task_role_arn
  execution_role_arn       = local.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "dagster-daemon"
      image     = var.dagster_image
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.log_group
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "dagster-daemon"
        }
      }
      repositoryCredentials = {
        credentialsParameter = aws_secretsmanager_secret.ghcr_pat.arn
      }
      command = ["dagster-daemon", "run", "-w", "${var.dagster_home}/workspace.yaml"]
      environment = concat(
        [
          { name = "DAGSTER_HOME", value = var.dagster_home },
          { name = "DAGSTER_POSTGRES_HOST", value = aws_rds_cluster.aurora.endpoint },
          { name = "DAGSTER_POSTGRES_USER", value = var.dagster_db_username },
          { name = "DAGSTER_POSTGRES_PASSWORD", value = var.dagster_db_password }
        ],
        var.environment
      )
      secrets = var.secrets
    }
  ])
}

resource "aws_ecs_service" "dagster_daemon" {
  name            = "dagster-daemon"
  cluster         = aws_ecs_cluster.dagster_cluster.id
  desired_count   = 1
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.dagster_daemon.arn

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.dagster_ecs.id]
    assign_public_ip = false
  }

  force_new_deployment = true
}

resource "aws_ecs_task_definition" "dagster_webserver" {
  family                   = "dagster-webserver"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  task_role_arn            = local.task_role_arn
  execution_role_arn       = local.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "dagster-webserver"
      image     = var.dagster_image
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.log_group
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "dagster-webserver"
        }
      }
      repositoryCredentials = {
        credentialsParameter = aws_secretsmanager_secret.ghcr_pat.arn
      }
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
          name          = "http"
        }
      ]
      command = ["dagster-webserver", "--host", "0.0.0.0", "--port", "80", "-w", "${var.dagster_home}/workspace.yaml"]
      environment = concat(
        [
          { name = "DAGSTER_HOME", value = var.dagster_home },
          { name = "DAGSTER_POSTGRES_HOST", value = aws_rds_cluster.aurora.endpoint },
          { name = "DAGSTER_POSTGRES_USER", value = var.dagster_db_username },
          { name = "DAGSTER_POSTGRES_PASSWORD", value = var.dagster_db_password }
        ],
        var.environment
      )
      secrets = var.secrets
    }
  ])
}

resource "aws_ecs_service" "dagster-webserver" {
  name            = "dagster-webserver"
  cluster         = aws_ecs_cluster.dagster_cluster.id
  desired_count   = 1
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.dagster_webserver.arn

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.dagster_ecs.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = [1]
    content {
      target_group_arn = local.lb_target_group_arn
      container_name   = "dagster-webserver"
      container_port   = 80
    }
  }

  force_new_deployment = true
}