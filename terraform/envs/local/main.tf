module "postgres" {
  source         = "../../modules/postgres"
  postgres_host = var.postgres_host
  postgres_master_username = var.postgres_master_username
  postgres_master_password = var.postgres_master_password
}

