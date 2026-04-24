variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "ap-south-1"
}

variable "github_repository" {
  type        = string
  description = "GitHub repo allowed to assume the deploy role (owner/repo)."
  default     = "manishdev92/NyayaSetu"

  validation {
    condition     = can(regex("^[^/]+/[^/]+$", var.github_repository))
    error_message = "github_repository must look like owner/repo"
  }
}

variable "deploy_api_service" {
  type        = bool
  description = "Create App Runner for the API (requires nyayasetu-api:latest in ECR)."
  default     = false
}

variable "deploy_web_service" {
  type        = bool
  description = "Create App Runner for the web (requires nyayasetu-web:latest in ECR)."
  default     = false

  validation {
    condition     = !var.deploy_web_service || var.deploy_api_service
    error_message = "deploy_api_service must be true when deploy_web_service is true."
  }
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key for the API container (sensitive; prefer TF_VAR_openai_api_key)."
  default     = ""
  sensitive   = true
}

variable "create_github_oidc_provider" {
  type        = bool
  description = "Set false if this account already has the GitHub OIDC provider (import it instead)."
  default     = true
}
