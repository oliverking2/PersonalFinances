resource "postgresql_role" "dagster_app" {
  name   = var.db_name
  login    = true
  password = random_password.dagster_db.result
}

resource "postgresql_database" "dagster_app_db" {
  name   = var.db_name
  owner  = postgresql_role.dagster_app.name
}

resource "random_password" "dagster_db" {
  length  = 16
  special = true
}