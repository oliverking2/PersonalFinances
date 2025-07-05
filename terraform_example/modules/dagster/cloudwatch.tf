locals {
  log_group =  aws_cloudwatch_log_group.ecs_task_log_group[0].name
}

resource "aws_cloudwatch_log_group" "ecs_task_log_group" {
  count = 1
  name_prefix = "/ecs/dagster-"
  retention_in_days = 7
}