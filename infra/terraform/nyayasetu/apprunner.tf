locals {
  api_image = "${module.ecr.api_repository_url}:latest"
  web_image = "${module.ecr.web_repository_url}:latest"
  # Browsers on CloudFront send Origin: https://<id>.cloudfront.net — include it so API CORS allows the app.
  api_cors_origins = join(
    ",",
    var.web_app_public_url != "" ? ["http://localhost:3000", var.web_app_public_url] : ["http://localhost:3000"]
  )
  # Runtime (server) sees App Runner host; this aligns env with the URL users & Clerk should use (e.g. CloudFront).
  web_app_runtime_env = merge(
    {
      NODE_ENV                          = "production"
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = var.clerk_publishable_key
      CLERK_SECRET_KEY                  = var.clerk_secret_key
    },
    var.web_app_public_url != "" ? { NEXT_PUBLIC_APP_URL = var.web_app_public_url } : {}
  )
}

resource "aws_apprunner_service" "api" {
  count        = var.deploy_api_service ? 1 : 0
  service_name = "nyayasetu-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    auto_deployments_enabled = true

    image_repository {
      image_identifier      = local.api_image
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = merge(
          {
            CORS_ORIGINS               = local.api_cors_origins
            CORS_ALLOW_APPRUNNER_REGEX = "true"
            BILLING_MODE               = "none"
            RAG_VECTOR_STORE           = lower(trimspace(var.rag_vector_store))
            EVALUATOR_DUAL_DRAFT       = "false"
            OPENAI_MODEL               = "gpt-4o-mini"
            OPENAI_API_KEY             = var.openai_api_key
            INGEST_OCR_PROVIDER        = "none"
          },
          lower(trimspace(var.rag_vector_store)) == "pinecone"
          ? {
            PINECONE_API_KEY   = var.pinecone_api_key
            PINECONE_INDEX     = var.pinecone_index
            PINECONE_NAMESPACE = var.pinecone_namespace
          }
          : {}
        )
      }
    }
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  lifecycle {
    precondition {
      condition = lower(trimspace(var.rag_vector_store)) != "pinecone" || (
        length(trimspace(var.pinecone_api_key)) > 0 && length(trimspace(var.pinecone_index)) > 0
      )
      error_message = "When rag_vector_store=pinecone, set TF_VAR_pinecone_api_key and a non-empty TF_VAR_pinecone_index (see backend/docs/RAG_PINECONE_RUNBOOK.md)."
    }
  }
}

resource "aws_apprunner_service" "web" {
  count        = var.deploy_web_service ? 1 : 0
  service_name = "nyayasetu-web"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    auto_deployments_enabled = true

    image_repository {
      image_identifier      = local.web_image
      image_repository_type = "ECR"

      image_configuration {
        port                          = "3000"
        runtime_environment_variables = local.web_app_runtime_env
      }
    }
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  lifecycle {
    precondition {
      condition     = !var.deploy_web_service || (length(var.clerk_secret_key) > 0 && length(var.clerk_publishable_key) > 0)
      error_message = "Set TF_VAR_clerk_secret_key and TF_VAR_clerk_publishable_key (Clerk) when deploy_web_service is true — the Next.js app requires them."
    }
  }

  depends_on = [aws_apprunner_service.api]
}
