output "gocardless_user" {
  description = "Username for GoCardless user"
  value       = postgresql_role.gocardless.name
}

output "gocardless_database" {
  description = "Database name for GoCardless"
  value       = postgresql_database.gocardless_db.name
}

output "gocardless_password" {
  description = "Auto-generated password for GoCardless user"
  value       = random_password.gocardless.result
  sensitive   = true
}

output "dagster_user" {
  description = "Username for Dagster user"
  value       = postgresql_role.dagster.name
}

output "dagster_database" {
  description = "Database name for Dagster"
  value       = postgresql_database.dagster_db.name
}

output "dagster_password" {
  description = "Auto-generated password for Dagster user"
  value       = random_password.dagster.result
  sensitive   = true
}
