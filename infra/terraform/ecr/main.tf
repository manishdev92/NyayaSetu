module "ecr" {
  source = "../modules/ecr"

  api_repository_name  = var.api_repository_name
  web_repository_name  = var.web_repository_name
  lifecycle_keep_count = var.lifecycle_keep_count
}
