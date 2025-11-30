provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Application = "dagster-testing"
    }
  }
}