output "dagster_db_username" {
  description = "Name of the PostgreSQL database that was created"
  value       = module.postgres.dagster_db_username
}

output "dagster_db_password" {
  description = "Generated password for the dagster_app role"
  value       = module.postgres.dagster_db_password
  sensitive   = true
}

output "aurora_endpoint" {
  value = module.dagster.aurora_endpoint
}

output "aurora_reader_endpoint" {
  value = module.dagster.aurora_reader_endpoint
}

output "dagster_webserver_lb_dns_name" {
  description = "DNS name of the Dagster webserver load-balancer"
  value       = module.dagster.dagster_webserver_lb_dns_name
}

output "postgres_master_username" {
  value = module.dagster.postgres_master_username
}

output "postgres_master_password" {
  value = module.dagster.postgres_master_password
  sensitive = true
}
