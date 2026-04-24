locals {
  api_image = "${module.ecr.api_repository_url}:latest"
  web_image = "${module.ecr.web_repository_url}:latest"
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
        runtime_environment_variables = {
          CORS_ORIGINS               = "http://localhost:3000"
          CORS_ALLOW_APPRUNNER_REGEX = "true"
          BILLING_MODE               = "none"
          RAG_VECTOR_STORE           = "local"
          EVALUATOR_DUAL_DRAFT       = "false"
          OPENAI_MODEL               = "gpt-4o-mini"
          OPENAI_API_KEY             = var.openai_api_key
          INGEST_OCR_PROVIDER        = "none"
        }
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
        port = "3000"
        runtime_environment_variables = {
          NODE_ENV = "production"
        }
      }
    }
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  depends_on = [aws_apprunner_service.api]
}
