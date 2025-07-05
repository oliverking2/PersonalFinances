# Gocardless role + database
resource "postgresql_role" "gocardless" {
  name     = "gocardless"
  login    = true
  password = random_password.gocardless.result
}

resource "postgresql_database" "gocardless_db" {
  name     = "gocardless_db"
  owner    = postgresql_role.gocardless.name
  encoding = "UTF8"
}

# Dagster role + database
resource "postgresql_role" "dagster" {
  name     = "dagster"
  login    = true
  password = random_password.dagster.result
}

resource "postgresql_database" "dagster_db" {
  name     = "dagster_db"
  owner    = postgresql_role.dagster.name
  encoding = "UTF8"
}

resource "random_password" "gocardless" {
  length           = 16
}

resource "random_password" "dagster" {
  length           = 16
}