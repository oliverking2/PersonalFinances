provider "postgresql" {
  host            = var.postgres_host
  port            = 5432
  database        = "postgres"                   # or the initial DB you specified
  username        = var.postgres_master_username              # your master user
  password        = var.postgres_master_password
  sslmode         = "require"
}