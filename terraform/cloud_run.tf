resource "google_artifact_registry_repository" "memoria" {
  location      = var.region
  repository_id = "memoria"
  format        = "DOCKER"
}

resource "google_cloud_run_v2_service" "webhook" {
  name     = "memoria-webhook"
  location = var.region

  template {
    service_account = google_service_account.webhook.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/memoria/webhook:latest"

      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.media.name
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "TWILIO_ACCOUNT_SID"
        value = var.twilio_account_sid
      }

      env {
        name = "TWILIO_AUTH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_auth_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
}

# Allow unauthenticated access (Twilio webhooks)
resource "google_cloud_run_v2_service_iam_member" "webhook_public" {
  name     = google_cloud_run_v2_service.webhook.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "batch" {
  name     = "memoria-batch"
  location = var.region

  template {
    template {
      service_account = google_service_account.batch.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/memoria/batch:latest"

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.media.name
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name = "ANTHROPIC_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.anthropic_api_key.secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }

      timeout = "1800s"
      max_retries = 1
    }
  }
}
