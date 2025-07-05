variable "github_user" {
  description = "GitHub username for GHCR auth"
  type        = string
}

variable "github_pat" {
  description = "GitHub Personal Access Token for GHCR pulls"
  type        = string
  sensitive   = true
}