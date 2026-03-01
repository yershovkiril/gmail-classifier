terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "gmail.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry for Docker Images
resource "google_artifact_registry_repository" "repo" {
  provider      = google
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Docker repository for the AI Gmail Classifier"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# 3. Dedicated Service Account
resource "google_service_account" "agent_sa" {
  account_id   = "${var.app_name}-sa"
  display_name = "Service Account for AI Gmail Classifier"
}

# Assign roles to the SA (e.g., Vertex AI if using Gemini)
resource "google_project_iam_member" "sa_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 4. Cloud Run Job
# NOTE: The initial apply requires a valid image. We use a placeholder alpine image 
# to bootstrap, which Cloud Build will overwrite on its first CI/CD run.
resource "google_cloud_run_v2_job" "job" {
  name     = "${var.app_name}-job"
  location = var.region

  template {
    task_count  = 1
    
    template {
      max_retries = 0
      execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
      containers {
        # Deploying strictly with the latest project image natively built by Cloud Build.
        # This requires `cloudbuild.yaml` to run before `terraform apply` fully succeeds.
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/${var.app_name}-repo/gmail-agent:latest"

        env {
          name  = "LLM_PROVIDER"
          value = var.llm_provider
        }
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "KEEP_UNREAD_DAYS"
          value = var.keep_unread_days
        }
        env {
          name  = "SUMMARY_FREQUENCY_HOURS"
          value = var.summary_frequency_hours
        }
        env {
          name  = "GMAIL_CREDENTIALS_FILE"
          value = "/secrets/credentials/credentials.json"
        }
        env {
          name  = "GMAIL_TOKEN_FILE"
          value = "/secrets/token/token.json"
        }
        env {
          name = "GEMINI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gemini_api_key.secret_id
              version = "latest"
            }
          }
        }

        volume_mounts {
          name       = "credentials-volume"
          mount_path = "/secrets/credentials"
        }
        volume_mounts {
          name       = "token-volume"
          mount_path = "/secrets/token"
        }
      }
      service_account = google_service_account.agent_sa.email

      volumes {
        name = "credentials-volume"
        secret {
          secret = google_secret_manager_secret.gmail_credentials.secret_id
          items {
            version = "latest"
            path    = "credentials.json"
          }
        }
      }
      volumes {
        name = "token-volume"
        secret {
          secret = google_secret_manager_secret.gmail_token.secret_id
          items {
            version = "latest"
            path    = "token.json"
          }
        }
      }
    }
  }
  depends_on = [google_project_service.apis]

  # Ignore the image and command changes in Terraform as they will be managed by Cloud Build
  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      template[0].template[0].containers[0].command
    ]
  }
}

# 5. Cloud Scheduler Triggers
resource "google_cloud_scheduler_job" "trigger_classify" {
  name             = "${var.app_name}-trigger-classify"
  description      = "Triggers the AI Gmail Classifier to route new emails"
  schedule         = var.schedule
  time_zone        = "Etc/UTC"
  attempt_deadline = "30s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.job.name}:run"
    body        = base64encode(jsonencode({
      overrides = {
        containerOverrides = [
          {
            args = ["--mode", "classify"]
          }
        ]
      }
    }))

    oauth_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "trigger_summary" {
  name             = "${var.app_name}-trigger-summary"
  description      = "Triggers the AI Gmail Classifier to send a daily digest"
  schedule         = var.summary_schedule
  time_zone        = "Etc/UTC"
  attempt_deadline = "30s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.job.name}:run"
    body        = base64encode(jsonencode({
      overrides = {
        containerOverrides = [
          {
            args = ["--mode", "summary"]
          }
        ]
      }
    }))

    oauth_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "trigger_cleanup" {
  name             = "${var.app_name}-trigger-cleanup"
  description      = "Triggers the AI Gmail Classifier to clear unread marks"
  schedule         = var.cleanup_schedule
  time_zone        = "Etc/UTC"
  attempt_deadline = "30s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.job.name}:run"
    body        = base64encode(jsonencode({
      overrides = {
        containerOverrides = [
          {
            args = ["--mode", "cleanup"]
          }
        ]
      }
    }))

    oauth_token {
      service_account_email = google_service_account.agent_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

# Give the SA permission to invoke the Cloud Run Job
resource "google_cloud_run_v2_job_iam_member" "invoker" {
  name     = google_cloud_run_v2_job.job.name
  location = google_cloud_run_v2_job.job.location
  project  = google_cloud_run_v2_job.job.project
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 6. Secret Manager for Credentials
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "${var.app_name}-gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "gmail_credentials" {
  secret_id = "${var.app_name}-gmail-credentials"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "gmail_token" {
  secret_id = "${var.app_name}-gmail-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "sa_gemini_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "sa_credentials_access" {
  secret_id = google_secret_manager_secret.gmail_credentials.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "sa_token_access" {
  secret_id = google_secret_manager_secret.gmail_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 7. Auto-populate Secrets from local files (Optional, runs if files exist locally during `terraform apply`)
resource "google_secret_manager_secret_version" "gemini_api_key_version" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_version" "gmail_credentials_version" {
  secret      = google_secret_manager_secret.gmail_credentials.id
  secret_data = fileexists("../credentials.json") ? file("../credentials.json") : "{}"
}

resource "google_secret_manager_secret_version" "gmail_token_version" {
  secret      = google_secret_manager_secret.gmail_token.id
  secret_data = fileexists("../token.json") ? file("../token.json") : "{}"
}

# 8. Grant Cloud Build Service Account permissions to update Cloud Run jobs during CI/CD
data "google_project" "project" {}

resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cloudbuild_sa_user" {
  service_account_id = google_service_account.agent_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}
