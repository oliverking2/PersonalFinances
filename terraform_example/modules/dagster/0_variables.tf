variable "region" {
  description = "The AWS region."
  type        = string
}

variable "dagster_image" {
  description = "Docker image for Dagster services."
  type        = string
}

variable "dagster_home" {
  description = "Directory with dagster.yaml"
  type        = string
}

variable "environment" {
  description = "List of environment variables for ECS tasks."
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "secrets" {
  description = "List of secrets to pass to the ECS task as environment variables."
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []
}

variable "aurora_db_username" {
  description = "Master username for Aurora"
  type        = string
}

variable "environment_name" {
  description = "Tag value for Environment"
  type        = string
  default     = "dev"
}

variable "dagster_db_name" {
  description = "Dagster DB Name"
  type        = string
}

variable "dagster_db_username" {
  description = "Username for connecting to Dagster"
  type        = string
}

variable "dagster_db_password" {
  description = "Password for connecting to Dagster"
  type        = string
}

variable "github_user" {
  description = "GitHub username for GHCR auth"
  type        = string
}

variable "github_pat" {
  type        = string
  description = "GitHub Personal Access Token with read:packages scope"
  sensitive   = true
}