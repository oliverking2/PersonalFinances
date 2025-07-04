provider "aws" {
  region = "eu-west-2"
}

module "postgres" {
  source         = "../../modules/postgres"
  db_name       = "dagster_app"
  postgres_host = module.dagster.aurora_endpoint
  postgres_master_username = module.dagster.postgres_master_username
  postgres_master_password = module.dagster.postgres_master_password
}

module "dagster" {
  source       = "../../modules/dagster"
  dagster_home = ""
  dagster_image = ""
  db_username = ""
  region = ""
  dagster_db_username = module.postgres.dagster_db_username
  dagster_db_password = module.postgres.dagster_db_password
}
