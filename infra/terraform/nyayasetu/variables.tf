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

variable "rag_vector_store" {
  type        = string
  description = "RAG backend: local (knowledge JSON in container) or pinecone (set PINECONE_* and run ingest). Env: RAG_VECTOR_STORE"
  default     = "local"

  validation {
    condition     = contains(["local", "pinecone"], lower(trimspace(var.rag_vector_store)))
    error_message = "rag_vector_store must be 'local' or 'pinecone'"
  }
}

variable "pinecone_api_key" {
  type        = string
  description = "Pinecone API key when RAG_VECTOR_STORE=pinecone (sensitive; prefer TF_VAR_pinecone_api_key)."
  default     = ""
  sensitive   = true
}

variable "pinecone_index" {
  type        = string
  description = "Pinecone index name (1536-dim, cosine) — see backend/docs/RAG_PINECONE_RUNBOOK.md. Env: PINECONE_INDEX"
  default     = "nyaya-legal-kb"
}

variable "pinecone_namespace" {
  type        = string
  description = "Optional Pinecone namespace; empty string uses the index default. Env: PINECONE_NAMESPACE"
  default     = ""
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
  description = "Public site URL (https://) when not using web_custom_domain — usually CloudFront https://dxxxx.cloudfront.net. Ignored when web_custom_domain is set (effective URL becomes https://<domain>)."
  default     = ""
}

variable "web_custom_domain" {
  type        = string
  description = "Optional apex hostname without scheme, e.g. nyayasetu.in. Requires a Route 53 public hosted zone for that name in this account, ACM DNS validation, and CloudFront aliases. See docs/CUSTOM_DOMAIN_IN.md."
  default     = ""

  validation {
    condition     = var.web_custom_domain == "" || can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", trimspace(var.web_custom_domain)))
    error_message = "web_custom_domain must be empty or a valid hostname (e.g. nyayasetu.in) without https://."
  }
}

variable "ingest_corpus_bucket_name" {
  type        = string
  description = "If non-empty, create a private S3 bucket for statute Markdown drops (ingest). Name must be globally unique. IAM for CI: grant s3:ListBucket (prefix) + s3:GetObject on that prefix to the key used in GitHub Actions."
  default     = ""
}
