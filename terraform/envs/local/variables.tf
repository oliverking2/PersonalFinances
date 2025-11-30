variable "postgres_host" {
  type        = string
  description = "PostgreSQL host"
}

variable "postgres_master_username" {
  type        = string
  description = "Master user name for the PostgreSQL provider"
}

variable "postgres_master_password" {
  type        = string
  description = "Master password for the PostgreSQL provider"
}