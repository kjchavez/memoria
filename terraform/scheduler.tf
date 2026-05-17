resource "google_cloud_scheduler_job" "nightly_batch" {
  name             = "memoria-nightly-batch"
  schedule         = var.batch_schedule
  time_zone        = var.batch_timezone
  attempt_deadline = "1800s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/memoria-batch:run"

    oauth_token {
      service_account_email = google_service_account.batch.email
    }
  }
}

resource "google_project_iam_member" "batch_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.batch.email}"
}
