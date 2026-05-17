output "webhook_url" {
  description = "URL of the webhook Cloud Run service"
  value       = google_cloud_run_v2_service.webhook.uri
}

output "bucket_name" {
  description = "GCS bucket name for trip media"
  value       = google_storage_bucket.media.name
}
