module "postgres" {
  source         = "../../modules/postgres"
  db_name       = "dagster_app"
  postgres_host = ""
  postgres_master_username = ""
  postgres_master_password = ""
}
