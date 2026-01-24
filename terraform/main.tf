terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

provider "github" {
  # The provider will use the GITHUB_TOKEN environment variable by default.
  # If you prefer, pass a token with `-var="github_token=..."` or set `TF_VAR_github_token`.
  owner = var.github_owner
}

locals {
  raw_secrets = {
    STRAVA_CLIENT_ID     = var.strava_client_id
    STRAVA_CLIENT_SECRET = var.strava_client_secret
    STRAVA_ACCESS_TOKEN  = var.strava_access_token
    STRAVA_EXPIRES_AT    = var.strava_expires_at
    STRAVA_EXPIRES_IN    = var.strava_expires_in
    STRAVA_REFRESH_TOKEN = var.strava_refresh_token
    GARMIN_TOKENS        = var.garmin_tokens
  }

  # remove empty values so we don't create blank secrets
  secrets = { for k, v in local.raw_secrets : k => v if v != "" }
}

resource "github_actions_secret" "repo_secrets" {
  for_each        = local.secrets
  repository      = var.github_repository
  secret_name     = each.key
  plaintext_value = each.value
}
