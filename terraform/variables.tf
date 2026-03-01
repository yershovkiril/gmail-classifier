variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The region to deploy resources to"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "The base name for the application resources"
  type        = string
  default     = "gmail-classifier"
}

variable "llm_provider" {
  description = "The LLM provider configuration for the application"
  type        = string
  default     = "vertexai"
}

variable "schedule" {
  description = "The cron schedule for the Cloud Scheduler job"
  type        = string
  default     = "*/15 * * * *"
}
