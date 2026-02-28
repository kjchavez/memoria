output "webhook_url" {
  description = "URL of the webhook Cloud Run service"
  value       = "Will be set after cloud_run.tf is applied"
}

output "bucket_name" {
  description = "GCS bucket name for trip media"
  value       = "memoria-${var.project_id}"
}
