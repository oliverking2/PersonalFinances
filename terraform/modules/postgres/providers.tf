provider "postgresql" {
  host            = var.postgres_host
  port            = 5432
  database        = "postgres"
  username        = var.postgres_master_username
  password        = var.postgres_master_password
  sslmode         = "disable"
}