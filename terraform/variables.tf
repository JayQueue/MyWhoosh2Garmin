variable "github_owner" {
  description = "The GitHub owner (user or organization) that owns the repository."
  type        = string
  default     = "MarcChen"
}

variable "github_repository" {
  description = "The repository name where secrets will be created."
  type        = string
  default     = "MyWhoosh2Garmin"
}


variable "strava_client_id" {
  description = "STRAVA_CLIENT_ID from .env-temmplate"
  type        = string
}

variable "strava_client_secret" {
  description = "STRAVA_CLIENT_SECRET from .env-temmplate"
  type        = string
}

variable "strava_access_token" {
  description = "STRAVA_ACCESS_TOKEN from .env-temmplate"
  type        = string
}

variable "strava_expires_at" {
  description = "STRAVA_EXPIRES_AT from .env-temmplate"
  type        = string
}

variable "strava_expires_in" {
  description = "STRAVA_EXPIRES_IN from .env-temmplate"
  type        = string
}

variable "strava_refresh_token" {
  description = "STRAVA_REFRESH_TOKEN from .env-temmplate"
  type        = string
}

variable "garmin_tokens" {
  description = "GARMIN_TOKENS from .env-temmplate"
  type        = string
}
