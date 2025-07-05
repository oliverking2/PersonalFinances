output "dagster_role_name" {
  description = "Name of the PostgreSQL role that was created"
  value       = postgresql_role.dagster_app.name
}

output "dagster_db_username" {
  description = "Name of the PostgreSQL database that was created"
  value       = postgresql_database.dagster_app_db.name
}

output "dagster_db_password" {
  description = "Generated password for the dagster_app role"
  value       = random_password.dagster_db.result
  sensitive   = true
}

output "dagster_db_name" {
  value = var.db_name
}