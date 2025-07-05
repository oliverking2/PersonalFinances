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
  value = var.aurora_db_username
}
output "postgres_master_password" {
  value = random_password.postgres_master.result
}