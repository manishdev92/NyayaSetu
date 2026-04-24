variable "aws_region" {
  description = "AWS region for ECR (e.g. ap-south-1, us-east-1)."
  type        = string
  default     = "ap-south-1"
}

variable "api_repository_name" {
  description = "ECR repository name for the FastAPI backend image."
  type        = string
  default     = "nyayasetu-api"
}

variable "web_repository_name" {
  description = "ECR repository name for the Next.js frontend image."
  type        = string
  default     = "nyayasetu-web"
}

variable "lifecycle_keep_count" {
  description = "Number of most recent images to retain per repository (older tagged images are expired)."
  type        = number
  default     = 15
}
