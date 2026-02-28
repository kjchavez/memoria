variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "twilio_auth_token" {
  description = "Twilio auth token"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic/Claude API key"
  type        = string
  sensitive   = true
}

variable "twilio_account_sid" {
  description = "Twilio account SID"
  type        = string
}

variable "batch_schedule" {
  description = "Cron schedule for nightly batch (in trip timezone)"
  type        = string
  default     = "0 2 * * *"
}

variable "batch_timezone" {
  description = "Timezone for batch schedule"
  type        = string
  default     = "Europe/London"
}
