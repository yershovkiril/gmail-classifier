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
  description = "The cron schedule for the classify Cloud Scheduler job"
  type        = string
  default     = "*/15 * * * *"
}

variable "summary_schedule" {
  description = "The cron schedule for the summary Cloud Scheduler job"
  type        = string
  default     = "0 8 * * *"
}

variable "cleanup_schedule" {
  description = "The cron schedule for the cleanup Cloud Scheduler job"
  type        = string
  default     = "0 2 * * *"
}

variable "keep_unread_days" {
  description = "Number of days to keep classified emails unread"
  type        = string
  default     = "7"
}

variable "summary_frequency_hours" {
  description = "Number of hours to look back when generating the daily summary"
  type        = string
  default     = "24"
}

variable "gemini_api_key" {
  description = "The Developer API Key for Gemini. Set this via TF_VAR_gemini_api_key or tfvars"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER_KEY"
}
