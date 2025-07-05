output "gocardless_user" {
  description = "Username for GoCardless user"
  value       = module.postgres.gocardless_user
}

output "gocardless_database" {
  description = "Database name for GoCardless"
  value       = module.postgres.gocardless_database
}

output "gocardless_password" {
  description = "Auto-generated password for GoCardless user"
  value       = module.postgres.gocardless_password
  sensitive   = true
}

output "dagster_user" {
  description = "Username for Dagster user"
  value       = module.postgres.dagster_user
}

output "dagster_database" {
  description = "Database name for Dagster"
  value       = module.postgres.dagster_database
}

output "dagster_password" {
  description = "Auto-generated password for Dagster user"
  value       = module.postgres.dagster_password
  sensitive   = true
}