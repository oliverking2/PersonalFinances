resource "aws_secretsmanager_secret" "ghcr_pat" {
  name        = "dagster/ghcr-pat"
  description = "GitHub PAT for pulling pf-dagster image (JSON-formatted)"
}

resource "aws_secretsmanager_secret_version" "ghcr_pat_version" {
  secret_id     = aws_secretsmanager_secret.ghcr_pat.id
  secret_string = jsonencode({
    username = var.github_user
    password = var.github_pat
  })
}