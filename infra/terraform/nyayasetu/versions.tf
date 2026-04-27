terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # All settings are supplied with -backend-config=… (e.g. backend.s3.hcl) — see backend.s3.hcl.example
  # GitHub: Destroy AWS (Terraform) workflow uses the same S3 key your laptop migrates to.
  backend "s3" {
  }
}

provider "aws" {
  region = var.aws_region
}

# CloudFront ACM certificates must be requested in us-east-1 (AWS requirement).
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
