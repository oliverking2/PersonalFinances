module "postgres" {
  source         = "../../modules/postgres"
  db_name       = "dagster_app"
  postgres_host = module.dagster.aurora_endpoint
  postgres_master_username = module.dagster.postgres_master_username
  postgres_master_password = module.dagster.postgres_master_password
}

module "dagster" {
  source       = "../../modules/dagster"
  region = "eu-west-2"
  dagster_home = "/opt/dagster/dagster_home"
  dagster_image = "ghcr.io/oliverking2/pf-dagster:latest"
  aurora_db_username = "master_user"
  dagster_db_username = module.postgres.dagster_db_username
  dagster_db_password = module.postgres.dagster_db_password
}
