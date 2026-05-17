resource "google_service_account" "webhook" {
  account_id   = "memoria-webhook"
  display_name = "Memoria Webhook Handler"
}

resource "google_service_account" "batch" {
  account_id   = "memoria-batch"
  display_name = "Memoria Batch Processor"
}

# Webhook SA permissions
resource "google_project_iam_member" "webhook_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "webhook_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_secret_manager_secret_iam_member" "webhook_twilio" {
  secret_id = google_secret_manager_secret.twilio_auth_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.webhook.email}"
}

# Batch SA permissions
resource "google_project_iam_member" "batch_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_project_iam_member" "batch_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_secret_manager_secret_iam_member" "batch_anthropic" {
  secret_id = google_secret_manager_secret.anthropic_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.batch.email}"
}
