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

variable "clerk_publishable_key" {
  type        = string
  description = "Clerk publishable key for the web container (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY)."
  default     = ""
  sensitive   = true
}

variable "clerk_secret_key" {
  type        = string
  description = "Clerk secret key for the web container (CLERK_SECRET_KEY)."
  default     = ""
  sensitive   = true
}

variable "create_github_oidc_provider" {
  type        = bool
  description = "Set true only on a fresh account with no token.actions.githubusercontent.com provider yet. Most accounts already have it (from GitHub Actions) — use false to avoid 409 EntityAlreadyExists."
  default     = false
}

variable "create_cloudfront_web" {
  type        = bool
  description = "When deploy_web_service is true, create a CloudFront distribution in front of the web App Runner service (default *.cloudfront.net)."
  default     = true
}

variable "web_app_public_url" {
  type        = string
  description = "Public site URL (https://) — use CloudFront URL so Next.js metadata/redirects match the browser. Baked in Docker as NEXT_PUBLIC_APP_URL; set to terraform output web_cloudfront_url after the first apply."
  default     = ""
}
