output "region" {
  description = "AWS Region"
  value = var.region
}

output "security_group_id" {
  description = "Security Group ID for Dagster"
  value       = aws_security_group.dagster.id
}

output "task_role_arn" {
  description = "Task Role ARN for Dagster"
  value       = local.task_role_arn
}

output "log_group_name" {
  description = "CloudWatch log group name for Dagster"
  value       = local.log_group
}

output "vpc_id" {
  value = aws_vpc.dagster.id
}

output "public_subnet_id" {
  value = aws_subnet.public.id
}

output "private_subnet_id" {
  value = aws_subnet.private.id
}

output "aurora_endpoint" {
  value = aws_rds_cluster.aurora.endpoint
}

output "aurora_reader_endpoint" {
  value = aws_rds_cluster.aurora.reader_endpoint
}

output "dagster_webserver_lb_dns_name" {
  description = "DNS name of the Dagster webserver load-balancer"
  value       = aws_lb.dagster_webserver[0].dns_name
}

output "postgres_master_username" {
  value = var.db_username
}
output "postgres_master_password" {
  value = random_password.postgres_master.result
}